"""
API Sanitizer Middleware — Tự động sanitize tất cả JSON request bodies.

Gắn vào FastAPI app: app.add_middleware(SanitizeRequestMiddleware)

Entry points được sanitize:
  - POST /api/properties           → PropertyCreate
  - POST /api/collect/iot          → IoT sensor data
  - POST /api/research/buyer-requirement → BuyerRequirement
  - POST /api/research/expert-rating     → ExpertRating
  - PUT  /api/properties/{id}             → PropertyUpdate
  - PATCH routes via body sanitization

Quy tắc:
  1. Chỉ sanitize endpoints có body (POST/PUT/PATCH)
  2. Đọc request body → parse JSON → sanitize → ghi lại vào request.state
  3. Các route handlers đọc từ request.state thay vì request.json()
  4. Không thay đổi request.body (FastAPI không cho phép)
  5. ValidationError → trả về 422 với chi tiết lỗi

Usage:
    from src.backend.api_sanitizer_middleware import SanitizeRequestMiddleware
    app.add_middleware(SanitizeRequestMiddleware)
"""
from __future__ import annotations

import json
import re
from typing import Callable, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


# ==============================================================================
# Paths that need sanitization (write endpoints)
# ==============================================================================

SANITIZE_PATHS: Set[str] = {
    "/api/properties",
    "/api/collect/iot",
    "/api/research/buyer-requirement",
    "/api/research/expert-rating",
    "/api/research/expert-property",
    "/api/buyer-requirements",
    "/api/upload",
    "/api/auth/register",
    "/api/auth/login",
}

# Paths that should NOT be sanitized (read-only, binary, or already validated)
SKIP_PATHS_PREFIXES: tuple[str, ...] = (
    "/api/properties/",      # GET, DELETE — only sanitize POST
    "/api/collect/status",
    "/api/dashboard",
    "/api/research/overview",
    "/api/research/stats",
    "/api/research/buyer-requirements",  # GET
    "/docs",
    "/openapi.json",
    "/redoc",
    "/ws",
)


# ==============================================================================
# VN→EN Canonical Mappings (mirrors data_sanitizer.py)
# ==============================================================================

PROPERTY_TYPE_VN_TO_EN: dict[str, str] = {
    "nhà": "house", "căn hộ": "apartment", "căn hộ chung cư": "apartment",
    "đất": "land", "lô đất": "land",
    "nhà phố": "townhouse", "townhouse": "townhouse",
    "biệt thự": "villa", "villa": "villa",
    "biet thu": "villa",
}

LEGAL_STATUS_VN_TO_EN: dict[str, str] = {
    "sổ đỏ": "ownership_certificate",
    "sổ hồng": "land_use_right",
    "hợp đồng mua bán": "full_ownership",
    "hợp đồng": "full_ownership",
    "chưa có sổ": "pending",
    "chưa sang tên": "pending",
    "đang chờ": "pending",
}

FURNISHING_VN_TO_EN: dict[str, str] = {
    "null": "null",
    "none": "none",
    "không": "none",
    "cơ bản": "basic",
    "basic": "basic",
    "partial": "partial",
    "một phần": "partial",
    "đầy đủ": "full",
    "full": "full",
    "đầy đủ nội thất": "full",
}

RECORD_STATUS_VN_TO_EN: dict[str, str] = {
    "thô": "raw",
    "chờ duyệt": "pending_review",
    "đã duyệt": "verified",
    "từ chối": "rejected",
    "lưu trữ": "archived",
}

SOURCE_METHOD_ALIASES: dict[str, str] = {
    "playwright": "scraper",
    "playwright_stealth": "scraper",
    "scrapy": "scraper",
    "selenium": "scraper",
    "api_call": "api",
    "api_request": "api",
    "manual": "manual_entry",
    "nhập tay": "manual_entry",
    "form_entry": "manual_entry",
    "demo": "demo_seed",
    "seed": "demo_seed",
    "batch": "batch_generator",
}

PROVINCE_ALIASES: dict[str, str] = {
    "tp hcm": "TP. Hồ Chí Minh",
    "tp.hcm": "TP. Hồ Chí Minh",
    "ho chi minh": "TP. Hồ Chí Minh",
    "hcm": "TP. Hồ Chí Minh",
    "tphcm": "TP. Hồ Chí Minh",
    "hanoi": "Hà Nội",
    "hn": "Hà Nội",
}


# ==============================================================================
# Sanitization Logic
# ==============================================================================

def _strip(value: str) -> str:
    return str(value).strip() if value else ""


