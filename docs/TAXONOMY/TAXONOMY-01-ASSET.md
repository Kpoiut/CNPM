# Taxonomy 01: Asset Type Taxonomy

> **Phiên bản:** 1.0 | **Trạng thái:** KHÓA | **Ngày:** 2026-04-22

---

## Asset Hierarchy (3 cấp)

```
Asset Class (Class)
├── Asset Type (Type)
│   └── Asset Subtype (Subtype)
```

---

## Cấp 1: Asset Class

| Class Code | Tên tiếng Việt | Mô tả |
|---|---|---|
| `RESIDENTIAL` | Nhà ở | Tài sản chính dùng để ở |
| `COMMERCIAL` | Thương mại | Tài sản dùng kinh doanh |
| `LAND` | Đất | Đất không có hoặc có công trình nhẹ |
| `INDUSTRIAL` | Công nghiệp | Nhà xưởng, kho bãi |
| `MIXED` | Hỗn hợp | Kết hợp nhiều mục đích |

---

## Cấp 2: Asset Type (Loại tài sản)

### 1. RESIDENTIAL

| Type Code | Tên | Mô tả | Comparable Engine |
|---|---|---|---|
| `APARTMENT` | Căn hộ | Căn hộ chung cư | ApartmentEngine |
| `TOWNHOUSE` | Nhà phố | Nhà liền kề trong khu đô thị | TownhouseEngine |
| `VILLA` | Biệt thự | Nhà riêng lớn, độc lập | VillaEngine |
| `ROWHOUSE` | Nhà row house | Nhà hàng ghép kiểu Anh/Mỹ | TownhouseEngine |
| `PENTHOUSE` | Penthouse | Căn hộ tầng cao nhất | ApartmentEngine |
| `STUDIO` | Căn hộ studio | Căn hộ 1 phòng tối thiểu | ApartmentEngine |

### 2. COMMERCIAL

| Type Code | Tên | Mô tả | Comparable Engine |
|---|---|---|---|
| `SHOPHOUSE` | Shophouse | Mặt bằng kinh doanh kết hợp ở | ShophouseEngine |
| `OFFICE_TEL` | Officetel | Căn hộ văn phòng | ApartmentEngine |
| `RETAIL_UNIT` | Mặt bằng bán lẻ | Cửa hàng, quầy | CommercialEngine |
| `WAREHOUSE` | Kho | Kho bãi, nhà xưởng nhẹ | IndustrialEngine |

### 3. LAND

| Type Code | Tên | Mô tả | Comparable Engine |
|---|---|---|---|
| `LAND_Urban` | Đất đô thị | Đất trong khu dân cư đô thị | LandUrbanEngine |
| `LAND_Suburban` | Đất ngoại thành | Đất vùng ven | LandSuburbanEngine |
| `LAND_Agricultural` | Đất nông nghiệp | Đất trồng trọt | LandAgriEngine |
| `LAND_Project` | Đất dự án | Đất trong dự án phát triển | LandUrbanEngine |
| `LAND_Industrial_Park` | Đất khu công nghiệp | Đất trong KCN | LandIndustrialEngine |

### 4. MIXED

| Type Code | Tên | Mô tả | Comparable Engine |
|---|---|---|---|
| `HOTEL` | Khách sạn | Khách sạn, nhà nghỉ | CommercialEngine |
| `RESORT` | Resort | Khu nghỉ dưỡng | CommercialEngine |
| `CONDO_HOTEL` | Condotel | Căn hộ khách sạn | ApartmentEngine |

---

## Cấp 3: Asset Subtype (Loại phụ — quan trọng cho comparable)

### APARTMENT

| Subtype | Mô tả | Floor Effect | View Factor |
|---|---|---|---|
| `APT_STANDARD` | Căn hộ tiêu chuẩn | standard | standard |
| `APT_PREMIUM` | Căn hộ cao cấp (≥25tr/m²) | premium curve | strong |
| `APT_LUXURY` | Căn hộ hạng sang (≥50tr/m²) | luxury curve | very strong |
| `APT_ECOnOMY` | Căn hộ kinh tế (<15tr/m²) | flat | minimal |
| `APT_PENTHOUSE` | Penthouse trong tòa | separate curve | dominant |

