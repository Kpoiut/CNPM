# Taxonomy 02: Factor Taxonomy

> **Phiên bản:** 1.0 | **Trạng thái:** KHÓA | **Ngày:** 2026-04-22

---

## Factor Layer Architecture

```
MARKET VALUATION LAYER
├── L1: Legal & Planning
├── L2: Geometry & Shape
├── L3: Location & Access
├── L4: Environment & Hazard
├── L5: Building Quality (nhà/căn hộ)
└── L6: View & Orientation (nhà/căn hộ)

FIT SUITABILITY LAYER
├── F1: Feng Shui
├── F2: Spiritual History
├── F3: Family & Lifestyle
└── F4: Investment Profile
```

**QUAN TRỌNG:** Layer MARKET ≠ Layer FIT. Market factors ảnh hưởng giá thị trường thực. Fit factors ảnh hưởng mức độ phù hợp cá nhân.

---

## Group A: Bắt buộc cho Market Valuation (L1-L6)

### L1: Legal & Planning

| Factor Code | Tên | Direction | Confidence | Evidence Source |
|---|---|---|---|---|
| `LEGAL_FULL` | Sổ đỏ/sổ hồng đầy đủ | + | 0.95 | Giấy tờ photo |
| `LEGAL_LURC` | Giấy phép sử dụng đất | 0 | 0.85 | LURC document |
| `LEGAL_PENDING` | Đang chờ cấp | - | 0.75 | Xác minh thực địa |
| `LEGAL_DISPUTE` | Đang tranh chấp | -- | 0.90 | Tòa án/policy |
| `LEGAL_MORTGAGE` | Đang thế chấp | - | 0.85 | Ngân hàng |
| `PLANNING_ROAD_EXPAND` | Quy hoạch mở đường | -- | 0.80 | Quy hoạch 1/500 |
| `PLANNING_SETBACK` | Quy hoạch lộ giới | - | 0.80 | Quy hoạch đô thị |
| `PLANNING_COMMERCIAL` | Quy hoạch thương mại | + | 0.75 | Quy hoạch |
| `PLANNING_GREEN` | Quy hoạch cây xanh | + | 0.70 | Quy hoạch |

### L2: Geometry & Shape (Đất)

| Factor Code | Tên | Direction | Confidence | Notes |
|---|---|---|---|---|
| `GEOM_NÖHẬU` | Nở hậu (vuông vắn) | + | 0.70 | Frontage/depth ratio 1:2~1:3 |
| `GEOM_THOP_HAU` | Thóp hậu nhẹ | - | 0.60 | Đất bị thắt 1 phía |
| `GEOM_THOP_HAU_SEVERE` | Thóp hậu nặng | -- | 0.60 | Đất bị thắt cả 2 phía |
| `GEOM_TAPER_MINOR` | Taper nhẹ | - | 0.55 | Hình côn <15% |
| `GEOM_TAPER_SEVERE` | Taper nặng | -- | 0.55 | Hình côn ≥15% |
| `GEOM_IRREGULAR` | Méo/irregular | - | 0.60 | Đa giác phức tạp |
| `GEOM_CORNER_PLOT` | Đất góc | + | 0.65 | 2+ mặt tiền |
| `DEPTH_60_PLUS` | Chiều sâu ≥60m | - | 0.55 | Quá sâu khó xây |
| `DEPTH_20_MINUS` | Chiều sâu <20m | - | 0.50 | Quá nông |

### L3: Location & Access

| Factor Code | Tên | Direction | Confidence | Notes |
|---|---|---|---|---|
| `ACCESS_MAIN_STREET` | Mặt đường chính ≥8m | ++ | 0.90 | Đường ô tô |
| `ACCESS_ALLEY_5M` | Hẻm ≥5m | + | 0.85 | Ô tô vào được |
| `ACCESS_ALLEY_3M` | Hẻm 3-5m | 0 | 0.80 | Xe máy thoải mái |
| `ACCESS_ALLEY_2M` | Hẻm 2-3m | - | 0.80 | Xe máy khó |
| `ACCESS_ALLEY_1M` | Hẻm <2m | -- | 0.75 | Không xe |
| `ACCESS_DEAD_END` | Hẻm cụt | - | 0.70 | Không lối thoát |
| `ACCESS_ALLEY_BRANCH` | Hẻm có nhánh | - | 0.60 | Phức tạp |
| `ACCESS_TRUCK` | Xe tải lớn vào được | + | 0.70 | Thương mại |
| `DIST_CENTER_2KM` | Cách trung tâm <2km | + | 0.85 | Đô thị |
| `DIST_CENTER_5KM` | Cách trung tâm 2-5km | 0 | 0.80 | Vùng ven đô |
| `DIST_CENTER_10KM` | Cách trung tâm 5-10km | - | 0.75 | Ngoại thành |
| `DIST_METRO_500M` | Cách metro <500m | ++ | 0.85 | Hà Nội/HCM |

