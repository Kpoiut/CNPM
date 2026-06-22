"""
Map Intelligence API — Location picker backend for the prediction page.

Cung cấp trải nghiệm "chọn vị trí trên bản đồ" kiểu Google Maps mà KHÔNG cần
Google Maps API key:

- /api/map/search       → proxy Nominatim (OpenStreetMap) để tìm địa chỉ/dự án
- /api/map/reverse      → tọa độ → địa chỉ + map về quận trong scope ML
- /api/map/location-context → gói dữ liệu đầy đủ cho modal:
      * địa chỉ + quận/phường (reverse geocode)
      * BĐS gần nhất trong DB (Haversine)
      * tóm tắt giá/m² khu vực
      * HỒ SƠ IoT tự sinh từ tọa độ (noise/temp/humidity/light/area_quality)
      * "prefill" để tự điền form dự đoán → giảm tối đa việc nhập tay

Nguyên tắc:
- Frontend KHÔNG gọi thẳng Nominatim. Mọi request đi qua backend để kiểm soát
  rate-limit (Nominatim: tối đa ~1 req/s) + gắn User-Agent định danh + cache.
- BĐS gần chỉ là dữ liệu THAM KHẢO/ngữ cảnh. Giá cuối cùng vẫn do model dự đoán.
"""

from __future__ import annotations

import math
import time
import threading
import json
import os
import queue
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.backend.deps import get_db
from src.backend.models import Property
from src.backend.iot_engine import IoTDataEngine, DISTRICT_BOUNDS, NOISE_PROFILES
from src.config.province_config import SCOPE_DISTRICTS

router = APIRouter(prefix="/api/map", tags=["Map Intelligence"])

# ---------------------------------------------------------------------------
# Nominatim config
# ---------------------------------------------------------------------------
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
# Nominatim usage policy yêu cầu User-Agent định danh ứng dụng.
NOMINATIM_HEADERS = {
    "User-Agent": "RealEstateAVM-VN/1.0 (academic project; map location picker)",
    "Accept-Language": "vi,en",
}
NOMINATIM_TIMEOUT = 5.0

# Chỉ 6 quận nằm trong scope ML (Hà Nội + TP.HCM)
ML_SCOPE_PROVINCES = ("Hà Nội", "TP. Hồ Chí Minh")

# Token nhận diện quận từ chuỗi địa chỉ Nominatim (có + không dấu)
SCOPE_DISTRICT_TOKENS: Dict[str, List[str]] = {
    "Quận Cầu Giấy": ["cầu giấy", "cau giay"],
    "Quận Thanh Xuân": ["thanh xuân", "thanh xuan"],
    "Quận Đống Đa": ["đống đa", "dong da"],
    "Quận 7": ["quận 7", "quan 7", "district 7"],
    "Quận Bình Thạnh": ["bình thạnh", "binh thanh"],
    "Quận Tân Bình": ["tân bình", "tan binh"],
}

PROVINCE_TOKENS: Dict[str, List[str]] = {
    "Hà Nội": ["hà nội", "ha noi", "hanoi"],
    "TP. Hồ Chí Minh": ["hồ chí minh", "ho chi minh", "sài gòn", "sai gon", "saigon"],
}

# DB property_type (lowercase) ↔ frontend property type key
DB_TYPE_TO_FORM = {
    "house": "house",
    "apartment": "apartment",
    "land": "land",
    "townhouse": "townhouse",
    "villa": "villa",
}

# legal_status (DB) → ownership_type code dùng trong form
LEGAL_TO_OWNERSHIP = {
    "ownership_certificate": "FULL_OWNERSHIP",
    "land_use_right_certificate": "LURC",
    "pending": "PENDING",
    "other": "OTHER",
}


# ---------------------------------------------------------------------------
# Tiny TTL cache (in-memory) — bảo vệ Nominatim khỏi spam
# ---------------------------------------------------------------------------
_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_TTL = 60 * 30  # 30 phút


def _cache_get(key: str) -> Optional[Any]:
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > _CACHE_TTL:
            _CACHE.pop(key, None)
            return None
        return value


