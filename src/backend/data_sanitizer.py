"""
Data Sanitizer — Canonical Layer cho tất cả entry points ghi vào database.

Mục đích: Đảm bảo dữ liệu đầu vào SẠCH trước khi vào DB.
Thay thế việc validate/ràng buộc rải rác ở nhiều nơi bằng 1 canonical layer.

Entry points sử dụng module này:
  1. Auth (register/login)         → User input
  2. Data collector (scrapers)     → Web scraped data
  3. Import script (CSV/JSON)      → Manual entry
  4. API routes (pydantic)         → REST input
  5. IoT/field survey             → Sensor data

Quy tắc:
  - MỌI data ghi vào DB phải đi qua sanitize_property() hoặc sanitize_user()
  - Canonical enum values: CHỈ các giá trị định nghĩa sẵn được phép
  - Province/district: CHỈ 6 quận trong scope mới được insert
  - Giá trị NULL: phải là None (Python), không phải chuỗi "null", "none", v.v.
  - Price/area: phải > 0, hoặc None (không phải 0)

Usage:
    from src.backend.data_sanitizer import (
        sanitize_property,
        sanitize_user,
        PropertySanitizer,
        UserSanitizer,
        CANONICAL_PROPERTY_TYPES,
        CANONICAL_PROVINCES,
        CANONICAL_LEGAL_STATUS,
        CANONICAL_FURNISHING,
        CANONICAL_EVIDENCE_TIERS,
        CANONICAL_RECORD_STATUS,
        CANONICAL_DATA_ORIGIN,
        CANONICAL_COLLECTION_METHODS,
        CANONICAL_SOURCE_ACCESS_METHODS,
        CANONICAL_AREA_TYPES,
        SCOPE_6_DISTRICTS,
        ValidationError,
    )
"""

from __future__ import annotations

import re
import hashlib
from datetime import datetime
from typing import Any, Optional, TypedDict


# ==============================================================================
# CANONICAL ENUM DOMAINS
# ==============================================================================

# property_type: CHỈ 5 giá trị này được phép trong DB
CANONICAL_PROPERTY_TYPES: frozenset[str] = frozenset([
    "house", "apartment", "land", "townhouse", "villa",
])

# Province: CHỈ 2 tỉnh/thành trong scope
CANONICAL_PROVINCES: frozenset[str] = frozenset([
    "Hà Nội",
    "TP. Hồ Chí Minh",
])

# 6 quận trong scope (province, district)
SCOPE_6_DISTRICTS: frozenset[tuple[str, str]] = frozenset([
    ("Hà Nội", "Quận Cầu Giấy"),
    ("Hà Nội", "Quận Thanh Xuân"),
    ("Hà Nội", "Quận Đống Đa"),
    ("TP. Hồ Chí Minh", "Quận 7"),
    ("TP. Hồ Chí Minh", "Quận Bình Thạnh"),
    ("TP. Hồ Chí Minh", "Quận Tân Bình"),
])

# district names: canonical form (không có tiền tố "Quận")
CANONICAL_DISTRICTS: frozenset[str] = frozenset([
    "Quận Cầu Giấy", "Quận Thanh Xuân", "Quận Đống Đa",
    "Quận 7", "Quận Bình Thạnh", "Quận Tân Bình",
])

# Evidence tier: E1-E5
CANONICAL_EVIDENCE_TIERS: frozenset[str] = frozenset([
    "E1", "E2", "E3", "E4", "E5",
])

# Record status: raw, pending_review, verified, rejected, archived
CANONICAL_RECORD_STATUS: frozenset[str] = frozenset([
    "raw", "pending_review", "verified", "rejected", "archived",
])

# Data origin type
CANONICAL_DATA_ORIGIN: frozenset[str] = frozenset([
    "public_collected", "self_collected", "system_demo",
])

# Collection method
CANONICAL_COLLECTION_METHODS: frozenset[str] = frozenset([
    "google_form_verified",
    "manual_verified_from_public_listing",
    "field_survey",
    "app_user_submission",
    "smartphone_sensor_capture",
    "manual_entry",
])

