# SPEC_DATA_REQUIREMENTS — Chiến lược Thu Thập & Quản Lý Dữ Liệu

> **Phiên bản:** 1.0 | **Trạng thái:** KHÓA | **Ngày:** 2026-04-28
> **Thay thế cho:** SPEC.md Section DATA (đang thiếu chi tiết)
> **Baseline:** Paper pilot v7 — MAPE=20-37% trên simulated data

---

## 1. Mục tiêu Định Lượng

| Thành phần | Mục tiêu | Hiện tại | Gap |
|---|---|---|---|
| Supply listings (người bán) | **≥ 3,000** | ~197 seed | **–2,803** |
| Buyer requirements (người mua) | **≥ 600** (20% của supply) | 150 | **–450** |
| Expert ratings (ground truth) | **150** (3 experts × 50 props) | 0 | **–150** |
| E1-E2 coverage | **≥ 15%** của total supply | ~0% | **urgent** |
| Nguồn độc lập | **≥ 4** nguồn supply | 1 (seed) | **–3** |

**Nguyên tắc tỷ lệ:**
- Buyer/Supply ratio ≥ 20% là bắt buộc — đảm bảo demand signal đủ mạnh để cạnh tranh với hedonic baseline
- Nếu supply < 3,000 → buyer ratio phải tăng tương ứng (25% cho 2,000, 30% cho 1,500)
- E1-E2 ≥ 15% của total — vì MAPE sensitive, cần đủ anchor evidence

---

## 2. Evidence Tier Specification (E1-E5)

Mỗi bản ghi **PHẢI** được gán tier khi thu thập, không phải sau. Pipeline gán tier tự động theo logic dưới:

```
assign_evidence_tier(property):
  # E1: Field-verified với GPS + ảnh + traceable collector
  if verification_status == "verified"
     AND collection_method ∈ {field_survey, smartphone_sensor_capture}
     AND evidence_photo_path NOT NULL
     AND verified_by IS NOT NULL:
    → E1

  # E2: Verified với strong source + ≥1 independent check
  elif verification_status == "verified"
     AND source_name IS NOT NULL
     AND source_url IS NOT NULL
     AND (verified_by IS NOT NULL OR source_screenshot_path IS NOT NULL):
    → E2

  # E3: Public listing có partial validation + IoT signal hoặc field context
  elif verification_status ∈ {verified, pending}
     AND source_name IS NOT NULL AND source_url IS NOT NULL
     AND (noise_level IS NOT NULL OR field_note IS NOT NULL OR image_url IS NOT NULL):
    → E3

  # E4: Public listing traceable nhưng weak market anchoring
  elif source_name IS NOT NULL AND source_url IS NOT NULL:
    → E4

  # E5: Không đạt E1-E4
  else:
    → E5
```

**Evidence weights cho MAPE:**
| Tier | Weight | Cap | MAPE contribution |
|---|---|---|---|
| E1 | 1.00 | 10.0 | Low — anchor quality |
| E2 | 0.85 | 9.0 | Low-Med |
| E3 | 0.65 | 8.0 | Medium |
| E4 | 0.45 | 6.5 | Medium-High |
| E5 | 0.20 | 4.0 | High risk — noise |

---

## 3. Nguồn Dữ Liệu Bắt Buộc

### Supply Side (Nguồn listings — người bán)

| Nguồn | Domain | Priority | Rate Limit | Fields | Target |
|---|---|---|---|---|---|
| alonhadat.com.vn | alonhadat.com.vn | **HIGH** | 2s/page | full listing | 1,000 |
| batdongsan.com.vn | batdongsan.com.vn | **HIGH** | 3s/page | full listing | 1,000 |
| nhatot.com | nhatot.com | MEDIUM | 2s/page | full listing | 500 |
| cafeland.vn | cafeland.vn | MEDIUM | 3s/page | partial | 300 |
| muabannhadat.vn | muabannhadat.vn | LOW | 2s/page | partial | 200 |

**Lý do multi-source:**
- Single source → overasking bias (Genesove & Mayer 2001)
- Cross-check giá giữa 2-3 nguồn → reduce noise
- Mỗi nguồn có metadata riêng (TOM, views) dùng cho weight

