# Baseline Sources — DEPRECATED (2026-04-16)

## Decision: All baselines removed

Sau khi chuyển sang hệ thống thu thập dữ liệu thực từ thị trường Việt Nam, tất cả baseline models dưới đây đã bị **xóa hoàn toàn** vì:
- Dữ liệu Mỹ/Ấn Độ, không phù hợp benchmark với dữ liệu VN
- Không có tính minh bạch nguồn gốc (source traceability)
- Vi phạm tiêu chuẩn CVX-BDS/IoT 1.1-VN

## Baseline History (Archived)

| Name | License | Status | Lý Do Xóa |
|------|---------|--------|-----------|
| CALIFORNIA-HOUSING-PRICE-PREDICTION | Apache-2.0 | REMOVED | Dữ liệu California, không phù hợp VN |
| House-price-prediction-using-flask | MIT | REMOVED | Dữ liệu Ấn Độ, không phù hợp VN |
| house-price-predictor (mlopsbootcamp) | MIT | REMOVED | Dữ liệu US, không phù hợp VN |

---

## Thay thế: Proprietary VN Data Collection System

Xem: `src/backend/data_collector.py` — Hệ thống thu thập dữ liệu thực từ:
- Alonhadat.com.vn (scraping)
- Các nguồn được phê duyệt trong `src/backend/approved_sources.py`

**Scope:** Chỉ Hà Nội (3 quận) + TP.HCM (3 quận)