### L4: Environment & Hazard

| Factor Code | Tên | Direction | Confidence | Notes |
|---|---|---|---|---|
| `ENV_FLOOD_NONE` | Không ngập | + | 0.80 | Khảo sát |
| `ENV_FLOOD_MINOR` | Ngập nhẹ (lụt cục bộ) | - | 0.75 | Lịch sử ngập |
| `ENV_FLOOD_SEVERE` | Ngập nặng/thường xuyên | -- | 0.85 | Bản đồ ngập |
| `ENV_CEMETERY_200M` | Gần nghĩa trang <200m | - | 0.70 | Tâm linh+thực |
| `ENV_LANDFILL_500M` | Gần bãi rác <500m | - | 0.70 | Khảo sát |
| `ENV_POWER_LINE` | Gần cột điện cao áp | - | 0.65 | Bản đồ |
| `ENV_POLLUTION_HIGH` | Ô nhiễm cao | - | 0.60 | Cảm biến |
| `NOISE_DAY_65DB` | Tiếng ồn ngày ≥65dB | - | 0.75 | IoT/cảm biến |
| `NOISE_NIGHT_55DB` | Tiếng ồn đêm ≥55dB | -- | 0.75 | IoT/cảm biến |
| `ENV_RIVER_200M` | Cách sông <200m | + | 0.70 | View sông |
| `ENV_PARK_300M` | Cách công viên <300m | + | 0.65 | Bản đồ |

### L5: Building Quality (Nhà/căn hộ)

| Factor Code | Tên | Direction | Confidence | Notes |
|---|---|---|---|---|
| `BLDG_NEW_5Y` | Xây dựng ≤5 năm | + | 0.80 | Biên nhận/thuế |
| `BLDG_MID_10Y` | Xây dựng 5-10 năm | 0 | 0.75 | Ước lượng |
| `BLDG_OLD_20Y` | Xây dựng 10-20 năm | - | 0.70 | Kiểm tra thực |
| `BLDG_VERY_OLD_20Y+` | Xây dựng >20 năm | -- | 0.70 | Kiểm tra thực |
| `BLDG_STRUCTURE_RC` | Kết cấu bê tông | + | 0.85 | Giấy phép |
| `BLDG_STRUCTURE_BRICK` | Kết cấu gạch | 0 | 0.80 | Kiểm tra |
| `BLDG_STRUCTURE_WOOD` | Kết cấu gỗ/tạm | -- | 0.80 | Kiểm tra |
| `BLDG_FLOORS_OPTIMAL` | Số tầng tối ưu vùng | 0 | 0.70 | Quy hoạch |
| `BLDG_FLOORS_EXCEED` | Vượt tầng quy hoạch | -- | 0.85 | Quy hoạch |
| `BLDG_ATTIC` | Có áp mái | + | 0.65 | Kiểm tra |
| `BLDG_BASEMENT` | Có tầng hầm | + | 0.70 | Phép xây |

### L6: View & Orientation (Căn hộ/Nhà)