### Demand Side (Nguồn buyer requirements — người mua)

| Nguồn | Phương thức | Fields | Target |
|---|---|---|---|
| batdongsan.com.vn/can-mua | Playwright scrape | full budget/area | 250 |
| alonhadat.com.vn/can-mua | Playwright scrape | full budget/area | 150 |
| nhatot.com/tim-mua | Playwright scrape | partial | 100 |
| Khảo sát web form | POST /api/research/buyer-requirement | full | 100+ |
| Nhóm Facebook (BĐS HN) | Manual annotation | partial | 50+ |

**Tổng buyer target: 600+ (20% của 3,000)**

---

## 4. Provenance Chain Contract

Mỗi bản ghi PHẢI có provenance chain với hash verification:

```
Step 1: COLLECTED
  actor: "system:scraper_v1" | "user:collector_001"
  timestamp: ISO8601
  input_hash: SHA256(raw_html)
  source: domain (e.g., "alonhadat.com.vn")
  verify_url: "https://..."
  metadata: {ip_address, user_agent, crawl_at}

Step 2: PARSED
  actor: "system:parser_v2"
  timestamp: ISO8601
  input_hash: SHA256(raw_html)
  output_hash: SHA256(structured_json)
  fields_extracted: [price, area, district, bedrooms, ...]

Step 3: VALIDATED
  actor: "system:validator_v1"
  timestamp: ISO8601
  checks: [price_outlier, missing_required_fields, geo_consistency]
  validation_passed: bool

Step 4: ENRICHED
  actor: "system:enricher_v1"
  timestamp: ISO8601
  additions: [geocoded_coordinates, area_band, cluster_key]

Step 5: TIER_ASSIGNED
  actor: "system:tier_classifier_v1"
  timestamp: ISO8601
  tier: "E3"
  reason: "Public listing with source URL + IoT signal"

Step 6: VERIFIED (optional, for E1-E2)
  actor: "user:reviewer_001"
  timestamp: ISO8601
  method: "onsite | document | photo"
  verified_by: "Nguyen Van A"
```

---

## 5. Data Quality Requirements

### Completeness threshold (per listing):
```
BẮT BUỘC: province_city, district, area_m2, price, source_name, source_url
KHUYẾN KHÍCH: bedrooms, bathrooms, legal_status, listing_date, latitude
TÙY CHỌN: floor_count, furnishing, description, views_count
```

### Freshness:
- Listings > 180 ngày tuổi → tự động downgrade tier (E1→E2, E2→E3, etc.)
- Listings > 365 ngày → E5 by default
- TOM (time on market) < 30 ngày → bonus weight trong comparable selection

### Cross-validation rules:
```
1. price_consistency: listing A price ∈ [listing B price × 0.7, listing B price × 1.3]
   in same cluster → flag as potentially stable
2. area_consistency: outlier area (< Q1-1.5×IQR or > Q3+1.5×IQR) → flag for review
3. district_consistency: lat/lng không khớp với district name → flag for geo-check
4. duplicate_detection: URL + price + area gần trùng → deduplicate
```

---