# Source access method (canonical: scraper | api | batch_generator | demo_seed | manual_entry)
CANONICAL_SOURCE_ACCESS_METHODS: frozenset[str] = frozenset([
    "scraper", "api", "batch_generator", "demo_seed", "manual_entry",
])

# Area type
CANONICAL_AREA_TYPES: frozenset[str] = frozenset([
    "urban_center", "suburban", "urban_fringe", "rural",
])

# Legal status: canonical values (EN only)
CANONICAL_LEGAL_STATUS: frozenset[str] = frozenset([
    "pending",
    "unknown",
    "full_ownership",
    "ownership_certificate",
    "land_use_right",
    "leasehold",
])

# Legal status legacy mapping: VN → EN canonical
LEGAL_STATUS_VN_TO_EN: dict[str, str] = {
    # Certificate types
    "sổ đỏ": "ownership_certificate",
    "sổ hồng": "land_use_right",
    "sổ đỏ chính chủ": "ownership_certificate",
    "sổ hồng chính chủ": "land_use_right",
    "hợp đồng mua bán": "full_ownership",
    "hợp đồng": "full_ownership",
    "còn sổ": "ownership_certificate",
    "chưa có sổ": "pending",
    "đang chờ sổ": "pending",
    # English aliases
    "pink_book": "ownership_certificate",
    "green_book": "land_use_right",
    "land_use_right_certificate": "land_use_right",
    "ownership_certificate": "ownership_certificate",
    "private": "full_ownership",
    "shared": "leasehold",
    "state": "unknown",
}

# Furnishing: canonical values
CANONICAL_FURNISHING: frozenset[str] = frozenset([
    "null", "none", "basic", "partial", "full",
])

# Furnishing mapping: various representations → canonical
FURNISHING_TO_CANONICAL: dict[str, str] = {
    "": "null",
    "null": "null",
    "none": "none",
    "null": "null",
    "None": "null",
    "basic": "basic",
    "partial": "partial",
    "full": "full",
    "fully_furnished": "full",
    "semi_furnished": "partial",
    "unfurnished": "none",
    "chưa có": "null",
    "chưa nội thất": "none",
    "nội thất cơ bản": "basic",
    "nội thất một phần": "partial",
    "nội thất đầy đủ": "full",
}

# Evidence tier confidence
CONFIDENCE_VALUES: frozenset[str] = frozenset([
    "low", "medium", "high",
])

# Source access method mapping: old names → canonical
SOURCE_METHOD_TO_CANONICAL: dict[str, str] = {
    "": "batch_generator",
    "playwright": "scraper",
    "playwright_stealth": "scraper",
    "api": "api",
    "batch_generator": "batch_generator",
    "manual_entry": "manual_entry",
    "demo_seed": "demo_seed",
    "scraper": "scraper",
}


# ==============================================================================
# EXCEPTIONS
# ==============================================================================

class ValidationError(Exception):
    """Raised when input data fails sanitization rules."""

    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"ValidationError[{field}]: {reason} (got {value!r})")