| Factor Code | Tên | Direction | Confidence | Notes |
|---|---|---|---|---|
| `APT_VIEW_RIVER` | View sông/nước | ++ | 0.80 | Ảnh/thực địa |
| `APT_VIEW_PARK` | View công viên | + | 0.70 | Ảnh |
| `APT_VIEW_CITY` | View thành phố | + | 0.65 | Ảnh |
| `APT_NO_VIEW` | Không view (hướng tường) | -- | 0.75 | Ảnh |
| `APT_FLOOR_HIGH_15+` | Tầng ≥15 | + | 0.80 | Chủng từ |
| `APT_FLOOR_LOW_3-` | Tầng ≤3 | - | 0.75 | Chủng từ |
| `APT_FLOOR_MID_4-14` | Tầng 4-14 | 0 | 0.70 | Tiêu chuẩn |
| `APT_ELEVATOR_CLOSE` | Gần thang máy | - | 0.65 | Ồn, đông |
| `APT_ELEVATOR_FAR` | Xa thang máy | - | 0.60 | Bất tiện |
| `APT_TRASH_NEAR` | Gần phòng rác | - | 0.70 | Mùi, ồn |
| `APT_CORE_ADJACENT` | Liền lõi kỹ thuật | -- | 0.70 | Ồn, rung |
| `APT_SUNLIGHT_WEST_STRONG` | Nắng Tây gay gắt | - | 0.70 | Hướng nhà |
| `APT_SUNLIGHT_GOOD` | Nắng tốt, không Tây | + | 0.65 | Hướng nhà |
| `APT_VENTILATION_GOOD` | Thông thoáng tốt | + | 0.70 | Kiểm tra |
| `APT_VENTILATION_POOR` | Thông thoáng kém | - | 0.70 | Kiểm tra |
| `APT_LAYOUT_OPEN` | Layout mở, hiện đại | + | 0.65 | Sơ đồ |
| `APT_LAYOUT_FRAGMENTED` | Layout phân mảnh | - | 0.60 | Sơ đồ |
| `ORIENTATION_NORTH` | Hướng Bắc | + | 0.60 | Tâm linh VN |
| `ORIENTATION_SOUTH` | Hướng Nam | + | 0.55 | Tâm linh VN |
| `ORIENTATION_EAST` | Hướng Đông | + | 0.55 | Tâm linh VN |

---

## Group B: Fit Suitability Factors (F1-F4)

> **QUY TẮC:** F1-F4 KHÔNG BAO GIỜ chảy vào market_value. Chỉ ảnh hưởng fit_score.

### F1: Feng Shui

| Factor Code | Tên | Notes | Confidence |
|---|---|---|---|
| `FS_AGE_COMPATIBLE` | Tuổi phù hợp hướng nhà | Dựa trên ngũ hành | 0.50 |
| `FS_AGE_INCOMPATIBLE` | Tuổi xung hướng | Theo bảng phong thủy | 0.50 |
| `FS_ELEMENT_WOOD` | Hành Mộc | Nhà hướng Đông/Đông Nam | 0.45 |
| `FS_ELEMENT_FIRE` | Hành Hỏa | Nhà hướng Nam | 0.45 |
| `FS_ELEMENT_EARTH` | Hành Thổ | Nhà hướng Tây Nam/Tây Bắc | 0.45 |
| `FS_ELEMENT_METAL` | Hành Kim | Nhà hướng Tây/Bắc | 0.45 |
| `FS_ELEMENT_WATER` | Hành Thủy | Nhà hướng Bắc | 0.45 |

### F2: Spiritual History

| Factor Code | Tên | Direction | Confidence |
|---|---|---|---|
| `SPIRIT_DEATH_RECORDED` | Có tử vong trong nhà | - | 0.60 |
| `SPIRIT_WORSHIP_NEAR` | Gần đền/chùa/nhà thờ | + | 0.55 |
| `SPIRIT_STIGMA_KNOWN` | Điểm灵的 đã biết | - | 0.50 |
| `SPIRIT_STIGMA_VERIFIED` | Điểm灵的 đã xác minh | -- | 0.70 |
| `SPIRIT_HISTORY_CLEAN` | Lịch sử sạch | + | 0.70 |

### F3: Family & Lifestyle

| Factor Code | Tên | Notes | Confidence |
|---|---|---|---|
| `FAM_SMALL_2-3` | Gia đình 2-3 người | Căn hộ vừa | 0.70 |
| `FAM_LARGE_5+` | Gia đình đông 5+ người | Cần ≥3 phòng ngủ | 0.70 |
| `FAM_ELDERLY` | Có người già | Cần thang máy, không cao tầng | 0.70 |
| `FAM_YOUNG_CHILDREN` | Có trẻ nhỏ | Cần sân chơi, an toàn | 0.65 |
| `LIFE_NOISE_SENSITIVE` | Nhạy cảm tiếng ồn | Không hẻm đông, không đường lớn | 0.60 |
| `LIFE_PARK_REQUIRED` | Cần công viên gần | Trẻ nhỏ/thú cưng | 0.55 |

