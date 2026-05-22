# Đề cương thuyết trình & bảo vệ

## 1) Thông tin đề tài
- Tên đề tài: **Nghiên cứu và xây dựng hệ thống dự đoán giá bất động sản theo khu vực bằng học máy kết hợp dữ liệu IoT từ điện thoại thông minh**.
- Mục tiêu: xây dựng hệ thống AVM có khả năng dự đoán giá, truy vết nguồn dữ liệu, tích hợp dữ liệu IoT và hỗ trợ ra quyết định.

## 2) Bám rubric (CLO) để trình bày đúng trọng số

### CLO1 (20%)
- Phân tích, mô hình hóa vấn đề (10%).
- Đề xuất giải pháp (10%).

### CLO2 (50%)
- Mức độ hoàn thiện chức năng (15%).
- Tính đúng và chất lượng kỹ thuật (15%).
- Tính mới/ứng dụng thực tế (10%).
- Áp dụng công nghệ/kỹ thuật mới (10%).

### CLO3 (30%)
- Báo cáo trình bày, bố cục, chính tả (10%).
- Trình bày thuyết trình (10%).
- Thái độ làm việc với GVHD, tinh thần học tập (10%).

## 3) Những gì đã làm được (dựa trên mã nguồn và DB hiện tại)

### 3.1 Hệ thống phần mềm
- Backend FastAPI đã có các nhóm API chính:
  - Dự đoán giá: `/api/predict`.
  - Dữ liệu & dashboard: `/api/dataset/stats`, `/api/dashboard/stats`.
  - Quản lý hồ sơ BĐS: `/api/properties`, `/api/properties/{id}/detail`.
  - Thu thập IoT và ảnh: `/api/collect/iot`, `/api/upload/image`, `/api/properties/{id}/images`.
  - Nguồn dữ liệu & audit: `/api/data-sources`, `/api/audit-logs`.
- Frontend React đã có các màn hình nghiệp vụ: `Prediction`, `Dashboard`, `DataCollector`, `RecordExplorer`, `DataSources`, `SelfCollected`, `Baselines`, `About`.

### 3.2 Dữ liệu (thực tế trong DB tại thời điểm 2026-03-17)
- Tổng bản ghi: **3001**.
- Self-collected: **181**.
- Public-collected: **2820**.
- Verified: **2100**.
- Bản ghi có IoT (`noise_level` khác null): **181**.
- Mô hình đã lưu version: **3 phiên bản**.

### 3.3 Kết quả mô hình (thực tế theo `model_versions`)
- `v1` (RandomForest):
  - MAE: 1,012,902,808 VND
  - RMSE: 1,683,211,910 VND
  - R²: 0.8858
- `v20260312_230327` (GradientBoosting):
  - MAE: 993,781,856 VND
  - RMSE: 1,664,645,188 VND
  - R²: 0.8883
- Cải thiện từ v1 -> v20260312_230327:
  - MAE giảm ~**1.89%**
  - RMSE giảm ~**1.10%**
  - R² tăng **0.0025**

## 4) Những gì đang cải tiến (cần nói rõ khi bảo vệ)

### 4.1 Đồng bộ số liệu báo cáo và số liệu hệ thống
- `docs/experiment_results.md` đang dùng số liệu demo, chưa khớp với `model_versions`/`models/metrics.json`.
- Hướng cải tiến: thống nhất nguồn số liệu “official” từ DB + log huấn luyện tự động.

### 4.2 Chuẩn hóa schema và pipeline dữ liệu
- Một số script/field chưa đồng nhất tên trường giữa các phiên bản (ví dụ `is_self_collected` vs `data_origin_type`, `gps_latitude` vs `gps_lat`).
- Hướng cải tiến: khóa schema chuẩn, thêm test tự động để chặn lỗi mapping.

### 4.3 Tỉ lệ dữ liệu tự thu thập theo yêu cầu môn học
- Hiện tại:
  - Theo toàn bộ dữ liệu: 181/3001 = **6.03%**.
  - Theo tập verified dùng train: 181/2100 = **8.57%**.
- Nếu yêu cầu cứng là 3-5% thì cần điều chỉnh sampling/quy tắc train để đúng khung.

