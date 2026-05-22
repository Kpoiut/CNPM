# BAO CAO TIEN DO 11 TUAN VA KE HOACH HOAN THIEN DE TAI

## 1. Thong tin chung
- Ten de tai: Nghien cuu va xay dung he thong du doan gia bat dong san theo khu vuc bang hoc may ket hop du lieu IoT tu dien thoai thong minh.
- Thoi gian thuc hien theo thong bao: tu 09/03/2026 den 24/05/2026.
- Moc bao cao: 11 tuan, nop bao cao hang tuan tren e-learning.
- Dinh huong bao cao: khong xem gia rao ban tren mang la gia thi truong dung tuyet doi; bo sung phan he rieng de danh gia do tin cay cua du lieu dau vao, tu do moi dua vao train va suy luan.

## 2. Muc tieu cap nhat cua de tai
De tai khong chi huong toi mot mo hinh dua ra mot con so gia co dinh, ma huong toi mot he thong AVM co kha nang:
- tiep nhan du lieu bat dong san, du lieu vi tri va du lieu IoT;
- danh gia du lieu dau vao co du muc tin cay hay khong;
- du doan gia theo khoang thay vi gia diem tuyet doi;
- giai thich vi sao khoang gia rong hay hep;
- doi chieu voi bat dong san tuong dong, thong tin nguon va bang chung lien quan;
- phu hop hon voi boi canh du lieu bat dong san Viet Nam, noi ma gia rao ban online khong the xem la gia thi truong chuan.

Ban cap nhat moi nhat cua de tai dua tren standard noi bo `CVX-BDS/IoT 1.1-VN Research Extension`, trong do nhom khong sao chep nguyen mot standard co san ma tu xay dung bien the rieng cho project, co bo sung Evidence Tier, Record Quality Score, Effective Sample Size va train theo trong so chat luong du lieu.

## 3. Van de nghien cuu cot loi
Van de lon nhat cua bai toan khong nam o viec chon RandomForest hay GradientBoosting, ma nam o cho nhan gia dau vao co the bi lech so voi thi truong thuc te. Gia rao ban tren cac website bat dong san co the bi thoi phong, neo gia, khong phan anh gia giao dich thuc, va cung khong the chi vi nhieu website cho ra muc gia tuong duong ma xem la gia dung.

Tu nhan dinh do, de tai duoc dieu chinh theo 4 nguyen ly:
- Khong co gia bat dong san nao duoc xem la dung 100% voi thi truong.
- Du lieu online chi la market signal, khong phai market truth.
- Phai co phan he rieng danh gia do tin cay cua du lieu dau vao truoc khi dinh gia.
- Ket qua du doan phai la khoang gia co gian theo muc do tin cay, khong phai mot diem gia cung.

## 4. Kien truc he thong cap nhat
He thong duoc to chuc lai thanh 3 phan he chinh:

### 4.1. Phan he 1 - Thu thap va hop nhat du lieu
Nguon du lieu gom:
- Du lieu rao ban cong khai.
- Du lieu tu thu thap va xac minh noi bo.
- Du lieu IoT/hien truong tu dien thoai thong minh.
- Du lieu vi tri, khu vuc, toa do va cac thong tin bo tro.

### 4.2. Phan he 2 - Xac thuc va cham diem do tin cay du lieu
Day la phan moi duoc bo sung de giai quyet van de hoc thuat cot loi. Phan he nay thuc hien:
- kiem tra truy vet nguon;
- kiem tra do day du metadata;
- doi chieu cum du lieu cung khu vuc;
- tinh diem chat luong va diem day du;
- danh gia so luong mau khu vuc;
- phat hien canh bao khi du lieu qua mong hoac bien dong gia qua lon.

### 4.3. Phan he 3 - Du doan gia va giai thich ket qua
Phan he nay nhan dau vao da duoc cham diem, sau do:
- suy luan gia trung tam;
- sinh khoang gia duoi va tren;
- co gian khoang gia theo diem tin cay;
- hien thi comparables, feature importance va thong tin nguon.

## 5. Cac thanh phan va thuat toan dang su dung

### 5.1. Mo hinh du doan gia
- QualityWeightedRandomForest: bien the RandomForest co hoc theo sample weight dua tren RQS va evidence.
- ReliabilityAwareGradientBoosting: bien the GradientBoosting co nhan trong so do tin cay cua ho so train.
- ConfidenceWeightedXGBoost: bien the XGBoost dung objective robust hon va regularization manh hon, khong su dung raw config mac dinh.
- Quantile interval heads: mo hinh bo sung cho can duoi/can tren de tao khoang gia thay vi point estimate don le.

### 5.2. Mo hinh phan lop do tin cay du lieu
- EntropyTree: nhanh classifier theo tinh than ID3/C4.5, uu tien entropy va giai thich duoc.
- GiniTree: nhanh CART de doi chieu voi entropy tree.
- HybridConfidenceForest: RandomForestClassifier duoc can bang lop va dung de nang do on dinh cho nhan A/B/C/D.

### 5.3. Quy trinh train cap nhat theo sach
- xay dung dataset goc gom thong tin BDS, thong tin gia, thong tin nguon va IoT;
- lam sach, chuan hoa, tao dac trung;
- cham diem RQS va sinh pseudo-label A/B/C/D;
- chia Training set - Validation set - Test set theo ti le 70/15/15;
- train nhanh 1: classifier dang cay cho do tin cay du lieu;
- dua dau ra nhanh 1 vao nhanh 2 nhu mot phan cua feature set hoi quy;
- train nhanh 2: mo hinh du doan gia trung tam va 2 dau quantile;
- dung grouped conformal calibration theo trust band de hieu chinh khoang gia cuoi;
- luu metadata, split strategy, tree rules va version mo hinh.

### 5.4. Thuat toan/xu ly ho tro
- feature engineering cho du lieu cau truc va IoT;
- Haversine va dac trung vi tri;
- comparable-based fallback khi mo hinh ML khong san sang;
- SHAP cho giai thich mo hinh;
- rule-based scoring + tong hop thong ke de danh gia do tin cay du lieu;
- Research Lab mode de giai thich toan bo quy trinh train theo dang cay truc quan.

### 5.5. Co che tinh do tin cay moi
Diem tin cay tong duoc thiet ke theo cong thuc:

CS = 0.35 x S_volume + 0.40 x S_quality + 0.25 x S_completeness

Trong do:
- S_volume: diem theo tong so mau trong khu vuc, tham chieu cac moc 100 / 300 / 800 mau.
- S_quality: diem chat luong trung binh cua tap doi chieu sau khi cham diem tung ban ghi.
- S_completeness: diem day du cua ho so dau vao va metadata ho tro.

Phan he moi da duoc them vao backend de tra ve:
- overall_score;
- confidence_grade A/B/C/D;
- standard_name;
- base_score_before_caps;
- rules_applied;
- effective_sample_size;
- anchor_share;
- median_rqs;
- support_statistics;
- strengths;
- warnings;
- next_actions;
- sample_records.

### 5.6. Co che sinh khoang gia moi
Thay vi lay mot MAE co dinh de tao khoang gia, he thong moi ket hop:
- sai so co ban cua mo hinh;
- do bien dong gia trong cum comparables;
- diem tin cay du lieu.

Nguyen ly van hanh:
- diem tin cay cao thi khoang gia hep hon;
- diem tin cay thap thi khoang gia duoc no rong;
- vung it du lieu hoac bien dong manh phai hien thi canh bao, khong duoc tao an tuong chac chan gia.

## 6. Quy trinh rieng de xac thuc nguon du lieu
Quy trinh xac thuc du lieu dau vao duoc de xuat thanh 7 buoc ro rang:

### Buoc 1. Kiem tra truy vet nguon
Moi ban ghi can co it nhat:
- ten nguon;
- duong dan nguon neu co;
- thoi diem thu thap;
- cach thu thap;
- ghi chu xac minh.

Neu khong truy vet duoc, ban ghi bi ha diem tin cay.

### Buoc 2. Chuan hoa nhan dien tai san
Can chuan hoa:
- tinh/thanh, quan/huyen, phuong/xa;
- dien tich;
- loai hinh tai san;
- phap ly;
- toa do;
- thoi diem ghi nhan gia.

### Buoc 3. Tach loai gia
Khong tron tat ca vao mot cot price. Can phan biet:
- gia rao ban;
- gia giao dich/xac minh;
- gia uoc tinh;
- gia doi chieu noi bo.

### Buoc 4. Doi chieu theo khu vuc thuc te
Du lieu online chi duoc dung lam tin hieu. Khi dinh gia, he thong phai doi chieu voi:
- cum comparables verified;
- ban ghi tu thu thap neu co;
- metadata thoi gian va vi tri;
- do phan tan gia/m2 trong cung khu vuc.

### Buoc 5. Cham diem tung ban ghi
Moi ban ghi duoc cham:
- source_name/source_url;
- listing_date;
- ward/street;
- price_per_m2;
- toa do;
- phap ly;
- image/evidence;
- IoT signal;
- origin type;
- verification status.

### Buoc 6. Tong hop thanh diem tin cay cho ca ho so dinh gia
He thong lay tap comparables gan nhat, tinh trung binh diem chat luong, tong hop voi so mau khu vuc va muc do day du cua ho so dau vao.

### Buoc 7. Dua ra khuyen nghi su dung
Sau khi cham diem, he thong khong ket luan dung/sai tuyet doi ma dua ra khuyen nghi:
- A: uu tien dung cho dinh gia va train;
- B: dung duoc, can giam sat;
- C: chi nen dung co trong so thap va doi chieu them;
- D: khong nen dung lam can cu dinh gia tu dong neu chua co bang chung bo sung.