### F4: Investment Profile

| Factor Code | Tên | Notes | Confidence |
|---|---|---|---|
| `INVEST_SHORT_TERM` | Đầu tư ngắn hạn | Ưu tiên thanh khoản | 0.70 |
| `INVEST_LONG_TERM` | Đầu tư dài hạn | Ưu tiên giá trị | 0.65 |
| `LIQUIDITY_HIGH_NEED` | Cần thanh khoản cao | Bán nhanh > giá cao | 0.70 |
| `LIQUIDITY_LOW_NEED` | Không cần thanh khoản | Giữ dài hạn | 0.60 |
| `RENT_YIELD_FOCUS` | Ưu tiên cho thuê | Vị trí cho thuê tốt | 0.65 |

---

## Factor Priority cho Alpha (20 factors đầu tiên)

### Nhóm Market (L1-L6) — ưu tiên cho alpha:

1. `LEGAL_FULL` — Pháp lý rõ ràng
2. `LEGAL_PENDING` — Pháp lý đang chờ
3. `PLANNING_ROAD_EXPAND` — Quy hoạch mở đường
4. `ACCESS_MAIN_STREET` — Mặt đường chính
5. `ACCESS_ALLEY_3M` — Hẻm 3-5m
6. `ACCESS_ALLEY_2M` — Hẻm 2-3m
7. `ACCESS_ALLEY_1M` — Hẻm <2m
8. `ACCESS_DEAD_END` — Hẻm cụt
9. `ENV_FLOOD_MINOR` — Ngập nhẹ
10. `ENV_FLOOD_SEVERE` — Ngập nặng
11. `ENV_CEMETERY_200M` — Gần nghĩa trang
12. `GEOM_NÖHẬU` — Nở hậu
13. `GEOM_THOP_HAU` — Thóp hậu
14. `GEOM_CORNER_PLOT` — Đất góc
15. `APT_VIEW_RIVER` — View sông
16. `APT_VIEW_CITY` — View thành phố
17. `APT_NO_VIEW` — Không view
18. `APT_FLOOR_HIGH_15+` — Tầng cao
19. `APT_FLOOR_LOW_3-` — Tầng thấp
20. `NOISE_DAY_65DB` — Tiếng ồn ngày cao

### Nhóm Fit (F1-F4) — cho phiên bản đầy đủ:

21. `FS_AGE_COMPATIBLE` / `FS_AGE_INCOMPATIBLE`
22. `SPIRIT_DEATH_RECORDED`
23. `SPIRIT_HISTORY_CLEAN`
24. `LIQUIDITY_HIGH_NEED`

---

## Delta Reference Tables (Bảng tham chiếu điều chỉnh)

| Factor Code | Delta Reference (VND/m²) | Reference Condition |
|---|---|---|
| `LEGAL_FULL` | +3tr đến +6tr | Hà Nội, so với LURC |
| `LEGAL_PENDING` | -5tr đến -10tr | So với legal full |
| `ACCESS_MAIN_STREET` | +5tr đến +15tr | Đường ≥12m so với hẻm |
| `ACCESS_ALLEY_3M` | baseline | Reference |
| `ACCESS_ALLEY_2M` | -3tr đến -7tr | So với alley 3m |
| `ACCESS_ALLEY_1M` | -8tr đến -15tr | Không xe vào |
| `ACCESS_DEAD_END` | -2tr đến -5tr | Hẻm cụt |
| `ENV_FLOOD_MINOR` | -3tr đến -8tr | Ngập theo mùa |
| `ENV_FLOOD_SEVERE` | -10tr đến -20tr | Thường xuyên |
| `GEOM_NÖHẬU` | +2tr đến +5tr | Vuông vắn |
| `GEOM_THOP_HAU` | -3tr đến -8tr | Taper |
| `APT_VIEW_RIVER` | +5tr đến +12tr | View sông |
| `APT_NO_VIEW` | -3tr đến -8tr | Tường đối diện |
| `APT_FLOOR_HIGH_15+` | +2tr đến +8tr | Cao tầng |
| `APT_FLOOR_LOW_3-` | -2tr đến -5tr | Thấp tầng |