### 4.4 Mức cải thiện mô hình còn khiêm tốn
- Chênh lệch giữa các version hiện mới ~1-2% MAE/RMSE.
- Hướng cải tiến: tuning có kiểm chứng, thử ablation IoT feature, rolling-validation theo thời gian.

## 5) Bảng so sánh với tài liệu khoa học (ISBN / Scopus / ISI)

> Dùng bảng này để trả lời khi hội đồng hỏi: “mô hình của nhóm đang đứng ở đâu so với nghiên cứu”.

| Nhóm tài liệu | Nguồn | Chuẩn học thuật | Ý nghĩa so sánh với đề tài |
|---|---|---|---|
| Sách nền tảng ML | *Statistical Learning from a Regression Perspective* (Springer, DOI: 10.1007/978-3-030-40189-4) | Có ISBN (Springer nêu rõ Hardcover/Softcover/eBook ISBN) | Cơ sở lý thuyết cho supervised learning, evaluation, bias-variance |
| Sách chuyên đề AVM | *Advances in Automated Valuation Modeling* (Springer, DOI: 10.1007/978-3-319-49746-4) | Có ISBN (Springer nêu rõ) | Khung lý thuyết AVM, mass appraisal, định hướng benchmark |
| Real estate + ML | Choy & Ho (2023), *Land*, DOI: 10.3390/land12040740 | Land được index Scopus + Web of Science | Tham chiếu trực tiếp bài toán dự báo giá BĐS bằng ML |
| Real estate + ML COVID context | Mora-Garcia et al. (2022), *Land*, DOI: 10.3390/land11112100 | Land được index Scopus + Web of Science | So sánh cách xử lý feature engineering và đánh giá sai số |
| IoT/smartphone noise | Zuo et al. (2016), *Sensors*, DOI: 10.3390/s16101692 | Sensors index Scopus + Web of Science | Cơ sở khoa học cho biến noise_level thu từ smartphone |
| IoT/mobile crowdsensing | Kraft et al. (2022), *Sensors*, DOI: 10.3390/s22010170 | Sensors index Scopus + Web of Science | Cơ sở về độ tin cậy đo đạc âm thanh qua mobile crowdsensing |
| AVM + Explainable AI | Tchuente (2024), *Journal of Real Estate Finance and Economics*, DOI: 10.1007/s11146-024-09998-9 | Bài báo quốc tế, có metadata theo hệ chỉ mục học thuật | Đối chiếu hướng dùng SHAP/XAI của nhóm |
| AVM + Uncertainty | Pollestad et al. (2024), *Journal of Real Estate Finance and Economics*, DOI: 10.1007/s11146-024-10002-7 | Bài báo quốc tế, có metadata theo hệ chỉ mục học thuật | Đối chiếu hướng mở rộng: dự báo kèm bất định |
| AVM metrics | Steurer et al. (2021), *Journal of Property Research*, DOI: 10.1080/09599916.2020.1858937 | Bài báo chuyên AVM metrics (nguồn xuất bản chính thức) | Gợi ý bộ metrics đánh giá công bằng mô hình |
| AVM + image fusion | Deng (2025), *PLOS ONE*, DOI: 10.1371/journal.pone.0321951 | PLOS ONE index Scopus + Web of Science | Đối chiếu hướng tăng chất lượng bằng dữ liệu ảnh đa nguồn |

## 6) Kịch bản slide thuyết trình (15–18 phút)

### Slide 1: Mở đầu (1 phút)
- Bài toán: định giá BĐS thủ công còn chủ quan, khó cập nhật theo khu vực.
- Mục tiêu đề tài: AVM + IoT smartphone + truy vết dữ liệu.

### Slide 2: Lý do chọn đề tài (1 phút)
- Nhu cầu định giá nhanh, minh bạch.
- Dữ liệu công khai tăng nhanh nhưng chất lượng không đồng đều.

### Slide 3: Tổng quan nghiên cứu liên quan (1.5 phút)
- Trình bày 4-5 tài liệu tiêu biểu (Land, JREFE, PLOS, Sensors).
- Chốt khoảng trống: ít nghiên cứu kết hợp dữ liệu cấu trúc + IoT thực địa cho bối cảnh Việt Nam.

