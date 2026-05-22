"""
APPROVED DATA SOURCES — Whitelist cho Real Estate AVM.
CHỈ các nguồn trong danh sách này mới được phép thu thập dữ liệu.

Nguyên tắc:
1. Mọi nguồn mới phải được review và add vào đây TRƯỚC KHI thu thập
2. PROHIBITED_SOURCES có mức ưu tiên cao hơn APPROVED_SOURCES
3. mỗi nguồn phải có đầy đủ config để collector hoạt động
"""

from typing import Dict, List, Optional
import enum


class SourceType(str, enum.Enum):
    SCRAPER = "scraper"           # Web scraping
    API = "api"                   # REST API
    MANUAL_ENTRY = "manual_entry" # Nhập tay thủ công
    FIELD_SURVEY = "field_survey" # Khảo sát thực địa


# ==============================================================================
# APPROVED SOURCES — Nguồn được phép thu thập
# ==============================================================================

APPROVED_SOURCES: Dict[str, Dict] = {

    # --------------------------------------------------------------------------
    # ALONHADAT.COM.VN — Nguồn chính #1
    # --------------------------------------------------------------------------
    "alonhadat.com.vn": {
        "name": "Alonhadat.com.vn",
        "type": SourceType.SCRAPER.value,
        "base_url": "https://alonhadat.com.vn",
        "rate_limit_seconds": 0.1,  # Fast collection
        "requires_proxy": False,
        "is_primary": True,
        "districts": {
            # Hà Nội — 3 quận được phép
            "Hà Nội": {
                "cau-giay": {
                    "name": "Quận Cầu Giấy",
                    "slug": "cau-giay",
                    "property_types": ["land", "apartment", "townhouse", "house", "villa"],
                    "priority": 1,  # Ưu tiên cao nhất
                },
                "thanh-xuan": {
                    "name": "Quận Thanh Xuân",
                    "slug": "thanh-xuan",
                    "property_types": ["land", "apartment", "townhouse", "house", "villa"],
                    "priority": 2,
                },
                "dong-da": {
                    "name": "Quận Đống Đa",
                    "slug": "dong-da",
                    "property_types": ["land", "apartment", "townhouse", "house", "villa"],
                    "priority": 3,
                },
            },
            # TP.HCM — 3 quận được phép
            "TP. Hồ Chí Minh": {
                "quan-7": {
                    "name": "Quận 7",
                    "slug": "quan-7",
                    "property_types": ["land", "apartment", "townhouse", "house", "villa"],
                    "priority": 1,
                },
                "binh-thanh": {
                    "name": "Quận Bình Thạnh",
                    "slug": "binh-thanh",
                    "property_types": ["land", "apartment", "townhouse", "house", "villa"],
                    "priority": 2,
                },
                "tan-binh": {
                    "name": "Quận Tân Bình",
                    "slug": "tan-binh",
                    "property_types": ["land", "apartment", "townhouse", "house", "villa"],
                    "priority": 3,
                },
            },
        },
        "selectors": {
            "listing_container": ".content-left .list",
            "listing_item": ".item",
            "title": ".title a::text",
            "price": ".price .value::text",
            "area": ".square .value::text",
            "address": ".location::text",
            "description": ".description::text",
            "image": "img::attr(src)",
            "posted_date": ".postdate::text",
            "next_page": ".next::attr(href)",
        },
        "pagination": {
            "type": "url_param",
            "param": "page",
            "start": 1,
            "max_pages": 50,  # Giới hạn 50 trang/quận
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        "retry_config": {
            "max_attempts": 3,
            "backoff_seconds": [5, 15, 45],  # Exponential backoff
            "retry_on_status": [429, 500, 502, 503, 504],
        },
        "notes": "Nguồn chính — nhiều listing nhất cho thị trường VN",
    },

    # --------------------------------------------------------------------------
    # BATDONGSAN.COM.VN — Nguồn chính #2
    # --------------------------------------------------------------------------
    "batdongsan.com.vn": {
        "name": "Batdongsan.com.vn",
        "type": SourceType.SCRAPER.value,
        "base_url": "https://batdongsan.com.vn",
        "rate_limit_seconds": 0.1,
        "requires_proxy": False,
        "is_primary": True,
        "districts": {
            "Hà Nội": {
                "cau-giay": {"name": "Quận Cầu Giấy", "slug": "cau-giay", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 1},
                "thanh-xuan": {"name": "Quận Thanh Xuân", "slug": "thanh-xuan", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 2},
                "dong-da": {"name": "Quận Đống Đa", "slug": "dong-da", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 3},
            },
            "TP. Hồ Chí Minh": {
                "quan-7": {"name": "Quận 7", "slug": "quan-7", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 1},
                "binh-thanh": {"name": "Quận Bình Thạnh", "slug": "binh-thanh", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 2},
                "tan-binh": {"name": "Quận Tân Bình", "slug": "tan-binh", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 3},
            },
        },
        "selectors": {
            "listing_item": ".prd",
            "title": ".prd-title a",
            "price": ".prd-price",
            "area": ".prd-size",
            "address": ".prd-address",
        },
        "pagination": {"type": "url_param", "param": "page", "start": 1, "max_pages": 30},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://batdongsan.com.vn/",
        },
        "retry_config": {"max_attempts": 3, "backoff_seconds": [10, 30, 60], "retry_on_status": [429, 500, 502, 503, 504]},
        "notes": "Nguồn #1 — CẦN Selenium/Playwright (Cloudflare 403 protection)",
    },

    # --------------------------------------------------------------------------
    # NHATOT.COM (Chợ Tốt) — Nguồn #2
    # --------------------------------------------------------------------------
    "nhatot.com": {
        "name": "Nhà Tốt / Chợ Tốt",
        "type": SourceType.SCRAPER.value,
        "base_url": "https://nhatot.com",
        "rate_limit_seconds": 0.1,
        "requires_proxy": False,
        "is_primary": True,
        "districts": {
            "Hà Nội": {
                "cau-giay": {"name": "Quận Cầu Giấy", "slug": "cau-giay", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 1},
                "thanh-xuan": {"name": "Quận Thanh Xuân", "slug": "thanh-xuan", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 2},
                "dong-da": {"name": "Quận Đống Đa", "slug": "dong-da", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 3},
            },
            "TP. Hồ Chí Minh": {
                "quan-7": {"name": "Quận 7", "slug": "quan-7", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 1},
                "binh-thanh": {"name": "Quận Bình Thạnh", "slug": "binh-thanh", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 2},
                "tan-binh": {"name": "Quận Tân Bình", "slug": "tan-binh", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 3},
            },
        },
        "selectors": {
            "listing_item": ".listing-item, .item-real-estate",
            "title": "h3.title a, .item-title a",
            "price": ".item-price, .price",
            "area": ".item-area, .square",
            "address": ".item-location, .location",
        },
        "pagination": {"type": "url_param", "param": "page", "start": 1, "max_pages": 30},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        "retry_config": {"max_attempts": 3, "backoff_seconds": [10, 30, 60], "retry_on_status": [429, 500, 502, 503, 504]},
        "notes": "Nguồn #2 — CẦN Selenium/Playwright (JS-rendered, anti-bot)",
    },

    # --------------------------------------------------------------------------
    # MUABAN.NET — Nguồn bổ sung #3
    # --------------------------------------------------------------------------
    "muaban.net": {
        "name": "Muaban.net",
        "type": SourceType.SCRAPER.value,
        "base_url": "https://muaban.net",
        "rate_limit_seconds": 0.1,
        "requires_proxy": False,
        "is_primary": True,
        "districts": {
            "Hà Nội": {
                "cau-giay": {"name": "Quận Cầu Giấy", "slug": "cau-giay", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 1},
                "thanh-xuan": {"name": "Quận Thanh Xuân", "slug": "thanh-xuan", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 2},
                "dong-da": {"name": "Quận Đống Đa", "slug": "dong-da", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 3},
            },
            "TP. Hồ Chí Minh": {
                "quan-7": {"name": "Quận 7", "slug": "quan-7", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 1},
                "binh-thanh": {"name": "Quận Bình Thạnh", "slug": "binh-thanh", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 2},
                "tan-binh": {"name": "Quận Tân Bình", "slug": "tan-binh", "property_types": ["land", "apartment", "townhouse", "house", "villa"], "priority": 3},
            },
        },
        "selectors": {
            "listing_item": ".item-real-estate, .listing-item",
            "title": "h3 a, .title a",
            "price": ".price, .item-price",
            "area": ".area, .square",
            "address": ".address, .location",
        },
        "pagination": {"type": "url_param", "param": "page", "start": 1, "max_pages": 30},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        "retry_config": {"max_attempts": 3, "backoff_seconds": [10, 30, 60], "retry_on_status": [429, 500, 502, 503, 504]},
        "notes": "Nguồn bổ sung #3 — cross-validation, tăng độ phủ land + nhà dân",
    },

    # --------------------------------------------------------------------------
    # REVER.VN — Nguồn chất lượng cao
    # --------------------------------------------------------------------------
    "rever.vn": {
        "name": "Rever.vn",
        "type": SourceType.SCRAPER.value,
        "base_url": "https://rever.vn",
        "rate_limit_seconds": 0.1,
        "requires_proxy": False,
        "is_primary": False,
        "districts": {
            "Hà Nội": {
                "cau-giay": {"name": "Quận Cầu Giấy", "slug": "cau-giay", "property_types": ["apartment", "townhouse", "villa"], "priority": 1},
                "thanh-xuan": {"name": "Quận Thanh Xuân", "slug": "thanh-xuan", "property_types": ["apartment", "townhouse", "villa"], "priority": 2},
            },
            "TP. Hồ Chí Minh": {
                "quan-7": {"name": "Quận 7", "slug": "quan-7", "property_types": ["apartment", "townhouse", "villa", "house"], "priority": 1},
                "binh-thanh": {"name": "Quận Bình Thạnh", "slug": "binh-thanh", "property_types": ["apartment", "townhouse", "villa", "house"], "priority": 2},
                "tan-binh": {"name": "Quận Tân Bình", "slug": "tan-binh", "property_types": ["apartment", "townhouse", "house"], "priority": 3},
            },
        },
        "selectors": {
            "listing_item": ".listing-card, .property-item",
            "title": ".listing-title a, h3 a",
            "price": ".listing-price, .price",
            "area": ".listing-area, .area",
            "address": ".listing-address, .address",
        },
        "pagination": {"type": "url_param", "param": "page", "start": 1, "max_pages": 20},
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        "retry_config": {"max_attempts": 3, "backoff_seconds": [10, 30, 60], "retry_on_status": [429, 500, 502, 503, 504]},
        "notes": "Nguồn chất lượng cao — Rever, căn hộ + nhà phố, dữ liệu kiểm duyệt tốt",
    },



    # --------------------------------------------------------------------------
    # PROPZY.COM — API (nếu có API key)
    # --------------------------------------------------------------------------
    # "propzy.com": {
    #     "name": "Propzy",
    #     "type": SourceType.API.value,
    #     "base_url": "https://api.propzy.vn",
    #     "api_endpoint": "/v1/listings",
    #     "rate_limit_seconds": 1,
    #     "requires_auth": True,
    #     "auth_type": "bearer_token",
    #     "api_key_env": "PROPZY_API_KEY",
    #     "is_primary": False,
    #     "notes": "Cần API key — uncomment khi có key",
    # },
}


