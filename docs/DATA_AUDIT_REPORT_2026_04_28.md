# DATA AUDIT REPORT — 2026-04-28 (Updated 14:00)

## Tình trạng Database

### Supply Listings: 1,404 records (target: 3,000) ⚠️

| Thuộc tính | Giá trị | Đánh giá |
|---|---|---|
| Nguồn | alonhadat.com.vn (1,091) + nhatot.com (224) + batdongsan.com.vn (89) | ✅ Đã xác minh |
| Source URL | 100% có URL có thể truy xuất | ✅ Real URLs verified 200 OK |
| Price diversity | 83% giá/m² unique | ✅ Không batch-generated |
| Duplicate combos | 0 price+area >3x | ✅ No batching pattern |
| E-tier | E2=1,393 (99.2%), E3=9, E5=2 | ✅ Chấp nhận được |
| Provenance chain | 6-step chain đầy đủ | ✅ Có SHA256 hash |
| Freshness | 100% scraped trong 30 ngày | ✅ Recent |

**Agent Probe (2026-04-28):**
- nhatot.com: ✅ WORKING — patterns `/nha-dat-ban/ha-noi/[district]` → 8 listing links/page
- nhadat.cafeland.vn: ✅ WORKING — pattern `/nha-dat-ban/` → 5 listing links/page
- batdongsan.com.vn: ❌ JS-SPA — 202 script tags, 626KB body, 0 property anchors
- alonhadat.com.vn: ❌ Anti-bot — 2-17 links only
- dinhgianhadat.vn: ❌ Error pages
- nhadatviet.vn: ❌ DNS not resolving
- realestate.com.vn: ❌ Connection timeout

**Kết luận SUPPLY: ✅ REAL, 1,404 records thực từ 3 nguồn. Agent probe xác nhận: nhatot + nhadat.cafeland.vn có thể scrape thêm. Collector đang chạy.**

### Buyer Requirements: 17 records (target: 600) ⚠️ ⚠️

| Nguồn | N | Ghi chú |
|---|---|---|
| tin_can_mua (web scraped) | 17 | ✅ REAL — thu thập từ alonhadat buyer section |
| survey (seeded math) | 504 | ❌ GENERATED — đã deactive |
| system-generated | 96 | ❌ GENERATED — đã deactive |

**Kết luận BUYER: ⚠️ 17 real records. 600 seeded ĐÃ deactive + labeled. Cần form thực.**

### Expert Ratings: 150 ratings / 50 properties ✅ COMPLETED

| Trạng thái | Giá trị |
|---|---|
| Expert properties | 50 ✅ |
| Expert ratings | 150 (3 experts × 50 props) ✅ |
| Properties completed | 50/50 ✅ |
| Aggregated sanity check | 10/10 ✅ |
| CSV file | data/pilot/expert_evaluation_completed.csv ✅ |
| Form HTML | paper/expert_evaluation_form.html (159 KB) ✅ |

**Expert prices 2026 Hà Nội (aggregated medians of 3 experts):**
| Quận | Avg VND/m² | Range |
|---|---|---|
| Cầu Giấy | ~80M | 63-90M/m² |
| Thanh Xuân | ~67M | 56-78M/m² |
| Đống Đa | ~76M | 66-85M/m² |

---

## Active Background Jobs

```
Collector (bg0tvzoxn): multi_source_collector.py --run --target 100 (test)
  - nhatot.com: /nha-dat-ban/ha-noi/[district] ✅ WORKING
  - nhadat.cafeland.vn: /nha-dat-ban/ ✅ WORKING
  - batdongsan.com.vn: SKIPPED (JS-SPA)
  - alonhadat.com.vn: SKIPPED (anti-bot)
```

---

## Data Quality Issues

### Supply listings

1. **batdongsan.com.vn — 89 records**: JS-SPA. URLs đã lưu trong DB là real.
2. **Missing temporal signal**: Không có listing_date thực.
3. **E-tier distribution**: E2=99.2% → chưa có E1 field survey.

### Buyer requirements

1. **17 real records** — cần form thực + /buyer-survey
2. **/buyer-survey**: http://localhost:3001/buyer-survey ✅
3. **Backend API**: http://localhost:8080 ✅ WORKING

---

## Recommended Actions

### ✅ Expert ratings — HOÀN THÀNH
```
150 ratings imported, 50/50 properties completed
CSV: data/pilot/expert_evaluation_completed.csv
```

### P1: Supply collection
```
# Test collector đang chạy, kiểm tra output
# Sau khi test xong:
python scripts/pilot/multi_source_collector.py --run --target 1596
```

### P2: Buyer collection
```
# Form buyer thực
http://localhost:3001/buyer-survey

# API POST (test thủ công)
curl -X POST http://localhost:8080/api/research/buyer-requirement \
  -H "Content-Type: application/json" \
  -d '{"property_type":"apartment","province_city":"Hà Nội","district":"Quận Cầu Giấy","min_budget":3000000000,"max_budget":6000000000,"bedrooms":2,"legal_requirement":"any","urgency":"normal"}'
```

---

## Verification commands

```bash
# Check DB
python scripts/pilot/audit_db.py

# Pipeline status
python scripts/pilot/data_pipeline_orchestrator.py --status

# Expert ratings
python scripts/pilot/collect_expert_ratings.py --status

# Supply collector
python scripts/pilot/multi_source_collector.py --status

# Quality validator
python scripts/pilot/data_quality_validator.py --full-report

# Expert form
start paper/expert_evaluation_form.html
```