### Slide 4: Phạm vi và đóng góp đề tài (1 phút)
- Đóng góp 1: Kiến trúc hệ thống end-to-end (collect -> verify -> train -> predict).
- Đóng góp 2: Tích hợp IoT (noise, GPS, môi trường).
- Đóng góp 3: Truy vết nguồn dữ liệu, audit log.

### Slide 5: Kiến trúc hệ thống (1 phút)
- Frontend React, Backend FastAPI, SQLite, ML pipeline.
- Luồng dữ liệu từ thu thập đến dự đoán.

### Slide 6: Dữ liệu hiện có (1 phút)
- 3001 bản ghi, 2100 verified, 181 self-collected, 181 có IoT.
- Bản đồ phân bố theo loại tài sản/khu vực.

### Slide 7: Tiền xử lý và feature engineering (1 phút)
- Nhóm đặc trưng: vị trí, pháp lý, tiện ích, IoT.
- Mã hóa biến phân loại, chuẩn hóa, xử lý thiếu.

### Slide 8: Mô hình và chiến lược huấn luyện (1.5 phút)
- So sánh RandomForest, GradientBoosting, XGBoost.
- Tiêu chí chọn best model: MAE chính, RMSE/R² phụ.

### Slide 9: Kết quả thực nghiệm (1 phút)
- Bảng v1 vs v20260312_230327.
- Chốt: model tốt nhất hiện tại là GradientBoosting.

### Slide 10: So sánh với tài liệu khoa học (1.5 phút)
- So cách tiếp cận với Land/JREFE/PLOS.
- Nêu điểm tương đồng (ensemble, explainability, uncertainty).
- Nêu điểm khác biệt của nhóm (IoT smartphone tại nguồn).

### Slide 11: Mức độ hoàn thiện chức năng (1 phút)
- Demo nhanh: Prediction + Dashboard + DataCollector + RecordExplorer.
- Liên hệ trực tiếp CLO2.

### Slide 12: Hạn chế hiện tại (1 phút)
- Chưa đồng bộ hoàn toàn số liệu báo cáo.
- Schema pipeline cần chuẩn hóa thêm.
- Tỉ lệ self-collected cần đưa về khung yêu cầu.

### Slide 13: Kế hoạch cải tiến (1 phút)
- Giai đoạn 1: chuẩn hóa dữ liệu và metric reporting.
- Giai đoạn 2: uncertainty calibration + ablation IoT.
- Giai đoạn 3: kiểm định ngoài mẫu và báo cáo học thuật.

### Slide 14: Kết luận và hướng phát triển (0.5 phút)
- Hệ thống đã có nền tảng kỹ thuật đầy đủ.
- Hướng nâng cấp rõ ràng để đạt mức “Tốt” theo rubric.

## 7) Kịch bản trả lời phản biện (Q&A mẫu)

### Câu 1: Vì sao chọn GradientBoosting làm model chính?
- Trả lời: theo dữ liệu hiện tại, GradientBoosting cho MAE và RMSE thấp hơn RandomForest, R² cao hơn; đã kiểm tra trên cùng tập dữ liệu verified.

### Câu 2: IoT đóng góp thực sự hay chỉ để minh họa?
- Trả lời: hiện đã lưu và sử dụng các biến IoT trong pipeline; bước tiếp theo là làm ablation study (có/không có IoT) để định lượng mức đóng góp rõ hơn.

### Câu 3: Tại sao số liệu trong báo cáo và trong DB chưa giống nhau?
- Trả lời: đây là phần nhóm đã nhận diện và đang chuẩn hóa; số liệu bảo vệ sẽ lấy theo nguồn chuẩn duy nhất từ model version trong DB.

### Câu 4: Dữ liệu tự thu thập có đảm bảo đúng yêu cầu 3-5% không?
- Trả lời: hiện tại đang cao hơn khung, nhóm đang hiệu chỉnh lại quy tắc sampling/train để đưa về đúng dải yêu cầu.