def _cache_set(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Snapshot cache — nạp gọn các cột cần cho geo/IoT 1 lần, tái dùng nhiều request
# (tránh hydrate hàng nghìn ORM object mỗi lần gọi → nhanh hơn nhiều)
# ---------------------------------------------------------------------------
from types import SimpleNamespace

_SNAP_LOCK = threading.Lock()
_SNAP: Dict[str, Any] = {"ts": 0.0, "rows": None}
_SNAP_TTL = 300.0  # 5 phút


def _get_geo_snapshot(db: Session) -> List[SimpleNamespace]:
    """Trả snapshot nhẹ (chỉ cột cần) của toàn bộ properties, có cache TTL."""
    now = time.time()
    cached = _SNAP.get("rows")
    if cached is not None and now - _SNAP["ts"] < _SNAP_TTL:
        return cached

    cols = db.query(
        Property.id, Property.latitude, Property.longitude, Property.gps_lat, Property.gps_lng,
        Property.district, Property.ward, Property.street_or_project, Property.property_type,
        Property.area_m2, Property.price, Property.price_per_m2,
        Property.bedrooms, Property.bathrooms, Property.floor_count, Property.frontage_m, Property.legal_status,
        Property.noise_level, Property.temperature, Property.humidity, Property.light_level,
        Property.area_quality_score, Property.sensor_source, Property.capture_time, Property.collected_at,
    ).all()

    rows: List[SimpleNamespace] = []
    for c in cols:
        lat = c.latitude if c.latitude is not None else c.gps_lat
        lng = c.longitude if c.longitude is not None else c.gps_lng
        rows.append(SimpleNamespace(
            id=c.id, latitude=lat, longitude=lng,
            district=c.district, ward=c.ward, street_or_project=c.street_or_project,
            property_type=c.property_type, area_m2=c.area_m2, price=c.price, price_per_m2=c.price_per_m2,
            bedrooms=c.bedrooms, bathrooms=c.bathrooms, floor_count=c.floor_count,
            frontage_m=c.frontage_m, legal_status=c.legal_status,
            noise_level=c.noise_level, temperature=c.temperature, humidity=c.humidity,
            light_level=c.light_level, area_quality_score=c.area_quality_score,
            sensor_source=c.sensor_source, capture_time=c.capture_time, collected_at=c.collected_at,
        ))

    with _SNAP_LOCK:
        _SNAP["rows"] = rows
        _SNAP["ts"] = now
    return rows


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách theo mét giữa 2 điểm GPS."""
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _match_scope(address: Dict[str, Any], display_name: str) -> Tuple[Optional[str], Optional[str], bool]:
    """Map address Nominatim → (province_city, district, in_scope) trong 6 quận ML."""
    blob_parts = [str(v) for v in address.values() if v]
    blob_parts.append(display_name or "")
    blob = " | ".join(blob_parts).lower()

    province = None
    for prov, tokens in PROVINCE_TOKENS.items():
        if any(tok in blob for tok in tokens):
            province = prov
            break

    district = None
    for dist, tokens in SCOPE_DISTRICT_TOKENS.items():
        if any(tok in blob for tok in tokens):
            # chỉ nhận district nếu khớp đúng province của district đó
            owner_prov = next(
                (p for p, ds in SCOPE_DISTRICTS.items()
                 if dist in ds and p in ML_SCOPE_PROVINCES),
                None,
            )
            if province is None:
                province = owner_prov
            if owner_prov == province or province is None:
                district = dist
                break

    in_scope = province in ML_SCOPE_PROVINCES and district in SCOPE_DISTRICT_TOKENS
    return province, district, in_scope


def _extract_ward(address: Dict[str, Any]) -> Optional[str]:
    for key in ("suburb", "quarter", "neighbourhood", "ward", "village"):
        if address.get(key):
            return address[key]
    return None


def _extract_road(address: Dict[str, Any]) -> Optional[str]:
    for key in ("road", "pedestrian", "residential", "street"):
        if address.get(key):
            return address[key]
    return None


def _nominatim_reverse(lat: float, lng: float) -> Dict[str, Any]:
    key = f"rev:{round(lat, 5)}:{round(lng, 5)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    params = {
        "lat": lat, "lon": lng, "format": "jsonv2",
        "addressdetails": 1, "zoom": 18, "accept-language": "vi",
    }
    try:
        with httpx.Client(timeout=NOMINATIM_TIMEOUT, headers=NOMINATIM_HEADERS) as client:
            resp = client.get(f"{NOMINATIM_BASE}/reverse", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        data = {"error": str(exc), "address": {}, "display_name": ""}
    _cache_set(key, data)
    return data


def _nominatim_search(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    key = f"search:{query.strip().lower()}:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    params = {
        "q": query, "format": "jsonv2", "addressdetails": 1,
        "limit": limit, "countrycodes": "vn", "accept-language": "vi",
    }
    try:
        with httpx.Client(timeout=NOMINATIM_TIMEOUT, headers=NOMINATIM_HEADERS) as client:
            resp = client.get(f"{NOMINATIM_BASE}/search", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001
        data = []
    _cache_set(key, data)
    return data


def _nearest_scope_district(lat: float, lng: float) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """Quận trong scope ML gần điểm nhất (theo centroid bounds). → (province, district, dist_m)."""
    best = (None, None)
    best_d = None
    for prov, dists in SCOPE_DISTRICTS.items():
        if prov not in ML_SCOPE_PROVINCES:
            continue
        for d in dists:
            b = DISTRICT_BOUNDS.get(d)
            if not b:
                continue
            clat = (b["lat_min"] + b["lat_max"]) / 2
            clng = (b["lng_min"] + b["lng_max"]) / 2
            dist = _haversine_m(lat, lng, clat, clng)
            if best_d is None or dist < best_d:
                best_d = dist
                best = (prov, d)
    return best[0], best[1], best_d


def _build_location(lat: float, lng: float) -> Dict[str, Any]:
    rev = _nominatim_reverse(lat, lng)
    address = rev.get("address", {}) or {}
    display_name = rev.get("display_name", "") or ""
    province, district, in_scope = _match_scope(address, display_name)

    snapped = False
    snap_message = None
    if not in_scope:
        nprov, ndist, ndist_m = _nearest_scope_district(lat, lng)
        if ndist:
            snapped = True
            district = ndist
            province = nprov
            km = (ndist_m or 0) / 1000.0
            snap_message = (
                f"Vị trí bạn chọn nằm NGOÀI 6 quận hệ thống hỗ trợ dự đoán. "
                f"Đã tự gán quận gần nhất: {ndist} ({nprov}), cách ~{km:.1f} km. "
                f"Các trường khác giữ nguyên — kết quả định giá chỉ mang tính tham khảo."
            )

    return {
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
        "display_name": display_name,
        "road": _extract_road(address),
        "ward": _extract_ward(address),
        "district": district,
        "province_city": province,
        "in_scope": in_scope,
        "snapped_to_nearest": snapped,
        "snap_message": snap_message,
        "raw_city": address.get("city") or address.get("town") or address.get("state"),
    }


IOT_SENSOR_FIELDS = ["noise_level", "temperature", "humidity", "light_level", "area_quality_score"]


def _aggregate_iot_rows(nodes: List[Tuple[float, Property]]) -> Dict[str, float]:
    """Tổng hợp các trường IoT từ list (distance, Property) — trọng số nghịch khoảng cách."""
    agg: Dict[str, float] = {}
    for field in IOT_SENSOR_FIELDS:
        wsum = 0.0
        vsum = 0.0
        for dist, p in nodes:
            val = getattr(p, field, None)
            if val is None:
                continue
            w = 1.0 / (1.0 + (dist or 0) / 200.0)
            vsum += float(val) * w
            wsum += w
        if wsum > 0:
            agg[field] = round(vsum / wsum, 1)
    return agg


def _db_tier_iot(db: Session, predicate, label: str) -> Optional[Dict[str, Any]]:
    """Lấy IoT từ DB theo tầng tương đồng (cùng phường / cùng quận) — dùng snapshot."""
    rows = [r for r in _get_geo_snapshot(db) if r.noise_level is not None and predicate(r)]
    if not rows:
        return None
    agg = _aggregate_iot_rows([(0.0, p) for p in rows])
    if not agg:
        return None
    breakdown: Dict[str, int] = {}
    latest = None
    for p in rows:
        src = p.sensor_source or "unknown"
        breakdown[src] = breakdown.get(src, 0) + 1
        ts = p.capture_time or p.collected_at
        if ts and (latest is None or ts > latest):
            latest = ts
    return {
        "tier": label,
        "readings": agg,
        "node_count": len(rows),
        "nearest_node_m": None,
        "source_breakdown": breakdown,
        "captured_latest": latest.isoformat() if latest else None,
    }


def _resolve_area_iot(
    db: Session,
    lat: Optional[float],
    lng: Optional[float],
    province: Optional[str],
    district: Optional[str],
    ward: Optional[str],
) -> Dict[str, Any]:
    """
    Phân giải IoT theo tầng:
      1) live_area  — node cảm biến quanh tọa độ (bán kính 1500m → 5000m)
      2) db_ward    — IoT trong DB cùng phường (tầng tương đồng)
      3) db_district— IoT trong DB cùng quận
      4) estimated  — ước lượng theo hồ sơ quận
    """
    if lat is not None and lng is not None:
        signal = _gather_area_iot(db, lat, lng, radius_m=1500.0) or _gather_area_iot(db, lat, lng, radius_m=5000.0)
        if signal and signal["aggregate"]:
            return {
                "tier": "live_area",
                "readings": signal["aggregate"],
                "node_count": signal["node_count"],
                "nearest_node_m": signal["nearest_node_m"],
                "source_breakdown": signal["source_breakdown"],
                "captured_latest": signal["captured_latest"],
            }

    if district and ward:
        t = _db_tier_iot(db, lambda r: r.district == district and r.ward == ward, "db_ward")
        if t:
            return t
    if district:
        t = _db_tier_iot(db, lambda r: r.district == district, "db_district")
        if t:
            return t

    est = _iot_estimate(lat or 21.0285, lng or 105.8542, district, province)
    return {
        "tier": "estimated",
        "readings": {k: est.get(k) for k in IOT_SENSOR_FIELDS},
        "node_count": 0,
        "nearest_node_m": None,
        "source_breakdown": {},
        "captured_latest": None,
    }


def _gather_area_iot(
    db: Session,
    lat: float,
    lng: float,
    radius_m: float = 1500.0,
    max_nodes: int = 50,
) -> Optional[Dict[str, Any]]:
    """
    "Phát tín hiệu IoT theo khu vực": query các NODE cảm biến (bản ghi có sensor
    data) quanh tọa độ trong bán kính, rồi tổng hợp có trọng số theo khoảng cách.

    Đây là mô hình pull của mạng cảm biến IoT — dùng dữ liệu THẬT đã thu
    (open_meteo_realtime / field survey), không bịa theo quận.
    Trả None nếu không có node nào trong bán kính (caller sẽ fallback ước lượng).
    """
    rows = [r for r in _get_geo_snapshot(db) if r.noise_level is not None]
    nodes: List[Tuple[float, Property]] = []
    for p in rows:
        plat = p.latitude
        plng = p.longitude
        if plat is None or plng is None:
            continue
        try:
            dist = _haversine_m(lat, lng, float(plat), float(plng))
        except (TypeError, ValueError):
            continue
        if dist <= radius_m:
            nodes.append((dist, p))

    nodes.sort(key=lambda x: x[0])
    nodes = nodes[:max_nodes]
    if not nodes:
        return None

    agg = _aggregate_iot_rows(nodes)
    source_breakdown: Dict[str, int] = {}
    latest = None
    for _, p in nodes:
        src = p.sensor_source or "unknown"
        source_breakdown[src] = source_breakdown.get(src, 0) + 1
        ts = p.capture_time or p.collected_at
        if ts and (latest is None or ts > latest):
            latest = ts

    return {
        "node_count": len(nodes),
        "nearest_node_m": round(nodes[0][0]),
        "radius_m": round(radius_m),
        "source_breakdown": source_breakdown,
        "captured_latest": latest.isoformat() if latest else None,
        "aggregate": agg,
    }


def _iot_profile(lat: float, lng: float, district: Optional[str], province: Optional[str], db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Hồ sơ IoT cho 1 điểm.
    Ưu tiên TÍN HIỆU KHU VỰC THẬT (mạng cảm biến quanh điểm). Nếu không có node
    nào trong bán kính → fallback ước lượng theo quận (đánh dấu rõ estimated).
    """
    # 1) Thử thu tín hiệu thật từ mạng cảm biến khu vực
    if db is not None:
        signal = _gather_area_iot(db, lat, lng, radius_m=1500.0)
        if signal is None:
            signal = _gather_area_iot(db, lat, lng, radius_m=5000.0)
        if signal and signal["aggregate"]:
            agg = signal["aggregate"]
            bounds = DISTRICT_BOUNDS.get(district or "", {})
            area_type = bounds.get("dominant_type", "residential")
            return {
                "noise_level": agg.get("noise_level"),
                "temperature": agg.get("temperature"),
                "humidity": agg.get("humidity"),
                "light_level": agg.get("light_level"),
                "area_quality_score": agg.get("area_quality_score"),
                "gps_accuracy": 12.0,
                "sensor_source": "area_sensor_network",
                "area_type": area_type,
                "noise_desc": NOISE_PROFILES.get(area_type, NOISE_PROFILES["residential"])[2],
                "estimated": False,
                "node_count": signal["node_count"],
                "nearest_node_m": signal["nearest_node_m"],
                "radius_m": signal["radius_m"],
                "source_breakdown": signal["source_breakdown"],
                "captured_latest": signal["captured_latest"],
            }

    # 2) Fallback: ước lượng theo hồ sơ quận
    return _iot_estimate(lat, lng, district, province)