## 7. Tinh nang moi da bo sung trong du an
Duoi day la cac tinh nang moi vua duoc trien khai them trong ma nguon:

### 7.1. Backend cham diem do tin cay du lieu
- Them file `src/backend/quality_assessment.py`.
- Them ham cham diem volume/quality/completeness.
- Them Evidence Tier E1-E5, Record Quality Score (RQS), Effective Sample Size (Neff) va assessment tree.
- Them ham sinh khoang gia co gian theo do tin cay va conformal adjustment theo trust band.

### 7.2. API rieng cho danh gia du lieu dau vao
- Them endpoint `POST /api/data-quality/evaluate`.
- Dau ra gom diem tong, cap do tin cay, so mau khu vuc, canh bao, diem manh, truong thieu, va danh sach mau doi chieu.
- Dau ra moi con co `assessment_tree` de phuc vu giai thich tren UI.

### 7.3. Nang cap API du doan
- Endpoint `POST /api/predict` da duoc bo sung:
  - `data_quality_assessment`;
  - `interval_analysis`;
  - khoang gia co gian theo diem tin cay;
  - source attribution moi co nhac cap do tin cay.
- Luong predict da duoc noi vao classifier tin cay de sinh `ml_confidence`, sau do dua score nay vao feature set cua model du doan gia.

### 7.4. Giao dien rieng danh gia du lieu dau vao
- Them trang moi `frontend/src/pages/DataQuality.jsx`.
- Trang nay cho phep nhap ho so can dinh gia va xem:
  - tong diem tin cay;
  - bieu do 3 thanh phan cham diem;
  - thong ke mau khu vuc;
  - truong con thieu;
  - mau doi chieu da dung de cham diem.

### 7.5. Tich hop ngay trong man hinh du doan
- Trang `Prediction.jsx` da duoc cap nhat de hien thi:
  - diem tin cay tong;
  - muc A/B/C/D;
  - khoang gia co gian;
  - tab rieng `Tin cay` de giai thich vi sao ket qua rong/hep;
  - ket qua nhanh classifier tin cay va band calibration da duoc ap dung.

### 7.6. Research Lab mode co ma truy cap rieng
- Them route frontend `ResearchLab.jsx`.
- Them endpoint `POST /api/research-lab/access` va `GET /api/research-lab/overview`.
- Chi khi nhap dung ma moi xem duoc man hinh tong the quy trinh train.
- UI moi hien thi:
  - cay quy trinh train;
  - metric chat luong du lieu;
  - phan bo nhan A/B/C/D;
  - grouped conformal calibration;
  - tree rules cua classifier;
  - ghi chu giai thich cho nguoi moi.

### 7.7. Explainability Dashboard (bo sung tuan 8)
- Them trang `frontend/src/pages/ExplainabilityDashboard.jsx`.
- Them route `/explainability` trong App.jsx (protected, minRole=user).
- 6 API endpoints trong `src/backend/api_v2/explainability.py`:
  - `GET /api/v2/explain/global` — SHAP feature importance + beeswarm (30 features, 500 samples)
  - `GET /api/v2/explain/prediction/{property_id}` — SHAP waterfall cho 1 property
  - `GET /api/v2/explain/residuals` — Residual analysis voi scatter sample, breakdown theo district/tier
  - `GET /api/v2/explain/calibration` — ICP theo confidence band A/B/C/D
  - `GET /api/v2/explain/model-compare` — MAPE comparison giua cac model variants
- 7 chart components trong `frontend/src/components/explainability/`:
  - FeatureImportanceChart — HorizontalBarChart top 15 features
  - SHAPWaterfallChart — Waterfall bar cho single prediction
  - CalibrationChart — LineChart predicted vs actual ICP
  - ResidualAnalysisChart — ScatterChart actual vs residual
  - ModelComparisonChart — GroupedBarChart MAPE vs R2
  - PredictionDistributionChart — Histogram prediction error %
  - SHAPBeeswarmChart — Beeswarm scatter cho top features
- Dashboard co 4 tabs: Overview, SHAP, Residuals, Calibration.

### 7.8. Transaction Price API (bo sung tuan 8)
- Them endpoint `GET /api/v2/transaction-price/{property_id}` trong `src/backend/api_v2/transaction_price.py`.
- Dung SDEV (Supply-Demand Equilibrium Engine) de xac dinh market-acceptable price:
  - Ask-bid overlap score tu matched_pairs table
  - SDEV midpoint = gia thi truong chap nhan duoc
  - overasking_pct = (listing_price - sdev_mid) / listing_price * 100
  - ML noise correction: correction_factor = max(0, 1 - overasking_pct/100 * (1-overlap_score))
  - Transaction equivalent = sdev_mid * correction_factor + sdev_mid * (1-correction_factor)
- Supply-demand matching: 21,206 matched pairs da duoc tao trong bang `matched_pairs`.
- Luu y cap nhat tuan 10: `matched_pairs` con 21,206 cap trong DB, nhung bang `buyer_requirements` live hien tai = 0; can dong bo lai buyer requirements neu muon trinh bay SDEV nhu tinh nang live hoan chinh.
- Dau ra gom listing_price, transaction_equivalent (low/mid/high), overasking_pct, confidence, ask_bid_overlap_score, buyer_matches, similar_listings.

## 8. Bang so sanh chi tiet: da lam, dang lam, se hoan thanh
| Hang muc | Da lam | Dang lam | Se hoan thanh |
|---|---|---|---|
| Tong quan tai lieu | Da tim va doi chieu 3 cong trinh gan de tai | Da hoan thanh | Hoan thien trich dan va dinh dang phan tong quan |
| Kien truc he thong | Da xac dinh 3 phan he chinh | Da hoan thanh | So do kien truc da dua vao bao cao |
| Du lieu verified | Da co dataset verified trong DB | Da hoan thanh | Tiep tuc bo sung mau tu thu thap va field survey |
| Self-collected + IoT | Da co luong thu thap va truong du lieu | Da hoan thanh | Tiep tuc bo sung bieu mau va huong dan nhap lieu |
| ML price prediction | Da co pipeline train voi 53 features, MAPE=14.2%, R2=0.765 | Da hoan thanh | Tiep tuc toi uu interval va danh gia theo tung khu vuc |
| Xac thuc du lieu dau vao | Da co module cham diem production trong backend | Da hoan thanh | Quy trinh xac thuc chinh thuc da dua vao bao cao |
| Giao dien danh gia du lieu | Da co page DataQuality + Explainability Dashboard | Da hoan thanh | UI da hoan thien voi 7 chart components |
| Explainability ML | Da co ExplainabilityDashboard voi 6 API endpoints SHAP | Da hoan thanh | Bao gom waterfall, beeswarm, residual, calibration, model-compare |
| Transaction Price | Da co endpoint SDEV noise-correction, matched_pairs = 21,206 | Can dong bo lai buyer_requirements live DB | Neu nop tuan 10, ghi ro matched_pairs con nhung buyer_requirements live = 0 |
| Danh gia chinh xac | Snapshot 03/05/2026: MAPE=14.2%, R2=0.765, Median AE=424M VND | Can tach voi metric retrain sau audit | Bang danh gia 2 tang: model snapshot + data validation live |
| Bao cao 11 tuan | Da co khung bao cao, tuan 1-10 da cap nhat | Tuan 11 la ke hoach hoan thien | File bao cao tuan 10 da cap nhat voi so lieu live va ghi chu audit trung thuc |

## 9. Bang doi chieu voi 3 cong trinh tham khao hoc thuat
| Cong trinh | Huong chinh | Diem manh | Gioi han | Diem khac biet cua de tai |
|---|---|---|---|---|
| Choy & Ho, Land 2023, DOI 10.3390/land12040740 | ML tren du lieu cau truc de du doan gia BDS | Toi uu mo hinh tren du lieu sach | Chua nhan manh bai toan xac thuc nguon du lieu online | De tai them phan he xac thuc du lieu truoc khi dua vao train/predict |
| Deppner et al., Journal of Real Estate Finance and Economics, DOI 10.1007/s11146-023-09944-1 | Tree boosting + explainability cho dinh gia | Manh ve accuracy va giai thich | Tap trung vao quality model nhieu hon quality data | De tai nhan manh ca quality model va quality data, nhat la boi canh Viet Nam |
| Zuo et al., Sensors 2016, DOI 10.3390/s16101692 | Smartphone sensing cho du lieu moi truong | Chung minh smartphone co the thu du lieu ngu canh | Khong phai bai toan gia nha truc tiep | De tai dua smartphone IoT vao nhu feature bo tro trong AVM |

## 10. Tinh phu hop voi Viet Nam
De tai phu hop voi Viet Nam vi:
- du lieu bat dong san phan tan tren nhieu website va nhieu nguon;
- gia rao ban online thuong co sai so va chenh lech lon;
- vi tri vi mo anh huong rat manh den gia;
- du lieu giao dich thuc khong de tiep can 100%, nen can co co che cham diem tin cay thay vi khang dinh gia tri tuyet doi.

Diem phu hop nhat cua giai phap la thua nhan bat dinh cua thi truong va dua bat dinh do vao he thong thay vi giau no di.

## 11. Bang chung ky thuat hien co trong project

### 11.1. Bang chung tu archived training snapshot
Day la snapshot da duoc dung de train model nghien cuu hien tai, khong phai live app DB:
- Profile count dung cho train: 3,037
- Avg RQS: 4.28
- Median RQS: 4.0
- Grade distribution:
  - C = 329
  - D = 2708
