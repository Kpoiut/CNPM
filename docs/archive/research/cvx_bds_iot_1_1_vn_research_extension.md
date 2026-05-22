# CVX-BDS-IoT 1.1-VN Research Extension

## 1. Dinh huong
Tai lieu nay khong sao chep nguyen van mot standard ben ngoai de gan ten cho do an. Nhom ke thua tinh than tu nhieu chuan ve valuation, data quality va trustworthy AI, sau do chuyen hoa thanh mot standard noi bo phu hop voi bai toan du doan gia bat dong san tai Viet Nam. Phien ban 1.1-VN la ban mo rong theo huong nghien cuu cua project, nhan manh 4 diem moi:
- tach ro market signal va market truth;
- co Evidence Tier E1-E5 va Record Quality Score (RQS) cho tung ho so;
- huan luyen ML theo trong so chat luong du lieu, khong hoc ngang nhau tren moi ban ghi;
- tao khoang gia co gian theo Neff, anchor share va median RQS, thay vi dung interval co dinh.

## 2. Nguyen ly cot loi
- Gia rao ban online khong duoc coi mac dinh la gia thi truong thuc.
- Moi ban ghi phai co diem tin cay rieng truoc khi train va truoc khi dinh gia.
- Du lieu khu vuc khong danh gia bang so luong thuan, ma bang so luong hieu dung Neff.
- He thong chi duoc xep hang tin cay cao khi co anchor E1/E2 va tap doi chieu khong bi thien lech don nguon.
- Ket qua cuoi cung phai la khoang gia + diem tin cay + giai thich.

## 3. Evidence Tier cua project
- E1: du lieu field-based/self-collected da verified, co nguoi xac minh va co bang chung.
- E2: du lieu verified, co source traceability manh va co it nhat mot kieu xac minh doc lap.
- E3: public record da co mot phan validation va co bo sung hien truong/IoT/chung cu.
- E4: public listing co traceability nhung market anchor yeu.
- E5: du lieu it chung cu, thieu truy vet hoac thieu xac minh.

## 4. Record Quality Score (RQS)
RQS duoc tinh theo cong thuc noi bo cua project:

RQS = 0.25 * P + 0.25 * V + 0.20 * M + 0.15 * C + 0.15 * T - Penalty

Trong do:
- P: provenance score
- V: verification score
- M: market-anchor score
- C: completeness score
- T: timeliness score
- Penalty: phat do thieu du lieu, sai logic, outlier va thien lech nguon

Luot chan cung:
- E4 thi RQS toi da 6.5
- E5 thi RQS toi da 4.0

## 5. Case Confidence Score (CS)
CS cua mot ca dinh gia duoc tinh theo 3 thanh phan:

CS = 0.35 * S_volume + 0.40 * S_quality + 0.25 * S_completeness

Cai tien so voi ban co ban:
- S_volume su dung Neff thay cho raw count
- S_quality la weighted mean cua RQS, trong so theo similarity, timeliness, evidence weight
- S_completeness ket hop ca ho so dau vao va tap doi chieu

## 6. Luat chan nghien cuu bo sung
Project bo sung them 3 luat chan de tranh ao giac do tin cay:
- khong co E1/E2 thi CS bi cap toi da 7.0
- Neff < 30 thi CS bi cap toi da 5.5
- median RQS < 5 thi ket qua chi duoc xuat o che do reference_only
- neu chi co mot nguon goc thong tin va khong co anchor thi CS bi cap xuong muc thap hon nua

## 7. Cai tien thuat toan train ML
Project khong dung raw XGBoost/GradientBoosting theo cach mac dinh. Quy trinh train duoc tach thanh 2 nhanh:
- Nhanh 1: classifier dang cay de hoc nhan do tin cay A/B/C/D theo tinh than ID3/C4.5/CART.
- Nhanh 2: regressor trust-aware de du doan gia trung tam va khoang gia.

Trong nhanh 1, project so sanh:
- EntropyTree
- GiniTree
- HybridConfidenceForest

Trong nhanh 2, cac mo hinh duoc bien doi thanh nhung bien the nghien cuu:
- QualityWeightedRandomForest: RandomForest hoc voi sample weight dua tren RQS va evidence.
- ReliabilityAwareGradientBoosting: GradientBoosting hoc voi training weight thay doi theo chat luong ban ghi.
- ConfidenceWeightedXGBoost: XGBoost dung sample weight, objective robust hon (`reg:pseudohubererror`), va regularization manh hon de giam anh huong outlier va listing-biased labels.
- Quantile interval heads: them 2 dau ra lower/upper bang GradientBoosting loss=quantile de tao khoang gia.
- Grouped conformal calibration: hieu chinh residual theo trust band A/B/C/D sau khi co quantile interval.

## 8. Feature engineering bo sung
Ngoai cac feature bat dong san va IoT, project them cac feature tin cay:
- rqs
- provenance_score
- verification_score
- market_anchor_score
- timeliness_score
- training_weight
- evidence_weight
- anchor_flag_feature
- has_iot_signal_feature

Nghia la mo hinh khong chi hoc tu dac trung tai san, ma con hoc tu do manh/yeu cua bang chung du lieu.

## 9. He thong interval moi
Khoang gia khong co dinh theo MAE nua. Thay vao do, no duoc co gian theo:
- do sai so co ban cua mo hinh
- do bien dong gia local
- trust gap
- Neff
- anchor share
- median RQS

Band muc tieu:
- A: 3-6%
- B: 5-8%
- C: 8-12%
- D: 12-18% hoac reference_only

## 10. Dong gop rieng cua de tai
- Bien bai toan quality control du lieu thanh mot phan he rieng trong he thong.
- Dua quality profile vao ca train va predict, thay vi chi dung cho giao dien giai thich.
- Bien XGBoost thanh bien the confidence-weighted thay vi dung raw default.
- Dua classifier dang cay vao quy trinh train de tao mot nhanh "hoc do tin cay" dung tinh than giao trinh.
- Dung Neff va rule caps de ngan he thong "qua tu tin" tren du lieu online.
- Phu hop hon voi boi canh Viet Nam, noi ma du lieu listing bi phan manh, thieu giao dich neo va hay co sai lech gia.
- Tao Research Lab mode de giai thich toan canh quy trinh train cho nguoi moi, phuc vu bao ve de tai va demo.