def _iot_estimate(lat: float, lng: float, district: Optional[str], province: Optional[str]) -> Dict[str, Any]:
    """Ước lượng IoT từ tọa độ — deterministic theo điểm (cùng điểm → cùng kết quả)."""
    seed = int(abs(lat) * 1e4) * 100000 + int(abs(lng) * 1e4)
    engine = IoTDataEngine(seed=seed)
    use_district = district or "Quận Cầu Giấy"
    use_province = province or "Hà Nội"
    engine.set_capture_context(use_province)
    bounds = DISTRICT_BOUNDS.get(use_district, {})
    area_type = bounds.get("dominant_type", "residential")
    profile = engine.generate_full_iot(district=use_district, province=use_province, area_type=area_type)
    noise_desc = NOISE_PROFILES.get(area_type, NOISE_PROFILES["residential"])[2]
    return {
        "noise_level": profile["noise_level"],
        "temperature": profile["temperature"],
        "humidity": profile["humidity"],
        "light_level": profile["light_level"],
        "area_quality_score": profile["area_quality_score"],
        "gps_accuracy": profile["gps_accuracy"],
        "sensor_source": profile["sensor_source"],
        "area_type": area_type,
        "noise_desc": noise_desc,
        "estimated": True,
        "node_count": 0,
        "nearest_node_m": None,
    }


def _nearby_properties(
    db: Session,
    lat: float,
    lng: float,
    property_type: Optional[str],
    limit: int,
    max_distance_m: float = 8000.0,
) -> Dict[str, Any]:
    rows = [r for r in _get_geo_snapshot(db) if r.latitude is not None and r.longitude is not None]
    if property_type:
        rows = [r for r in rows if r.property_type == property_type]

    scored: List[Tuple[float, Property]] = []
    for p in rows:
        try:
            dist = _haversine_m(lat, lng, float(p.latitude), float(p.longitude))
        except (TypeError, ValueError):
            continue
        scored.append((dist, p))

    scored.sort(key=lambda x: x[0])
    near = [(d, p) for d, p in scored if d <= max_distance_m][:limit]
    # nếu không có gì trong bán kính → vẫn lấy điểm gần nhất để tham khảo
    if not near and scored:
        near = scored[:limit]

    items = []
    ppm_values = []
    for dist, p in near:
        ppm = p.price_per_m2
        if not ppm and p.price and p.area_m2:
            try:
                ppm = float(p.price) / float(p.area_m2)
            except (TypeError, ZeroDivisionError, ValueError):
                ppm = None
        if ppm:
            ppm_values.append(ppm)
        items.append({
            "id": p.id,
            "property_type": p.property_type,
            "district": p.district,
            "ward": p.ward,
            "area_m2": p.area_m2,
            "price": p.price,
            "price_per_m2": ppm,
            "distance_m": round(dist),
            "latitude": p.latitude,
            "longitude": p.longitude,
        })

    summary = {
        "count": len(items),
        "nearest_distance_m": items[0]["distance_m"] if items else None,
        "avg_price_per_m2": round(sum(ppm_values) / len(ppm_values)) if ppm_values else None,
        "min_price_per_m2": round(min(ppm_values)) if ppm_values else None,
        "max_price_per_m2": round(max(ppm_values)) if ppm_values else None,
    }
    return {"properties": items, "summary": summary, "nearest": near[0][1] if near else None}


# ---------------------------------------------------------------------------
# OSM enrichment (Overpass) — điền các trường DB KHÔNG có bằng dữ liệu thật từ
# OpenStreetMap: khoảng cách tiện ích, hạng/bề rộng đường, hình học thửa đất,
# số tầng, hướng nhà, nguy cơ ngập... → prefill gần đầy đủ chỉ từ toạ độ.
# ---------------------------------------------------------------------------
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OVERPASS_TIMEOUT = 25.0