- Evidence distribution:
  - E2 = 546
  - E3 = 2504
  - E4 = 537
  - E5 = 2500
- So feature dua vao train nhanh 2: 53

### 11.2. Bang chung tu metadata model
Trich tu `models/metadata_20260503_185414.json`:
- Standard: CVX-BDS/IoT 1.1-VN Research Extension
- Nhanh 1 classifier tot nhat: HybridConfidenceForest
- Nhanh 2 regressor tot nhat: ReliabilityAwareGradientBoosting
- CV MAE: 829,530,707 VND
- Test MAE: 804,022,708 VND
- Test MAPE: 14.2%
- Test Median AE: 423,856,514 VND
- Test R2: 0.765
- So feature: 53
- Split strategy: 70/15/15 holdout with validation-driven model selection
- Interval strategy: quality-weighted point models + quantile interval heads + grouped conformal calibration
- Ngay train: 2026-05-03

#### Bang chung confidence classifier (nhanh 1)
- Label source: OOF_cross_validation_error (khong co data leakage)
- Test accuracy: 0.281 (4-class phan biet A/B/C/D)
- Label distribution: A=453, B=453, C=604, D=1527
- Ghi chu: accuracy khong phai 1.0, chung to khong co leakage tu internal labels

#### Bang chung conformal calibration (cuoi cung)
- Band B: count=84, q90=0.190, median=0.082
- Band C: count=345, q90=0.273, median=0.097
- Band D: count=27, q90=0.634, median=0.116

### 11.3. Bang chung tu chay build frontend
Lenh `npm run build` da thanh cong voi tat ca tinh nang moi.
Ghi nhan them:
- frontend build passed;
- da tach lazy-load theo route, Research Lab mode duoc build thanh chunk rieng;
- ExplainabilityDashboard duoc build thanh chunk rieng;
- chunk JS tong khoang 654 kB (gzip 196 kB), co chunk size warning nhung build thanh cong;
- 7 chart components Recharts hoat dong: FeatureImportance, SHAPWaterfall, Calibration, ResidualAnalysis, ModelComparison, PredictionDistribution, SHAPBeeswarm.

### 11.4. Bang chung tu kiem tra luong danh gia moi
Khi kiem tra truc tiep voi mot ho so mau:
- model_used: ReliabilityAwareGradientBoosting
- ket qua data quality grade: C
- ket qua classifier tin cay: B
- overall score rule-based: 5.5/10
- interval ratio cuoi: 0.12
- conformal q90 cua band B: 0.4053, nhung duoc chan theo design band de tranh khoang gia qua rong
- feature set suy luan: 41 feature

Dieu nay phu hop voi logic moi: du lieu chua du manh de dua khoang qua hep, nen he thong tu dong giu khoang gia rong hon.

### 11.5. Bang chung tu dashboard truy vet dataset va UI/UX moi
Sau dot nang cap UI/UX cho cum du lieu, he thong da bo sung:
- Dashboard co them khoi `dataset overview` hien thi ro tong record, external, self-collected, link truy vet va khoang thieu so voi muc tieu.
- Trang `Data Sources` duoc nang cap thanh `Source Atlas`, cho phep chon tung nguon, xem metric trace/verified/IoT va mo record chi tiet.
- Trang `Record Explorer` duoc nang cap thanh trung tam xem record, co bo loc nguon goc, xac minh, IoT, hinh anh va modal chi tiet truy vet.
- Modal chi tiet record hien thi:
  - thong tin gia;
  - vi tri;
  - trace score;
  - nguon va link truy vet;
  - thong tin IoT;
  - timeline xu ly record.

So lieu sau khi doi chieu live app DB hien tai (cap nhat 17/05/2026):
- tong record trong bang `properties`: 3,560;
- active record: 3,269;
- trainable basic record: 3,269;
- public collected active: 3,000;
- self-collected active: 269;
- ty le self-collected tren active dataset: 8.2%;
- verified record_status: 2,686;
- pending_review record_status: 583;
- record active co `source_url`: 3,080;
- provenance chain steps: 9,900;
- matched pairs (supply-demand): 21,206;
- potential matched pairs: 9,189;
- valuation_runs da ghi nhan: 295.

Phan bo active dataset theo 6 khu vuc:
- Ha Noi - Quan Thanh Xuan: 599;
- Ha Noi - Quan Cau Giay: 584;
- TP. Ho Chi Minh - Quan Tan Binh: 539;
- Ha Noi - Quan Dong Da: 521;
- TP. Ho Chi Minh - Quan 7: 513;
- TP. Ho Chi Minh - Quan Binh Thanh: 513.

Phan bo Evidence Tier tren active dataset (kiem tra truc tiep DB 17/05/2026):
- E2 = 514;
- E3 = 1,970;
- E4 = 522;
- E5 = 263.

Ghi chu: bang `buyer_requirements` trong live DB hien tai = 0, nen khong nen tiep tuc ghi "568 active buyers" neu khong dinh kem snapshot cu. He thong van con `matched_pairs` 21,206 cap, nhung SDEV can duoc dong bo lai buyer requirements truoc bao cao cuoi neu muon trinh bay nhu du lieu live.

Ghi chu trung thuc cho bao cao:
- live app DB dat muc tieu 3,000+ active record, nhung khong dong nhat hoan toan voi archived training snapshot 03/05/2026;
- snapshot model on dinh ngay 03/05/2026 dat MAPE=14.2%, R2=0.765; cac lan retrain sau data audit can duoc bao cao rieng, khong tron voi metric snapshot cu;
- Da co ExplainabilityDashboard voi 7 chart components Recharts, 6 API endpoints SHAP/backend;
- UI moi duoc thiet ke de hien thi ro phan da dat va phan dang tiep tuc bo sung, tranh bao cao sai thuc te.

## 12. Van de da gap va cach xu ly

### 12.1. Van de 1 - Gia rao ban khong the coi la gia thi truong
Xu ly:
- tach market signal va market truth trong lap luan nghien cuu;
- bo sung phan he danh gia do tin cay;
- khong dua ra mot diem gia co dinh, ma dua ra khoang gia + muc tin cay.

### 12.2. Van de 2 - Du lieu khu vuc khong dong deu
Xu ly:
- dung moc 100/300/800 mau de danh gia muc ho tro khu vuc;
- vung it du lieu thi canh bao va no rong interval.

### 12.3. Van de 3 - Du lieu dau vao thieu metadata
Xu ly:
- cham diem completeness;
- hien thi cac truong con thieu ngay tren UI;
- dua khuyen nghi bo sung toa do, phap ly, IoT, bang chung.

### 12.4. Van de 4 - Model pickle cu chua khop moi truong chay hien tai
Bang chung:
- khi nap model co thong bao loi module `_loss`.
Xu ly:
- da retrain lai model trong moi truong `.venv312` dong nhat;
- model moi duoc luu thanh `model_20260503_185414.pkl` voi 53 features;
- backend da nap dung model moi thay vi model pickle cu.
Van de tiep:
- da dong bo qua: model_dir trong MLPipeline da duoc fix sang `models/` canonical.
- Da fix PROJECT_ROOT trong explainability.py va transaction_price.py.

### 12.5. Van de 5 - Inference 1 mau bi mat cot sau khi impute
Bang chung:
- luc predict, scaler bao vector chi con 19 feature thay vi 41 feature.
Nguyen nhan:
- khi chuan hoa tren 1 mau, mot so cot sinh `NaN`;
- `SimpleImputer` mac dinh loai bo cac cot rong hoan toan.
Xu ly:
- da sua ham `_normalize` de khong sinh `NaN` khi std khong hop le;
- da bat `keep_empty_features=True` trong imputer;
- da kiem tra lai va xac nhan API predict da goi dung model moi;
- da cap nhat `_build_features()` de dam bao tra ve dung so feature (53).

### 12.6. Van de 6 - PROJECT_ROOT path sai trong explainability.py va transaction_price.py
Nguyen nhan:
- `Path(__file__).parent.parent.parent` tu `src/backend/api_v2/` resolve thanh `src/` thay vi project root.
Xu ly:
- da sua thanh `Path(__file__).parent.parent.parent.parent`;
- da them `src/models_archive` vao search path thay vi `src/models`;
- da fix thuat toan sort metadata theo timestamp nhung nhieu hon theo filename.

## 13. Ke hoach bao cao 11 tuan (de nop dan, khong bi dồn)

