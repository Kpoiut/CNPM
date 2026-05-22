# Product Specification v1.0 — Real Estate Decision Intelligence Platform

> **Ngày:** 2026-04-22
> **Trạng thái:** KHÓA — Không thay đổi sau khi sign-off
> **Owner:** Architecture Team
> **Version:** 1.0
> **Round 22:** FastAPI tái cấu trúc (schemas/deps), ML KNN features, frontend API client + TanStack Query

---

## 1. Định nghĩa cốt lõi (3 định nghĩa bắt buộc)

### 1.1 Market Value (Giá trị thị trường)

**Định nghĩa:** Giá trị thị trường là ước tính giá có thể giao dịch hợp lý của tài sản dựa trên các yếu tố **có thể bảo vệ bằng bằng chứng thị trường hoặc khảo sát thực địa**.

**Thuộc về Layer:** `MARKET_VALUATION`

**Yếu tố market value:**
- Pháp lý (quyền sở hữu, giấy tờ)
- Quy hoạch (đất quy hoạch, khu dân cư)
- Vị trí (hẻm/đường, khoảng cách trung tâm)
- Hình dạng (nở hậu, thóp hậu, méo)
- Hạ tầng (đường, điện, nước)
- View (cây xanh, hồ, không view)
- Tiếng ồn (độ ồn ngày/đêm)
- Ngập (vùng ngập, cao độ)
- Tầng (với căn hộ)
- Độ thoáng (với căn hộ)
- Nắng Tây (hướng chiếu buổi chiều)

**Output mẫu:**
```
fair_market_value: 6.8 tỷ
quick_sale_value:  6.45 tỷ   (fair - 5.1%)
listing_value:     7.1 tỷ   (fair + 4.4%)
range_low:         6.6 tỷ
range_high:        7.2 tỷ
liquidity:         medium
confidence:        0.71
```

### 1.2 Fit Score (Điểm phù hợp cá nhân)

**Định nghĩa:** Fit score là điểm đánh giá mức độ phù hợp của tài sản với **niềm tin, nhu cầu, và bối cảnh cụ thể của một người mua/cá nhân cụ thể**. Không phải giá trị thị trường.

**Thuộc về Layer:** `FIT_SUITABILITY`

**Yếu tố fit (tách biệt khỏi market value):**
- Hướng nhà phù hợp tuổi/ngũ hành
- Cung mệnh người mua
- Lịch sử tâm linh của đất (có chết chóc không, có ma không)
- Mức độ nghe tiếng ồn chấp nhận được
- Ưu tiên view (sẵn sàng đổi view lấy giá)
- Nhu cầu thanh khoản nhanh
- Cấu trúc gia đình (trẻ nhỏ vs người già)
- Ngân sách thực tế (khác với budget band)
- Tầm nhìn đầu tư (ngắn hạn/trung hạn/dài hạn)

**Output mẫu:**
```
persona_fit_score:     0.73
feng_shui_fit:         0.85
liquidity_fit:         0.60
family_layout_fit:     0.90
overall_fit_reason:    "Phù hợp gia đình 4 người, tuổi 1985, cần ở dài hạn"
warnings:              ["Hướng Đông Nam hơi xung với Tuổi 1985", "Khu vực hay ngập nhẹ"]
```

### 1.3 Confidence (Độ tin cậy)

**Định nghĩa:** Confidence là mức độ tin cậy của kết quả định giá, dựa trên **chất lượng và số lượng bằng chứng hỗ trợ**, không phải mức độ chắc chắn về giá.

**Thuộc về Layer:** `CONFIDENCE_EVIDENCE`

**Cấu phần confidence:**
- `evidence_tier`: E1-E5 (từ `quality_assessment.py`)
  - E1: Khảo sát thực địa + xác minh độc lập + ảnh chứng + traceable collector
  - E2: Xác minh + source mạnh + ít nhất 1 independent check
  - E3: Public listing + partial validation + field context
  - E4: Public listing signal + traceability nhưng weak market anchoring
  - E5: Low-evidence, không traceability, không validation
- `effective_sample_size`: Neff dựa trên alpha-weighted evidence
- `anchor_share`: tỷ lệ E1+E2 trong comparable set
- `source_diversity`: số nguồn độc lập
- `data_freshness`: ngày thu thập gần nhất
- `comparable_count`: số lượng comparable trong cùng quận

**Output mẫu:**
```
confidence_score:     0.71
confidence_grade:    B
evidence_tier:        E2
effective_sample:     47.3
anchor_share:        0.23
source_diversity:    3
data_freshness_days: 45
interval_ratio:       0.068
```

---

## 2. Output Contract (3 lớp)

Mỗi lần gọi API định giá, hệ thống phải trả đủ 3 lớp:

```json
{
  "market_valuation": {
    "fair_market_value": 6_800_000_000,
    "quick_sale_value": 6_450_000_000,
    "recommended_listing": 7_100_000_000,
    "optimistic_ask": 7_400_000_000,
    "expected_range_low": 6_600_000_000,
    "expected_range_high": 7_200_000_000,
    "liquidity_score": "medium",
    "liquidity_band": "medium",
    "adjustment_ledger": [
      {
        "factor_code": "LEGAL_FULL",
        "layer": "MARKET",
        "delta_pct": 0.04,
        "delta_vnd": 260_000_000,
        "confidence": 0.90,
        "rationale": "Sổ đỏ rõ ràng, không tranh chấp",
        "evidence_id": "ev_001"
      },
      {
        "factor_code": "ALLEY_NARROW",
        "layer": "MARKET",
        "delta_pct": -0.065,
        "delta_vnd": -420_000_000,
        "confidence": 0.80,
        "rationale": "Hẻm 2.8m, xe máy vào được nhưng ô tô không",
        "evidence_id": "ev_002"
      }
    ],
    "base_price_from_comps": 6_540_000_000
  },
  "fit_suitability": {
    "persona_fit_score": 0.73,
    "feng_shui_fit": 0.85,
    "liquidity_fit": 0.60,
    "family_layout_fit": 0.90,
    "adjustment_ledger": [
      {
        "factor_code": "ORIENTATION_MISMATCH",
        "layer": "FIT",
        "delta_pct": -0.03,
        "delta_vnd": -195_000_000,
        "confidence": 0.55,
        "rationale": "Hướng Đông Nam hơi xung với tuổi 1985",
        "evidence_id": "fs_001"
      }
    ]
  },
  "confidence_evidence": {
    "overall_confidence": 0.71,
    "confidence_grade": "B",
    "evidence_tier": "E2",
    "data_freshness_days": 45,
    "effective_sample_size": 47.3,
    "comparable_count": 12,
    "comparable_breakdown": {
      "E1": 2,
      "E2": 3,
      "E3": 5,
      "E4": 2,
      "E5": 0
    },
    "warnings": ["Thiếu E1 trong comparable set", "Neff dưới ngưỡng 50"],
    "recommendations": ["Bổ sung khảo sát thực địa để nâng E1"]
  }
}
```

---

## 3. Anti-Patterns bắt buộc tránh

1. **KHÔNG** nhét phong thủy/tâm linh vào cùng score với market_value
2. **KHÔNG** dùng one-hot thô cho biến có cấu trúc (hướng nhà, loại hẻm)
3. **KHÔNG** để comparable_score và price_adjustment nhập nhằng
4. **KHÔNG** hardcode 6 quận trong logic sản phẩm lõi
5. **KHÔNG** output chỉ một số giá không kèm adjustment ledger
6. **KHÔNG** dùng một form chung cho mọi loại tài sản

---

## 4. Comparable Engine Contract

Comparable engine là **engine riêng**, không phải phụ thuộc của prediction.

**5 lớp xử lý:**

```
1. Candidate Retrieval     → Tìm tất cả property trong cùng ward/quận cùng loại
2. Similarity Scoring     → Tính similarity score (nhiều chiều, không chỉ area)
3. Adjustment Normalization → Điều chỉnh comparable về property mục tiêu
4. Evidence Ranking       → Xếp hạng comparable theo evidence tier
5. Explanation Rendering   → Sinh human-readable explanation
```

**Similarity phải gồm:**
- `asset_subtype_similarity` (cùng loại phụ)
- `geo_proximity` (khoảng cách Euclidean từ lat/lng)
- `access_class_similarity` (hẻm/đường, chiều rộng)
- `legal_comparability` (cùng pháp lý vs khác)
- `geometry_comparability` (taper, irregularity)
- `frontage_depth_ratio_similarity` (với đất)
- `floor_view_similarity` (với căn hộ)
- `recency_weight` (ngày giao dịch)
- `source_quality_weight` (E1-E5)

**QUAN TRỌNG:** Similarity score ≠ Price adjustment. Đây là 2 lớp riêng biệt.

---

## 5. Asset-Type Specific Flows

### 5.1 Đất (Land)

**Form fields riêng:**
- Polygon geometry (vẽ trên bản đồ)
- Đa đỉnh với edge lengths
- Nở hậu / thóp hậu score
- Chiều sâu biến thiên
- Hẻm phụ có/không
- Phần tóp/méo