## 6. Collection Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│  MULTI-SOURCE COLLECTOR (4 sources concurrently)     │
│  alonhadat │ batdongsan │ nhatot │ cafeland         │
│  Rate-limited │ Retry │ Proxy rotation              │
│  Raw HTML storage → hash verification               │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  DEDUPLICATION ENGINE                                 │
│  URL dedup + price/area fuzzy dedup (SHA256 key)       │
│  Cross-source dedup (match by address approximation)  │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  TIER CLASSIFIER (E1-E5 auto-assign)                  │
│  Rules: verification_status, collection_method,       │
│  source_strength, IoT signal, field evidence        │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  QUALITY VALIDATOR                                    │
│  cross-check prices between sources                  │
│  outlier detection (IQR method)                      │
│  freshness check (age > 180d → downgrade)            │
│  completeness check (required fields)                 │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  ENRICHER                                            │
│  geocoding lat/lng from address                      │
│  area_band computation                              │
│  cluster_key = district::area_band::bedrooms          │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  BUYER REQUIREMENT COLLECTOR (separate pipeline)      │
│  4 sources: batdongsan, alonhadat, nhatot, survey     │
│  Target: 600+ records (20% of supply target)         │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  EXPERT RATING PIPELINE                              │
│  3 experts × 50 properties → 150 ratings             │
│  median-of-medians aggregation                       │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────┐
│  PIPELINE ORCHESTRATOR (full_pipeline.py)            │
│  M0 hedonic vs M4 SDEV vs expert ground truth        │
│  MAPE reporting per tier, per district, per model    │
└──────────────────────────────────────────────────────┘
```

---

## 7. Agent Scripts (chạy bằng lệnh)

| Script | Mục đích | Chạy |
|---|---|---|
| `scripts/pilot/multi_source_collector.py` | Thu thập listings từ 4 nguồn | `python scripts/pilot/multi_source_collector.py --run --target 3000` |
| `scripts/pilot/collect_buyer_requirements.py` | Thu thập buyer requirements từ 4 nguồn | `python scripts/pilot/collect_buyer_requirements.py --scrape --target 600` |
| `scripts/pilot/seed_expert_properties.py` | Seed properties cho expert evaluation | `python scripts/pilot/seed_expert_properties.py` |
| `scripts/pilot/generate_expert_form.py` | Generate expert HTML form | `python scripts/pilot/generate_expert_form.py` |
| `scripts/pilot/collect_expert_ratings.py` | Pipeline expert ratings | `python scripts/pilot/collect_expert_ratings.py --status` |
| `scripts/pilot/data_quality_validator.py` | Validate quality + cross-check | `python scripts/pilot/data_quality_validator.py --full-report` |
| `scripts/pilot/data_pipeline_orchestrator.py` | Orchestrate full pipeline | `python scripts/pilot/data_pipeline_orchestrator.py --full` |

---

## 8. SDEV Data Requirements

SDEV cần đủ demand signal để thắng hedonic MAPE=20%. Threshold:

```
SDEV effective demand signal ≥ 50 buyer requirements per cluster
cluster = district × area_band × bedrooms (±1 BR tolerance)

Minimum viable:
  district × NBR combinations = 3 districts × 4 area_bands × 4 BR types = 48 clusters
  50 buyers/cluster × 48 clusters = 2,400 buyer requirements

Target: 600 buyer requirements → ~12-15 per cluster → marginal quality

RECOMMENDED: 1,000+ buyer requirements → 20-25 per cluster → sufficient
```

---

## 9. Stop Criteria (khi nào được phép báo cáo)

Nghiên cứu được phép công bố khi TẤT CẢ:

```
□ Supply listings ≥ 3,000 records trong DB
□ Buyer requirements ≥ 600 records (20% ratio)
□ E1-E2 ≥ 15% của total supply (≥ 450 high-quality)
□ ≥ 3 nguồn supply độc lập
□ Expert ratings: 150 ratings (3 experts × 50 properties)
□ MAPE measured on real expert data (not simulated)
□ SDEV MAPE re-computed với real expert baseline
□ Provenance chain đầy đủ cho ≥ 80% records
□ No cherry-pick: all results reported (failures included)
```

---

## 10. Current State (2026-04-28)

| Metric | Current | Target | Status |
|---|---|---|---|
| Supply listings | ~197 seed | 3,000 | ❌ CRITICAL |
| Buyer requirements | 150 | 600 | ❌ GAP |
| Expert ratings | 0 | 150 | ❌ CRITICAL |
| E1-E2 coverage | ~0% | ≥15% | ❌ CRITICAL |
| Sources | 1 (seed only) | ≥4 | ❌ CRITICAL |
| Provenance chain | Partial | Full | ⚠ PARTIAL |

**Priority actions:**
1. [P0] Chạy `multi_source_collector.py` để thu thập 3,000 listings
2. [P0] Chạy `collect_buyer_requirements.py --scrape` để thu thập 450+ buyer requirements thực
3. [P0] Expert form điền 150 ratings
4. [P1] Quality validator chạy cross-check
5. [P2] Full pipeline recomputed với real data

---

*Sign-off: [ ] Architecture Lead | [ ] Data Engineer | [ ] Research Lead*