### LAND

| Subtype | Mô tả | Geometry Weight | Access Weight |
|---|---|---|---|
| `LAND_LEGAL_STREET` | Đất mặt đường chính | medium | dominant |
| `LAND_ALLEY_3M` | Đất hẻm ≥3m | high | high |
| `LAND_ALLEY_2M` | Đất hẻm <3m | very high | critical |
| `LAND_ALLEY_1M` | Đất hẻm <1m | critical | critical |
| `LAND_CORNER` | Đất góc 2 mặt tiền | bonus | bonus |
| `LAND_END_PLOT` | Đất cuối hẻm | varies | negative |
| `LAND_ODD_SHAPE` | Đất hình dạng bất thường | penalty | medium |

### TOWNHOUSE

| Subtype | Mô tả | Facade Factor |
|---|---|---|
| `TH_SINGLE_FACADE` | 1 mặt tiền | 1.0x |
| `TH_DOUBLE_FACADE` | 2 mặt tiền (góc) | 1.15x |
| `TH_TRIPLE_FACADE` | 3 mặt tiền | 1.25x |
| `TH_ALLEY_EXTENDED` | Có hẻm phụ mở rộng | varies |

---

## Priority Implementation Order

| Priority | Asset Type | Lý do |
|---|---|---|
| **P1** | `APARTMENT` | Thị trường lớn nhất, nhiều biến riêng bị bỏ sót |
| **P1** | `LAND_URBAN` | Đất có geometry phức tạp nhất, hiện gần như không có |
| **P2** | `TOWNHOUSE` | Thị trường phổ biến, có overlay với apartment |
| **P3** | `VILLA` | Thị trường cao cấp, có thể dùng apartment adjustments |
| **P4** | `SHOPHOUSE` | Cần commercial adjustments riêng |
| **P4** | `OFFICE_TEL` | Có thể reuse apartment engine |

---

## Validation Rules

```python
VALID_ASSET_CLASSES = {"RESIDENTIAL", "COMMERCIAL", "LAND", "INDUSTRIAL", "MIXED"}
VALID_ASSET_TYPES = {
    "RESIDENTIAL": {"APARTMENT", "TOWNHOUSE", "VILLA", "ROWHOUSE", "PENTHOUSE", "STUDIO"},
    "COMMERCIAL": {"SHOPHOUSE", "OFFICE_TEL", "RETAIL_UNIT", "WAREHOUSE"},
    "LAND": {"LAND_URBAN", "LAND_SUBURBAN", "LAND_AGRICULTURAL", "LAND_PROJECT", "LAND_INDUSTRIAL_PARK"},
    "INDUSTRIAL": {"WAREHOUSE", "FACTORY", "FACTORY_SHARED"},
    "MIXED": {"HOTEL", "RESORT", "CONDO_HOTEL"},
}
VALID_ASSET_SUBTYPES = {
    "APARTMENT": {"APT_STANDARD", "APT_PREMIUM", "APT_LUXURY", "APT_ECONOMY", "APT_PENTHOUSE"},
    "LAND_URBAN": {"LAND_LEGAL_STREET", "LAND_ALLEY_3M", "LAND_ALLEY_2M", "LAND_ALLEY_1M",
                   "LAND_CORNER", "LAND_END_PLOT", "LAND_ODD_SHAPE"},
    "TOWNHOUSE": {"TH_SINGLE_FACADE", "TH_DOUBLE_FACADE", "TH_TRIPLE_FACADE", "TH_ALLEY_EXTENDED"},
}
```

---

## Comparable Engine Routing

```python
def get_comparable_engine(asset_type: str) -> str:
    engine_map = {
        "APARTMENT": "ApartmentComparableEngine",
        "TOWNHOUSE": "TownhouseComparableEngine",
        "VILLA": "VillaComparableEngine",
        "LAND_URBAN": "LandUrbanComparableEngine",
        "LAND_SUBURBAN": "LandSuburbanComparableEngine",
        "SHOPHOUSE": "ShophouseComparableEngine",
        "OFFICE_TEL": "ApartmentComparableEngine",
    }
    return engine_map.get(asset_type, "GenericComparableEngine")
```
