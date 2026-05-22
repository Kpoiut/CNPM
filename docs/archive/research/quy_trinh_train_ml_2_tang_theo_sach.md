# QUY TRINH TRAIN ML 2 TANG THEO SACH VA THEO CVX-BDS-IoT

## 1. Tu tuong nen
Quy trinh nay bam sat logic trong giao trinh:
- co dataset goc;
- co giai doan huan luyen;
- co validation set de toi uu;
- co test set de danh gia cuoi;
- co mo hinh phan lop;
- co mo hinh du doan.

Diem cai tien cua de tai la khong dung mot model duy nhat, ma tach thanh 2 nhanh:
- nhanh 1: phan lop do tin cay du lieu;
- nhanh 2: du doan khoang gia bat dong san.

## 2. So do tong the
Dataset goc
-> Tien xu ly va lam sach
-> Cham diem RQS va tao pseudo-label tin cay
-> Chia Training set / Validation set / Test set
-> Train nhanh 1: Confidence Classifier
-> Sinh score tin cay tu nhanh 1
-> Ghep score nay vao bo feature dinh gia
-> Train nhanh 2: Price Interval Model
-> Hieu chinh bang grouped conformal calibration
-> Xuat gia trung tam + can duoi + can tren + muc tin cay

## 3. Nhanh 1 - Confidence Classifier
### Input
- support_volume_score
- support_quality_score
- support_completeness_score
- support_anchor_share
- support_source_count
- support_volatility
- district_support_count
- province_support_count
- property_type_support_count
- effective_sample_size
- input_completeness_score
- input_iot_signal_count
- input_has_legal_status
- input_has_coordinates
- input_has_furnishing
- local_price_gap_ratio
- self_collected_hint

### Output
- nhan A/B/C/D
- score tin cay uoc luong

### Candidate models
- EntropyTree
- GiniTree
- HybridConfidenceForest

### Rule chon model
- chia 70/15/15
- train tren training set
- chon model theo macro F1 tren validation set
- danh gia cuoi tren test set

## 4. Nhanh 2 - Price Interval Model
### Input
- feature BDS co cau truc
- feature vi tri
- feature IoT
- RQS va trust features
- score tu nhanh classifier tin cay
- probability A/B/C/D cua nhanh classifier

### Output
- P_mid
- P_low
- P_high

### Candidate models
- QualityWeightedRandomForest
- ReliabilityAwareGradientBoosting
- ConfidenceWeightedXGBoost

### Rule chon model
- train tren training set
- chon theo validation MAE
- danh gia cuoi bang test MAE / RMSE / R2

## 5. Calibration
Sau khi co quantile interval, he thong tiep tuc:
- tinh residual ratio tren validation set;
- gom residual theo trust band A/B/C/D;
- lay q90 cho tung band;
- mo rong/thu hep khoang gia theo band residual nay.

Day la grouped conformal calibration theo trust band.

## 6. Tai sao cach nay phu hop voi de tai
- phu hop logic giao trinh: phan lop truoc, danh gia sau.
- co validation set dung nghia, khong gom chung vao train.
- co mo hinh dang cay de giai thich de hieu voi GVHD.
- co nhanh hoi quy rieng de dinh gia, khong tron vai tro.
- co calibration de tranh qua tu tin tren du lieu bat dong san online.

## 7. Cach trinh bay ngan gon truoc hoi dong
"Nhom em xay dung quy trinh train ML 2 tang. Tang thu nhat la mo hinh phan lop do tin cay du lieu theo tinh than ID3/C4.5/CART, duoc train voi Training set, Validation set va Test set de sinh nhan A/B/C/D. Tang thu hai la mo hinh du doan khoang gia, nhan them output tu tang 1 nhu mot phan cua bo dac trung. Sau cung nhom em dung quantile interval va grouped conformal calibration de hieu chinh can duoi va can tren theo trust band."
