# Taxonomy 03: Evidence Taxonomy

> **Phiên bản:** 1.0 | **Trạng thái:** KHÓA | **Ngày:** 2026-04-22

---

## Evidence Tier System (E1-E5)

**Nguồn gốc:** Mở rộng từ `quality_assessment.py` — `classify_evidence_tier()` và `score_property_quality()` (Round 17)

| Tier | Tên tiếng Việt | Anchor Strength | Evidence Weight | Cap |
|---|---|---|---|---|
| E1 | Rất cao | 1.00 | 1.00 | 10.0 |
| E2 | Cao | 0.85 | 0.85 | 9.0 |
| E3 | Trung bình | 0.65 | 0.65 | 8.0 |
| E4 | Thấp | 0.35 | 0.45 | 6.5 |
| E5 | Rất thấp | 0.15 | 0.20 | 4.0 |

---

## E1: Verified Field-Based Evidence

**Định nghĩa:** Bản ghi đã xác minh thực địa với traceable collector và bằng chứng hỗ trợ.

**Criteria đạt E1:**
1. `verification_status == "verified"` AND
2. `collection_method` ∈ {`field_survey`, `google_form_verified`, `smartphone_sensor_capture`} AND
3. Có ảnh minh chứng (ảnh thực địa, ảnh nhà) AND
4. Có người xác minh (`verified_by`)

**Evidence gốc:**
- Ảnh chụp thực địa GPS-tagged
- Báo cáo khảo sát có chữ ký
- Xác minh từ cơ quan có thẩm quyền
- Giao dịch đã công chứng

**RQS components:**
- Provenance: 10/10
- Verification: 9.8/10
- Market Anchor: 9.5/10
- Completeness: 8.5/10
- Timeliness: 10/10 (nếu <30 ngày)

---

## E2: Verified with Strong Source Traceability

**Định nghĩa:** Bản ghi xác minh với traceability nguồn mạnh và ít nhất 1 independent check.

**Criteria đạt E2:**
1. `verification_status == "verified"` AND
2. Có source_name VÀ source_url (hoặc source_screenshot_path) AND
3. (Có ảnh minh chứng HOẶC có verified_by HOẶC verified_at)

**Evidence gốc:**
- Listing đã xác minh từ nguồn uy tín (alonhadat, batdongsan.com.vn)
- Giao dịch trong sổ đỏ (có thể cross-check)
- Báo cáo thẩm định ngân hàng

**RQS components:**
- Provenance: 8.5/10
- Verification: 8.0/10
- Market Anchor: 8.2/10
- Completeness: 7.5/10
- Timeliness: 8.0/10

---

## E3: Supported Public Record

**Định nghĩa:** Public listing với partial validation và usable field context.

**Criteria đạt E3:**
1. `verification_status` ∈ {`verified`, `pending`} AND
2. Có source_name VÀ source_url AND
3. (Có IoT signal HOẶC có ảnh minh chứng HOẶC có field_capture)

**Evidence gốc:**
- Listing từ nguồn công khai (website BDS)
- Dữ liệu từ smartphone sensor capture
- Ghi chú thực địa không đầy đủ

**RQS components:**
- Provenance: 6.5/10
- Verification: 5.5/10
- Market Anchor: 6.6/10
- Completeness: 6.0/10
- Timeliness: 7.0/10

---

## E4: Public Listing Signal

**Định nghĩa:** Public listing với traceability nhưng weak market anchoring.

**Criteria đạt E4:**
1. Có source_name AND source_url (traceable)
2. KHÔNG đạt E1, E2, E3

**Evidence gốc:**
- Listing online không có ảnh
- Listing có giá bất thường (cao/thấp bất thường)
- Listing từ nguồn không quen biết

**RQS components:**
- Provenance: 5.0/10
- Verification: 3.0/10
- Market Anchor: 4.4/10
- Completeness: 4.0/10
- Timeliness: 5.0/10

---

## E5: Low-Evidence Record

**Định nghĩa:** Bản ghi không có traceability hoặc validation mạnh.

**Criteria đạt E5:**
- KHÔNG đạt bất kỳ criteria nào ở E1-E4
- HOẶC: batch_generator source (tự động tạo)

**Evidence gốc:**
- Demo data (system_demo)
- Batch import không có nguồn gốc
- Giá ước tính không có bằng chứng

