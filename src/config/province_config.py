"""
Canonical province configuration for Real Estate AVM.
Dùng file này làm NGUỒN DUY NHẤT cho tên tỉnh/thành.
KHÔNG hardcode tên tỉnh ở bất kỳ đâu khác.

Usage:
    from src.config.province_config import (
        CANONICAL_PROVINCES, NORMALIZE_PROVINCE,
        CENTER_COORDS, BASE_PRICES_PER_M2, SCOPE_DISTRICTS,
    )
"""

from typing import Dict, List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL PROVINCE NAMES (dùng trong DB và API)
# ═══════════════════════════════════════════════════════════════════════════════
CANONICAL_PROVINCES: List[str] = [
    "Hà Nội",
    "TP. Hồ Chí Minh",
    "Đà Nẵng",
    "Hải Phòng",
    "Cần Thơ",
    "Bình Dương",
    "Đồng Nai",
    "Bà Rịa - Vũng Tàu",
    "Hà Nam",
    "Hải Dương",
    "Nam Định",
    "Thái Bình",
    "Vĩnh Phúc",
    "Bắc Ninh",
]

# Aliases → canonical name (để normalize input từ user/scraper/ML)
NORMALIZE_PROVINCE: Dict[str, str] = {
    # TP.HCM variants
    "ho chi minh": "TP. Hồ Chí Minh",
    "tp ho chi minh": "TP. Hồ Chí Minh",
    "tp hcm": "TP. Hồ Chí Minh",
    "tp hồ chí minh": "TP. Hồ Chí Minh",
    "hochiminh": "TP. Hồ Chí Minh",
    "hcm": "TP. Hồ Chí Minh",
    "ho chi minh city": "TP. Hồ Chí Minh",
    # Hà Nội variants
    "ha noi": "Hà Nội",
    "hanoi": "Hà Nội",
    "hn": "Hà Nội",
    "ha noi city": "Hà Nội",
    # Đà Nẵng variants
    "da nang": "Đà Nẵng",
    "danang": "Đà Nẵng",
    "đà nẵng": "Đà Nẵng",
    # Others
    "hai phong": "Hải Phòng",
    "can tho": "Cần Thơ",
    "binh duong": "Bình Dương",
    "dong nai": "Đồng Nai",
    "ba ria - vung tau": "Bà Rịa - Vũng Tàu",
    "ha nam": "Hà Nam",
    "hai duong": "Hải Dương",
    "nam dinh": "Nam Định",
    "thai binh": "Thái Bình",
    "vinh phuc": "Vĩnh Phúc",
    "bac ninh": "Bắc Ninh",
    # Old wrong spellings (dùng trong code cũ — BUG FIX)
    "ha no": "Hà Nội",         # FIX: typo cũ
    "ha noi": "Hà Nội",        # FIX: English spelling
    "tp. ho chi minh": "TP. Hồ Chí Minh",  # FIX: English spelling
    "tp. ho chi minh": "TP. Hồ Chí Minh",
}


def normalize_province(name: Optional[str]) -> Optional[str]:
    """Normalize a province name to its canonical form."""
    if not name:
        return None
    key = str(name).strip().lower()
    return NORMALIZE_PROVINCE.get(key, name.strip())


def is_valid_province(name: Optional[str]) -> bool:
    """Check if a province name is a valid canonical name."""
    if not name:
        return False
    return name.strip() in CANONICAL_PROVINCES


# ═══════════════════════════════════════════════════════════════════════════════
# GEO COORDINATES (lat, lng) của trung tâm thành phố
# ═══════════════════════════════════════════════════════════════════════════════
CENTER_COORDS: Dict[str, Tuple[float, float]] = {
    "Hà Nội": (21.0285, 105.8542),
    "TP. Hồ Chí Minh": (10.8231, 106.6297),
    "Đà Nẵng": (16.0544, 108.2022),
    "Hải Phòng": (20.8449, 106.6881),
    "Cần Thơ": (10.0381, 105.7831),
    "Bình Dương": (13.1691, 106.8806),
    "Đồng Nai": (10.9448, 107.0663),
    "Bà Rịa - Vũng Tàu": (10.5418, 107.0849),
    "Hà Nam": (20.5835, 105.9236),
    "Hải Dương": (20.9399, 106.3009),
    "Nam Định": (20.4195, 106.1636),
    "Thái Bình": (20.4493, 106.3367),
    "Vĩnh Phúc": (21.3068, 105.6058),
    "Bắc Ninh": (21.1861, 106.0761),
}