class ScopeViolationError(ValidationError):
    """Raised when data is outside allowed scope."""

    def __init__(self, field: str, value: Any, allowed: set):
        self.allowed = allowed
        super().__init__(
            field, value,
            f"value outside scope. Allowed: {sorted(allowed)!r}"
        )


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def _to_none(value: Any) -> Optional[Any]:
    """Convert various representations of NULL to None."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped in ("", "null", "none", "na", "n/a", "-", "unknown"):
            return None
    return value


def _to_float(value: Any, ge: Optional[float] = None,
              le: Optional[float] = None) -> Optional[float]:
    """Convert to float with optional range check. Returns None for invalid."""
    if _to_none(value) is None:
        return None
    try:
        f = float(value)
        if ge is not None and f < ge:
            return None
        if le is not None and f > le:
            return None
        return f
    except (ValueError, TypeError):
        return None


def _to_int(value: Any, ge: Optional[int] = None,
            le: Optional[int] = None) -> Optional[int]:
    """Convert to int with optional range check. Returns None for invalid."""
    if _to_none(value) is None:
        return None
    try:
        i = int(float(value))  # handles "3.0" → 3
        if ge is not None and i < ge:
            return None
        if le is not None and i > le:
            return None
        return i
    except (ValueError, TypeError):
        return None


def _to_str(value: Any, maxlen: int = 255,
            strip: bool = True) -> Optional[str]:
    """Convert to sanitized string. Returns None for empty/invalid."""
    if _to_none(value) is None:
        return None
    s = str(value)
    if strip:
        s = s.strip()
    if s == "":
        return None
    if len(s) > maxlen:
        s = s[:maxlen]
    return s


def _canonical_enum(value: Any, canonical_set: frozenset[str],
                    default: str) -> str:
    """Map a value to canonical enum, return default if not recognized."""
    if _to_none(value) is None:
        return default
    v = str(value).strip().lower()
    # Direct match
    for c in canonical_set:
        if c.lower() == v:
            return c
    return default


# ==============================================================================
# PROPERTY SANITIZER
# ==============================================================================

class PropertySanitizer:
    """
    Canonical sanitizer cho property data.
    Dùng CHO TẤT CẢ entry points: scraper, import, API, IoT.

    Mỗi field có:
      - input: giá trị thô từ source
      - output: giá trị đã sanitize, sẵn sàng insert vào DB
      - action: drop (None), coerce (cast), normalize (map), reject (raise)

    Rules:
      ┌─────────────────────┬──────────┬──────────────────────────────────┐
      │ Field               │ Action   │ Rule                             │
      ├─────────────────────┼──────────┼──────────────────────────────────┤
      │ property_type       │ REJECT   │ Phải là 1 trong 5 canonical      │
      │ province_city       │ REJECT   │ Phải là Hà Nội hoặc TP.HCM      │
      │ district            │ REJECT   │ Phải là 1 trong 6 quận scope    │
      │ area_m2             │ REJECT   │ > 10 AND <= 20000                │
      │ price               │ REJECT   │ >= 100_000_000 (100M VND)       │
      │ price_per_m2        │ COERCE   │ > 0 AND <= 500_000_000          │
      │ bedrooms/bathrooms  │ COERCE   │ >= 0 AND <= 50                  │
      │ floor_count         │ COERCE   │ >= 1 AND <= 100                 │
      │ frontage_m          │ COERCE   │ > 0 AND <= 200                  │
      │ legal_status        │ NORMALIZE│ Map VN → EN canonical            │
      │ furnishing          │ NORMALIZE│ Map các variants → canonical     │
      │ evidence_tier        │ NORMALIZE│ E1-E5, default E5              │
      │ source_access_method │ NORMALIZE│ playwright→scraper, default batch │
      │ ward                │ COERCE   │ None nếu empty                 │
      │ street_or_project   │ COERCE   │ None nếu empty                 │
      │ latitude            │ COERCE   │ -90 to 90                       │
      │ longitude           │ COERCE   │ -180 to 180                     │
      │ source_name         │ REJECT   │ Không được NULL                 │
      └─────────────────────┴──────────┴──────────────────────────────────┘
    """

    # VN province name normalization
    PROVINCE_ALIASES: dict[str, str] = {
        "hn": "Hà Nội",
        "hanoi": "Hà Nội",
        "ha noi": "Hà Nội",
        "hồ chí minh": "TP. Hồ Chí Minh",
        "ho chi minh": "TP. Hồ Chí Minh",
        "hcm": "TP. Hồ Chí Minh",
        "tp hcm": "TP. Hồ Chí Minh",
        "tp. hcm": "TP. Hồ Chí Minh",
        "thành phố hồ chí minh": "TP. Hồ Chí Minh",
        "tp hồ chí minh": "TP. Hồ Chí Minh",
    }

    # VN district normalization
    DISTRICT_ALIASES: dict[str, str] = {
        "cầu giấy": "Quận Cầu Giấy",
        "cau giay": "Quận Cầu Giấy",
        "quận cầu giấy": "Quận Cầu Giấy",
        "quan cau giay": "Quận Cầu Giấy",
        "thanh xuân": "Quận Thanh Xuân",
        "quận thanh xuân": "Quận Thanh Xuân",
        "đống đa": "Quận Đống Đa",
        "dong da": "Quận Đống Đa",
        "quận đống đa": "Quận Đống Đa",
        "quan dong da": "Quận Đống Đa",
        "quận 7": "Quận 7",
        "quan 7": "Quận 7",
        "district 7": "Quận 7",
        "q7": "Quận 7",
        "bình thạnh": "Quận Bình Thạnh",
        "binh thanh": "Quận Bình Thạnh",
        "quận bình thạnh": "Quận Bình Thạnh",
        "bình thạnh": "Quận Bình Thạnh",
        "tân bình": "Quận Tân Bình",
        "tan binh": "Quận Tân Bình",
        "quận tân bình": "Quận Tân Bình",
    }

    def __init__(self, *, strict_scope: bool = True):
        """
        Args:
            strict_scope: Nếu True, REJECT records ngoài 6 quận scope.
                         Nếu False, cho phép province/district bất kỳ (cho dev/testing).
        """
        self.strict_scope = strict_scope

    def _normalize_province(self, raw: Any) -> str:
        """Normalize province name → canonical."""
        if _to_none(raw) is None:
            raise ValidationError("province_city", raw, "province_city is required")
        s = str(raw).strip()
        key = s.lower()
        if key in self.PROVINCE_ALIASES:
            return self.PROVINCE_ALIASES[key]
        # Direct canonical match
        if s in CANONICAL_PROVINCES:
            return s
        raise ValidationError(
            "province_city", raw,
            f"province must be one of: {sorted(CANONICAL_PROVINCES)}"
        )

    def _normalize_district(self, raw: Any) -> str:
        """Normalize district name → canonical."""
        if _to_none(raw) is None:
            raise ValidationError("district", raw, "district is required")
        s = str(raw).strip()
        key = s.lower()
        if key in self.DISTRICT_ALIASES:
            return self.DISTRICT_ALIASES[key]
        if s in CANONICAL_DISTRICTS:
            return s
        raise ValidationError(
            "district", raw,
            f"district must be one of: {sorted(CANONICAL_DISTRICTS)}"
        )

    def _validate_scope(self, province: str, district: str) -> None:
        """Validate (province, district) is in scope."""
        if self.strict_scope and (province, district) not in SCOPE_6_DISTRICTS:
            raise ValidationError(
                "scope", (province, district),
                f"({province}, {district}) not in allowed scope of 6 districts"
            )

    def _normalize_legal_status(self, raw: Any) -> Optional[str]:
        """Map legal status → canonical EN value."""
        v = _to_none(raw)
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in LEGAL_STATUS_VN_TO_EN:
            return LEGAL_STATUS_VN_TO_EN[s]
        # Already canonical?
        if s in CANONICAL_LEGAL_STATUS:
            return s
        # Try without underscores/spaces
        for canonical, mapped in LEGAL_STATUS_VN_TO_EN.items():
            if s.replace(" ", "").replace("_", "") == canonical:
                return mapped
        # Unknown → default to "unknown"
        return "unknown"

    def _normalize_furnishing(self, raw: Any) -> Optional[str]:
        """Map furnishing → canonical value."""
        v = _to_none(raw)
        if v is None:
            return "null"
        s = str(v).strip().lower()
        if s in FURNISHING_TO_CANONICAL:
            return FURNISHING_TO_CANONICAL[s]
        if s in CANONICAL_FURNISHING:
            return s
        return "null"

    def _normalize_property_type(self, raw: Any) -> str:
        """Validate and normalize property_type."""
        if _to_none(raw) is None:
            raise ValidationError("property_type", raw, "property_type is required")
        v = str(raw).strip().lower()
        # Direct match
        for t in CANONICAL_PROPERTY_TYPES:
            if t == v:
                return t
        raise ValidationError(
            "property_type", raw,
            f"property_type must be one of: {sorted(CANONICAL_PROPERTY_TYPES)}"
        )

    def _normalize_source_method(self, raw: Any) -> str:
        """Map source_access_method → canonical scraper|api|batch_generator|demo_seed."""
        v = _to_none(raw)
        if v is None:
            return "batch_generator"
        s = str(v).strip().lower()
        if s in SOURCE_METHOD_TO_CANONICAL:
            return SOURCE_METHOD_TO_CANONICAL[s]
        if s in CANONICAL_SOURCE_ACCESS_METHODS:
            return s
        return "batch_generator"

    def sanitize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize a raw property dict. Returns clean dict ready for DB insert.

        Raises ValidationError nếu field bắt buộc vi phạm rules.
        """
        errors: dict[str, str] = {}

        # ── 1. Province & District (bắt buộc, đầu tiên) ──
        try:
            province = self._normalize_province(raw.get("province_city"))
        except ValidationError as e:
            errors[e.field] = str(e)

        try:
            district = self._normalize_district(raw.get("district"))
        except ValidationError as e:
            errors[e.field] = str(e)

        # ── 2. Scope check ──
        if "province_city" not in errors and "district" not in errors:
            try:
                self._validate_scope(province, district)
            except ValidationError as e:
                errors[e.field] = str(e)

        # ── 3. property_type (bắt buộc) ──
        try:
            property_type = self._normalize_property_type(raw.get("property_type"))
        except ValidationError as e:
            errors[e.field] = str(e)

        # ── 4. area_m2 (bắt buộc, > 0) ──
        area_m2 = _to_float(raw.get("area_m2"), ge=10.0, le=20000.0)
        if area_m2 is None:
            errors["area_m2"] = f"area_m2 must be between 10 and 20000 m2 (got {raw.get('area_m2')!r})"

        # ── 5. price (bắt buộc, >= 100M VND) ──
        price = _to_float(raw.get("price"), ge=100_000_000.0)
        if price is None:
            errors["price"] = f"price must be >= 100,000,000 VND (got {raw.get('price')!r})"

        # ── 6. price_per_m2 ──
        ppm = None
        if price and area_m2:
            ppm = round(price / area_m2, -3)  # Round to nearest 1M
        ppm_raw = raw.get("price_per_m2")
        if ppm_raw is not None:
            ppm_check = _to_float(ppm_raw, ge=0.0, le=500_000_000.0)
            if ppm_check is not None:
                ppm = ppm_check

        # ── 7. Optional numerics ──
        bedrooms = _to_int(raw.get("bedrooms"), ge=0, le=50) or 0
        bathrooms = _to_int(raw.get("bathrooms"), ge=0, le=50) or 0
        floor_count = _to_int(raw.get("floor_count"), ge=1, le=100) or 1

        frontage = _to_float(raw.get("frontage_m"), ge=0.0, le=200.0)
        if frontage is not None and frontage <= 0:
            frontage = None

        # ── 8. Lat/lng ──
        lat = _to_float(raw.get("latitude"), ge=-90.0, le=90.0)
        lng = _to_float(raw.get("longitude"), ge=-180.0, le=180.0)

        # ── 9. Enums ──
        legal_status = self._normalize_legal_status(raw.get("legal_status"))
        furnishing = self._normalize_furnishing(raw.get("furnishing"))
        area_type = _canonical_enum(
            raw.get("area_type"), CANONICAL_AREA_TYPES, "urban_center"
        )
        source_method = self._normalize_source_method(raw.get("source_access_method"))

        # ── 10. Data origin & record status ──
        data_origin = _canonical_enum(
            raw.get("data_origin_type"), CANONICAL_DATA_ORIGIN, "public_collected"
        )
        record_status = _canonical_enum(
            raw.get("record_status"), CANONICAL_RECORD_STATUS, "raw"
        )

        # ── 11. Evidence tier ──
        raw_tier = _to_none(raw.get("evidence_tier"))
        if raw_tier is not None:
            tier_str = str(raw_tier).strip().upper()
            if tier_str in CANONICAL_EVIDENCE_TIERS:
                evidence_tier = tier_str
            else:
                evidence_tier = "E5"  # Unknown → lowest tier
        else:
            evidence_tier = "E5"

        # ── 12. Source tracking ──
        source_name = _to_str(raw.get("source_name"), maxlen=200)
        if source_name is None:
            errors["source_name"] = "source_name is required"

        source_url = _to_str(raw.get("source_url"), maxlen=500)
        source_domain = raw.get("source_domain")
        if source_domain is None and source_url:
            m = re.search(r"https?://([^/]+)", str(source_url))
            if m:
                source_domain = m.group(1)

        # ── 13. String fields ──
        ward = _to_str(raw.get("ward"), maxlen=100)
        street = _to_str(raw.get("street_or_project"), maxlen=255)
        description = _to_str(raw.get("description"), maxlen=10000)
        collection_method = _canonical_enum(
            raw.get("collection_method"), CANONICAL_COLLECTION_METHODS, "manual_entry"
        )

        # ── 14. Raise if critical errors ──
        if errors:
            raise ValidationError(
                "_compound",
                raw,
                f"Validation failed for {len(errors)} field(s): {errors}"
            )

        # ── 15. Build clean output ──
        return {
            # Core (NOT NULL in production design)
            "property_type": property_type,
            "province_city": province,
            "district": district,
            "area_m2": area_m2,
            "price": price,
            "price_per_m2": ppm,
            # Location
            "ward": ward,
            "street_or_project": street,
            "latitude": lat,
            "longitude": lng,
            "area_type": area_type,
            # Property attributes
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "floor_count": floor_count,
            "frontage_m": frontage,
            "legal_status": legal_status,
            "furnishing": furnishing,
            # Source tracking
            "source_name": source_name,
            "source_url": source_url,
            "source_domain": source_domain,
            "source_access_method": source_method,
            # Provenance
            "data_origin_type": data_origin,
            "record_status": record_status,
            "evidence_tier": evidence_tier,
            "collection_method": collection_method,
            # Text
            "description": description,
            # IoT fields passthrough (optional)
            "gps_lat": _to_float(raw.get("gps_lat"), ge=-90, le=90),
            "gps_lng": _to_float(raw.get("gps_lng"), ge=-180, le=180),
            "gps_accuracy": _to_float(raw.get("gps_accuracy"), ge=0),
            "noise_level": _to_float(raw.get("noise_level"), ge=0, le=200),
            "light_level": _to_float(raw.get("light_level"), ge=0),
            "temperature": _to_float(raw.get("temperature"), ge=-50, le=60),
            "humidity": _to_float(raw.get("humidity"), ge=0, le=100),
            "phone_device": _to_str(raw.get("phone_device"), maxlen=100),
            "os_version": _to_str(raw.get("os_version"), maxlen=50),
            "app_version": _to_str(raw.get("app_version"), maxlen=20),
            "field_notes": _to_str(raw.get("field_notes"), maxlen=5000),
            "area_quality_score": _to_float(raw.get("area_quality_score"), ge=0, le=10),
            "capture_time": raw.get("capture_time"),
            "listing_date": raw.get("listing_date"),
            "evidence_photo_path": _to_str(raw.get("evidence_photo_path"), maxlen=255),
        }

    def sanitize_batch(self, raw_records: list[dict[str, Any]]) -> tuple[list[dict], list[tuple[int, ValidationError]]]:
        """
        Sanitize a batch of records.
        Returns (valid_records, errors) where errors = list of (index, error).
        """
        valid = []
        errors = []
        for i, raw in enumerate(raw_records):
            try:
                valid.append(self.sanitize(raw))
            except ValidationError as e:
                errors.append((i, e))
        return valid, errors