**RQS components:**
- Provenance: 3.0/10
- Verification: 2.0/10
- Market Anchor: 2.2/10
- Completeness: 3.0/10
- Timeliness: 4.0/10

---

## Evidence Source Types

| Source Type | Mô tả | Default Tier |
|---|---|---|
| `FIELD_SURVEY` | Khảo sát thực địa có chứng minh | E1 |
| `BANK_APPRAISAL` | Thẩm định ngân hàng | E1-E2 |
| `GOVERNMENT_RECORD` | Hồ sơ pháp lý nhà nước | E1 |
| `PUBLIC_LISTING` | Listing công khai online | E3-E4 |
| `IOT_SENSOR` | Dữ liệu cảm biến smartphone | E3 |
| `BATCH_IMPORT` | Import hàng loạt | E4-E5 |
| `DEMO_DATA` | Data demo hệ thống | E5 |
| `USER_SUBMISSION` | User tự nhập | E4 |
| `BROKER_ESTIMATE` | Ước tính môi giới | E3-E4 |

---

## Evidence Asset Schema (Dữ liệu thu thập được)

```json
{
  "evidence_id": "ev_uuid_v4",
  "property_asset_id": "asset_uuid",
  "source_type": "FIELD_SURVEY | PUBLIC_LISTING | ...",
  "url_or_ref": "https://...",
  "images": [
    {"type": "exterior", "path": "...", "gps_tag": {"lat": 21.028, "lng": 105.854}},
    {"type": "interior", "path": "..."},
    {"type": "floor_plan", "path": "..."}
  ],
  "survey_notes": "Ghi chú khảo sát thực địa...",
  "verified_by": "Nguyen Van A",
  "verified_at": "2026-04-20T10:30:00Z",
  "verification_method": "onsite | photo | remote | document",
  "raw_content_hash": "sha256:...",
  "collection_timestamp": "2026-04-20T10:30:00Z",
  "data_freshness_days": 45
}
```

---

## Confidence Band Definition (Từ quality_assessment.py)

| Grade | Score Range | Interval Ratio | Policy |
|---|---|---|---|
| A | ≥ 8.5 | 3-6% | Cho phép dự báo tự động mức cao |
| B | 7.0-8.4 | 5-8% | Cho phép dự báo tự động, cần đối chỉnh định kỳ |
| C | 5.5-6.9 | 8-12% | Chỉ dùng với cảnh báo, ưu tiên bổ sung bằng chứng |
| D | < 5.5 | 12-18% | Không đủ điều kiện cho định giá tự động |

---

## Effective Sample Size (Neff) Computation

**Công thức từ `quality_assessment.py`:**

```
Neff = Σ (alpha[i] × evidence_weight[i] × (rqs[i] / 10.0))
```

Trong đó:
- `alpha[i]` = similarity × time_weight × quality_weight × evidence_weight
- `evidence_weight[i]` = từ bảng E1-E5
- `rqs[i]` = Record Quality Score của bản ghi thứ i

**Neff bands:**
- Neff ≥ 800: Rất mạnh (score 10/10)
- Neff ≥ 300: Tốt (score 8/10)
- Neff ≥ 100: Đạt tối thiểu (score 6/10)
- Neff ≥ 30: Hạn chế (score 4.5/10)
- Neff ≥ 10: Tham khảo có điều kiện (score 2.8/10)
- Neff < 10: Rất yếu (score 1.2/10)

---

## Provenance Chain Contract

Mỗi evidence record phải có provenance chain hoàn chỉnh:

```
Step 1: COLLECTED
  - actor: "user:field_collector_001" | "system:scraper_001"
  - timestamp: ISO8601
  - input_hash: SHA256(raw_content)
  - source: "alonhadat.com.vn"
  - verify_url: "https://..."

Step 2: PARSED
  - actor: "system:parser_v2"
  - timestamp: ISO8601
  - input_hash: SHA256(raw_html)
  - output_hash: SHA256(StructuredData)

Step 3: VALIDATED
  - actor: "system:validator_v1"
  - timestamp: ISO8601
  - checks: ["price_outlier", "missing_required_fields", "geo_consistency"]

Step 4: ENRICHED
  - actor: "system:enricher_v1"
  - timestamp: ISO8601
  - additions: ["geocoded_coordinates", "iot_signals"]

Step 5: VERIFIED (nếu có)
  - actor: "user:reviewer_name"
  - timestamp: ISO8601
  - method: "onsite | document | photo"
  - verified_by: "reviewer_id"
```
