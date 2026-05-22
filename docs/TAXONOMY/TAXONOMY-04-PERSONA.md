# Taxonomy 04: Persona Taxonomy

> **Phiên bản:** 1.0 | **Trạng thái:** KHÓA | **Ngày:** 2026-04-22

---

## Persona Profile Schema

```json
{
  "persona_id": "persona_uuid",
  "buyer_archetype": "FIRST_HOME_BUYER | UPGRADER | INVESTOR | SPECULATOR | RETIREE",
  "budget_band": "BELOW_2B | 2B_TO_5B | 5B_TO_10B | 10B_TO_20B | ABOVE_20B",
  "holding_horizon": "FLIP_12M | SHORT_3Y | MEDIUM_5Y | LONG_10Y | FOREVER",
  "feng_shui_sensitivity": "NONE | LOW | MEDIUM | HIGH | CRITICAL",
  "liquidity_preference": "MAX_LIQUIDITY | PREFER_LIQUID | BALANCED | PREFER_APPRECIATION",
  "family_structure": "SINGLE | COUPLE_NO_KIDS | COUPLE_WITH_KIDS | LARGE_FAMILY | ELDERLY_PARENTS",
  "noise_tolerance": "VERY_SENSITIVE | SENSITIVE | NEUTRAL | TOLERANT | VERY_TOLERANT",
  "view_preference": "PARK_REQUIRED | CITY_OK | NO_VIEW_OK | ANY_VIEW",
  "investment_profile": "RENTAL_YIELD | CAPITAL_APPRECIATION | BALANCED_RETURN",
  "location_flexibility": "CBD_ONLY | DISTRICT_FLEXIBLE | CITY_WIDE | SUBURBS_OK",
  "age_group": "UNDER_30 | 30_TO_40 | 40_TO_50 | 50_TO_60 | ABOVE_60",
  "occupation_type": "EMPLOYEE | BUSINESS_OWNER | INVESTOR | RETIRED | FREELANCER"
}
```

---

## Buyer Archetypes

### 1. FIRST_HOME_BUYER (Người mua nhà đầu tiên)

**Mô tả:** Người mua lần đầu, thường tuổi 25-35, budget vừa phải, chưa có kinh nghiệm.

**Budget band phổ biến:** `BELOW_2B`, `2B_TO_5B`
**Holding horizon:** `MEDIUM_5Y`, `LONG_10Y`, `FOREVER`

**Ưu tiên:**
- Giá rẻ nhất cho spec
- Thanh khoản tốt (bán lại được)
- An toàn pháp lý tuyệt đối
- Gần giao thông công cộng
- Ít quan tâm phong thủy

**Fit adjustments:**
- `LEGAL_FULL` → trọng số cao hơn (sẵn sàng trả thêm)
- `ACCESS_ALLEY_1M` → trọng số cao hơn (không mua hẻm nhỏ)
- `FENG_SHUI_SENSITIVITY` → thường LOW/MEDIUM

### 2. UPGRADER (Người nâng cấp)

**Mô tả:** Đã có nhà/nhỏ hơn, muốn nâng cấp lên tài sản tốt hơn. Tuổi 35-50.

**Budget band phổ biến:** `5B_TO_10B`, `10B_TO_20B`
**Holding horizon:** `MEDIUM_5Y`, `LONG_10Y`

**Ưu tiên:**
- Chất lượng xây dựng cao
- View tốt, không gian thoáng
- Khu vực tốt hơn
- Phong thủy (bắt đầu quan tâm)
- Gia đình có trẻ nhỏ

**Fit adjustments:**
- `APT_VIEW_*` → trọng số cao
- `BLDG_AGE_*` → trọng số cao (không mua nhà cũ quá)
- `FENG_SHUI_SENSITIVITY` → thường MEDIUM/HIGH

### 3. INVESTOR (Nhà đầu tư cho thuê)

**Mô tả:** Mua để cho thuê, quan tâm đến rental yield và thanh khoản. Tuổi 30-55.

**Budget band phổ biến:** `2B_TO_5B`, `5B_TO_10B`
**Holding horizon:** `SHORT_3Y`, `MEDIUM_5Y`
**Investment profile:** `RENTAL_YIELD`

**Ưu tiên:**
- Rental yield cao
- Vị trí cho thuê tốt (gần trường, bệnh viện, khu công sở)
- Thanh khoản tốt
- Ít quan tâm view/phong thủy
- Chi phí bảo trì thấp

