"""
Research-grade data-quality assessment for the AVM project.

This module implements a project-specific standard inspired by the user's
CVX-BDS/IoT baseline and extended for Vietnam-focused real-estate workflows.
Key ideas:
- every record has its own Record Quality Score (RQS)
- every record is mapped to an evidence tier E1..E5
- support volume is based on effective sample size (Neff), not raw counts
- prediction intervals expand/contract with both uncertainty and data trust
- training can reuse the same quality profile to create sample weights
"""

from __future__ import annotations

from datetime import datetime
from statistics import mean, median, pstdev
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def safe_mean(values: Sequence[float], default: float = 0.0) -> float:
    cleaned = [float(v) for v in values if v is not None]
    return mean(cleaned) if cleaned else default


def safe_median(values: Sequence[float], default: float = 0.0) -> float:
    cleaned = [float(v) for v in values if v is not None]
    return median(cleaned) if cleaned else default


def _get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    if hasattr(record, key):
        return getattr(record, key, default)
    if hasattr(record, "get"):
        try:
            return record.get(key, default)
        except Exception:
            return default
    try:
        return record[key]
    except Exception:
        pass
    return default


def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().replace(tzinfo=None)
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                return datetime.fromisoformat(candidate).replace(tzinfo=None)
            except ValueError:
                continue
    return None


def _days_since(value: Any, reference_date: Optional[datetime] = None) -> Optional[int]:
    dt_value = _to_datetime(value)
    if dt_value is None:
        return None
    reference = reference_date or datetime.now()
    return max((reference - dt_value).days, 0)