### Câu 5: Làm sao chứng minh tài liệu tham khảo đạt chuẩn khoa học?
- Trả lời: nhóm sử dụng nguồn DOI chính thức từ Springer/MDPI/PLOS/Taylor & Francis, đồng thời kiểm tra trạng thái index Scopus/Web of Science từ trang journal chính thức và ISSN Portal.

### Câu 6: Mô hình có giải thích được cho người không chuyên không?
- Trả lời: có hướng XAI (SHAP), hiện đã tích hợp nền tảng giải thích feature importance và đang hoàn thiện mức giải thích theo từng dự đoán.

### Câu 7: Rủi ro lớn nhất của đề tài là gì?
- Trả lời: rủi ro chất lượng dữ liệu thực địa không đồng nhất; giải pháp là quy trình verify + audit + chuẩn hóa schema.

## 8) Kế hoạch cải tiến đề cương (4 tuần)

### Tuần 1
- Khóa schema chuẩn, sửa các mapping field cũ/mới.
- Đồng bộ báo cáo metric theo một nguồn dữ liệu chuẩn.

### Tuần 2
- Chạy lại train/eval với cấu hình cố định, lưu artifact có version.
- Thực hiện ablation IoT và báo cáo chênh lệch MAE/RMSE/R².

### Tuần 3
- Bổ sung uncertainty estimate + calibration.
- Cập nhật dashboard hiển thị confidence interval rõ ràng.

### Tuần 4
- Hoàn thiện báo cáo cuối: so sánh với paper Scopus/ISI, kiểm thử chức năng và kiểm thử dữ liệu.

## 9) Checklist trước ngày bảo vệ
- Số liệu slide khớp 100% với DB/model version.
- Demo chạy được 4 màn hình chính.
- Có backup ảnh/chụp màn hình nếu mạng yếu.
- Thuộc 7 câu phản biện quan trọng ở mục 7.
- Có bảng tài liệu tham khảo DOI + ISBN + trạng thái index.

## 10) Nguồn tham khảo chính (kèm link)

1. Springer (Book): *Advances in Automated Valuation Modeling* (ISBN + DOI).  
   https://link.springer.com/book/10.1007/978-3-319-49746-4
2. Springer (Book): *Statistical Learning from a Regression Perspective* (ISBN + DOI).  
   https://link.springer.com/book/10.1007/978-3-030-40189-4
3. Land (2023): Choy & Ho, DOI: 10.3390/land12040740.  
   https://www.mdpi.com/2073-445X/12/4/740
4. Land (2022): Mora-Garcia et al., DOI: 10.3390/land11112100.  
   https://doi.org/10.3390/land11112100
5. Sensors (2016): Zuo et al., DOI: 10.3390/s16101692.  
   https://pubmed.ncbi.nlm.nih.gov/27754359/
6. Sensors (2022): Kraft et al., DOI: 10.3390/s22010170.  
   https://pubmed.ncbi.nlm.nih.gov/35009713/
7. Journal of Real Estate Finance and Economics (2024): Tchuente, DOI: 10.1007/s11146-024-09998-9.  
   https://doi.org/10.1007/s11146-024-09998-9
8. Journal of Real Estate Finance and Economics (2024): Pollestad et al., DOI: 10.1007/s11146-024-10002-7.  
   https://link.springer.com/article/10.1007/s11146-024-10002-7
9. Journal of Property Research (2021): Steurer et al., DOI: 10.1080/09599916.2020.1858937.  
   https://doi.org/10.1080/09599916.2020.1858937
10. PLOS ONE (2025): Deng, DOI: 10.1371/journal.pone.0321951.  
    https://pubmed.ncbi.nlm.nih.gov/40388441/
11. ISSN Portal (Sensors 1424-8220): có SCOPUS + WEB OF SCIENCE.  
    https://portal.issn.org/resource/ISSN/1424-8220
12. ISSN Portal (PLOS ONE 1932-6203): có SCOPUS + WEB OF SCIENCE.  
    https://portal.issn.org/resource/ISSN/1932-6203
13. ISSN Portal (Land 2073-445X): có SCOPUS + WEB OF SCIENCE.  
    https://portal.issn.org/resource/ISSN-L/2073-445X