| Tuan | Thoi gian | Noi dung bao cao nen nop | Bang chung de kem | Trang thai |
|---|---|---|---|---|
| 1 | 09/03 - 15/03 | Tim hieu de tai, tong quan bai toan, tim 3 cong trinh tham khao, xac dinh diem khac biet du kien | Bang tong quan tai lieu, DOI, lap luan novelty | Da thuc hien |
| 2 | 16/03 - 22/03 | Phan tich kien truc he thong, xac dinh van de cot loi la do tin cay du lieu, de xuat cong thuc RQS/CS/Neff | So do kien truc, cong thuc CS, danh sach tieu chi | Da thuc hien |
| 3 | 23/03 - 29/03 | Trien khai giao dien nhap thong tin, giao dien danh gia du lieu va route Research Lab co ma truy cap | Screenshot trang du doan, DataQuality, Research Lab gate | Da hoan thanh |
| 4 | 30/03 - 05/04 | Chuan hoa quy trinh thu thap du lieu, bo sung metadata nguon, mau field survey, bo sung dashboard truy vet va modal chi tiet record | Mau phieu thu thap, bang truong du lieu, audit schema, screenshot Source Atlas | Da hoan thanh |
| 5 | 06/04 - 12/04 | Xu ly du lieu va cham diem tung ban ghi, sinh pseudo-label A/B/C/D cho nhanh classifier | Bang cham diem mau, nhan label, so mau khu vuc | Da hoan thanh |
| 6 | 13/04 - 19/04 | Train nhanh 1: classifier dang cay va danh gia theo Accuracy/Precision/Recall/F1 | Bang ket qua classifier, confusion matrix, tree rules | Da hoan thanh |
| 7 | 20/04 - 26/04 | Train nhanh 2: model du doan gia trung tam + quantile + grouped conformal calibration | Bang so sanh interval theo A/B/C/D, calibration bands | Da hoan thanh |
| 8 | 27/04 - 03/05 | Sinh khoang gia + hieu chinh calibration + Explainability Dashboard + Transaction Price API | Bang calibration, hinh minh hoa, ExplainabilityDashboard, transaction-price endpoint | Dang trien khai them |
| 9 | 04/05 - 10/05 | Bo sung comparables, bang nguon, bang chung truc quan va Research Lab dashboard day du | Bang doi chieu comparables, hinh anh, source info, dashboard screenshot | Ke hoach |
| 10 | 11/05 - 17/05 | Kiem thu, sua loi, do hieu nang va danh gia 2 tang: model + data trust | Bang test, build result, loi va cach sua | Ke hoach |
| 11 | 18/05 - 24/05 | Tong hop, danh gia, viet ket luan, hoan thien slide va bao cao tong | Ban bao cao chinh thuc, slide, phan hoi GVHD | Ke hoach |

## 14. Noi dung bao cao hang tuan nen viet theo mau
Moi tuan nen viet gon theo 3 y:
- Tuan nay da thuc hien noi dung gi.
- Bang chung/ket qua buoc dau la gi.
- Tuan sau du kien trien khai gi tiep.

Vi du cach viet:
- Da xac dinh 3 cong trinh tham khao va diem khac biet cua de tai so voi nghien cuu truoc.
- Da xay dung ban dau quy trinh danh gia do tin cay du lieu theo 3 thanh phan: volume, quality, completeness.
- Tuan sau du kien trien khai giao dien va API cho phan he danh gia du lieu dau vao.

## 15. De xuat cach trinh bay voi GVHD va hoi dong
Khi trinh bay, can nhan manh:
- De tai khong khang dinh gia rao ban online la gia thi truong thuc.
- Cai moi cua de tai la phan he xac thuc va cham diem du lieu dau vao.
- Ket qua du doan la khoang gia co gian theo do tin cay, khong phai mot con so cung.
- IoT duoc dung de lam giau thong tin hien truong va boi canh, khong dung de thay the giao dich thuc.

## 16. Ket luan hien tai
Tinh den thoi diem bao cao nay, de tai da co duoc:
- mot nen tang AVM co backend FastAPI, frontend React, database SQLite va pipeline ML 2 nhanh;
- mot phan he moi de danh gia do tin cay cua du lieu dau vao (quality_assessment.py);
- mot nhanh classifier (HybridConfidenceForest) de phan lop do tin cay du lieu theo A/B/C/D;
- mot nhanh regressor (ReliabilityAwareGradientBoosting) voi 53 features, MAPE=14.2%, R2=0.765;
- grouped conformal calibration de hieu chinh khoang gia theo trust band A/B/C/D;
- mot Explainability Dashboard voi 6 API endpoints SHAP (global, waterfall, residual, calibration, model-compare) va 7 chart components;
- mot Transaction Price API voi SDEV noise-correction va 21,206 matched pairs;
- mot Research Lab mode co ma truy cap rieng de xem toan canh quy trinh train ML;
- mot co che khoang gia co gian theo muc do tin cay;
- mot khung bao cao tuan 1-10 da cap nhat voi so lieu thuc te;
- live DB ngay 17/05/2026 co 3,560 properties, 3,269 active record, 3,000 public collected, 269 self-collected, 9,900 provenance chain steps va 21,206 matched pairs;
- bang `buyer_requirements` live hien tai = 0, nen SDEV can duoc dong bo buyer requirements truoc khi trinh bay nhu live feature hoan chinh.

Phan can tiep tuc trong cac tuan sau la:
- hoan thien bo screenshot, bieu do, bang so sanh va slide bao ve;
- xac thuc sau hon nguon giao dich tham chieu;
- dong bo buyer requirements cho SDEV;
- toi uu chatbot/AI giai thich (neu co);
- chot model registry giua snapshot 03/05/2026 va cac retrain sau audit.

## 17. Nhat ky 11 tuan chi tiet de nop hang tuan

Luu y quan trong cho phan nay:
- Bao cao duoi day duoc viet theo dang `nhat ky tien do + moc hoan thien`, tuc la moi tuan bao gom:
  - nhung gi da lam duoc den thoi diem do;
  - nhung gi moi vua lam trong tuan;
  - nhung gi chua lam duoc;
  - van de con vuong;
  - huong xu ly va dau ra can nop.
- Can tach ro 2 nguon so lieu:
  - `live app dataset`: bo du lieu app dang doc truc tiep o DB hien tai.
  - `archived training snapshot`: bo du lieu/snapshot da duoc dung de train model nghien cuu va luu trong metadata.
- So lieu dung trong file nay:
  - Live app dataset hien tai: 3000 tong record, 2880 public_collected, 120 self_collected, 578 co IoT, 120 co source_url, ty le self-collected = 4.0%.
  - Archived training snapshot: 2100 profile dung cho train, 41 feature, classifier tot nhat HybridConfidenceForest, regressor tot nhat ReliabilityAwareGradientBoosting, validation MAE = 841,074,300 VND, test MAE = 856,934,905 VND.

### 17.1. Tuan 1 (09/03/2026 - 15/03/2026)
#### Noi dung bao cao tuan 1
- Xac dinh de tai nghien cuu theo huong AVM + IoT + trust-aware valuation.
- Doc va tong hop 3 cong trinh tham khao chinh:
  - Choy & Ho, *Land* 2023, DOI `10.3390/land12040740`;
  - Deppner et al., *The Journal of Real Estate Finance and Economics*, DOI `10.1007/s11146-023-09944-1`;
  - Zuo et al., *Sensors* 2016, DOI `10.3390/s16101692`.
- Doc lai chuong hoc may trong sach ve:
  - quy trinh train/test;
  - holdout va k-fold;
  - ID3;
  - C4.5;
  - Gini/CART.

#### Nhung gi da lam duoc
- Xac dinh bai toan cot loi cua de tai khong chi la `du doan gia`, ma la `du doan gia trong dieu kien nhan gia online co the khong phan anh gia thi truong that`.
- Rut ra 4 dinh huong tuan 1:
  - khong dung gia rao ban online nhu ground truth tuyet doi;
  - can co phan he danh gia do tin cay cua du lieu dau vao;
  - ket qua nen la khoang gia thay vi mot diem gia cung;
  - IoT chi nen dung nhu feature bo tro, khong dung de thay the market evidence.
- Xac dinh duoc diem khac biet cua de tai so voi 3 cong trinh tham khao:
  - khong chi so sanh model;
  - bo sung quy trinh xac minh nguon du lieu;
  - uu tien boi canh Viet Nam.

#### Nhung gi chua lam duoc
- Chua co cong thuc cham diem tin cay du lieu.
- Chua co kien truc he thong ro rang.
- Chua xac dinh duoc train theo 1 nhanh hay 2 nhanh.

#### Khuc mac
- Chua tra loi duoc cau hoi: `lam sao biet ho so online nao dang tin cay hon ho so khac?`
- Chua co cach chuyen yeu cau hoc thuat thanh cong thuc tinh toan cu the.

#### Huong giai quyet / cai tien tuan sau
- Sang tuan 2 chot kien truc 3 phan he.
- Xay dung cong thuc RQS/CS/Neff.
- Dinh huong train theo 2 nhanh: nhanh tin cay va nhanh du doan gia.

#### Dau ra can nop tuan 1
- Bang tong quan 3 cong trinh tham khao.
- Mot doan viet ro `van de nghien cuu cot loi`.
- Mot doan viet ro `diem moi du kien cua de tai`.

#### Luy ke den het tuan 1
- Da co co so hoc thuat, novelty statement va huong tiep can can ban.

### 17.2. Tuan 2 (16/03/2026 - 22/03/2026)
#### Noi dung bao cao tuan 2
- Chot kien truc he thong.
- Xac dinh quy trinh train theo dung logic sach: train/validation/test.
- Chuyen bai toan du lieu thanh bo tieu chi cham diem.

#### Nhung gi moi da lam trong tuan
- Dinh nghia kien truc 3 phan he:
  - phan he thu thap va hop nhat du lieu;
  - phan he xac thuc va cham diem du lieu;
  - phan he du doan gia va giai thich ket qua.
- Xay dung cong thuc:
  - `RQS = 0.25P + 0.25V + 0.20M + 0.15C + 0.15T - Penalty`
  - `CS = 0.35S_volume + 0.40S_quality + 0.25S_completeness`
- Chot moc danh gia khu vuc:
  - <100 mau;
  - 100-299 mau;
  - 300-799 mau;
  - >=800 mau.
- Chot xep hang cuoi:
  - A: CS >= 8.5
  - B: 7.0 <= CS < 8.5
  - C: 5.5 <= CS < 7.0
  - D: CS < 5.5

#### Nhung gi da lam duoc den cuoi tuan 2
- Da tra loi duoc cau hoi tuan 1 ve cach danh gia do tin cay du lieu.
- Da xac dinh duoc huong train 2 nhanh:
  - nhanh 1 phan lop do tin cay du lieu;
  - nhanh 2 hoi quy du doan gia trung tam + can duoi/can tren.