def _has_value(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


def _weighted_presence(fields: Iterable[tuple[str, bool, float]]) -> Dict[str, Any]:
    total_weight = 0.0
    present_weight = 0.0
    missing_fields: List[str] = []
    provided_fields: List[str] = []

    for field_name, is_present, weight in fields:
        total_weight += weight
        if is_present:
            present_weight += weight
            provided_fields.append(field_name)
        else:
            missing_fields.append(field_name)

    ratio = present_weight / total_weight if total_weight else 0.0
    return {
        "score": round(ratio * 10, 2),
        "ratio": round(ratio, 4),
        "missing_fields": missing_fields,
        "provided_fields": provided_fields,
    }


def _source_root(record: Any) -> str:
    source_url = (_get(record, "source_url", "") or "").strip()
    if source_url:
        try:
            parsed = urlparse(source_url)
            if parsed.netloc:
                return parsed.netloc.lower()
        except Exception:
            pass
    source_name = (_get(record, "source_name", "unknown") or "unknown").strip().lower()
    return source_name


def _iot_signal_count(record: Any) -> int:
    keys = [
        "noise_level",
        "temperature",
        "humidity",
        "light_level",
        "gps_lat",
        "gps_lng",
        "area_quality_score",
    ]
    return sum(1 for key in keys if _has_value(_get(record, key)))


def score_input_completeness(request_data: Dict[str, Any]) -> Dict[str, Any]:
    fields = [
        ("property_type", _has_value(request_data.get("property_type")), 1.2),
        ("province_city", _has_value(request_data.get("province_city")), 1.2),
        ("district", _has_value(request_data.get("district")), 1.2),
        ("area_m2", request_data.get("area_m2") not in (None, "", 0), 1.4),
        ("ward", _has_value(request_data.get("ward")), 0.4),
        ("bedrooms", request_data.get("bedrooms") is not None, 0.5),
        ("bathrooms", request_data.get("bathrooms") is not None, 0.5),
        ("floor_count", request_data.get("floor_count") is not None, 0.5),
        ("frontage_m", request_data.get("frontage_m") not in (None, ""), 0.5),
        ("legal_status", _has_value(request_data.get("legal_status")), 0.9),
        ("furnishing", _has_value(request_data.get("furnishing")), 0.4),
        (
            "latitude_or_gps",
            request_data.get("latitude") is not None or request_data.get("gps_lat") is not None,
            0.7,
        ),
        (
            "longitude_or_gps",
            request_data.get("longitude") is not None or request_data.get("gps_lng") is not None,
            0.7,
        ),
        ("noise_level", request_data.get("noise_level") is not None, 0.5),
        ("temperature", request_data.get("temperature") is not None, 0.3),
        ("humidity", request_data.get("humidity") is not None, 0.3),
        ("light_level", request_data.get("light_level") is not None, 0.3),
        ("area_type", _has_value(request_data.get("area_type")), 0.4),
    ]
    result = _weighted_presence(fields)
    result["note"] = (
        "Input completeness combines property identity, legal context, "
        "location traceability, and optional IoT/environment signals."
    )
    return result


def _is_real_evidence_path(path) -> bool:
    """Reject placeholder patterns used by data generators."""
    if not _has_value(path):
        return False
    s = str(path).lower()
    for pat in ("fs_placeholder", "_placeholder.", "e2_", "synthetic_",
                "demo_", "placeholder.", ".placeholder",
                "uploads/evidence/fs_", "uploads/screenshots/fs_",
                "uploads/evidence/e2_", "uploads/screenshots/e2_"):
        if pat in s:
            return False
    return len(s) >= 10


def classify_evidence_tier(record: Any) -> Dict[str, Any]:
    """
    Evidence tier classification — E5 = HIGHEST confidence (most complete evidence),
    E1 = LOWEST confidence (minimal evidence).

    Priority: (1) stored evidence_tier from DB > (2) recompute from raw fields.

    Tier criteria (most → least evidence):
      E5: verified + self-collected + IoT + GPS + notes + photo  (complete self-collected)
      E4: verified + at least 2 evidence types (notes, IoT, photo, GPS, screenshot)
      E3: verified + at least 1 evidence type, OR pending + strong evidence
      E2: has source URL/name (public listing, minimal traceability)
      E1: no source, no verification, minimal evidence
    """
    stored = _get(record, "evidence_tier", "")
    collection_method = (_get(record, "collection_method", "") or "").lower()
    if stored in ("E1", "E2", "E3", "E4", "E5"):
        # Config inverted: E5=highest (1.0), E1=lowest (0.15)
        cfg = {
            "E5": (1.0, 1.0, 10.0),
            "E4": (0.85, 0.85, 9.0),
            "E3": (0.65, 0.65, 8.0),
            "E2": (0.35, 0.45, 6.5),
            "E1": (0.15, 0.2, 4.0),
        }
        # Special case: public auction = E5 tier (high confidence, anchored asset)
        if stored == "E5" and collection_method == "public_auction_asset_evidence":
            return {
                "tier": stored,
                "note": "E5 public auction asset evidence; auction anchor, not private transaction.",
                "anchor_strength": 1.0,
                "evidence_weight": 1.0,
                "cap": 10.0,
            }
        a, e, c = cfg[stored]
        return {
            "tier": stored,
            "note": f"Stored tier from DB import: {stored}",
            "anchor_strength": a, "evidence_weight": e, "cap": c,
        }

    verification_status = (_get(record, "verification_status", "unverified") or "unverified").lower()
    data_origin_type = (_get(record, "data_origin_type", "public_collected") or "public_collected").lower()

    real_ev_photo = _is_real_evidence_path(_get(record, "evidence_photo_path"))
    real_image = _is_real_evidence_path(_get(record, "image_url"))
    real_screenshot = _is_real_evidence_path(_get(record, "source_screenshot_path"))
    real_field_photos = _is_real_evidence_path(_get(record, "field_photos"))
    has_verifier = _has_value(_get(record, "verified_by")) or _get(record, "verified_at") is not None
    has_field_capture = data_origin_type == "self_collected" or any(
        token in collection_method
        for token in ["field", "google_form", "smartphone", "submission", "manual_verified"]
    )
    has_iot_signal = _iot_signal_count(record) > 0
    has_gps = _get(record, "gps_lat") is not None or _get(record, "latitude") is not None
    has_notes = _has_value(_get(record, "field_note")) or _has_value(_get(record, "field_notes"))
    has_photo = real_ev_photo or real_image
    has_source = _has_value(_get(record, "source_name")) and (
        _has_value(_get(record, "source_url")) or real_screenshot
    )

    # Self-collected records: collector counts as verifier
    if data_origin_type == "self_collected" and _has_value(_get(record, "collected_by")):
        has_verifier = True

    # ── Self-collected path ─────────────────────────────────────────────
    if data_origin_type == "self_collected" and _has_value(_get(record, "collected_by")):
        # IoT + GPS + notes = real field evidence for self-collected
        sc_notes = bool(has_notes)
        sc_photo = bool(has_photo)
        sc_iot = bool(has_iot_signal)
        sc_gps = bool(has_gps)
        sc_evidence = sum([sc_notes, sc_photo, sc_iot, sc_gps])

        # E5: notes + GPS + IoT (complete field evidence)
        if sc_notes and sc_gps and sc_iot:
            tier, note = "E5", "E5: Complete field evidence — notes + GPS + IoT."
        # E5 alt: notes + GPS + photo (without IoT)
        elif sc_notes and sc_gps and sc_photo:
            tier, note = "E5", "E5: Complete field evidence — notes + GPS + photo."
        # E5 alt: notes + IoT + photo (without GPS)
        elif sc_notes and sc_iot and sc_photo:
            tier, note = "E5", "E5: Complete field evidence — notes + IoT + photo."
        # E5 alt: all 4 types
        elif sc_evidence >= 4:
            tier, note = "E5", "E5: Full 4-type field evidence."
        # E4: notes + (GPS OR IoT)
        elif sc_notes and (sc_gps or sc_iot):
            tier, note = "E4", "E4: Field evidence — notes + GPS or IoT."
        # E4 alt: GPS + IoT + photo (no notes but 3 other types)
        elif sc_gps and sc_iot and sc_photo:
            tier, note = "E4", "E4: Field evidence — GPS + IoT + photo."
        # E3: notes only, or GPS+IoT without notes
        elif sc_notes or (sc_gps and sc_iot):
            tier, note = "E3", "E3: Partial field evidence."
        # E2: photo only, or GPS only, or IoT only
        elif sc_photo or sc_gps or sc_iot:
            tier, note = "E2", "E2: Minimal field evidence."
        else:
            tier, note = "E1", "E1: No field evidence."
    # ── Public scraped path ─────────────────────────────────────────────
    else:
        # For public scraped data, IoT is seeded data (not real field evidence).
        # verified_by is set by the verification script — it's not real field evidence.
        # Real evidence for public records = photo or screenshot.
        has_source = _has_value(_get(record, "source_name")) and bool(_get(record, "source_url"))

        # E4: verified + photo + source (verified listing with real photo evidence)
        if verification_status == "verified" and has_photo and has_source:
            tier, note = "E4", "E4: Verified public listing with photo."
        # E3: verified + source URL (basic verified public listing)
        elif verification_status == "verified" and has_source:
            tier, note = "E3", "E3: Verified public listing."
        # E2: pending + source URL
        elif verification_status == "pending" and has_source:
            tier, note = "E2", "E2: Pending public listing."
        # E1: no source, no verification
        else:
            tier, note = "E1", "E1: Minimal evidence."

    # Config inverted: E5=highest
    cfg = {
        "E5": (1.0, 1.0, 10.0),
        "E4": (0.85, 0.85, 9.0),
        "E3": (0.65, 0.65, 8.0),
        "E2": (0.35, 0.45, 6.5),
        "E1": (0.15, 0.2, 4.0),
    }
    a, e, c = cfg[tier]
    return {"tier": tier, "note": note,
            "anchor_strength": a, "evidence_weight": e, "cap": c}

def _score_provenance(record: Any) -> Dict[str, Any]:
    fields = [
        ("source_name", _has_value(_get(record, "source_name")), 1.3),
        ("source_url", _has_value(_get(record, "source_url")), 1.1),
        ("source_access_method", _has_value(_get(record, "source_access_method")), 0.7),
        ("source_collected_at", _get(record, "source_collected_at") is not None, 0.8),
        ("source_page_title", _has_value(_get(record, "source_page_title")), 0.4),
        ("source_screenshot_path", _has_value(_get(record, "source_screenshot_path")), 0.7),
        ("collector_or_reviewer", _has_value(_get(record, "collected_by")) or _has_value(_get(record, "verified_by")), 0.6),
        ("collection_method", _has_value(_get(record, "collection_method")), 0.6),
    ]
    return _weighted_presence(fields)


def _score_verification(record: Any) -> float:
    verification_status = (_get(record, "verification_status", "unverified") or "unverified").lower()
    status_base = {
        "verified": 7.0,
        "pending": 4.0,
        "unverified": 2.0,
        "rejected": 0.0,
    }.get(verification_status, 2.0)

    bonuses = 0.0
    if _has_value(_get(record, "verified_by")):
        bonuses += 1.0
    if _get(record, "verified_at") is not None:
        bonuses += 0.8
    if _has_value(_get(record, "verification_note")) or _has_value(_get(record, "verification_notes")):
        bonuses += 0.6
    if _has_value(_get(record, "evidence_photo_path")) or _has_value(_get(record, "image_url")):
        bonuses += 0.6
    if _has_value(_get(record, "field_note")) or _has_value(_get(record, "field_notes")):
        bonuses += 0.4

    return round(clamp(status_base + bonuses, 0.0, 10.0), 2)


def _score_market_anchor(record: Any, evidence_profile: Dict[str, Any]) -> float:
    # E5 = highest evidence → highest market anchor base score
    base = {
        "E5": 9.5,
        "E4": 8.2,
        "E3": 6.6,
        "E2": 4.4,
        "E1": 2.2,
    }[evidence_profile["tier"]]

    if _has_value(_get(record, "price_per_m2")):
        base += 0.3
    if _has_value(_get(record, "legal_status")):
        base += 0.2
    if _iot_signal_count(record) >= 2:
        base += 0.2

    return round(clamp(base, 0.0, 10.0), 2)


def _score_record_completeness(record: Any) -> Dict[str, Any]:
    fields = [
        ("property_type", _has_value(_get(record, "property_type")), 1.1),
        ("province_city", _has_value(_get(record, "province_city")), 1.0),
        ("district", _has_value(_get(record, "district")), 1.0),
        ("ward", _has_value(_get(record, "ward")), 0.4),
        ("area_m2", _get(record, "area_m2") not in (None, "", 0), 1.2),
        ("price", _get(record, "price") not in (None, "", 0), 1.3),
        ("price_per_m2", _get(record, "price_per_m2") not in (None, "", 0), 0.9),
        ("listing_date", _get(record, "listing_date") is not None, 0.5),
        ("legal_status", _has_value(_get(record, "legal_status")), 0.7),
        ("latitude", _get(record, "latitude") is not None or _get(record, "gps_lat") is not None, 0.8),
        ("longitude", _get(record, "longitude") is not None or _get(record, "gps_lng") is not None, 0.8),
        ("source_url", _has_value(_get(record, "source_url")), 0.7),
        ("image_or_evidence", _has_value(_get(record, "image_url")) or _has_value(_get(record, "evidence_photo_path")), 0.7),
        ("iot_signal", _iot_signal_count(record) > 0, 0.5),
    ]
    return _weighted_presence(fields)


def _score_timeliness(record: Any, reference_date: Optional[datetime] = None) -> float:
    candidate_dates = [
        _get(record, "verified_at"),
        _get(record, "source_collected_at"),
        _get(record, "listing_date"),
        _get(record, "collected_at"),
        _get(record, "capture_time"),
        _get(record, "created_at"),
    ]
    valid_dates = [_to_datetime(item) for item in candidate_dates if _to_datetime(item) is not None]
    if not valid_dates:
        return 4.0

    freshest = max(valid_dates)
    age_days = _days_since(freshest, reference_date=reference_date) or 0
    if age_days <= 30:
        return 10.0
    if age_days <= 90:
        return 9.0
    if age_days <= 180:
        return 7.5
    if age_days <= 365:
        return 6.0
    if age_days <= 730:
        return 4.0
    return 2.5


def _compute_penalty(record: Any, market_context: Optional[Dict[str, Any]] = None) -> float:
    penalty = 0.0
    price = _get(record, "price")
    area_m2 = _get(record, "area_m2")
    price_per_m2 = _get(record, "price_per_m2")
    verification_status = (_get(record, "verification_status", "unverified") or "unverified").lower()

    if price in (None, 0) or area_m2 in (None, 0):
        penalty += 1.4
    if verification_status == "rejected":
        penalty += 2.0
    if not _has_value(_get(record, "source_url")) and not _has_value(_get(record, "source_screenshot_path")):
        penalty += 0.4
    if _get(record, "latitude") is None and _get(record, "gps_lat") is None:
        penalty += 0.25
    if _get(record, "longitude") is None and _get(record, "gps_lng") is None:
        penalty += 0.25

    if market_context and price_per_m2 not in (None, 0):
        median_price = market_context.get("median_price_per_m2")
        if median_price:
            deviation = abs((float(price_per_m2) - median_price) / median_price)
            if deviation > 0.7:
                penalty += 1.2
            elif deviation > 0.4:
                penalty += 0.6

    return round(clamp(penalty, 0.0, 4.0), 2)


def _record_grade(score: float) -> str:
    if score >= 8.5:
        return "A"
    if score >= 7.0:
        return "B"
    if score >= 5.5:
        return "C"
    return "D"


def score_property_quality(
    record: Any,
    market_context: Optional[Dict[str, Any]] = None,
    reference_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    evidence_profile = classify_evidence_tier(record)

    # Priority 1: stored evidence_tier from DB (set by verify_scraped_data.py)
    # This takes precedence over everything else — verify_scraped_data.py has already
    # determined the correct tier, so respect it.
    if _get(record, "evidence_tier") in ("E1", "E2", "E3", "E4", "E5"):
        stored_tier = _get(record, "evidence_tier")
        # Config inverted: E5=highest, E1=lowest
        tier_config = {
            "E5": {"anchor_strength": 1.0, "evidence_weight": 1.0, "cap": 10.0},
            "E4": {"anchor_strength": 0.85, "evidence_weight": 0.85, "cap": 9.0},
            "E3": {"anchor_strength": 0.65, "evidence_weight": 0.65, "cap": 8.0},
            "E2": {"anchor_strength": 0.35, "evidence_weight": 0.45, "cap": 6.5},
            "E1": {"anchor_strength": 0.15, "evidence_weight": 0.2, "cap": 4.0},
        }
        if (
            stored_tier == "E5"
            and (_get(record, "collection_method", "") or "").lower() == "public_auction_asset_evidence"
        ):
            tier_config["E5"] = {"anchor_strength": 1.0, "evidence_weight": 1.0, "cap": 10.0}
        evidence_profile = {
            "tier": stored_tier,
            "note": (
                "E5 public auction asset evidence; auction anchor"
                if stored_tier == "E5"
                and (_get(record, "collection_method", "") or "").lower() == "public_auction_asset_evidence"
                else f"Stored tier from DB: {stored_tier}"
            ),
            **tier_config[stored_tier],
        }
    # Priority 2: batch_generator records without stored tier -> E1 (lowest, minimal evidence)
    elif _get(record, "source_access_method") == "batch_generator":
        evidence_profile = {
            "tier": "E1",
            "note": "E1: Batch-generated record with minimal evidence.",
            "anchor_strength": 0.15,
            "evidence_weight": 0.2,
            "cap": 4.0,
        }
    provenance = _score_provenance(record)
    completeness = _score_record_completeness(record)
    verification_score = _score_verification(record)
    market_anchor_score = _score_market_anchor(record, evidence_profile)
    timeliness_score = _score_timeliness(record, reference_date=reference_date)
    penalty = _compute_penalty(record, market_context=market_context)

    raw_rqs = (
        (0.25 * provenance["score"]) +
        (0.25 * verification_score) +
        (0.20 * market_anchor_score) +
        (0.15 * completeness["score"]) +
        (0.15 * timeliness_score) -
        penalty
    )
    rqs = clamp(raw_rqs, 0.0, evidence_profile["cap"])
    grade = _record_grade(rqs)

    # E4/E5 = high confidence tiers → boost training weight
    strong_tier_multiplier = 1.02 if evidence_profile["tier"] in {"E4", "E5"} else 0.92
    training_weight = clamp(
        ((rqs / 10.0) ** 1.45) * (0.65 + evidence_profile["evidence_weight"]) * strong_tier_multiplier,
        0.15,
        3.0,
    )

    return {
        "id": _get(record, "id"),
        "source_name": _get(record, "source_name", "Unknown"),
        "source_root": _source_root(record),
        "district": _get(record, "district"),
        "price": _get(record, "price"),
        "price_per_m2": _get(record, "price_per_m2"),
        "has_iot": _iot_signal_count(record) > 0,
        "iot_signal_count": _iot_signal_count(record),
        "origin": _get(record, "data_origin_type", "public_collected"),
        "verification_status": _get(record, "verification_status", "unverified"),
        "evidence_tier": evidence_profile["tier"],
        "evidence_note": evidence_profile["note"],
        "evidence_weight": evidence_profile["evidence_weight"],
        "evidence_cap": evidence_profile["cap"],
        "anchor_flag": evidence_profile["tier"] in {"E4", "E5"},
        "provenance_score": round(provenance["score"], 2),
        "verification_score": round(verification_score, 2),
        "market_anchor_score": round(market_anchor_score, 2),
        "completeness_score": round(completeness["score"], 2),
        "timeliness_score": round(timeliness_score, 2),
        "penalty": penalty,
        "rqs": round(rqs, 2),
        "quality_score": round(rqs, 2),
        "record_grade": grade,
        "training_weight": round(training_weight, 4),
        "missing_fields": completeness["missing_fields"],
        "provided_fields": completeness["provided_fields"],
    }


def build_training_quality_profiles(records: Sequence[Any]) -> List[Dict[str, Any]]:
    prices_per_m2 = [float(_get(record, "price_per_m2", 0) or 0) for record in records if _get(record, "price_per_m2", None)]
    market_context = {
        "median_price_per_m2": safe_median(prices_per_m2, default=0.0),
        "avg_price_per_m2": safe_mean(prices_per_m2, default=0.0),
    }
    return [score_property_quality(record, market_context=market_context) for record in records]


def summarize_training_quality_profiles(profiles: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not profiles:
        return {
            "profile_count": 0,
            "avg_rqs": 0.0,
            "median_rqs": 0.0,
            "avg_training_weight": 0.0,
            "evidence_distribution": {},
            "grade_distribution": {},
            "anchor_rate": 0.0,
        }

    evidence_distribution: Dict[str, int] = {}
    grade_distribution: Dict[str, int] = {}
    for profile in profiles:
        evidence_distribution[profile["evidence_tier"]] = evidence_distribution.get(profile["evidence_tier"], 0) + 1
        grade_distribution[profile["record_grade"]] = grade_distribution.get(profile["record_grade"], 0) + 1

    return {
        "profile_count": len(profiles),
        "avg_rqs": round(safe_mean([item["rqs"] for item in profiles]), 2),
        "median_rqs": round(safe_median([item["rqs"] for item in profiles]), 2),
        "avg_training_weight": round(safe_mean([item["training_weight"] for item in profiles]), 4),
        "max_training_weight": round(max(item["training_weight"] for item in profiles), 4),
        "min_training_weight": round(min(item["training_weight"] for item in profiles), 4),
        "evidence_distribution": evidence_distribution,
        "grade_distribution": grade_distribution,
        "anchor_rate": round(sum(1 for item in profiles if item["anchor_flag"]) / len(profiles), 4),
    }

def _location_similarity(request_data: Dict[str, Any], record: Any) -> float:
    province_match = (_get(record, "province_city") or "") == (request_data.get("province_city") or "")
    district_match = (_get(record, "district") or "") == (request_data.get("district") or "")
    ward_match = bool(request_data.get("ward")) and request_data.get("ward") == _get(record, "ward")

    score = 0.45
    if province_match:
        score += 0.25
    if district_match:
        score += 0.2
    if ward_match:
        score += 0.1
    return clamp(score, 0.3, 1.0)


def _area_similarity(request_data: Dict[str, Any], record: Any) -> float:
    target_area = float(request_data.get("area_m2") or 0)
    record_area = float(_get(record, "area_m2") or 0)
    if target_area <= 0 or record_area <= 0:
        return 0.35
    deviation = abs(record_area - target_area) / max(target_area, 1.0)
    return clamp(1.0 - deviation, 0.25, 1.0)


def _support_market_stats(properties: Sequence[Any]) -> Dict[str, Any]:
    prices_per_m2 = [float(_get(item, "price_per_m2", 0) or 0) for item in properties if _get(item, "price_per_m2", None)]
    if len(prices_per_m2) >= 2:
        avg_price = safe_mean(prices_per_m2)
        volatility = pstdev(prices_per_m2) / avg_price if avg_price else 0.0
    else:
        avg_price = safe_mean(prices_per_m2, default=0.0)
        volatility = 0.12

    return {
        "comparable_count": len(properties),
        "avg_price_per_m2": round(avg_price, 0) if avg_price else None,
        "median_price_per_m2": round(safe_median(prices_per_m2), 0) if prices_per_m2 else None,
        "local_price_volatility": round(volatility, 4),
    }


def _support_alpha(request_data: Dict[str, Any], profile: Dict[str, Any], record: Any) -> float:
    similarity = _area_similarity(request_data, record) * _location_similarity(request_data, record)
    time_weight = clamp(profile["timeliness_score"] / 10.0, 0.25, 1.0)
    quality_weight = clamp(profile["rqs"] / 10.0, 0.15, 1.0)
    evidence_weight = profile["evidence_weight"]
    alpha = similarity * time_weight * evidence_weight * quality_weight
    return round(clamp(alpha, 0.02, 1.0), 4)


def score_support_volume(neff_value: float) -> Dict[str, Any]:
    if neff_value >= 800:
        score = 10.0
        note = "Nguon du lieu hieu dung rat manh, vuot moc 800 mau quy doi."
    elif neff_value >= 300:
        score = 8.0
        note = "Nguon du lieu hieu dung tot, dat moc 300 mau quy doi."
    elif neff_value >= 100:
        score = 6.0
        note = "Nguon du lieu hieu dung dat muc toi thieu 100 mau quy doi."
    elif neff_value >= 30:
        score = 4.5
        note = "Da co tap ho tro nhung chua dat nguong 100 mau quy doi."
    elif neff_value >= 10:
        score = 2.8
        note = "Neff thap, chi nen xem nhu tap tham khao co dieu kien."
    else:
        score = 1.2
        note = "Neff rat thap, can canh bao manh khi dinh gia tu dong."
    return {"score": score, "note": note, "effective_sample_size": round(neff_value, 2)}


def _grade_from_score(score: float) -> Dict[str, str]:
    if score >= 8.5:
        return {"grade": "A", "label": "Rat cao", "policy": "Cho phep du bao tu dong muc cao va co the dua vao train voi uu tien cao."}
    if score >= 7.0:
        return {"grade": "B", "label": "Cao", "policy": "Cho phep du bao tu dong nhung van can doi chieu dinh ky."}
    if score >= 5.5:
        return {"grade": "C", "label": "Trung binh", "policy": "Chi nen dung co canh bao ro va uu tien bo sung bang chung truoc khi ket luan."}
    return {"grade": "D", "label": "Thap", "policy": "Khong du dieu kien cho dinh gia tu dong chuan; chi nen xem nhu muc tham khao."}


def build_data_quality_assessment(
    request_data: Dict[str, Any],
    support_properties: Sequence[Any],
    district_support_count: int,
    province_support_count: int,
    property_type_support_count: int,
) -> Dict[str, Any]:
    input_profile = score_input_completeness(request_data)
    market_context = _support_market_stats(support_properties)

    property_scores = [score_property_quality(item, market_context=market_context) for item in support_properties]
    weighted_profiles: List[Dict[str, Any]] = []
    for item, profile in zip(support_properties, property_scores):
        alpha = _support_alpha(request_data, profile, item)
        weighted_profiles.append({**profile, "alpha": alpha})

    neff_value = sum(item["alpha"] * item["evidence_weight"] * (item["rqs"] / 10.0) for item in weighted_profiles)
    volume_info = score_support_volume(neff_value)

    alpha_sum = sum(item["alpha"] for item in weighted_profiles) or 1.0
    support_quality = sum(item["alpha"] * item["rqs"] for item in weighted_profiles) / alpha_sum if weighted_profiles else 3.0
    support_completeness = sum(item["alpha"] * item["completeness_score"] for item in weighted_profiles) / alpha_sum if weighted_profiles else 4.0
    completeness_score = clamp((0.55 * input_profile["score"]) + (0.45 * support_completeness), 0.0, 10.0)

    base_score = (
        (0.35 * volume_info["score"]) +
        (0.40 * support_quality) +
        (0.25 * completeness_score)
    )

    evidence_distribution: Dict[str, int] = {}
    for profile in weighted_profiles:
        evidence_distribution[profile["evidence_tier"]] = evidence_distribution.get(profile["evidence_tier"], 0) + 1

    anchor_count = sum(1 for item in weighted_profiles if item["anchor_flag"])
    anchor_share = (anchor_count / len(weighted_profiles)) if weighted_profiles else 0.0
    median_rqs = safe_median([item["rqs"] for item in weighted_profiles], default=0.0)
    independent_source_count = len({_source_root(item) for item in support_properties}) if support_properties else 0

    capped_score = base_score
    applied_rules: List[str] = []
    warnings: List[str] = []
    strengths: List[str] = []
    next_actions: List[str] = []

    if anchor_count == 0:
        capped_score = min(capped_score, 7.0)
        applied_rules.append("cap_no_anchor_E1_E2")
        warnings.append("Khong co ho so E1/E2 trong tap doi chieu; he thong khong duoc xep muc tin cay qua cao.")
        next_actions.append("Bo sung ho so co bang chung field-survey, giao dich neo hoac xac minh doc lap manh hon.")
    else:
        strengths.append("Tap doi chieu da co ho so E1/E2, giup tang kha nang neo vao thi truong thuc te hon.")

    if neff_value < 30:
        capped_score = min(capped_score, 5.5)
        applied_rules.append("cap_low_effective_sample")
        warnings.append("Neff duoi 30, nghia la tap so sanh huu dung qua nho de ket luan chuan hoa.")
        next_actions.append("Mo rong tap doi chieu theo khu vuc vi mo va bo sung nguon xac minh doc lap.")
    elif neff_value >= 100:
        strengths.append("Neff dat nguong on hon cho suy luan khu vuc.")

    if median_rqs < 5:
        capped_score = min(capped_score, 5.4)
        applied_rules.append("reference_only_low_median_rqs")
        warnings.append("RQS trung vi cua tap doi chieu duoi 5; chi nen xem ket qua nhu tham khao.")
        next_actions.append("Loc bo cac ban ghi E4/E5 chat luong thap va uu tien ban ghi co truy vet ro rang hon.")
    else:
        strengths.append("RQS trung vi cua tap doi chieu dat nguong co the su dung cho suy luan co kiem soat.")

    if independent_source_count <= 1 and anchor_count == 0:
        capped_score = min(capped_score, 4.8)
        applied_rules.append("single_source_bias_cap")
        warnings.append("Tap doi chieu co dau hieu thien lech don nguon; khong duoc xem la dong thuan doc lap.")
        next_actions.append("Bo sung them nguon khac goc thong tin va xac minh bang phieu khao sat/doi chieu offline.")
    elif independent_source_count >= 3:
        strengths.append("Tap doi chieu da co nhieu nguon goc khac nhau, giam bot rui ro lech don nguon.")

    if input_profile["score"] < 7:
        warnings.append("Ho so dau vao chua du day du; cac truong phap ly, toa do, IoT hoac ward con thieu.")
        next_actions.append("Bo sung them truong dau vao de thu hep khoang gia va tang kha nang giai thich.")
    else:
        strengths.append("Ho so dau vao da kha day du cho quy trinh so sanh va giai thich ket qua.")

    if market_context["local_price_volatility"] and market_context["local_price_volatility"] > 0.18:
        warnings.append("Do bien dong gia/m2 trong cum so sanh cao; interval can duoc mo rong de tranh ao tuong chac chan.")
        next_actions.append("Tach them cum theo phan khuc, ward hoac cua so thoi gian ngan hon de giam bien dong.")
    else:
        strengths.append("Do bien dong gia/m2 trong tap doi chieu nam trong muc chap nhan duoc.")

    grade_info = _grade_from_score(round(capped_score, 2))
    output_mode = "reference_only" if any(rule.startswith("reference_only") for rule in applied_rules) or grade_info["grade"] == "D" else "standard_with_warning"
    if grade_info["grade"] in {"A", "B"} and not applied_rules:
        output_mode = "standard_ready"

    sample_records = sorted(weighted_profiles, key=lambda item: item.get("alpha", 0), reverse=True)[:8]

    return {
        "standard_name": "CVX-BDS/IoT 1.1-VN Research Extension",
        "overall_score": round(capped_score, 2),
        "base_score_before_caps": round(base_score, 2),
        "confidence_grade": grade_info["grade"],
        "confidence_label": grade_info["label"],
        "recommended_policy": grade_info["policy"],
        "output_mode": output_mode,
        "component_scores": {
            "support_volume": round(volume_info["score"], 2),
            "data_quality": round(support_quality, 2),
            "data_completeness": round(completeness_score, 2),
        },
        "component_weights": {
            "support_volume": 0.35,
            "data_quality": 0.40,
            "data_completeness": 0.25,
        },
        "support_statistics": {
            "district_support_count": district_support_count,
            "province_support_count": province_support_count,
            "property_type_support_count": property_type_support_count,
            "comparable_count": len(support_properties),
            "effective_sample_size": round(neff_value, 2),
            "avg_support_quality": round(support_quality, 2),
            "avg_support_completeness": round(support_completeness, 2),
            "median_rqs": round(median_rqs, 2),
            "anchor_count": anchor_count,
            "anchor_share": round(anchor_share, 4),
            "independent_source_count": independent_source_count,
            "self_collected_support_count": sum(1 for item in weighted_profiles if item["origin"] == "self_collected"),
            "iot_support_count": sum(1 for item in weighted_profiles if item["has_iot"]),
            "evidence_distribution": evidence_distribution,
            **market_context,
        },
        "input_profile": input_profile,
        "rules_applied": applied_rules,
        "strengths": strengths[:6],
        "warnings": warnings[:6],
        "next_actions": next_actions[:6],
        "sample_records": sample_records,
    }


def build_adaptive_interval(
    predicted_price: float,
    mae_value: float,
    support_properties: Sequence[Any],
    overall_score: Optional[float] = None,
    assessment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    market_stats = _support_market_stats(support_properties)
    confidence_score = overall_score if overall_score is not None else (assessment or {}).get("overall_score", 5.0)
    support_stats = (assessment or {}).get("support_statistics", {})
    grade = (assessment or {}).get("confidence_grade") or _grade_from_score(confidence_score)["grade"]
    output_mode = (assessment or {}).get("output_mode", "standard_with_warning")

    neff_value = support_stats.get("effective_sample_size", len(support_properties))
    anchor_share = support_stats.get("anchor_share", 0.0)
    median_rqs = support_stats.get("median_rqs", confidence_score)

    model_ratio = clamp((mae_value / predicted_price) if predicted_price else 0.09, 0.03, 0.18)
    volatility_ratio = clamp(market_stats["local_price_volatility"] or 0.12, 0.04, 0.22)
    trust_gap = clamp((10 - confidence_score) / 100.0, 0.02, 0.12)

    if grade == "A":
        band_min, band_max = 0.03, 0.06
    elif grade == "B":
        band_min, band_max = 0.05, 0.08
    elif grade == "C":
        band_min, band_max = 0.08, 0.12
    else:
        band_min, band_max = 0.12, 0.18

    scarcity_multiplier = 1.0
    if neff_value < 30:
        scarcity_multiplier = 1.28
    elif neff_value < 100:
        scarcity_multiplier = 1.12

    anchor_multiplier = 1.0
    if anchor_share == 0:
        anchor_multiplier = 1.14
    elif anchor_share < 0.25:
        anchor_multiplier = 1.07
    elif anchor_share > 0.5:
        anchor_multiplier = 0.94

    quality_multiplier = 1.0
    if median_rqs < 5:
        quality_multiplier = 1.1

    raw_ratio = ((0.45 * model_ratio) + (0.35 * volatility_ratio) + (0.20 * trust_gap))
    interval_ratio = raw_ratio * scarcity_multiplier * anchor_multiplier * quality_multiplier
    if output_mode == "reference_only":
        interval_ratio = max(interval_ratio, 0.12)

    interval_ratio = clamp(interval_ratio, band_min, band_max)
    lower = predicted_price * (1 - interval_ratio)
    upper = predicted_price * (1 + interval_ratio)

    return {
        "confidence_low": round(lower, 0),
        "confidence_high": round(upper, 0),
        "interval_ratio": round(interval_ratio, 4),
        "interval_width": round(upper - lower, 0),
        "model_error_ratio": round(model_ratio, 4),
        "local_volatility_ratio": round(volatility_ratio, 4),
        "trust_gap_ratio": round(trust_gap, 4),
        "design_band": {"min": band_min, "max": band_max},
        "scarcity_multiplier": round(scarcity_multiplier, 3),
        "anchor_multiplier": round(anchor_multiplier, 3),
        "quality_multiplier": round(quality_multiplier, 3),
        "note": (
            "Prediction interval follows the project standard: it tightens only when both data trust and local market support improve."
        ),
    }


def _choose_support_indices(
    idx: int,
    record: Any,
    district_groups: Dict[tuple, List[int]],
    province_groups: Dict[tuple, List[int]],
    type_groups: Dict[str, List[int]],
) -> List[int]:
    province_key = ((_get(record, "province_city") or "").strip(), (_get(record, "property_type") or "").strip())
    district_key = (
        (_get(record, "province_city") or "").strip(),
        (_get(record, "district") or "").strip(),
        (_get(record, "property_type") or "").strip(),
    )
    property_type = (_get(record, "property_type") or "").strip()

    district_support = [item for item in district_groups.get(district_key, []) if item != idx]
    if len(district_support) >= 5:
        return district_support

    province_support = [item for item in province_groups.get(province_key, []) if item != idx]
    if len(province_support) >= 5:
        return province_support

    return [item for item in type_groups.get(property_type, []) if item != idx]


def build_confidence_training_rows(records: Sequence[Any]) -> List[Dict[str, Any]]:
    """
    Build a classifier-ready dataset for the stage-1 confidence model.

    The feature set is intentionally case-oriented so the same structure can be
    reused at prediction time when we score a brand-new property request.
    """
    records = list(records)
    if not records:
        return []

    profiles = build_training_quality_profiles(records)

    district_groups: Dict[tuple, List[int]] = {}
    province_groups: Dict[tuple, List[int]] = {}
    type_groups: Dict[str, List[int]] = {}

    for idx, record in enumerate(records):
        district_key = (
            (_get(record, "province_city") or "").strip(),
            (_get(record, "district") or "").strip(),
            (_get(record, "property_type") or "").strip(),
        )
        province_key = (
            (_get(record, "province_city") or "").strip(),
            (_get(record, "property_type") or "").strip(),
        )
        property_type = (_get(record, "property_type") or "").strip()
        district_groups.setdefault(district_key, []).append(idx)
        province_groups.setdefault(province_key, []).append(idx)
        type_groups.setdefault(property_type, []).append(idx)

    rows: List[Dict[str, Any]] = []
    for idx, (record, profile) in enumerate(zip(records, profiles)):
        support_indices = _choose_support_indices(idx, record, district_groups, province_groups, type_groups)
        support_profiles = [profiles[item] for item in support_indices]
        support_records = [records[item] for item in support_indices]

        support_prices = [float(item["price_per_m2"]) for item in support_profiles if item.get("price_per_m2")]
        target_price = float(profile["price_per_m2"] or 0)
        local_median_price = safe_median(support_prices, default=target_price or 0.0)
        local_price_gap_ratio = (
            abs(target_price - local_median_price) / local_median_price
            if local_median_price and target_price
            else 0.0
        )

        support_anchor_share = (
            sum(1 for item in support_profiles if item["anchor_flag"]) / len(support_profiles)
            if support_profiles
            else 0.0
        )
        support_avg_rqs = safe_mean([item["rqs"] for item in support_profiles], default=profile["rqs"])
        support_median_rqs = safe_median([item["rqs"] for item in support_profiles], default=profile["rqs"])
        support_completeness_score = safe_mean(
            [item["completeness_score"] for item in support_profiles],
            default=profile["completeness_score"],
        )
        support_volatility = _support_market_stats(support_records).get("local_price_volatility", 0.12)
        support_source_count = len({_source_root(item) for item in support_records}) if support_records else 1
        effective_sample_size = sum(
            item["evidence_weight"] * max(item["rqs"] / 10.0, 0.1)
            for item in support_profiles
        )
        volume_info = score_support_volume(effective_sample_size)

        row = {
            "support_volume_score": round(volume_info["score"], 2),
            "support_quality_score": round(support_avg_rqs, 2),
            "support_completeness_score": round(support_completeness_score, 2),
            "support_anchor_share": round(support_anchor_share, 4),
            "support_source_count": support_source_count,
            "support_volatility": round(support_volatility, 4),
            "district_support_count": len(district_groups.get((
                (_get(record, "province_city") or "").strip(),
                (_get(record, "district") or "").strip(),
                (_get(record, "property_type") or "").strip(),
            ), [])),
            "province_support_count": len(province_groups.get((
                (_get(record, "province_city") or "").strip(),
                (_get(record, "property_type") or "").strip(),
            ), [])),
            "property_type_support_count": len(type_groups.get((_get(record, "property_type") or "").strip(), [])),
            "effective_sample_size": round(effective_sample_size, 2),
            "input_completeness_score": round(profile["completeness_score"], 2),
            "input_iot_signal_count": profile["iot_signal_count"],
            "input_has_legal_status": 1 if _has_value(_get(record, "legal_status")) else 0,
            "input_has_coordinates": 1 if (_get(record, "latitude") is not None or _get(record, "gps_lat") is not None) and (_get(record, "longitude") is not None or _get(record, "gps_lng") is not None) else 0,
            "input_has_furnishing": 1 if _has_value(_get(record, "furnishing")) else 0,
            "local_price_gap_ratio": round(clamp(local_price_gap_ratio, 0.0, 3.0), 4),
            "self_collected_hint": 1 if profile["origin"] == "self_collected" else 0,
            "rule_score": round(profile["rqs"], 2),
            "rule_grade": profile["record_grade"],
            "rule_evidence_tier": profile["evidence_tier"],
        }
        rows.append(row)

    return rows


def build_case_confidence_features(request_data: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the same stage-1 feature space for a brand-new valuation request.
    """
    support_stats = assessment.get("support_statistics", {})
    component_scores = assessment.get("component_scores", {})
    input_profile = assessment.get("input_profile", {})

    return {
        "support_volume_score": round(component_scores.get("support_volume", 0.0), 2),
        "support_quality_score": round(component_scores.get("data_quality", 0.0), 2),
        "support_completeness_score": round(support_stats.get("avg_support_completeness", input_profile.get("score", 0.0)), 2),
        "support_anchor_share": round(support_stats.get("anchor_share", 0.0), 4),
        "support_source_count": int(support_stats.get("independent_source_count", 0) or 0),
        "support_volatility": round(support_stats.get("local_price_volatility", 0.12) or 0.12, 4),
        "district_support_count": int(support_stats.get("district_support_count", 0) or 0),
        "province_support_count": int(support_stats.get("province_support_count", 0) or 0),
        "property_type_support_count": int(support_stats.get("property_type_support_count", 0) or 0),
        "effective_sample_size": round(support_stats.get("effective_sample_size", 0.0) or 0.0, 2),
        "input_completeness_score": round(input_profile.get("score", 0.0), 2),
        "input_iot_signal_count": sum(
            1 for key in ["noise_level", "temperature", "humidity", "light_level", "gps_lat", "gps_lng"]
            if request_data.get(key) is not None
        ),
        "input_has_legal_status": 1 if _has_value(request_data.get("legal_status")) else 0,
        "input_has_coordinates": 1 if request_data.get("latitude") is not None or request_data.get("gps_lat") is not None else 0,
        "input_has_furnishing": 1 if _has_value(request_data.get("furnishing")) else 0,
        "local_price_gap_ratio": 0.0,
        "self_collected_hint": 0,
    }


def build_assessment_tree(assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a tree-shaped explanation object for UI visualization.
    """
    support_stats = assessment.get("support_statistics", {})
    component_scores = assessment.get("component_scores", {})
    input_profile = assessment.get("input_profile", {})

    return {
        "name": "CVX-BDS/IoT Research Flow",
        "children": [
            {
                "name": "Input Profile",
                "value": round(input_profile.get("score", 0.0), 2),
                "children": [
                    {"name": "Property identity", "value": 1 if "property_type" in input_profile.get("provided_fields", []) else 0},
                    {"name": "Location traceability", "value": 1 if "latitude_or_gps" in input_profile.get("provided_fields", []) else 0},
                    {"name": "IoT signals", "value": sum(1 for key in ["noise_level", "temperature", "humidity", "light_level"] if key in input_profile.get("provided_fields", []))},
                ],
            },
            {
                "name": "Support Evidence",
                "value": round(component_scores.get("data_quality", 0.0), 2),
                "children": [
                    {"name": "Effective sample size", "value": support_stats.get("effective_sample_size", 0)},
                    {"name": "Anchor share", "value": support_stats.get("anchor_share", 0)},
                    {"name": "Independent sources", "value": support_stats.get("independent_source_count", 0)},
                ],
            },
            {
                "name": "Decision Output",
                "value": round(assessment.get("overall_score", 0.0), 2),
                "children": [
                    {"name": "Grade", "value": assessment.get("confidence_grade", "D")},
                    {"name": "Output mode", "value": assessment.get("output_mode", "reference_only")},
                    {"name": "Rules applied", "value": len(assessment.get("rules_applied", []))},
                ],
            },
        ],
    }