def _to_float(value, default=None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_int(value, default=None) -> int | None:
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _canonical_property_type(raw: str) -> str:
    key = _strip(raw).lower()
    return PROPERTY_TYPE_VN_TO_EN.get(key, key)


def _canonical_legal_status(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    key = _strip(raw).lower()
    return LEGAL_STATUS_VN_TO_EN.get(key, key)


def _canonical_furnishing(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    key = _strip(raw).lower()
    return FURNISHING_VN_TO_EN.get(key, key)


def _canonical_province(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    key = _strip(raw).lower()
    return PROVINCE_ALIASES.get(key, _strip(raw))


def _canonical_source_method(raw: str | None) -> str:
    if raw is None or raw == "":
        return "manual_entry"
    key = _strip(raw).lower()
    return SOURCE_METHOD_ALIASES.get(key, key)


def _canonical_record_status(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    key = _strip(raw).lower()
    return RECORD_STATUS_VN_TO_EN.get(key, key)


def _strip_vn_price(raw) -> float | None:
    """Parse VND text (6.5 tỷ, 650 triệu) → float."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    text = re.sub(r"[^\d.,tỷtriệu]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    m = re.search(r"([\d.,]+)\s*tỷ", text)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e9
        except ValueError:
            pass
    m = re.search(r"([\d.,]+)\s*triệu", text)
    if m:
        try:
            return float(m.group(1).replace(",", ".")) * 1e6
        except ValueError:
            pass
    return _to_float(raw)


def _strip_vn_area(raw) -> float | None:
    """Parse area text (75m2, 75.5) → float."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    text = re.sub(r"[^\d.,m²]", " ", text)
    m = re.search(r"([\d.,]+)", text)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return _to_float(raw)


def sanitize_property_create(body: dict) -> dict:
    """
    Sanitize PropertyCreate body fields.
    Canonicalizes: property_type, legal_status, furnishing, province,
                   source_access_method, price (VN parsing), area_m2 (VN parsing).
    """
    out = dict(body)

    # property_type: VN→EN canonical
    if "property_type" in out and out["property_type"]:
        out["property_type"] = _canonical_property_type(out["property_type"])

    # province_city: aliases → canonical
    if "province_city" in out and out["province_city"]:
        out["province_city"] = _canonical_province(out["province_city"])

    # legal_status: VN→EN canonical
    if "legal_status" in out:
        out["legal_status"] = _canonical_legal_status(out["legal_status"])

    # furnishing: VN→EN canonical
    if "furnishing" in out:
        out["furnishing"] = _canonical_furnishing(out["furnishing"])

    # price: parse VN text format
    if "price" in out and out["price"] is not None:
        parsed = _strip_vn_price(out["price"])
        if parsed is not None:
            out["price"] = parsed

    # area_m2: parse VN text format
    if "area_m2" in out and out["area_m2"] is not None:
        parsed = _strip_vn_area(out["area_m2"])
        if parsed is not None:
            out["area_m2"] = parsed

    # district: strip whitespace
    if "district" in out and out["district"]:
        out["district"] = _strip(out["district"])

    # ward: strip whitespace
    if "ward" in out and out["ward"]:
        out["ward"] = _strip(out["ward"])

    # source_access_method: aliases → canonical
    if "source_access_method" in out:
        out["source_access_method"] = _canonical_source_method(out["source_access_method"])

    # record_status: aliases → canonical
    if "record_status" in out:
        out["record_status"] = _canonical_record_status(out["record_status"])

    # data_origin_type: normalize
    if "data_origin_type" in out and out["data_origin_type"]:
        dot = str(out["data_origin_type"]).strip().lower()
        if dot in ("khảo sát", "survey", "thực địa", "field_survey", "field"):
            out["data_origin_type"] = "self_collected"

    # bool fields: normalize string booleans
    for bool_field in ("near_supermarket", "near_school", "near_hospital",
                       "near_main_road", "is_self_collected", "has_basement",
                       "car_access", "motorcycle_access"):
        if bool_field in out:
            val = out[bool_field]
            if isinstance(val, str):
                out[bool_field] = val.strip().lower() in ("true", "1", "yes", "có", "vâng")

    return out


def sanitize_buyer_requirement(body: dict) -> dict:
    """Sanitize buyer requirement body."""
    out = dict(body)

    if "province_city" in out and out["province_city"]:
        out["province_city"] = _canonical_province(out["province_city"])

    if "property_type" in out and out["property_type"]:
        out["property_type"] = _canonical_property_type(out["property_type"])

    # budget: parse VN text
    for field in ("min_budget", "max_budget"):
        if field in out and out[field] is not None:
            parsed = _strip_vn_price(out[field])
            if parsed is not None:
                out[field] = parsed

    # area: parse VN text
    for field in ("min_area", "max_area"):
        if field in out and out[field] is not None:
            parsed = _strip_vn_area(out[field])
            if parsed is not None:
                out[field] = parsed

    return out


def sanitize_expert_rating(body: dict) -> dict:
    """Sanitize expert rating body."""
    out = dict(body)

    # Expert prices: parse VN text
    for field in ("expert_low", "expert_mid", "expert_high"):
        if field in out and out[field] is not None:
            parsed = _strip_vn_price(out[field])
            if parsed is not None:
                out[field] = parsed

    return out


def sanitize_auth(body: dict) -> dict:
    """Sanitize auth body (register/login)."""
    out = dict(body)

    # username: strip and lowercase
    if "username" in out and out["username"]:
        out["username"] = _strip(out["username"]).lower()

    # email: strip and lowercase
    if "email" in out and out["email"]:
        out["email"] = _strip(out["email"]).lower()

    return out


def _route_sanitizer(path: str, body: dict) -> dict:
    """Route body to the correct sanitizer."""
    path_lower = path.lower()

    if path_lower == "/api/properties":
        return sanitize_property_create(body)
    if path_lower == "/api/collect/iot":
        # IoT: parse VN floats
        out = dict(body)
        for field in ("latitude", "longitude", "noise_level", "temperature",
                      "humidity", "light_level", "accuracy"):
            if field in out and out[field] is not None:
                out[field] = _to_float(out[field], out[field])
        return out
    if path_lower == "/api/research/buyer-requirement":
        return sanitize_buyer_requirement(body)
    if path_lower == "/api/research/expert-rating":
        return sanitize_expert_rating(body)
    if path_lower in ("/api/auth/register", "/api/auth/login"):
        return sanitize_auth(body)

    # Generic sanitization for other write paths
    return sanitize_property_create(body)


# ==============================================================================
# Middleware
# ==============================================================================

class SanitizeRequestMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware: tự động sanitize JSON body của các write endpoints.

    Flow:
      1. Nhận request → kiểm tra method + path
      2. Đọc request.body() → parse JSON
      3. Sanitize → lưu vào request.state.sanitized_body
      4. Cho request đi tiếp (starlette sẽ re-parse body từ raw)
      5. Route handlers dùng request.state.sanitized_body nếu có

    Lưu ý: FastAPI đọc body trước khi route handler → dùng body override pattern
    hoặc route-level sanitization. Middleware này ghi log + attach metadata.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path

        # Only process JSON write methods
        if method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # Skip non-data paths
        if any(path.lower().startswith(p.lower()) for p in SKIP_PATHS_PREFIXES):
            return await call_next(request)

        # Check content type
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return await call_next(request)

        # Read body
        body_bytes = await request.body()
        if not body_bytes:
            return await call_next(request)

        # Parse JSON
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid JSON body: {e}"}
            )

        # Sanitize
        sanitized = _route_sanitizer(path, body)

        # Attach to request state for downstream handlers
        request.state.sanitized_body = sanitized
        request.state.sanitizer_applied = True

        # Log sanitization action (async, non-blocking)
        import logging
        logger = logging.getLogger("api_sanitizer")
        logger.debug(
            f"[SANITIZE] {method} {path} — "
            f"keys={list(sanitized.keys())}"
        )

        # Continue request — but the body is already consumed.
        # FastAPI will fail to parse since we consumed body_bytes.
        # Solution: replace the request's receive with a cached copy.
        # We use a custom Request subclass pattern via ASGI scope override.
        # For FastAPI, we instead validate here and return early on error.
        # The actual route handler will re-read from the original body.
        # Since we already consumed it, we pass sanitized via state
        # and document that routes should read from request.state.

        # Return response via call_next — this will fail because body was consumed.
        # Instead, we validate here and return error, OR we need to stream the
        # request differently. The cleanest FastAPI approach is to handle sanitization
        # at the route level (in dependency), not middleware.
        #
        # Middleware approach: create a new request with the sanitized body.
        from starlette.requests import HTTPConnection
        from starlette.responses import JSONResponse

        # Build a new Request with sanitized body in scope
        scope = dict(request.scope)
        sanitized_bytes = json.dumps(sanitized, ensure_ascii=False).encode("utf-8")

        # Replace receive with a function that returns our sanitized body
        async def receive_sanitized():
            return {
                "type": "http.request",
                "body": sanitized_bytes,
                "more_body": False,
            }

        # Create a new request with sanitized body
        scope["receive"] = receive_sanitized
        from starlette.requests import Request as ASGIRequest
        sanitized_request = ASGIRequest(scope, receive=receive_sanitized)

        # Continue with sanitized request
        response = await call_next(sanitized_request)

        # Attach sanitizer metadata to response headers
        response.headers["X-Sanitize-Applied"] = "1"

        return response