# ═══════════════════════════════════════════════════════════════════════════════
# BASE PRICE PER M² (VND) — fallback khi không có dữ liệu thị trường
# ═══════════════════════════════════════════════════════════════════════════════
# Nguồn: tham khảo thị trường Q1/2026, chỉ dùng làm FALLBACK
# Luôn ưu tiên dữ liệu thực từ DB
#
# ĐẤT NỀN:    giá đất thuần — cao nhất vì quyền sử dụng đất 100%
# NHÀ PHỐ:    giá bao gồm đất + công trình — khấu hao tùy tuổi
# CHUNG CƯ:   giá sàn thông thủy — không bao gồm đất riêng
# BIỆT THỰ:   giá đất + khuôn viên + công trình
BASE_PRICES_PER_M2: Dict[str, Dict[str, int]] = {
    "Hà Nội": {
        "LAND":      90_000_000,
        "TOWNHOUSE": 65_000_000,
        "HOUSE":     55_000_000,   # ~15% below townhouse
        "APARTMENT": 48_000_000,
        "VILLA":     85_000_000,
    },
    "TP. Hồ Chí Minh": {
        "LAND":      80_000_000,
        "TOWNHOUSE": 60_000_000,
        "HOUSE":     50_000_000,
        "APARTMENT": 45_000_000,
        "VILLA":     75_000_000,
    },
    "Đà Nẵng": {
        "LAND":      40_000_000,
        "TOWNHOUSE": 30_000_000,
        "HOUSE":     25_000_000,
        "APARTMENT": 25_000_000,
        "VILLA":     55_000_000,
    },
    "Hải Phòng": {
        "LAND":      25_000_000,
        "TOWNHOUSE": 18_000_000,
        "HOUSE":     15_000_000,
        "APARTMENT": 15_000_000,
        "VILLA":     30_000_000,
    },
    "Cần Thơ": {
        "LAND":      20_000_000,
        "TOWNHOUSE": 15_000_000,
        "HOUSE":     12_000_000,
        "APARTMENT": 12_000_000,
        "VILLA":     25_000_000,
    },
    "Bình Dương": {
        "LAND":      28_000_000,
        "TOWNHOUSE": 20_000_000,
        "HOUSE":     17_000_000,
        "APARTMENT": 22_000_000,
        "VILLA":     35_000_000,
    },
    "Đồng Nai": {
        "LAND":      22_000_000,
        "TOWNHOUSE": 18_000_000,
        "HOUSE":     15_000_000,
        "APARTMENT": 18_000_000,
        "VILLA":     28_000_000,
    },
    "Bà Rịa - Vũng Tàu": {
        "LAND":      25_000_000,
        "TOWNHOUSE": 20_000_000,
        "HOUSE":     17_000_000,
        "APARTMENT": 18_000_000,
        "VILLA":     35_000_000,
    },
    "Hà Nam": {
        "LAND":      15_000_000,
        "TOWNHOUSE": 12_000_000,
        "HOUSE":     10_000_000,
        "APARTMENT": 10_000_000,
        "VILLA":     18_000_000,
    },
    "Hải Dương": {
        "LAND":      15_000_000,
        "TOWNHOUSE": 12_000_000,
        "HOUSE":     10_000_000,
        "APARTMENT": 10_000_000,
        "VILLA":     18_000_000,
    },
    "Nam Định": {
        "LAND":      12_000_000,
        "TOWNHOUSE": 10_000_000,
        "HOUSE":     8_500_000,
        "APARTMENT": 8_000_000,
        "VILLA":     15_000_000,
    },
    "Thái Bình": {
        "LAND":      12_000_000,
        "TOWNHOUSE": 10_000_000,
        "HOUSE":     8_500_000,
        "APARTMENT": 8_000_000,
        "VILLA":     15_000_000,
    },
    "Vĩnh Phúc": {
        "LAND":      18_000_000,
        "TOWNHOUSE": 14_000_000,
        "HOUSE":     12_000_000,
        "APARTMENT": 12_000_000,
        "VILLA":     22_000_000,
    },
    "Bắc Ninh": {
        "LAND":      20_000_000,
        "TOWNHOUSE": 15_000_000,
        "HOUSE":     12_500_000,
        "APARTMENT": 14_000_000,
        "VILLA":     25_000_000,
    },
}


def get_base_price_per_m2(province: str, asset_type: str) -> int:
    """Get base price per m2 for a specific province + asset type.

    Falls back gracefully: province-specific → province default → system default.
    Uses canonical property_types taxonomy.
    """
    from src.domain.property_types import to_price_category

    category = to_price_category(asset_type)

    province_prices = BASE_PRICES_PER_M2.get(province)
    if province_prices:
        return province_prices.get(category, province_prices.get("TOWNHOUSE", 30_000_000))
    return 30_000_000  # System-wide fallback


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE DISTRICTS — các quận có luồng dữ liệu đủ chất lượng cho ML
# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE_DISTRICTS: 6 quận gốc — ML train trên 6 quận này
# Mở rộng scope = retrain model → để sau khi có đủ dữ liệu thực tế
SCOPE_DISTRICTS: Dict[str, List[str]] = {
    "Hà Nội": [
        "Quận Cầu Giấy",
        "Quận Thanh Xuân",
        "Quận Đống Đa",
    ],
    "TP. Hồ Chí Minh": [
        "Quận 7",
        "Quận Bình Thạnh",
        "Quận Tân Bình",
    ],
    # Mở rộng tương lai (cần retrain ML trước)
    "Đà Nẵng": ["Quận Hải Châu", "Quận Thanh Khê", "Quận Sơn Trà"],
    "Hải Phòng": ["Quận Ngô Quyền", "Quận Hồng Bàng", "Quận Lê Chân"],
    "Cần Thơ": ["Quận Ninh Kiều", "Quận Bình Thủy", "Quận Cái Răng"],
    "Bình Dương": ["Thành phố Thủ Dầu Một", "Thành phố Dĩ An", "Thành phố Thuận An"],
    "Đồng Nai": ["Thành phố Biên Hòa", "Thành phố Long Khánh", "Huyện Trảng Bom"],
}


def get_districts_for_province(province: str) -> List[str]:
    """Get list of districts for a province, or empty list if unknown."""
    return SCOPE_DISTRICTS.get(province, [])


def is_in_scope(province: str, district: str) -> bool:
    """Check if (province, district) is within the ML training scope."""
    districts = SCOPE_DISTRICTS.get(province, [])
    return district in districts