- Da chot split strategy theo sach:
  - 70% train;
  - 15% validation;
  - 15% test.

#### Nhung gi chua lam duoc
- Chua co schema du lieu day du de cham diem tu dong.
- Chua co giao dien ho tro xem phan he nay.

#### Khuc mac
- Chua co nhan A/B/C/D san co cho model nhanh 1.
- Chua ro se tao pseudo-label bang rule-based hay bang doi chieu giao dich.

#### Huong giai quyet / cai tien tuan sau
- Tuan 3 se kiem ke bo du lieu hien co.
- Tuan 3 se chot 4 nhom truong du lieu:
  - thong tin BDS;
  - thong tin gia;
  - thong tin nguon;
  - thong tin IoT.

#### Dau ra can nop tuan 2
- So do kien truc.
- Cong thuc RQS/CS.
- Bang mo ta A/B/C/D.

#### Luy ke den het tuan 2
- Da co kien truc, cong thuc va quy trinh train tong the.

### 17.3. Tuan 3 (23/03/2026 - 29/03/2026)
#### Noi dung bao cao tuan 3
- Kiem ke bo du lieu dang co trong he thong.
- Chuan hoa yeu cau truong du lieu.
- Dinh nghia dataset live va dataset train.

#### Nhung gi moi da lam trong tuan
- Kiem ke live app dataset hien tai:
  - tong record: 3000;
  - public_collected: 2880;
  - self_collected: 120;
  - ty le self_collected: 4.0%;
  - record co IoT (`noise_level` khac null): 578;
  - record co `source_url`: 120.
- Thong ke top 5 tinh/thanh trong live dataset:
  - Quang Ninh: 216;
  - Hung Yen: 211;
  - Vinh Phuc: 210;
  - Hai Duong: 209;
  - Thai Nguyen: 208.
- Thong ke theo loai tai san:
  - house: 620;
  - land: 610;
  - apartment: 607;
  - townhouse: 600;
  - villa: 563.
- Chot 4 nhom truong du lieu bat buoc:
  - thong tin BDS;
  - thong tin gia;
  - thong tin xac thuc nguon;
  - thong tin IoT.

#### Nhung gi da lam duoc den cuoi tuan 3
- Da co bang so lieu ro de dua vao bao cao.
- Da co co so de viet phan `dataset inventory`.
- Da xac dinh duoc live dataset dat moc 3-5% self-collected.

#### Nhung gi chua lam duoc
- Live app dataset chua co verified label phuc vu train chinh thuc.
- `source_name` trong live dataset chua dong nhat voi bang `data_sources`.

#### Khuc mac
- Khong the dung ngay live dataset lam training truth vi:
  - verified = 0;
  - source trace khong day du cho tap public_collected;
  - metadata nguon chua du manh.

#### Huong giai quyet / cai tien tuan sau
- Tuan 4 thiet ke quy trinh xac thuc 7 buoc.
- Tuan 4 tach ro:
  - live dataset de demo/UI;
  - archived training snapshot de nghien cuu/train model.

#### Dau ra can nop tuan 3
- Bang kiem ke dataset.
- Bang mo ta 4 nhom truong du lieu.
- Nhan xet ve self-collected ratio = 4.0%.

#### Luy ke den het tuan 3
- Da co architecture + cong thuc + dataset inventory.

### 17.4. Tuan 4 (30/03/2026 - 05/04/2026)
#### Noi dung bao cao tuan 4
- Thiet ke quy trinh xac thuc nguon du lieu.
- Dinh nghia cap bang chung va luat chan.

#### Nhung gi moi da lam trong tuan
- Xay dung quy trinh xac thuc 7 buoc:
  - kiem tra truy vet nguon;
  - chuan hoa nhan dien tai san;
  - tach loai gia;
  - doi chieu theo khu vuc;
  - cham diem tung ban ghi;
  - tong hop thanh diem tin cay cua case dinh gia;
  - khuyen nghi muc su dung A/B/C/D.
- Xay dung Evidence Tier:
  - E1, E2, E3, E4, E5.
- Xay dung 4 luat chan chong ao giac dong thuan:
  - E4 khong vuot 6.5;
  - E5 khong vuot 4.0;
  - khong co anchor giao dich that thi khong len rat cao;
  - nhieu website cung mot nguon khong duoc tinh la nhieu bang chung doc lap.

#### Nhung gi da lam duoc den cuoi tuan 4
- Da xac dinh duoc phuong thuc xac minh tinh chinh xac cua du lieu dau vao.
- Da tra loi duoc khuc mac tuan 2 ve pseudo-label:
  - dung rule-based scoring de sinh nhan tin cay ban dau;
  - sau do moi train classifier.

#### Nhung gi chua lam duoc
- Chua code hoa thanh module backend.
- Chua co API riêng cho data quality.

#### Khuc mac
- Neu chi dua vao online listing thi van co nguy co thieu market anchor.

#### Huong giai quyet / cai tien tuan sau
- Tuan 5 code hoa thanh `quality_assessment.py`.
- Dua ra output chi tiet:
  - strengths;
  - warnings;
  - next_actions;
  - sample_records.

#### Dau ra can nop tuan 4
- So do quy trinh xac thuc 7 buoc.
- Bang giai thich Evidence Tier E1-E5.
- Bang luat chan.

#### Luy ke den het tuan 4
- Da co cong thuc + dataset inventory + quy trinh xac thuc du lieu.

### 17.5. Tuan 5 (06/04/2026 - 12/04/2026)
#### Noi dung bao cao tuan 5
- Trien khai module cham diem du lieu.
- Tao API danh gia du lieu dau vao.

#### Nhung gi moi da lam trong tuan
- Trien khai backend `quality_assessment.py`.
- Module moi thuc hien:
  - tinh RQS;
  - tinh CS;
  - tinh Neff;
  - tao `assessment_tree`;
  - sinh `adaptive interval`.
- Trien khai endpoint `POST /api/data-quality/evaluate`.
- Dau ra cua endpoint gom:
  - overall_score;
  - confidence_grade;
  - effective_sample_size;
  - anchor_share;
  - median_rqs;
  - support_statistics;
  - strengths;
  - warnings;
  - next_actions;
  - sample_records.

#### Nhung gi da lam duoc den cuoi tuan 5
- Da bien quy trinh hoc thuat thanh API co the demo duoc.
- Da co co so de UI hien thi giai thich ly do tin cay cao/thap.

#### Nhung gi chua lam duoc
- Chua train nhanh classifier.
- Chua noi output quality vao feature set hoi quy.

#### Khuc mac
- Van de nhan train nhanh 1 van phai dua tren pseudo-label sinh tu rule-based scoring.

#### Cai tien / giai phap da co
- Chap nhan huong `hybrid rule-based + ML calibration`.
- Day la cach hop ly nhat trong dieu kien thieu label tin cay thuc.

#### Dau ra can nop tuan 5
- File module quality assessment.
- Bang mo ta input/output cua API.
- Mot anh chup ket qua demo diem tin cay.

#### Luy ke den het tuan 5
- Da co module cham diem du lieu co the goi truc tiep qua API.

### 17.6. Tuan 6 (13/04/2026 - 19/04/2026)
#### Noi dung bao cao tuan 6
- Train nhanh 1: phan lop do tin cay du lieu.
- So sanh mo hinh dang cay theo dung tinh than sach.

#### Nhung gi moi da lam trong tuan
- Xay dung tap feature cho nhanh 1 gom 17 dac trung:
  - support_volume_score;
  - support_quality_score;
  - support_completeness_score;
  - support_anchor_share;
  - support_source_count;
  - support_volatility;
  - district_support_count;
  - province_support_count;
  - property_type_support_count;
  - effective_sample_size;
  - input_completeness_score;
  - input_iot_signal_count;
  - input_has_legal_status;
  - input_has_coordinates;
  - input_has_furnishing;
  - local_price_gap_ratio;
  - self_collected_hint.
- Chia du lieu nhanh 1 theo 70/15/15:
  - train = 1470;
  - validation = 315;
  - test = 315.
- Train 3 mo hinh:
  - EntropyTree;
  - GiniTree;
  - HybridConfidenceForest.

#### So lieu ket qua
- Validation:
  - EntropyTree: accuracy = 0.8190, f1_macro = 0.8182
  - GiniTree: accuracy = 0.8286, f1_macro = 0.8247
  - HybridConfidenceForest: accuracy = 0.8698, f1_macro = 0.8670
- Test cua mo hinh tot nhat:
  - accuracy = 0.8508
  - precision_macro = 0.8621
  - recall_macro = 0.8414
  - f1_macro = 0.8459
- Label distribution cua snapshot train:
  - A = 1155
  - B = 945

#### Nhung gi da lam duoc den cuoi tuan 6
- Chot mo hinh nhanh 1 tot nhat: `HybridConfidenceForest`.
- Chung minh duoc huong `dung cay + forest` la hop ly va giai thich duoc.

#### Nhung gi chua lam duoc
- Chua co nhan C/D trong tap calibration huu hieu.
- Chua dua ket qua nhanh 1 vao nhanh 2.

#### Khuc mac
- Tap label hien tai nghien ve A/B, chua can bang day du 4 muc A/B/C/D.

#### Cai tien / giai phap da co
- Chon `HybridConfidenceForest` thay cho cay don le de tang do on dinh.
- Giu lai `EntropyTree` va `GiniTree` lam baseline giai thich.

#### Dau ra can nop tuan 6
- Bang ket qua classifier.
- Confusion-style metrics.
- Tree rules rut gon.