**Fit adjustments:**
- `LOCATION_CBD_*` → trọng số cao
- `LIQUIDITY_PREFERENCE` → MAX_LIQUIDITY hoặc PREFER_LIQUID
- `BLDG_AGE_*` → không mua nhà quá cũ (chi phí bảo trì cao)

### 4. SPECULATOR (Đầu cơ ngắn hạn)

**Mô tả:** Mua để bán lại kiếm lời, chấp nhận rủi ro cao. Tuổi 25-40.

**Budget band phổ biên:** `2B_TO_5B`, `5B_TO_10B`
**Holding horizon:** `FLIP_12M`, `SHORT_3Y`
**Investment profile:** `CAPITAL_APPRECIATION`

**Ưu tiên:**
- Giá mua thấp nhất có thể
- Tiềm năng tăng giá cao
- Thanh khoản cực cao
- Chấp nhận rủi ro pháp lý
- Không quan tâm phong thủy

**Fit adjustments:**
- Quan tâm discount rate nhiều nhất
- Ưu tiên đất nền dự án mới (giá rẻ, tăng nhanh)
- `LIQUIDITY_PREFERENCE` → MAX_LIQUIDITY

### 5. RETIREE (Người về hưu)

**Mô tả:** Mua nhà ở cuối đời hoặc đầu tư an toàn. Tuổi 55+.

**Budget band phổ biến:** `2B_TO_5B`, `5B_TO_10B`
**Holding horizon:** `FOREVER`, `LONG_10Y`

**Ưu tiên:**
- An toàn tuyệt đối (pháp lý, không tranh chấp)
- Không xa bệnh viện
- Không ngập, không ồn
- Thang máy (nếu căn hộ cao tầng)
- Gần con cháu
- Quan tâm phong thủy CAO NHẤT

**Fit adjustments:**
- `LEGAL_FULL` → bắt buộc (sẽ từ chối nếu không đủ)
- `ENV_FLOOD_*` → rất nhạy cảm
- `NOISE_*` → rất nhạy cảm
- `FENG_SHUI_SENSITIVITY` → HIGH hoặc CRITICAL
- `BLDG_ELEVATOR_*` → bắt buộc nếu căn hộ cao tầng

---

## Feng Shui Sensitivity Levels

| Level | Mô tả | Impact on Market |
|---|---|---|
| `NONE` | Không quan tâm phong thủy | Không adjustment |
| `LOW` | Biết phong thủy nhưng không quyết định mua | ±1-2% |
| `MEDIUM` | Tham khảo phong thủy, có thể từ chối | ±3-5% |
| `HIGH` | Phong thủy ảnh hưởng quyết định mạnh | ±5-10% |
| `CRITICAL` | Sẽ không mua nếu phong thủy xấu | Thay đổi hoàn toàn quyết định |

**Age-to-Element mapping (Thiên can-Dương):**

| Tuổi | Thiên can | Hành | Hướng tốt | Hướng xấu |
|---|---|---|---|---|
| 1985 | Ất | Mộc | Đông, Đông Nam | Tây Bắc |
| 1986 | Bính | Hỏa | Nam | Bắc |
| 1987 | Đinh | Hỏa | Nam | Bắc |
| 1988 | Mậu | Thổ | Tây Nam, Đông Bắc | Đông |
| 1989 | Kỷ | Thổ | Tây Nam, Đông Bắc | Đông |
| 1990 | Canh | Kim |Tây, Tây Bắc | Đông Nam |
| 1991 | Tân | Kim | Tây, Tây Bắc | Đông Nam |
| 1992 | Nhâm | Thủy | Bắc | Nam |
| 1993 | Quý | Thủy | Bắc | Nam |
| 1994 | Giáp | Mộc | Đông, Đông Nam | Tây |
| 1995 | Ất | Mộc | Đông, Đông Nam | Tây |
| 1996 | Bính | Hỏa | Nam | Bắc |

---

## Liquidity Preference

| Preference | Mô tả | Suitable Asset |
|---|---|---|
| `MAX_LIQUIDITY` | Cần bán được ngay, chấp nhận giảm 10-15% | Căn hộ chung cư, đất nền dự án |
| `PREFER_LIQUID` | Ưu tiên thanh khoản, sẵn trả thêm 3-5% | Căn hộ, shophouse đường lớn |
| `BALANCED` | Cân bằng giữa giá và thanh khoản | Townhouse, villa |
| `PREFER_APPRECIATION` | Chấp nhận khóa vốn để tăng giá | Đất nền, dự án mới |

---