# highway (OSM) → road_class (form ROAD_CLASSES)
_HIGHWAY_TO_ROADCLASS = {
    "motorway": "MAIN_STREET", "trunk": "MAIN_STREET", "primary": "MAIN_STREET",
    "secondary": "MAIN_STREET", "tertiary": "SECONDARY_STREET",
    "unclassified": "SECONDARY_STREET", "residential": "SECONDARY_STREET",
    "living_street": "ALLEY_5M", "service": "ALLEY_3M", "pedestrian": "ALLEY_3M",
    "footway": "ALLEY_2M", "path": "ALLEY_2M", "track": "ALLEY_2M",
}
_ROADCLASS_RANK = {"MAIN_STREET": 4, "SECONDARY_STREET": 3, "ALLEY_5M": 2, "ALLEY_3M": 1, "ALLEY_2M": 0}
_DIRS_VI = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]


def _overpass(query: str) -> List[Dict[str, Any]]:
    cache_key = f"ovp:{hash(query)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    for url in OVERPASS_URLS:
        try:
            with httpx.Client(timeout=OVERPASS_TIMEOUT) as client:
                r = client.post(url, data={"data": query},
                                headers={"User-Agent": NOMINATIM_HEADERS["User-Agent"]})
                if r.status_code == 200:
                    els = r.json().get("elements", [])
                    if els:  # KHÔNG cache rỗng → cho phép thử lại khi Overpass chậm
                        _cache_set(cache_key, els)
                    return els
        except Exception:
            continue
    return []