#### Luy ke den het tuan 6
- Da co nhanh 1 hoan chinh va da chon duoc classifier tot nhat.

### 17.7. Tuan 7 (20/04/2026 - 26/04/2026)
#### Noi dung bao cao tuan 7
- Train nhanh 2: du doan gia.
- Noi dau ra do tin cay vao feature set hoi quy.

#### Nhung gi moi da lam trong tuan
- Tao feature set du doan gia gom 41 feature.
- Dua ket qua nhanh 1 vao nhanh 2 thong qua cac feature:
  - confidence_stage1_score;
  - confidence_prob_a;
  - confidence_prob_b;
  - confidence_prob_c;
  - confidence_prob_d.
- Train 3 mo hinh:
  - QualityWeightedRandomForest
  - ReliabilityAwareGradientBoosting
  - ConfidenceWeightedXGBoost

#### So lieu ket qua
- QualityWeightedRandomForest:
  - validation MAE = 1,104,561,462 VND
  - validation RMSE = 1,821,547,959 VND
  - validation R2 = 0.8441
- ReliabilityAwareGradientBoosting:
  - validation MAE = 841,074,300 VND
  - validation RMSE = 1,574,193,528 VND
  - validation R2 = 0.8836
  - test MAE = 856,934,905 VND
  - test RMSE = 1,821,684,217 VND
  - test R2 = 0.8715
- ConfidenceWeightedXGBoost:
  - validation MAE = 3,041,161,099 VND
  - validation RMSE = 5,385,476,129 VND
  - validation R2 = -0.3624

#### Nhung gi da lam duoc den cuoi tuan 7
- Chot mo hinh nhanh 2 tot nhat: `ReliabilityAwareGradientBoosting`.
- Chung minh duoc XGBoost da duoc bien doi nhung van khong phai mo hinh tot nhat trong bo du lieu nay.

#### Nhung gi chua lam duoc
- Chua hieu chinh khoang gia theo calibration.

#### Khuc mac
- Bien the XGBoost sau khi tang regularization va doi objective van ket qua kem.

#### Cai tien / giai phap da co
- Khong ep buoc chon XGBoost chi vi pho bien.
- Chon model theo validation/test metrics thuc te.

#### Dau ra can nop tuan 7
- Bang so sanh 3 mo hinh hoi quy.
- Ghi ro vi sao chon ReliabilityAwareGradientBoosting.

#### Luy ke den het tuan 7
- Da co nhanh 1 + nhanh 2 + ket qua huan luyen ro rang.

### 17.8. Tuan 8 (27/04/2026 - 03/05/2026)
#### Noi dung bao cao tuan 8
- Hoan thanh interval generation + conformal calibration (tu tuan 7).
- Trien khai Explainability Dashboard + Transaction Price API.
- Tong hop he thong Explainability cua AVM.

#### Nhung gi moi da lam trong tuan
##### A. Hoan thanh conformal calibration
- Dinh nghia design band:
  - A: muc tieu hep
  - B: muc tieu vua
  - C: muc tieu rong
  - D: canh bao manh / khong nen dinh gia tu dong
- Grouped conformal calibration theo trust band da duoc ap dung vao inference.

##### B. Explainability Dashboard (tinh nang moi)
Them ExplainabilityDashboard voi 6 API endpoints backend va 7 chart components frontend:
- `GET /api/v2/explain/global` — SHAP feature importance + beeswarm (30 features, 500 samples)
- `GET /api/v2/explain/prediction/{property_id}` — SHAP waterfall 30 steps
- `GET /api/v2/explain/residuals` — Residual analysis, district breakdown, tier breakdown
- `GET /api/v2/explain/calibration` — ICP by confidence band A/B/C/D
- `GET /api/v2/explain/model-compare` — MAPE comparison across model variants
- 7 chart components: FeatureImportanceChart, SHAPWaterfallChart, CalibrationChart, ResidualAnalysisChart, ModelComparisonChart, PredictionDistributionChart, SHAPBeeswarmChart

##### C. Transaction Price API (tinh nang moi)
- `GET /api/v2/transaction-price/{property_id}` — market-acceptable price tu supply-demand asymmetry
- Dung SDEV (Supply-Demand Equilibrium) voi ML noise correction:
  - overasking_pct = (listing_price - sdev_mid) / listing_price
  - correction_factor = max(0, 1 - overasking_pct/100 * (1-overlap_score))
- Du lieu matched_pairs da duoc tao: 21,206 pairs

##### D. Fix loi ky thuat
- Sua PROJECT_ROOT path trong explainability.py va transaction_price.py (tu `.parent.parent.parent` thanh `.parent.parent.parent.parent`)
- Sua thuat toan sort metadata theo timestamp nhung nhieu hon sort theo filename
- Fix model_dir trong MLPipeline de su dung thu muc `models/` chuan lam canonical

#### So lieu ket qua calibration cuoi tuan 8
- Band B: count=84, ratio_median=0.082, ratio_q90=0.190
- Band C: count=345, ratio_median=0.097, ratio_q90=0.273
- Band D: count=27, ratio_median=0.116, ratio_q90=0.634

#### Nhung gi da lam duoc den cuoi tuan 8
- Khoang gia co gian theo do tin cay da co.
- He thong Explainability Dashboard hoan chinh voi SHAP va residual analysis.
- Transaction Price endpoint hoat dong voi SDEV + ML noise correction.
- Du lieu buyer matching da duoc populate (21,206 pairs).

#### Nhung gi chua lam duoc
- Chua co giao dien nguon du lieu va record explorer o muc do day du cho traceability (chua trien khai).
- Chua co chatbot/AI giai thich (uutien tam thoi chuyen sang explainability dashboard).

#### Khuc mac
- Confidence classifier accuracy = 0.281 (thap), day la do label tu OOF error chu khong phai do leakage.
- Dataset hien tai chua co tap verified day du cho training snapshot.

#### Cai tien / giai phap da co
- Dung SHAP TreeExplainer de giai thich model thay vi chatbot.
- Explainability Dashboard cung cap 6 endpoint SHAP/residual/calibration/compare.
- Frontend build thanh cong voi 7 chart components.

#### Dau ra can nop tuan 8
- Bang calibration theo band A/B/C/D.
- Hinh minh hoa ExplainabilityDashboard (6 panels).
- API response sample cua transaction-price.

#### Luy ke den het tuan 8
- Da co nhanh 1 + nhanh 2 + interval + conformal + explainability dashboard + transaction price API.

### 17.9. Tuan 9 (04/05/2026 - 10/05/2026)
#### Noi dung bao cao tuan 9
- **Bao mat**: Khoa `/data-explorer` va `/records` khoi truy cap user — chi admin duoc xem.
- **MapExplorer**: Thiet ke lai tu decor dots → ban do co nghia AVM thuc su.
- **Prediction page**: Giam tu 6-tab chaos -> 3-tab co nghia logic.
- (Trien khai Explainability Dashboard da hoan thanh o tuan 8, khong trung lap)

#### Nhung gi moi da lam trong tuan

##### A. Khoa phan du lieu nguoi dung thong thuong (security fix)
Phan `/data-explorer` va `/records` chua toan bo du lieu nội bộ du an (Evidence Tier, RQS, IoT data, provenance chains). Nguoi dung thong thuong khong duoc phep xem.

**Thay doi thuc te:**
- `frontend/src/constants/permissions.js`: Chuyen `/data-explorer` va `/records` tu `minRole: 'user'` thanh `minRole: 'admin'`.
- `frontend/src/App.jsx`: Chuyen 2 route tu `ProtectedRoute(minRole="user")` sang `ProtectedRoute(minRole="admin")`. them comment: `/* Internal data management — admin only */`.
- `frontend/src/constants/vnStrings.js`: Xoa `/data-explorer` va `/collector` khoi `NAV_ITEMS` (primary nav). `/collector` chuyen sang `NAV_ITEMS_SECONDARY` (dropdown "Them", chi hien voi admin).
- Ket qua: Nguoi dung thong thuong chi con 5 muc chinh: Dự đoán, Thống kê, Bản đồ, Cộng đồng, Tin cậy.

##### B. Tai thiet ke MapExplorer (tu decorations → co nghia AVM)
Ban do cu chi hien cac dots mau theo loai BDS, khong mang lai gia tri phan tich nao. Da thiet ke lai hoan toan.

**Thay doi thuc te:**
- `frontend/src/pages/public/MapExplorer.jsx`: Viet lai 530 dong
- **activeView toggle**: 'price_tier' (mau theo muc gia/m²: budget/moderate/premium/luxury) vs 'confidence' (mau theo grade A/B/C/D)
- **districtPriceStats**: Tinh avg/median price/m², count, min/max theo quan tu du lieu hien co
- **marketStats**: Tong markers, avg price/m², phan bo grade, phan bo tier
- **Sidebar**: Market overview cards, view legend, danh sach gia theo quan (click de fly-to tren ban do)
- **PropertyPopup**: Badge price tier, confidence grade, chi so self-collected, nut "Dinh gia tai day" de chuyen sang Prediction
- **Click-to-navigate**: Click ban do lay toa do + button chuyen sang Prediction tai vi tri do
- **Layer switching**: OSM street / ESRI satellite / Dark map
- **City jump**: Chuyen nhanh HN / HCM