**Adjustment riêng:**
- `GEOM_NÖHẬU`: +X% nở hậu (đất vuông vắn)
- `GEOM_THOP_HAU`: -X% thóp hậu (đất bị thắt)
- `GEOM_TAPER`: -X% hình dạng côn
- `GEOM_IRREGULAR`: -X% méo/irregular
- `ALLEY_BRANCH`: -X% hẻm phụ
- `DEPTH_VARIATION`: +/-X% chiều sâu biến thiên
- `FRONTAGE_DEPTH_RATIO`: +X% frontage/depth ratio tối ưu

### 5.2 Căn hộ (Apartment)

**Form fields riêng:**
- Hướng cửa chính (8 hướng)
- Hướng ban công/view
- View type (city, garden, nothing, river, mountain)
- Tầng (số thực, không phải floor_count chung)
- Vị trí trong block (đầu/cuối/cánh)
- Khoảng cách thang máy
- Khoảng cách phòng rác
- Khoảng cách lõi kỹ thuật
- Bố cục (cửa-bếp-toilet-ban công)
- Độ thoáng
- Tiếng ồn thực đo

**Adjustment riêng:**
- `APT_FLOOR_PREMIUM`: +/-X% theo tầng
- `APT_ELEVATOR_DISTANCE`: -X% gần thang máy quá hoặc xa quá
- `APT_TRASH_DISTANCE`: -X% gần phòng rác
- `APT_CORE_PROXIMITY`: -X% gần lõi kỹ thuật
- `APT_VIEW_CITY`: +X% view thành phố
- `APT_VIEW_RIVER`: +X% view sông
- `APT_NO_VIEW`: -X% không view
- `APT_SUNLIGHT_WEST`: -X% nắng Tây gay gắt
- `APT_VENTILATION`: +/-X% độ thoáng
- `APT_NOISE`: -X% tiếng ồn cao
- `APT_LAYOUT_BALCONY`: +X% bố cục tốt

### 5.3 Nhà phố (Townhouse)

**Form fields riêng:**
- Số mặt tiền (1, 2, 3)
- Chiều sâu nhà
- Hướng mặt tiền
- Tầng thực tế (không phải floor_count)
- Kết cấu (bê tông, gạch, vật liệu khác)
- Năm xây dựng (ước tính)
- Tầng áp mái có/không

**Adjustment riêng:**
- `HOUSE_FACADE_COUNT`: +X% nhiều mặt tiền
- `HOUSE_DEPTH`: +/-X% chiều sâu bất thường
- `HOUSE_STRUCTURE`: +/-X% theo kết cấu
- `HOUSE_AGE`: -X% nhà cũ theo năm
- `HOUSE_ATTIC`: +X% có áp mái

---

## 6. Migration Strategy (Strangler Fig)

**KHÔNG xóa legacy predictor ngay.**

1. Giữ legacy predictor làm baseline
2. Dựng engine mới song song
3. Cùng một asset → trả cả 2 kết quả
4. Log deviation giữa 2 kết quả
5. Review 50-100 ca thực tế
6. Cutover khi explanation quality + range quality đủ tốt

**Cutover criteria:**
- Deviation trung bình < 8% giữa legacy và new
- Adjustment ledger có đủ 10+ factor cho ít nhất 70% predictions
- Evidence tier coverage: >60% predictions có ít nhất E2 comparable

---

## 7. Schema Bounded Modules (Tóm tắt)

17 bảng được phân thành 4 nhóm:

**Asset Core:**
1. `property_asset` — ID, loại tài sản, subtype, mục đích, status
2. `location_context` — Province, district, ward, lat/lng, geocode_quality
3. `parcel_geometry` — Polygon, diện tích official/measured, frontage, depth_profile, taper, irregularity
4. `building_unit` — Built area, floors, bedrooms, bathrooms, structure_grade
5. `apartment_attributes` — Block, floor, position, orientations, view, distances, layout flags

**Market Context:**
6. `legal_planning` — Ownership type, certificate status, disputes, mortgage, planning zone, setback risks
7. `environment_context` — Flood risk, cemetery distance, landfill distance, transmission lines, pollution, noise
8. `access_context` — Road width, alley width, truck/car access, dead end, road class

**Overlay:**
9. `spiritual_history` — Death history flag, worship proximity, stigma notes, verified level
10. `persona_profile` — Buyer archetype, budget band, holding horizon, feng_shui sensitivity, liquidity preference, family structure

**Valuation Output:**
11. `valuation_run` — Run ID, asset ID, engine version, base_price, fair_value, quick_sale, listing, range, liquidity
12. `valuation_adjustment` — Factor code, layer, direction, delta_pct, delta_vnd, confidence, rationale, evidence_id
13. `evidence_asset` — Source type, URL, images, survey notes, verified_by, verified_at

---

*Sign-off: [ ] Architecture Lead | [ ] Product Owner | [ ] Engineering Lead*