# ==============================================================================
# USER SANITIZER
# ==============================================================================

class UserSanitizer:
    """Sanitizer cho user/auth data."""

    USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")
    EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def sanitize_registration(self, raw: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize user registration input.

        Rules:
          - username: 3-50 chars, alphanumeric + underscore/dash, UNIQUE (caller checks)
          - email: valid format (optional)
          - password: >= 6 chars (hashing caller handles)
        """
        errors: dict[str, str] = {}

        # Username
        username = _to_str(raw.get("username"), maxlen=50)
        if username is None:
            errors["username"] = "username is required (3-50 chars, alphanumeric)"
        elif not self.USERNAME_RE.match(username):
            errors["username"] = (
                f"username must be 3-50 chars, alphanumeric/underscore/dash only "
                f"(got {username!r})"
            )

        # Password (no sanitization needed, caller hashes)
        password = raw.get("password")
        if _to_none(password) is None:
            errors["password"] = "password is required"
        elif len(str(password)) < 6:
            errors["password"] = "password must be at least 6 characters"

        # Email (optional but must be valid if provided)
        email = _to_str(raw.get("email"), maxlen=200)
        if email is not None and not self.EMAIL_RE.match(email):
            errors["email"] = f"email format invalid (got {email!r})"

        if errors:
            raise ValidationError("_user_registration", raw, f"Failed: {errors}")

        return {
            "username": username,
            "password": str(password),
            "email": email,
            "role": "user",
        }


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def sanitize_property(raw: dict[str, Any], **kwargs) -> dict[str, Any]:
    """One-shot sanitize a property dict."""
    return PropertySanitizer(**kwargs).sanitize(raw)


def sanitize_user_registration(raw: dict[str, Any]) -> dict[str, Any]:
    """One-shot sanitize a user registration dict."""
    return UserSanitizer().sanitize_registration(raw)


# ==============================================================================
# VALIDATOR FOR EXISTING DB DATA
# ==============================================================================

class DatabaseValidator:
    """
    Kiểm tra và báo cáo dirty data trong DB.
    Dùng cho audit/repair scripts.
    """

    def __init__(self, db_session):
        from sqlalchemy.orm import Session
        if not isinstance(db_session, Session):
            raise TypeError("Must pass a SQLAlchemy Session")
        self.db = db_session

    def check_property(self, prop) -> list[str]:
        """Check a single Property ORM object. Returns list of violations."""
        violations = []

        # property_type
        if prop.property_type not in CANONICAL_PROPERTY_TYPES:
            violations.append(
                f"property_type={prop.property_type!r} not in {CANONICAL_PROPERTY_TYPES}"
            )

        # Province
        if prop.province_city not in CANONICAL_PROVINCES:
            violations.append(
                f"province_city={prop.province_city!r} not in {CANONICAL_PROVINCES}"
            )

        # District scope
        if (prop.province_city, prop.district) not in SCOPE_6_DISTRICTS:
            violations.append(
                f"scope=({prop.province_city}, {prop.district}) not in SCOPE_6_DISTRICTS"
            )

        # Area
        if prop.area_m2 is None or prop.area_m2 <= 0:
            violations.append(f"area_m2={prop.area_m2} (<= 0 or NULL)")
        elif prop.area_m2 < 10 or prop.area_m2 > 20000:
            violations.append(f"area_m2={prop.area_m2} (out of 10-20000 range)")

        # Price
        if prop.price is None or prop.price <= 0:
            violations.append(f"price={prop.price} (<= 0 or NULL)")
        elif prop.price < 100_000_000:
            violations.append(f"price={prop.price:,.0f} (< 100M VND)")

        # source_access_method
        if prop.source_access_method not in CANONICAL_SOURCE_ACCESS_METHODS:
            violations.append(
                f"source_access_method={prop.source_access_method!r} not in "
                f"{CANONICAL_SOURCE_ACCESS_METHODS}"
            )

        # legal_status: check if VN
        if prop.legal_status in LEGAL_STATUS_VN_TO_EN:
            violations.append(
                f"legal_status={prop.legal_status!r} is VN (should be EN canonical)"
            )

        # furnishing
        if prop.furnishing is not None:
            f = str(prop.furnishing).strip().lower()
            if f not in CANONICAL_FURNISHING and f not in FURNISHING_TO_CANONICAL:
                violations.append(
                    f"furnishing={prop.furnishing!r} not canonical"
                )

        # evidence_tier
        if prop.evidence_tier not in CANONICAL_EVIDENCE_TIERS:
            violations.append(
                f"evidence_tier={prop.evidence_tier!r} not in {CANONICAL_EVIDENCE_TIERS}"
            )

        # record_status
        if prop.record_status not in CANONICAL_RECORD_STATUS:
            violations.append(
                f"record_status={prop.record_status!r} not in {CANONICAL_RECORD_STATUS}"
            )

        return violations