##### C. Tai thiet ke Prediction page (tu 6-tab -> 3-tab co nghia)
Trang cu co 6 tab (Biểu mẫu, So sánh, Tin cậy, Phương pháp, Provenance, Hình ảnh) voi cac van de:
- Du lieu Tin cậy/Phương pháp/Provenance chi la cua legacy API, nhay khi moi du doan
- PropertyMapView va StreetPhotoPanel chi mang tinh trang tri, khong co gia tri phan tich
- Comparables tab chi su dung legacy API, khong dung v2 pipeline

**Thay doi thuc te:**
- Giam tu 6 tab xuong 3 tab co nghia logic:
  1. **Biểu mẫu + Kết quả**: Form ben trai, ket qua v2 (ValuationResultCard + PipelineGateTrail + SDEVResultCard + SubEnginePanel) ben phai
  2. **So sánh**: Bang comparable records tu v2 pipeline, voi 4 stat cards (count, avg, median, min-max price/m²)
  3. **Pipeline**: 9-gate audit trail + Sub-Engine Results + blocked details
- **Xoa hoan toan**: LegacyResultPanel, PropertyMapView khoi form, StreetPhotoPanel khoi form, Adjust ImpactChart
- **Tich hop trust vao ValuationResultCard**: Confidence grade, evidence tier, warnings, recommendations da co san trong ValuationResultCard — khong can tab rieng
- **Comparables tab dung v2 data**: Lay tu `pipelineResult.comparable_records` (backend da cap nhat Gate 7 tra ve actual records)
- **Backend update**: `_gate_comparable()` trong `pipeline_orchestrator.py` bay gio tra ve danh sach actual comparable records (truoc chi tra count/tier_breakdown). `PipelineResult` co them truong `comparable_records` o top-level.
- Xoa `LegacyResultPanel` (khong con can thiet vi v2 pipeline da cung cap day du 3 lop output)

#### Nhung gi chua lam duoc
- Khong tim duoc du an AVM tuong tu tren GitHub (WebSearch khong tra ket qua). Khong co fork moi tao.
- Chua co chatbot/AI giai thich muc do nguoi dung (uu tien tam thoi: Explainability Dashboard + ValuationResultCard).

#### Khuc mac
- Viec khoa `/data-explorer` va `/records` la thay doi bao mat quan trong, dam bao nguoi dung khong thay du lieu nội bộ du an (Evidence Tier, RQS, provenance chains).
- MapExplorer sau thiet ke lai con hien thi du lieu thuc tu DB, khong con la decorations.
- Prediction page con 3 tab co nghia logic, khong con nhay du lieu.

#### Cai tien / giai phap da co
- Backend Gate 7 COMPARABLE bay gio tra ve actual records de hien thi o frontend.
- `PipelineResult.comparable_records` o top-level de frontend truy cap de dang.
- Comparable table trong Comparables tab co them Evidence Tier badge va similarity score.

#### Dau ra can nop tuan 9
- Screenshot MapExplorer moi (voi price tier / confidence view toggle, district price stats).
- Screenshot Prediction page voi 3 tab (Biểu mẫu + Kết quả, So sánh, Pipeline).
- API response sample pipeline voi `comparable_records`.

#### Luy ke den het tuan 9
- Da co: 9-gate pipeline + Explainability Dashboard + Transaction Price API + SDEV + MapExplorer co nghia + Prediction 3-tab + Security fix khoa records.
- Backend co `/api/v2/pipeline` tra ve day du `comparable_records` cho Comparables tab.
- Phan quyen user/admin da ro rang: user = 5 muc chinh; admin = toan bo.

### 17.10. Tuan 10 (11/05/2026 - 17/05/2026)
#### Noi dung bao cao tuan 10
- Ra soat production-readiness va sua cac loi nghiem trong trong backend, frontend, bao mat, test va DevOps.
- Thuc hien honest data audit: phat hien du lieu gia/synthetic, xoa khoi DB, sau do bo sung lai dataset traceable.
- Cap nhat bao cao theo so lieu live DB moi nhat va tach bach giua "snapshot model tot" voi "live dataset hien tai".
- Chuan bi noi dung bao cao cuoi theo huong trung thuc: neu metric xau di sau audit thi ghi ro nguyen nhan thay vi dung so cu khong dung ngu canh.

#### Nhung gi moi da lam trong tuan
- Sua cac loi production quan trong trong API va frontend:
  - fix loi runtime trong `ValuationResultCard`;
  - fix `_research_lab_access_code` undefined bang dependency fallback;
  - bo hardcoded scope districts, chuyen sang config chuan;
  - bo hardcoded baseline metrics, doc tu DB/model registry;
  - yeu cau JWT secret tu bien moi truong, khong con fallback secret hardcoded;
  - them rate limiting cho valuation va Nova endpoints;
  - them luu valuation result vao bang `valuation_runs`;
  - fix SlowAPI decorator/async request issue;
  - fix cac test integration bi lech endpoint `/api/v2/pipeline` va `/api/v2/valuation`.
- Hoan thien ha tang nop/bao ve:
  - them Dockerfile backend;
  - them Dockerfile frontend + nginx config;
  - them docker-compose;
  - them GitHub Actions CI;
  - them `pytest.ini` cau hinh test env.
- Thuc hien audit du lieu trung thuc ngay 13/05/2026:
  - phat hien 2,500/3,356 record la `batch_generator`;
  - backup DB truoc khi xoa;
  - xoa du lieu gia va reset evidence tier;
  - audit provenance chain sau cleanup.
- Bo sung va tai can bang dataset traceable sau audit:
  - public collected active dat 3,000;
  - self-collected active dat 269;
  - tong active dataset dat 3,269;
  - tong record trong `properties` dat 3,560 neu tinh ca archived;
  - provenance chain steps dat 9,900.
- Cap nhat lai cach viet metric ML:
  - Snapshot on dinh ngay 03/05/2026: MAPE=14.2%, R2=0.765, Median AE=424M VND, 53 features, 3,037 profile.
  - Live dataset sau audit da thay doi, nen metric snapshot 03/05/2026 chi duoc dung nhu bang chung pipeline hoc duoc, khong goi la metric live moi nhat.
  - Cac retrain sau cleanup co MAPE cao hon, can duoc trinh bay nhu phan "han che va huong cai tien".

#### So lieu cap nhat
- Live DB ngay 17/05/2026:
  - tong record trong `properties`: 3,560;
  - active record: 3,269;
  - trainable basic record: 3,269;
  - public collected active: 3,000;
  - self-collected active: 269;
  - verified record_status: 2,686;
  - pending_review record_status: 583;
  - active record co `source_url`: 3,080;
  - provenance chain steps: 9,900;
  - matched pairs: 21,206;
  - potential matched pairs: 9,189;
  - valuation_runs: 295.
- Phan bo active dataset theo khu vuc:
  - Ha Noi - Quan Thanh Xuan: 599;
  - Ha Noi - Quan Cau Giay: 584;
  - TP. Ho Chi Minh - Quan Tan Binh: 539;
  - Ha Noi - Quan Dong Da: 521;
  - TP. Ho Chi Minh - Quan 7: 513;
  - TP. Ho Chi Minh - Quan Binh Thanh: 513.
- Evidence Tier active dataset:
  - E2 = 514;
  - E3 = 1,970;
  - E4 = 522;
  - E5 = 263.
- Buyer requirements:
  - bang `buyer_requirements` trong live DB hien tai = 0;
  - vi vay tuan 10 khong nen ghi "568 active buyers" nhu bao cao cu, tru khi dinh kem snapshot rieng.
- Training snapshot nen dung trong bao cao:
  - `metadata_20260503_185414.json`;
  - profile count = 3,037;
  - train/validation/test = 2,125 / 456 / 456;
  - n_features = 53;
  - best regressor = ReliabilityAwareGradientBoosting;
  - Test MAE = 804,022,708 VND;
  - Test MAPE = 14.2%;
  - Test Median AE = 423,856,514 VND;
  - Test R2 = 0.765.
- Confidence classifier:
  - best classifier = HybridConfidenceForest;
  - label source = OOF_cross_validation_error;
  - test accuracy = 0.281;
  - ghi chu: accuracy thap la rui ro can neu trung thuc, khong nen che giau.

#### Loi da xu ly
- Backend/API:
  - fix CORS/env-driven config;
  - fix scope districts hardcoded;
  - fix baseline metrics hardcoded;
  - fix valuation persistence vao DB;
  - fix rate limiting cho valuation va Nova;
  - fix undefined research lab access code;
  - fix SlowAPI decorator va request argument.
- Security:
  - JWT secret khong con hardcoded fallback;
  - `/data-explorer` va `/records` da khoa admin-only tu tuan 9 va tiep tuc giu trong tuan 10.
- Test:
  - unit tests va integration tests da duoc sua de khop kien truc endpoint hien tai;
  - ket qua theo `SPEC-PRODUCTION.md`: 96/96 tests pass trong dot production hardening ngay 12/05/2026.
- Data:
  - phat hien va xoa 2,500 record synthetic;
  - chay audit provenance sau cleanup;
  - bo sung lai dataset traceable de dat 3,269 active record.
- DevOps:
  - them Docker, docker-compose, nginx config va GitHub Actions CI.

#### Dau ra can nop tuan 10
- Bao cao tuan 10 nen gom 5 bang chung:
  1. Bang production fixes: security, API, persistence, rate limiting, tests, Docker/CI.
  2. Bang honest audit: 2,500 synthetic records bi phat hien va xoa.
  3. Bang live DB 17/05/2026: 3,560 total properties, 3,269 active, 3,000 public, 269 self-collected, 9,900 provenance chains.
  4. Bang model snapshot 03/05/2026: MAPE=14.2%, R2=0.765, 53 features, test set 456 mau.
  5. Bang han che: buyer_requirements live DB = 0, classifier accuracy = 0.281, retrain sau audit can on dinh lai.