## Family Structure Profiles

| Structure | Mô tả | Căn hộ phù hợp | Nhà phố phù hợp |
|---|---|---|---|
| `SINGLE` | Một người | Studio, 1PN | 1-2 tầng |
| `COUPLE_NO_KIDS` | Vợ chồng chưa có con | 2PN | 2-3 tầng |
| `COUPLE_WITH_KIDS` | Gia đình có con | 3PN, gần trường | 3-4 tầng |
| `LARGE_FAMILY` | 5+ người | Hiếm phù hợp | ≥4 tầng, đất ≥100m² |
| `ELDERLY_PARENTS` | Có người già | Tầng thấp, thang máy | Không cao quá 3 tầng |

---

## Fit Score Computation

```python
def compute_fit_score(persona: PersonaProfile, asset: AssetData, adjustments: list[Adjustment]) -> FitScore:
    # Layer 1: Market fit (dựa trên budget và loại tài sản)
    budget_fit = compute_budget_fit(persona.budget_band, asset.fair_market_value)
    
    # Layer 2: Feng shui fit (nếu sensitivity > NONE)
    feng_shui_fit = compute_feng_shui_fit(persona, asset) if persona.feng_shui_sensitivity != "NONE" else 1.0
    
    # Layer 3: Family fit
    family_fit = compute_family_layout_fit(persona.family_structure, asset)
    
    # Layer 4: Lifestyle fit
    lifestyle_fit = compute_lifestyle_fit(persona, asset)
    
    # Layer 5: Investment fit
    investment_fit = compute_investment_fit(persona.investment_profile, asset)
    
    # Weighted average
    weights = {
        "FIRST_HOME_BUYER": {"budget": 0.40, "feng_shui": 0.10, "family": 0.25, "lifestyle": 0.25, "investment": 0.00},
        "UPGRADER": {"budget": 0.25, "feng_shui": 0.20, "family": 0.30, "lifestyle": 0.20, "investment": 0.05},
        "INVESTOR": {"budget": 0.20, "feng_shui": 0.05, "family": 0.00, "lifestyle": 0.15, "investment": 0.60},
        "SPECULATOR": {"budget": 0.35, "feng_shui": 0.00, "family": 0.00, "lifestyle": 0.05, "investment": 0.60},
        "RETIREE": {"budget": 0.30, "feng_shui": 0.30, "family": 0.20, "lifestyle": 0.20, "investment": 0.00},
    }
    
    w = weights[persona.buyer_archetype]
    overall = (
        w["budget"] * budget_fit +
        w["feng_shui"] * feng_shui_fit +
        w["family"] * family_fit +
        w["lifestyle"] * lifestyle_fit +
        w["investment"] * investment_fit
    )
    
    return FitScore(
        overall=round(overall, 2),
        feng_shui_fit=round(feng_shui_fit, 2),
        family_layout_fit=round(family_fit, 2),
        liquidity_fit=compute_liquidity_fit(persona.liquidity_preference, asset.liquidity_score),
        investment_fit=round(investment_fit, 2),
        warnings=generate_warnings(persona, asset),
        fit_reason=generate_fit_reason(persona, asset, adjustments)
    )
```

---

## Persona-to-Asset Type Matching

| Archetype | Đất | Căn hộ | Nhà phố | Villa | Shophouse |
|---|---|---|---|---|---|
| FIRST_HOME_BUYER | ★★★ | ★★★★★ | ★★ | ★ | ★★★ |
| UPGRADER | ★★ | ★★★★ | ★★★★★ | ★★★ | ★★ |
| INVESTOR | ★★★★ | ★★★★★ | ★★★ | ★ | ★★★★★ |
| SPECULATOR | ★★★★★ | ★★★ | ★★ | ★ | ★★★ |
| RETIREE | ★ | ★★★★ | ★★★ | ★★ | ★ |

---

## Input Form: Persona Profiling

Để thu thập persona, form intake nên hỏi:

**Bắt buộc:**
1. Mục đích mua? (ở/đầu tư/cho thuê)
2. Ngân sách dự kiến?
3. Thời gian dự định nắm giữ?
4. Có tuổi cụ thể cần xem phong thủy không?

**Tùy chọn (ảnh hưởng fit):**
5. Gia đình có mấy người? (vị trí phòng ngủ, tầng)
6. Có người già hoặc trẻ nhỏ?
7. Mức độ nhạy cảm với tiếng ồn?
8. Có cần view đẹp không?
9. Ưu tiên thanh khoản hay tăng giá?