def _el_center(el: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    if el.get("center"):
        return el["center"]["lat"], el["center"]["lon"]
    if el.get("lat") is not None:
        return el["lat"], el["lon"]
    geom = el.get("geometry") or []
    if geom:
        return (sum(p["lat"] for p in geom) / len(geom), sum(p["lon"] for p in geom) / len(geom))
    return None


def _bearing_to_dir(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    d_lon = math.radians(lng2 - lng1)
    y = math.sin(d_lon) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
         - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(d_lon))
    brng = (math.degrees(math.atan2(y, x)) + 360) % 360
    return _DIRS_VI[int((brng + 22.5) // 45) % 8]


def _polygon_metrics(geom: List[Dict[str, float]]) -> Tuple[float, float, float, float]:
    """area_m2, width_m, depth_m, rectangularity(0..1) từ polygon lat/lng."""
    n = len(geom)
    lat0 = sum(p["lat"] for p in geom) / n
    m_lat = 111_320.0
    m_lng = 111_320.0 * math.cos(math.radians(lat0))
    xs = [p["lon"] * m_lng for p in geom]
    ys = [p["lat"] * m_lat for p in geom]
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += xs[i] * ys[j] - xs[j] * ys[i]
    area = abs(area) / 2.0
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    bbox = (w * h) or 1.0
    rect = min(1.0, area / bbox)
    return round(area, 1), w, h, rect


def _extract_year(s: str) -> Optional[int]:
    import re
    m = re.search(r"(19|20)\d{2}", str(s))
    return int(m.group()) if m else None


def _osm_enrich(lat: float, lng: float) -> Dict[str, Any]:
    """Một lần gọi Overpass → tiện ích gần + thửa đất + đường. Cache theo toạ độ."""
    key = f"enrich:{round(lat, 4)}:{round(lng, 4)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    q = (
        "[out:json][timeout:25];"
        "("
        f'nwr(around:2200,{lat},{lng})[amenity~"^(place_of_worship|hospital|clinic|school|marketplace)$"];'
        f"node(around:1500,{lat},{lng})[highway=bus_stop];"
        f"way(around:2200,{lat},{lng})[leisure=park];"
        f'way(around:3500,{lat},{lng})[landuse~"^(cemetery|grave_yard)$"];'
        f"way(around:2800,{lat},{lng})[natural=water];"
        f'way(around:2800,{lat},{lng})[waterway~"^(river|canal)$"];'
        ");out center tags;"
        "("
        f"way(around:38,{lat},{lng})[building];"
        f"way(around:85,{lat},{lng})[highway];"
        ");out geom tags;"
    )
    els = _overpass(q)

    feats: Dict[str, int] = {}

    def _add(cat: str, el: Dict[str, Any]) -> None:
        c = _el_center(el)
        if not c:
            return
        d = round(_haversine_m(lat, lng, c[0], c[1]))
        if cat not in feats or d < feats[cat]:
            feats[cat] = d

    buildings: List[Dict[str, Any]] = []
    roads: List[Dict[str, Any]] = []
    for el in els:
        t = el.get("tags", {}) or {}
        if "building" in t and el.get("geometry"):
            buildings.append(el); continue
        if t.get("highway") and t.get("highway") != "bus_stop" and el.get("geometry"):
            roads.append(el); continue
        am = t.get("amenity")
        if am == "place_of_worship":
            _add("worship", el)
        elif am in ("hospital", "clinic"):
            _add("hospital", el)
        elif am == "school":
            _add("school", el)
        elif am == "marketplace":
            _add("market", el)
        if t.get("highway") == "bus_stop":
            _add("bus", el)
        if t.get("leisure") == "park":
            _add("park", el)
        if t.get("landuse") in ("cemetery", "grave_yard"):
            _add("cemetery", el)
        if t.get("natural") == "water" or t.get("waterway"):
            _add("water", el)

    parcel: Dict[str, Any] = {}

    # Thửa đất gần nhất
    best_b, best_d = None, 1e9
    for b in buildings:
        c = _el_center(b)
        if not c:
            continue
        d = _haversine_m(lat, lng, c[0], c[1])
        if d < best_d:
            best_d, best_b = d, b
    if best_b:
        geom = best_b["geometry"]
        if len(geom) >= 3:
            area, w, h, rect = _polygon_metrics(geom)
            parcel["footprint_area"] = area
            parcel["frontage_est"] = round(min(w, h), 1)
            parcel["depth_est"] = round(max(w, h), 1)
            parcel["irregularity"] = round(max(0.0, min(1.0, 1.0 - rect)), 2)
        bt = best_b.get("tags", {}) or {}
        if bt.get("building:levels"):
            try:
                parcel["levels"] = int(float(bt["building:levels"]))
            except (ValueError, TypeError):
                pass
        if bt.get("start_date") or bt.get("year_of_construction"):
            yr = _extract_year(bt.get("start_date") or bt.get("year_of_construction"))
            if yr:
                parcel["year"] = yr

    # Đường gần nhất (hạng cao nhất trong bán kính)
    best_rank, road_pt = -1, None
    road_ids = set()
    for r in roads:
        rc = _HIGHWAY_TO_ROADCLASS.get((r.get("tags") or {}).get("highway"))
        if not rc:
            continue
        geom = r.get("geometry") or []
        d_min, pt = 1e9, None
        for p in geom:
            d = _haversine_m(lat, lng, p["lat"], p["lon"])
            if d < d_min:
                d_min, pt = d, p
        if d_min <= 55:
            road_ids.add(r.get("id"))
        rank = _ROADCLASS_RANK.get(rc, 0)
        if rank > best_rank:
            best_rank = rank
            parcel["road_class"] = rc
            road_pt = pt
            t = r.get("tags", {}) or {}
            width = t.get("width") or t.get("est_width")
            if width:
                try:
                    parcel["road_width_m"] = float(str(width).split()[0])
                except (ValueError, IndexError):
                    pass
            elif t.get("lanes"):
                try:
                    parcel["road_width_m"] = round(float(t["lanes"]) * 3.5, 1)
                except (ValueError, TypeError):
                    pass
    parcel["road_count"] = len(road_ids)
    if best_b and road_pt:
        c = _el_center(best_b)
        parcel["main_facing"] = _bearing_to_dir(c[0], c[1], road_pt["lat"], road_pt["lon"])

    result = {"features": feats, "parcel": parcel}
    _cache_set(key, result)
    return result


def _enrich_to_prefill(enrich: Dict[str, Any], suggested_type: Optional[str], nearest_area: Optional[float]) -> Dict[str, Any]:
    """Chuyển dữ liệu OSM → các field form (mã hợp lệ theo enum form)."""
    f = enrich.get("features", {}) or {}
    p = enrich.get("parcel", {}) or {}
    pf: Dict[str, Any] = {}

    if "worship" in f:
        pf["worship_site_distance_m"] = f["worship"]
    if "cemetery" in f:
        pf["cemetery_distance_m"] = f["cemetery"]
    if "park" in f:
        pf["park_distance_m"] = f["park"]
    if "water" in f:
        pf["river_distance_m"] = f["water"]

    water = f.get("water")
    if water is not None:
        pf["flood_risk"] = "moderate" if water < 80 else "minor" if water < 300 else "none"
    else:
        pf["flood_risk"] = "none"

    rc = p.get("road_class")
    if rc:
        pf["road_class"] = rc
        pf["frontage_road_class"] = rc
        pf["pollution_score"] = "0.5" if rc == "MAIN_STREET" else "0"
        if suggested_type == "land":
            sub_map = {
                "MAIN_STREET": "LAND_LEGAL_STREET", "SECONDARY_STREET": "LAND_LEGAL_STREET",
                "ALLEY_5M": "LAND_ALLEY_3M", "ALLEY_3M": "LAND_ALLEY_3M", "ALLEY_2M": "LAND_ALLEY_2M",
            }
            pf["asset_subtype"] = sub_map.get(rc, "LAND_LEGAL_STREET")
    if p.get("road_width_m"):
        pf["road_width_m"] = p["road_width_m"]
        pf["car_access"] = bool(p["road_width_m"] >= 3.5)
    elif rc in ("MAIN_STREET", "SECONDARY_STREET", "ALLEY_5M"):
        pf["car_access"] = True

    if p.get("main_facing"):
        mf = p["main_facing"]
        pf["main_facing"] = mf
        pf["door_orientation"] = mf
        pf["balcony_orientation"] = mf
        pf["sunlight_exposure"] = "POOR" if "Tây" in mf else "FAIR"

    if p.get("footprint_area"):
        fa = p["footprint_area"]
        # Chỉ tin footprint khi kích thước hợp lý cho 1 thửa (20–800 m²);
        # polygon quá lớn thường là cả block/công trình → bỏ qua hình học.
        if 20 <= fa <= 800:
            pf["land_area_m2"] = round(fa, 1)
            if not nearest_area:
                pf["area_m2"] = round(fa, 1)
            if p.get("frontage_est"):
                pf["frontage_m"] = p["frontage_est"]
            if p.get("depth_est"):
                pf["depth_min_m"] = p["depth_est"]
                pf["depth_max_m"] = p["depth_est"]
            if p.get("irregularity") is not None:
                pf["irregularity_score"] = str(p["irregularity"])
        lv = p.get("levels")
        if lv:
            pf["floor_count"] = lv
            pf["apt_floor"] = lv
            if 20 <= fa <= 800:
                pf["built_area_m2"] = round(fa * lv, 1)
    if p.get("year"):
        pf["construction_year"] = p["year"]

    if suggested_type == "apartment":
        if f.get("water") and f["water"] < 250:
            pf["view_type"] = "RIVER"
        elif f.get("park") and f["park"] < 200:
            pf["view_type"] = "PARK"
        else:
            pf["view_type"] = "CITY"

    return pf


def _build_prefill(
    location: Dict[str, Any],
    iot: Dict[str, Any],
    nearest: Optional[Property],
    suggested_type: Optional[str],
    nearest_distance_m: Optional[float],
    osm_prefill: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Gói các field tự điền vào form. Frontend chỉ áp dụng key nào form có."""
    prefill: Dict[str, Any] = {
        # Vị trí — chắc chắn
        "province_city": location.get("province_city"),
        "district": location.get("district"),
        "ward": location.get("ward"),
        "street_or_project": location.get("road"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        # IoT — tự sinh từ tọa độ (Internet of Things)
        "noise_level": iot.get("noise_level"),
        "temperature": iot.get("temperature"),
        "humidity": iot.get("humidity"),
        "gps_lat": location.get("latitude"),
        "gps_lng": location.get("longitude"),
    }

    # Template từ BĐS gần nhất (chỉ khi đủ gần ≤ 1.5km) — người dùng sẽ chỉnh lại
    template_used = False
    if nearest is not None and (nearest_distance_m is None or nearest_distance_m <= 1500):
        template_used = True
        if nearest.area_m2:
            prefill["area_m2"] = nearest.area_m2
            prefill["land_area_m2"] = nearest.area_m2
        if nearest.bedrooms is not None:
            prefill["bedrooms"] = nearest.bedrooms
        if nearest.bathrooms is not None:
            prefill["bathrooms"] = nearest.bathrooms
        if nearest.floor_count is not None:
            prefill["floor_count"] = nearest.floor_count
            prefill["apt_floor"] = nearest.floor_count
        if nearest.frontage_m is not None:
            prefill["frontage_m"] = nearest.frontage_m
        if nearest.legal_status and nearest.legal_status in LEGAL_TO_OWNERSHIP:
            prefill["ownership_type"] = LEGAL_TO_OWNERSHIP[nearest.legal_status]

    # Làm giàu từ OSM/web — chỉ điền field CHƯA có (DB/nearest ưu tiên hơn)
    for k, v in (osm_prefill or {}).items():
        if v is None:
            continue
        prefill.setdefault(k, v)

    # bỏ key None để không ghi đè giá trị mặc định của form
    prefill = {k: v for k, v in prefill.items() if v is not None}
    prefill["_template_from_nearest"] = template_used
    prefill["_suggested_type"] = suggested_type
    return prefill


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/search")
def map_search(q: str = Query(..., min_length=2), limit: int = Query(6, ge=1, le=10)):
    """Tìm địa chỉ/dự án theo từ khóa (proxy Nominatim, có cache)."""
    raw = _nominatim_search(q, limit=limit)
    results = []
    for item in raw:
        try:
            lat = float(item.get("lat"))
            lng = float(item.get("lon"))
        except (TypeError, ValueError):
            continue
        results.append({
            "display_name": item.get("display_name", ""),
            "name": item.get("name") or item.get("display_name", "").split(",")[0],
            "latitude": round(lat, 6),
            "longitude": round(lng, 6),
            "type": item.get("type"),
        })
    return {"query": q, "results": results}


@router.get("/reverse")
def map_reverse(lat: float = Query(...), lng: float = Query(...)):
    """Tọa độ → địa chỉ + map về quận trong scope ML."""
    return _build_location(lat, lng)


@router.get("/location-context")
def map_location_context(
    lat: float = Query(...),
    lng: float = Query(...),
    property_type: Optional[str] = Query(None, description="house|apartment|land|townhouse|villa"),
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Gói dữ liệu đầy đủ cho modal chọn vị trí:
    địa chỉ + BĐS gần + tóm tắt giá + hồ sơ IoT + prefill cho form.
    """
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Tọa độ không hợp lệ")

    location = _build_location(lat, lng)
    iot = _iot_profile(lat, lng, location.get("district"), location.get("province_city"), db=db)

    nearby = _nearby_properties(db, lat, lng, property_type, limit=limit)
    nearest = nearby.pop("nearest", None)

    suggested_type = property_type
    if not suggested_type and nearest is not None:
        suggested_type = DB_TYPE_TO_FORM.get(nearest.property_type)

    nearest_distance = nearby["summary"]["nearest_distance_m"]
    prefill = _build_prefill(location, iot, nearest, suggested_type, nearest_distance)

    field_options = _field_options(db, location.get("district"), suggested_type or property_type)

    return {
        "location": location,
        "iot": iot,
        "nearby": nearby,
        "suggested_property_type": suggested_type,
        "prefill": prefill,
        "field_options": field_options,
        "disclaimer": (
            "BĐS gần chỉ là dữ liệu tham khảo khu vực. Giá cuối cùng do model dự đoán "
            "dựa trên thông tin bạn xác nhận trong biểu mẫu."
        ),
    }


def _field_options(db: Session, district: Optional[str], property_type: Optional[str]) -> Dict[str, Any]:
    """
    Gợi ý "kiểu OneHousing": từ dữ liệu THỰC trong DB, trả về các lựa chọn có sẵn
    của hệ thống cho quận đã chọn (phường, đường/dự án, dải diện tích, dải giá/m²).
    Người dùng vẫn nhập tự do, nhưng có dropdown gợi ý theo khu vực thật.
    """
    empty = {
        "wards": [], "streets": [], "area_range": None,
        "price_per_m2_range": None, "sample_size": 0,
    }
    if not district:
        return empty

    snap = [r for r in _get_geo_snapshot(db) if r.district == district]
    rows = [r for r in snap if r.property_type == property_type] if property_type else snap
    if not rows and property_type:
        # nới lỏng: bỏ filter loại hình nếu quá ít
        rows = snap
    if not rows:
        return empty

    def _top(values, n=12):
        counts: Dict[str, int] = {}
        for v in values:
            if v and str(v).strip():
                key = str(v).strip()
                counts[key] = counts.get(key, 0) + 1
        return [k for k, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]]

    wards = _top([p.ward for p in rows])

    def _clean_street(v) -> Optional[str]:
        if not v:
            return None
        s = str(v).strip().strip(",").strip()
        # bỏ các giá trị là địa chỉ đầy đủ/ghép chuỗi (dữ liệu nhiễu)
        if not s or len(s) > 28 or s.count(",") >= 1:
            return None
        if any(tok in s.lower() for tok in ("hà nội", "quận", "phường", "(cũ)", "tp.")):
            return None
        return s

    streets = _top([_clean_street(p.street_or_project) for p in rows])
    areas = [float(p.area_m2) for p in rows if p.area_m2]
    ppms = [float(p.price_per_m2) for p in rows if p.price_per_m2]

    area_range = None
    if areas:
        areas.sort()
        area_range = {
            "min": round(areas[0], 1),
            "median": round(areas[len(areas) // 2], 1),
            "max": round(areas[-1], 1),
        }
    price_range = None
    if ppms:
        ppms.sort()
        price_range = {
            "min": round(ppms[0]),
            "median": round(ppms[len(ppms) // 2]),
            "max": round(ppms[-1]),
        }

    return {
        "wards": wards,
        "streets": streets,
        "area_range": area_range,
        "price_per_m2_range": price_range,
        "sample_size": len(rows),
    }


@router.get("/enrich")
def map_enrich(
    lat: float = Query(...),
    lng: float = Query(...),
    property_type: Optional[str] = Query(None),
):
    """
    Làm giàu dữ liệu từ OpenStreetMap (Overpass) cho 1 toạ độ — gọi LAZY sau khi
    đã hiển thị dashboard cơ bản (Overpass có thể chậm vài giây).

    Trả về:
      - amenities: khoảng cách (m) tới trường/bệnh viện/chợ/công viên/trạm bus/
        nghĩa trang/sông gần nhất.
      - parcel: hình học thửa đất + hạng/bề rộng đường + hướng nhà suy từ OSM.
      - prefill: các field form điền sẵn từ dữ liệu trên (mã hợp lệ theo enum).
    """
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Tọa độ không hợp lệ")
    enrich = _osm_enrich(lat, lng)
    osm_prefill = _enrich_to_prefill(enrich, property_type, nearest_area=None)
    osm_prefill = {k: v for k, v in osm_prefill.items() if v is not None}
    osm_prefill["_v"] = int(time.time() * 1000)
    return {
        "amenities": enrich.get("features", {}),
        "parcel": enrich.get("parcel", {}),
        "prefill": osm_prefill,
        "ok": bool(enrich.get("features") or enrich.get("parcel", {}).get("road_class")),
    }


@router.get("/parcel")
def map_parcel(
    lat: float = Query(...),
    lng: float = Query(...),
):
    """
    Hình học thửa đất + công trình lân cận + đường (OSM) để vẽ "sơ đồ lô đất"
    kiểu Guland/ZoLa: lô chính tô màu nổi bật, công trình xung quanh làm nền.
    """
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Tọa độ không hợp lệ")
    return _osm_parcel_geometry(lat, lng)


# ---------------------------------------------------------------------------
# Zoning tile store — cache vùng sử dụng đất theo ô lưới 0.02° trong bộ nhớ +
# đĩa, nạp nền cả thành phố qua worker → trả bbox tức thì (~ms).
# ---------------------------------------------------------------------------
_ZTILE = 0.02
_ZSTORE: Dict[str, List[Dict[str, Any]]] = {}
_ZQUEUED: set = set()
_ZQ: "queue.Queue[str]" = queue.Queue()
_ZLOCK = threading.Lock()
_ZWORKER_STARTED = False
_ZCACHE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "zoning_cache.json"))
_ZDIRTY = {"v": False, "last": 0.0}


def _zload_cache() -> None:
    try:
        if os.path.exists(_ZCACHE_PATH):
            with open(_ZCACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            with _ZLOCK:
                _ZSTORE.update(data)
    except Exception:
        pass


def _zsave_cache() -> None:
    try:
        with _ZLOCK:
            snap = dict(_ZSTORE)
        tmp = _ZCACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False)
        os.replace(tmp, _ZCACHE_PATH)
    except Exception:
        pass


def _zfetch_tile(key: str) -> None:
    ti, tj = key.split("_")
    la, ln = int(ti) * _ZTILE, int(tj) * _ZTILE
    bbox = f"{la:.5f},{ln:.5f},{la + _ZTILE:.5f},{ln + _ZTILE:.5f}"
    q = (
        "[out:json][timeout:25];("
        f"way[landuse]({bbox});"
        f"way[leisure~\"^(park|garden|nature_reserve|pitch|playground)$\"]({bbox});"
        f"way[natural~\"^(water|wood|wetland|scrub)$\"]({bbox});"
        ");out geom tags;"
    )
    els = _overpass(q)
    zones: List[Dict[str, Any]] = []
    for el in els:
        t = el.get("tags", {}) or {}
        geom = el.get("geometry") or []
        coords = [[round(p["lat"], 6), round(p["lon"], 6)] for p in geom if "lat" in p and "lon" in p]
        if len(coords) < 3:
            continue
        z = _zone_of(t)
        if z:
            zones.append({"coords": coords, "zone": z})
    with _ZLOCK:
        _ZSTORE[key] = zones[:220]
    _ZDIRTY["v"] = True


def _zworker() -> None:
    while True:
        key = _ZQ.get()
        try:
            _zfetch_tile(key)
        except Exception:
            with _ZLOCK:
                _ZSTORE.setdefault(key, [])
        finally:
            with _ZLOCK:
                _ZQUEUED.discard(key)
            _ZQ.task_done()
        now = time.time()
        if _ZDIRTY["v"] and now - _ZDIRTY["last"] > 10:
            _ZDIRTY["v"] = False
            _ZDIRTY["last"] = now
            _zsave_cache()


def _zstart() -> None:
    global _ZWORKER_STARTED
    if _ZWORKER_STARTED:
        return
    _ZWORKER_STARTED = True
    _zload_cache()
    for _ in range(2):
        threading.Thread(target=_zworker, daemon=True).start()


def _zone_of(t: Dict[str, Any]) -> Optional[str]:
    """OSM tags → nhóm sử dụng đất (kiểu zoning) để tô màu bản đồ quy hoạch."""
    lu = t.get("landuse"); le = t.get("leisure"); na = t.get("natural"); am = t.get("amenity")
    if na in ("water", "wetland") or lu == "reservoir" or t.get("waterway"):
        return "water"
    if (le in ("park", "garden", "nature_reserve", "pitch", "playground")
            or lu in ("grass", "recreation_ground", "meadow", "village_green", "forest")
            or na in ("wood", "scrub")):
        return "green"
    if lu == "residential":
        return "residential"
    if lu in ("commercial", "retail"):
        return "commercial"
    if lu == "industrial":
        return "industrial"
    if lu in ("construction", "brownfield", "greenfield"):
        return "construction"
    if lu == "education" or am in ("school", "university", "college", "hospital"):
        return "public"
    if lu in ("cemetery", "grave_yard"):
        return "cemetery"
    if lu in ("farmland", "farmyard", "orchard", "plant_nursery", "vineyard"):
        return "agriculture"
    if lu or le or na:
        return "other"
    return None


def _osm_parcel_geometry(lat: float, lng: float) -> Dict[str, Any]:
    key = f"parcelgeo:{round(lat, 4)}:{round(lng, 4)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    q = (
        "[out:json][timeout:25];("
        f"way(around:150,{lat},{lng})[building];"
        f"way(around:150,{lat},{lng})[highway];"
        f"way(around:450,{lat},{lng})[landuse];"
        f"way(around:450,{lat},{lng})[leisure];"
        f'way(around:450,{lat},{lng})[natural~"^(water|wood|scrub|wetland)$"];'
        ");out geom tags;"
    )
    els = _overpass(q)
    buildings: List[List[List[float]]] = []
    roads: List[Dict[str, Any]] = []
    zones: List[Dict[str, Any]] = []
    for el in els:
        t = el.get("tags", {}) or {}
        geom = el.get("geometry") or []
        coords = [[p["lat"], p["lon"]] for p in geom if "lat" in p and "lon" in p]
        if len(coords) < 2:
            continue
        if "building" in t:
            buildings.append(coords)
        elif t.get("highway") and t.get("highway") != "bus_stop":
            roads.append({"coords": coords, "cls": _HIGHWAY_TO_ROADCLASS.get(t.get("highway"))})
        elif len(coords) >= 3:
            z = _zone_of(t)
            if z:
                zones.append({"coords": coords, "zone": z,
                              "name": t.get("name") or ""})

    subject = None
    best, subj_idx = 1e9, -1
    for i, b in enumerate(buildings):
        cx = sum(c[0] for c in b) / len(b)
        cy = sum(c[1] for c in b) / len(b)
        d = _haversine_m(lat, lng, cx, cy)
        if d < best:
            best, subject, subj_idx = d, b, i
    others = [b for i, b in enumerate(buildings) if i != subj_idx][:60]
    result = {
        "center": [lat, lng],
        "subject": subject,
        "subject_dist_m": round(best) if subject else None,
        "buildings": others,
        "roads": roads[:40],
        "zones": zones[:90],
    }
    _cache_set(key, result)
    return result


# ---------------------------------------------------------------------------
# BĐS tương đồng THẬT — proxy gateway công khai của Chợ Tốt (keyless).
# Lấy listing rao bán thật (ảnh + giá + diện tích + vị trí) đúng loại hình +
# khu vực, xếp hạng theo cùng quận + gần diện tích. Không cần API key.
# ---------------------------------------------------------------------------
CHOTOT_GATEWAY = "https://gateway.chotot.com/v1/public/ad-listing"
_TYPE_TO_CG = {"apartment": "1010", "house": "1020", "townhouse": "1020", "villa": "1020", "land": "1040"}


def _region_v2(province: Optional[str]) -> str:
    p = (province or "").lower()
    if any(t in p for t in ("hồ chí minh", "ho chi minh", "hcm", "sài gòn", "sai gon", "saigon")):
        return "13000"
    return "12000"


def _norm_dist(s: Optional[str]) -> str:
    return (s or "").lower().replace("quận", "").replace("huyện", "").replace("quan", "").replace("huyen", "").strip()


def _chotot_listings(property_type: str, province: Optional[str], district: Optional[str],
                     area_m2: Optional[float], limit: int = 12) -> Dict[str, Any]:
    cache_key = f"chotot:{property_type}:{province}:{district}:{round(area_m2 or 0)}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    cg = _TYPE_TO_CG.get(property_type, "1020")
    region = _region_v2(province)
    params = {"cg": cg, "region_v2": region, "limit": "50", "st": "s,k", "page": "1"}
    ads: List[Dict[str, Any]] = []
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(CHOTOT_GATEWAY, params=params,
                           headers={"User-Agent": NOMINATIM_HEADERS["User-Agent"]})
            if r.status_code == 200:
                ads = r.json().get("ads", []) or []
    except Exception:
        ads = []

    dnorm = _norm_dist(district)
    ranked: List[Tuple[float, Dict[str, Any]]] = []
    for a in ads:
        img = a.get("image")
        if not img:
            continue
        ar = a.get("size") or a.get("area")
        score = 0.0
        if dnorm and dnorm in _norm_dist(a.get("area_name")):
            score -= 2.0  # ưu tiên cùng quận
        if area_m2 and ar:
            score += abs(float(ar) - float(area_m2)) / max(float(area_m2), 1.0)
        ranked.append((score, {
            "title": a.get("subject"),
            "price": a.get("price_string"),
            "area": round(float(ar)) if ar else None,
            "rooms": a.get("rooms"),
            "toilets": a.get("toilets"),
            "image": img,
            "images": (a.get("images") or [])[:6],
            "location": ", ".join([x for x in [a.get("ward_name"), a.get("area_name")] if x]),
            "url": f"https://www.nhatot.com/{a.get('list_id')}.htm",
        }))
    ranked.sort(key=lambda x: x[0])
    listings = [x[1] for x in ranked[:limit]]
    result = {"source": "Chợ Tốt / Nhà Tốt", "count": len(listings), "listings": listings}
    if listings:
        _cache_set(cache_key, result)
    return result


@router.get("/listings")
def map_listings(
    property_type: str = Query(...),
    province_city: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    area_m2: Optional[float] = Query(None),
    limit: int = Query(12, ge=1, le=24),
):
    """BĐS tương đồng thật từ Chợ Tốt (ảnh + giá + diện tích), đúng loại hình + khu vực."""
    return _chotot_listings(property_type, province_city, district, area_m2, limit)


@router.get("/zoning")
def map_zoning(
    min_lat: float = Query(...), min_lng: float = Query(...),
    max_lat: float = Query(...), max_lng: float = Query(...),
):
    """
    Lớp quy hoạch sử dụng đất — phục vụ từ CACHE ô lưới trong bộ nhớ (≈ vài ms).
    Ô nào chưa có sẽ được nạp NỀN (background) từ Overpass; client poll lại để
    lấy thêm → phủ dần toàn Hà Nội / TP.HCM mà không chặn phản hồi.
    """
    _zstart()
    span = max(max_lat - min_lat, max_lng - min_lng)
    if span <= 0 or span > 0.45:
        return {"zones": [], "too_large": True, "pending": 0}
    ti0, ti1 = math.floor(min_lat / _ZTILE), math.floor(max_lat / _ZTILE)
    tj0, tj1 = math.floor(min_lng / _ZTILE), math.floor(max_lng / _ZTILE)
    tiles = []
    for ti in range(ti0, ti1 + 1):
        for tj in range(tj0, tj1 + 1):
            tiles.append(f"{ti}_{tj}")
    tiles = tiles[:240]
    result: List[Dict[str, Any]] = []
    pending = 0
    with _ZLOCK:
        for k in tiles:
            if k in _ZSTORE:
                result += _ZSTORE[k]
            else:
                pending += 1
                if k not in _ZQUEUED:
                    _ZQUEUED.add(k)
                    _ZQ.put(k)
    return {"zones": result[:5000], "pending": pending, "too_large": False}


@router.get("/field-options")
def map_field_options(
    district: str = Query(...),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Gợi ý field theo quận từ dữ liệu thật (phường/đường/dải diện tích/dải giá)."""
    return _field_options(db, district, property_type)


# ---------------------------------------------------------------------------
# IoT — mạng cảm biến theo khu vực (pull model)
# ---------------------------------------------------------------------------
iot_router = APIRouter(prefix="/api/iot", tags=["IoT Sensor Network"])


@iot_router.get("/area-signal")
def iot_area_signal(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: float = Query(1500.0, ge=100, le=20000),
    db: Session = Depends(get_db),
):
    """
    Phát tín hiệu thu dữ liệu IoT từ KHU VỰC quanh tọa độ.

    Hệ thống query các node cảm biến (bản ghi có sensor data) trong bán kính,
    tổng hợp có trọng số theo khoảng cách, trả về tín hiệu môi trường khu vực.
    Nếu bán kính yêu cầu không có node → tự nới rộng; vẫn trống → ước lượng.
    """
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Tọa độ không hợp lệ")

    signal = _gather_area_iot(db, lat, lng, radius_m=radius_m)
    used_radius = radius_m
    if signal is None and radius_m < 5000:
        signal = _gather_area_iot(db, lat, lng, radius_m=5000.0)
        used_radius = 5000.0

    if not signal or not signal["aggregate"]:
        location = _build_location(lat, lng)
        est = _iot_estimate(lat, lng, location.get("district"), location.get("province_city"))
        return {
            "status": "estimated",
            "message": "Không có node cảm biến trong vùng — dùng ước lượng theo quận.",
            "latitude": round(lat, 6), "longitude": round(lng, 6),
            "node_count": 0,
            "readings": {k: est.get(k) for k in IOT_SENSOR_FIELDS},
            "sensor_source": est["sensor_source"],
        }

    return {
        "status": "live_area_signal",
        "message": f"Thu tín hiệu từ {signal['node_count']} node cảm biến trong bán kính {round(used_radius)}m.",
        "latitude": round(lat, 6), "longitude": round(lng, 6),
        "node_count": signal["node_count"],
        "nearest_node_m": signal["nearest_node_m"],
        "radius_m": round(used_radius),
        "captured_latest": signal["captured_latest"],
        "source_breakdown": signal["source_breakdown"],
        "readings": signal["aggregate"],
        "sensor_source": "area_sensor_network",
    }


@iot_router.get("/auto-fill")
def iot_auto_fill(
    province_city: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    street_or_project: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Tự phát IoT khi người dùng nhập trường địa chỉ:
      - Nếu chưa có tọa độ → geocode từ địa chỉ đã nhập (đường + phường + quận + tỉnh).
      - Phân giải IoT theo tầng: live_area → db_ward → db_district → estimated.
    Trả tọa độ (nếu geocode được) + readings môi trường để form tự điền.
    """
    geocoded = False
    approx = False
    if lat is None or lng is None:
        # 1) Ưu tiên centroid quận trong scope → tức thì, không gọi mạng
        if district and district in DISTRICT_BOUNDS:
            b = DISTRICT_BOUNDS[district]
            lat = (b["lat_min"] + b["lat_max"]) / 2
            lng = (b["lng_min"] + b["lng_max"]) / 2
            approx = True
        # 2) Ngoài scope mới geocode qua Nominatim (có cache)
        elif district:
            parts = [street_or_project, ward, district, province_city, "Việt Nam"]
            q = ", ".join([p for p in parts if p])
            results = _nominatim_search(q, limit=1)
            if results:
                try:
                    lat = float(results[0].get("lat"))
                    lng = float(results[0].get("lon"))
                    geocoded = True
                except (TypeError, ValueError):
                    pass

    resolved = _resolve_area_iot(db, lat, lng, province_city, district, ward)

    tier_label = {
        "live_area": "Tín hiệu cảm biến khu vực (theo tọa độ)",
        "db_ward": "IoT trong DB — cùng phường",
        "db_district": "IoT trong DB — cùng quận",
        "estimated": "Ước lượng theo hồ sơ quận",
    }.get(resolved["tier"], resolved["tier"])

    return {
        "latitude": round(lat, 6) if lat is not None else None,
        "longitude": round(lng, 6) if lng is not None else None,
        "geocoded": geocoded or approx,
        "approx": approx,
        "tier": resolved["tier"],
        "tier_label": tier_label,
        "node_count": resolved.get("node_count", 0),
        "nearest_node_m": resolved.get("nearest_node_m"),
        "captured_latest": resolved.get("captured_latest"),
        "source_breakdown": resolved.get("source_breakdown", {}),
        "readings": resolved["readings"],
    }