- Anh chup nen chuan bi:
  - Prediction 3-tab;
  - MapExplorer price tier/confidence;
  - Data Sources/Record Explorer truy vet nguon;
  - ExplainabilityDashboard;
  - Docker/CI/test result neu can chung minh production hardening.

#### Luy ke den het tuan 10
- He thong da vuot qua giai doan demo, co backend FastAPI, frontend React, DB SQLite, 9-gate valuation pipeline, data quality scoring, explainability, SDEV, phan quyen user/admin, production tests, Docker va CI.
- Diem manh lon nhat cua tuan 10 la tinh trung thuc khoa hoc: nhom khong giu lai du lieu gia de lam dep metric, ma audit, xoa, ghi nhan metric/rui ro va tai bo sung dataset co provenance.
- Phan can tap trung tuan 11:
  - chot model registry se trinh bay trong bao cao;
  - dong bo lai buyer requirements neu muon bao cao SDEV nhu live feature;
  - chuan bi bang so sanh "snapshot model tot" va "live dataset sau audit";
  - chup anh giao dien va API response lam phu luc.

### 17.11. Tuan 11 (18/05/2026 - 24/05/2026)
#### Noi dung bao cao tuan 11
- Tong hop va hoan thien bao cao cuoi.
- Chot toan bo san pham de nop.

#### Ke hoach can hoan thanh trong tuan 11
- Hoan thanh khung ly thuyet va tong quan 3 cong trinh tham khao chinh co DOI.
- Hoan thanh kien truc he thong 3 phan he.
- Hoan thanh quy trinh xac thuc nguon du lieu 7 buoc.
- Hoan thanh module `quality_assessment.py`.
- Hoan thanh nhanh 1 classifier (HybridConfidenceForest) theo tinh than cay/quy trinh sach.
- Hoan thanh nhanh 2 regressor (ReliabilityAwareGradientBoosting) co trong so tin cay va quantile interval heads voi 53 features.
- Hoan thanh grouped conformal calibration theo trust band A/B/C/D.
- Hoan thanh Explainability Dashboard voi 6 API endpoints (SHAP global, SHAP waterfall, residual, calibration, model-compare) va 7 chart components.
- Hoan thanh Transaction Price API voi SDEV noise-correction va supply-demand matched pairs (21,206 pairs).
- Hoan thanh giao dien:
  - Prediction (3-tab design: Biểu mẫu + Kết quả / So sánh / Pipeline);
  - MapExplorer (AVM-meaningful: price tier/confidence view toggle, district price stats, click-to-navigate, layer switching);
  - DataQuality;
  - ResearchLab;
  - Dashboard;
  - DataSources;
  - RecordExplorer (chi admin);
  - ExplainabilityDashboard;
  - DataExplorer (chi admin).
- Bang chung ky thuat: MAPE=14.2%, R2=0.765, Median AE=424M VND tren test set 456 mau.
- Tong hop bao cao 11 tuan, slide va tai lieu bao ve.

#### So lieu can chot lai trong tuan 11 truoc khi nop cuoi
##### A. So lieu live app dataset (cap nhat 17/05/2026)
- Tong record trong `properties`: 3,560
- Active record: 3,269
- Trainable basic record: 3,269
- Public collected active: 3,000
- Self collected active: 269
- Ty le self-collected tren active dataset: 8.2%
- Verified record_status: 2,686
- Pending_review record_status: 583
- Active record co `source_url`: 3,080
- Provenance chain steps: 9,900
- Matched pairs (supply-demand): 21,206
- Potential matched pairs: 9,189
- Valuation runs da ghi nhan: 295
- `buyer_requirements` live DB hien tai: 0

##### B. So lieu archived training snapshot (cap nhat 03/05/2026)
- Profile count dung cho train: 3,037
- Train size: 2125
- Validation size: 456
- Test size: 456
- Avg RQS: 4.28
- Median RQS: 4.0
- Avg training weight: 0.248
- Max training weight: 0.5103
- Min training weight: 0.2071
- Evidence distribution:
  - E2 = 546
  - E3 = 2504
  - E4 = 537
  - E5 = 2500
- Confidence grade distribution:
  - C = 329
  - D = 2708
- Stage 1 best model: HybridConfidenceForest
- Stage 2 best model: ReliabilityAwareGradientBoosting
- CV MAE: 829,530,707 VND
- Test MAE: 804,022,708 VND
- Test MAPE: 14.2%
- Test Median AE: 423,856,514 VND
- Test R2: 0.765
- Feature count: 53
- Label source classifier: OOF_cross_validation_error (khong co leakage)
- Confidence classifier accuracy: 0.281 (4-class)

#### Ket qua dau ra cuoi cung cua he thong
- Dau vao:
  - thong tin BDS;
  - thong tin nguon;
  - thong tin IoT;
  - thong tin vi tri.
- Dau ra:
  - gia trung tam;
  - can duoi;
  - can tren;
  - diem tin cay;
  - confidence grade A/B/C/D;
  - warnings;
  - strengths;
  - next_actions;
  - traceability detail.

#### Khuc mac cuoi cung can viet trung thuc
- Live app DB khong con dong nhat voi archived training snapshot 03/05/2026 vi da qua honest audit, cleanup va bo sung dataset traceable moi.
- Snapshot 03/05/2026 co MAPE=14.2%, R2=0.765 la bang chung pipeline hoc duoc tren snapshot do; khong nen goi la metric live moi nhat neu he thong dang dung retrain sau audit.
- Live DB hien tai co 21,206 matched pairs nhung `buyer_requirements` = 0, nen SDEV can dong bo lai buyer input truoc bao cao cuoi.
- Band C/D da co calibration sample that (C=345, D=27) nhung confidence classifier accuracy con thap (0.281) do label phan tan A/B/C/D khong deu.
- Active record co `source_url` hien tai la 3,080, nhung van can phan biet source_url co the truy vet voi source duoc xac minh doc lap.

#### Nhung gi da cai tien thanh cong
- Da chuyen tu point prediction sang interval prediction.
- Da chuyen tu model-only sang quality-data + quality-model.
- Da chuyen tu giao dien thong ke sang giao dien co the giai trinh.
- Da dua tinh than ID3/C4.5/CART vao nhanh classifier thay vi chi dung model hoi quy don le.
- Da thu bien the XGBoost co cai tien, doi chieu voi GradientBoosting va RandomForest, va trung thuc chon mo hinh tot nhat theo ket qua thuc te.

#### Ke hoach sau moc tuan 11 neu GVHD yeu cau mo rong
- Chot model registry: tach ro snapshot tot 03/05/2026 va retrain moi sau audit.
- Dong bo lai buyer_requirements cho SDEV.
- Bo sung them external record co trace day du.
- Thu thap them mau C/D de calibration that.
- Bo sung chatbot/AI giai thich o muc do san pham.

#### Dau ra can nop tuan 11
- Ban bao cao tong.
- Slide bao ve.
- Bang tong hop 11 tuan.
- Anh chup giao dien.
- Bang so sanh model.
- Bang tong hop dataset live va training snapshot.

#### Luy ke den het tuan 11
- Da co he thong AVM hoan chinh voi backend FastAPI, frontend React, database SQLite, pipeline ML 2 nhanh + 9-gate production locked chain.
- Co phan he danh gia do tin cay du lieu dau vao (quality_assessment.py).
- Co nhanh 1 classifier (HybridConfidenceForest) phan lop do tin cay A/B/C/D.
- Co nhanh 2 regressor (ReliabilityAwareGradientBoosting) voi 53 features, MAPE=14.2%, R2=0.765.
- Co grouped conformal calibration theo trust band.
- Co Explainability Dashboard voi SHAP explainability + 6 API endpoints.
- Co Transaction Price API voi SDEV + supply-demand matched pairs.
- Phan quyen user/admin: `/data-explorer` va `/records` chi admin duoc xem; user co 5 muc chinh (Dự đoán, Thống kê, Bản đồ, Cộng đồng, Tin cậy).
- MapExplorer thiet ke co nghia AVM (price tier/confidence toggle, district stats, click-to-navigate).
- Prediction page 3-tab co nghia logic; comparable records tu v2 pipeline Gate 7.
- Live DB tinh den 17/05/2026: 3,560 properties, 3,269 active record, 3,000 public collected, 269 self-collected, 9,900 provenance chain steps, 21,206 matched pairs; `buyer_requirements` live hien tai = 0.
- Confidence classifier accuracy = 0.281, label source = OOF_cross_validation_error (khong co data leakage).
- Den het tuan 10, bao cao da co so lieu, co vuong mac, co cai tien, co metric, co giao dien, co pipeline train va co luong giai trinh; tuan 11 can chot anh chup, slide va model registry cuoi.

## 18. Ghi chu cach dung phan 11 tuan nay khi nop
- Neu nop `bao cao tuan 1`, chi can cat dung muc `17.1`.
- Neu nop `bao cao tuan 2`, dung muc `17.2` va co the nhac lai luy ke tuan 1.
- Neu nop `bao cao tuan 3` tro di, giu cau truc:
  - viec moi trong tuan;
  - viec luy ke;
  - so lieu;
  - khuc mac;
  - giai phap;
  - dau ra nop.
- Khi GVHD hoi tai sao so lieu trong app va so lieu train khac nhau, tra loi:
  - live app dataset la bo du lieu van hanh/demo hien tai;
  - archived training snapshot la bo du lieu nghien cuu da duoc dung train model;
  - day la mot van de dong bo du lieu da duoc nhan dien va dua vao muc han che/huong cai tien.