# ==============================================================================
# PROHIBITED SOURCES — Nguồn tuyệt đối không được thu thập
# ==============================================================================

PROHIBITED_SOURCES: List[str] = [
    # Fake/scam sites
    "nhadat24h.net",       # Nhiều tin rao không xác thực
    # Sites yêu cầu đăng nhập/payment mà không có agreement
    # Sites vi phạm robots.txt một cách rõ ràng
]


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_approved_source(domain: str) -> Optional[Dict]:
    """Kiểm tra xem domain có được phép thu thập không."""
    normalized = domain.lower().strip()
    if not normalized.startswith("http"):
        normalized = f"https://{normalized}"
    if normalized in PROHIBITED_SOURCES:
        return None
    return APPROVED_SOURCES.get(normalized.replace("https://", "").replace("http://", "").split("/")[0])


def is_source_approved(domain: str) -> bool:
    """Kiểm tra nhanh domain có được phê duyệt không."""
    return get_approved_source(domain) is not None


def is_source_prohibited(domain: str) -> bool:
    """Kiểm tra nhanh domain có bị cấm không."""
    normalized = domain.lower().strip()
    if normalized.startswith("http"):
        normalized = normalized.replace("https://", "").replace("http://", "").split("/")[0]
    return normalized in PROHIBITED_SOURCES or normalized in [
        s.replace("https://", "").replace("http://", "").split("/")[0]
        for s in PROHIBITED_SOURCES
    ]


def get_allowed_districts_for_source(domain: str) -> Dict:
    """Lấy danh sách quận được phép thu thập cho 1 nguồn."""
    source = get_approved_source(domain)
    if not source:
        return {}
    return source.get("districts", {})


def get_primary_sources() -> List[Dict]:
    """Lấy danh sách nguồn chính (is_primary=True)."""
    return [
        {**cfg, "domain": domain}
        for domain, cfg in APPROVED_SOURCES.items()
        if cfg.get("is_primary", False)
    ]


def get_all_approved_domains() -> List[str]:
    """Lấy tất cả domain được phê duyệt."""
    return list(APPROVED_SOURCES.keys())


def get_scraper_sources() -> List[Dict]:
    """Lấy nguồn scraping."""
    return [
        {**cfg, "domain": domain}
        for domain, cfg in APPROVED_SOURCES.items()
        if cfg.get("type") == SourceType.SCRAPER.value
    ]


def get_api_sources() -> List[Dict]:
    """Lấy nguồn API."""
    return [
        {**cfg, "domain": domain}
        for domain, cfg in APPROVED_SOURCES.items()
        if cfg.get("type") == SourceType.API.value
    ]
