# BAO CAO TIEN DO 80% DE TAI AVM BAT DONG SAN

## 1. Thong tin chung

- Ten de tai: Nghien cuu va xay dung he thong du doan gia bat dong san theo khu vuc bang hoc may ket hop du lieu IoT tu dien thoai thong minh.
- San pham bao cao: He thong AVM (Automated Valuation Model - mo hinh dinh gia tu dong) cho bat dong san, co du doan gia, khoang gia, muc do tin cay du doan, do tin cay du lieu va giai thich ket qua.
- Moc tien do: 80% khung de tai.
- Pham vi du lieu hien tai: 6 quan/huyen trong hai thanh pho, gom Ha Noi (Quan Cau Giay, Quan Thanh Xuan, Quan Dong Da) va TP. Ho Chi Minh (Quan 7, Quan Binh Thanh, Quan Tan Binh).
- Cong nghe: FastAPI (framework Python de xay dung API), SQLite (co so du lieu dang file), React/Vite (frontend web), scikit-learn (thu vien hoc may), XGBoost (thu vien gradient boosting co regularization), Recharts/Leaflet (bieu do va ban do).
- Nguon doc de lap bao cao: ma nguon trong project, file `docs/archive/research/bao_cao_tien_do_11_tuan_day_du_2026.md`, metadata model trong `models/`, audit JSON trong `reports/`, va SQLite live DB `real_estate_avm.db`.

## 2. Tom tat dieu hanh

De tai da chuyen tu mot bai toan "du doan mot con so gia" thanh mot he thong AVM (Automated Valuation Model - mo hinh dinh gia tu dong) co 4 lop ket qua:

1. Gia du doan trung tam: gia tri tham chieu cua bat dong san theo du lieu hien co.
2. Khoang gia: can duoi va can tren, mo rong hoac thu hep theo muc do tin cay.
3. Muc do tin cay du doan: diem P-CONF (Prediction Confidence - do tin cay cua ket qua du doan), chu yeu dua tren so mau so sanh gan giong va do on dinh cua cum du lieu.
4. Do tin cay du lieu: diem D-TRUST/RQS (Data Trust/Record Quality Score - do tin cay cua ban ghi du lieu), chu yeu dua tren truy vet nguon, xac minh, day du truong va do moi cua du lieu.

Diem manh cua de tai la khong xem gia rao ban online la gia thi truong dung tuyet doi. Gia rao ban chi duoc xem la market signal (tin hieu thi truong), con market truth (su that thi truong, thuong la gia giao dich thuc) van can duoc xac minh bang nguon tot hon. Vi vay he thong khong chi hoc gia, ma con danh gia xem du lieu co du dang tin cay de hoc va de suy luan hay khong.

Tai moc 80%, he thong da co:

- Database live (co so du lieu dang van hanh): 3,269 ban ghi active/trainable trong 6 quan, gom 3,000 public_collected (du lieu cong khai) va 269 self_collected (du lieu tu thu thap).
- Evidence Tier (cap do bang chung) trong live DB: E1 = 91, E2 = 2,603, E3 = 523, E4 = 39, E5 = 13.
- Provenance chains (chuoi truy vet nguon): 9,900 buoc truy vet.
- IoT fields (truong cam bien/thuc dia): 3,269 ban ghi co it nhat mot tin hieu IoT hoac truong hien truong lien quan theo query live DB.
- Matched pairs (cap ghep cung-cau): 21,206 cap, trong do 9,189 cap duoc danh dau la potential match (co kha nang phu hop).
- Pipeline ML 2 tang (quy trinh hoc may hai nhanh): tang 1 chon confidence classifier (mo hinh phan lop do tin cay), tang 2 chon price regressor (mo hinh hoi quy du doan gia).
- Research Lab (khu giai thich thuat toan): co cac nhom AVM-PREDICT, P-CONF, D-TRUST, IMPACT, Calibration va Training Pipeline.
- Frontend (giao dien): Prediction, DataQuality, ResearchLab, MapExplorer, Dashboard, DataSources, RecordExplorer, ExplainabilityDashboard.

Can viet trung thuc: snapshot co metric tot nhat da co MAPE = 14.20% tren `metadata_20260503_185414.json`, trong khi model retrain moi nhat `metadata_20260514_110830.json` co MAPE = 45.18%. Vi vay trong bao cao 80% khong duoc tron hai so lieu nay. Cach trinh bay dung la: snapshot 03/05/2026 chung minh pipeline co kha nang dat sai so tot trong mot cau hinh du lieu on dinh; retrain 14/05/2026 chung minh live data da mo rong va pipeline chay duoc, nhung can 20% con lai de on dinh lai metric sau khi thay doi chat luong/tier du lieu.

## 3. Quy uoc thuat ngu bat buoc

Bang nay dung de tranh bi bat be ve tu ngu. Trong bao cao, cac thuat ngu tieng Anh deu co giai nghia tieng Viet.

| Thuat ngu | Giai nghia dung trong de tai |
|---|---|
| AVM (Automated Valuation Model) | Mo hinh dinh gia bat dong san tu dong bang du lieu va thuat toan. |
| ML (Machine Learning) | Hoc may, ky thuat cho may hoc quan he tu du lieu thay vi lap trinh tung cong thuc co dinh. |
| Regressor (mo hinh hoi quy) | Mo hinh du doan gia tri lien tuc, o day la gia bat dong san. |
| Classifier (mo hinh phan lop) | Mo hinh gan nhan roi rac, o day la nhan tin cay A/B/C/D. |
| Feature (dac trung dau vao) | Bien duoc dua vao mo hinh, vi du dien tich, toa do, RQS, evidence tier. |
| Label (nhan dau ra) | Gia tri muc tieu de mo hinh hoc, vi du gia nha hoac nhan A/B/C/D. |
| Evidence Tier (cap bang chung E1-E5) | He phan cap do manh/yeu cua bang chung du lieu, E1 manh nhat, E5 yeu nhat. |
| RQS (Record Quality Score) | Diem chat luong tung ban ghi, tinh tu provenance, verification, market anchor, completeness, timeliness va penalty. |
| CS (Case Confidence Score) | Diem tin cay cua mot ca dinh gia, gom volume, quality va completeness. |
| P-CONF (Prediction Confidence) | Muc do tin cay cua ket qua du doan gia, chu yeu dua tren so mau gan giong va do on dinh cua tap comparable. |
| D-TRUST (Data Trust) | Do tin cay cua du lieu dau vao va du lieu ho tro, chu yeu dua tren truy vet nguon, xac minh va tier bang chung. |
| Neff (Effective Sample Size) | So mau hieu dung sau khi giam trong so cac mau kem tin cay hoac it tuong dong. |
| Comparable (bat dong san so sanh) | Bat dong san tuong dong dung de doi chieu va neo gia. |
| SHAP (SHapley Additive exPlanations) | Phuong phap giai thich dong gop cua tung dac trung vao du doan. |
| Conformal Calibration (hieu chinh conformal) | Cach hieu chinh khoang du doan bang residual tren validation set de tranh qua tu tin. |
| Quantile Regression (hoi quy phan vi) | Mo hinh du doan can duoi/can tren cua phan phoi gia, khong chi du doan gia trung binh. |
| MAPE (Mean Absolute Percentage Error) | Sai so phan tram tuyet doi trung binh, dung de doc sai so theo ty le %. |
| MAE (Mean Absolute Error) | Sai so tuyet doi trung binh, don vi VND. |
| RMSE (Root Mean Squared Error) | Can bac hai trung binh binh phuong sai so, phat nang cac loi lon. |
| R2 (R-squared) | Ty le bien thien cua gia duoc mo hinh giai thich, cang gan 1 cang tot. |
| SDEV (Supply-Demand Equilibrium Valuation) | Thuat toan noi bo uoc luong vung gia chap nhan tu tin hieu cung (ask/listing) va cau (bid/buyer requirement). |
| Overasking (rao cao hon gia chap nhan) | Hien tuong nguoi ban dat gia rao cao hon kha nang giao dich thuc. |
| Provenance (truy vet nguon goc) | Chuoi thong tin cho biet ban ghi duoc thu thap, parse, validate, enrich va verify ra sao. |

## 4. Van de nghien cuu va ly do chon huong tiep can

Van de trung tam cua de tai khong phai chi la "chon RandomForest hay XGBoost", ma la "du lieu gia bat dong san co dang tin hay khong". Neu gia rao ban tren website bi thoi phong, neo gia hoac thieu xac minh, mo hinh hoc may co the hoc sai. Khi do mo hinh co ve chinh xac ve mat so hoc nhung khong dang tin ve mat thi truong.

Vi vay de tai dat 4 nguyen tac:

1. Khong mac dinh gia rao ban la gia giao dich thuc.
2. Moi ban ghi phai co diem chat luong rieng truoc khi dua vao train (huan luyen mo hinh).
3. Ket qua du doan phai la khoang gia va muc tin cay, khong chi la mot diem gia.
4. He thong phai giai thich duoc tai sao gia cao/thap va tai sao do tin cay cao/thap.

Diem moi cua de tai la tach ro:

- Muc do tin cay du doan: du doan nay co du mau gan giong khong.
- Do tin cay du lieu: ban ghi va tap so sanh co bang chung, nguon va xac minh khong.

Hai khai niem nay khong trung nhau. Mot ban ghi co nguon tot van co the cho du doan tin cay thap neu khu vuc do co qua it mau gan giong. Nguoc lai, mot khu vuc co nhieu mau nhung neu toan la listing kem truy vet thi do tin cay du lieu van bi ha.

## 5. Kien truc he thong tai moc 80%

He thong hien duoc to chuc thanh 5 lop:

1. Lop thu thap du lieu: scraper (bo thu thap website), manual entry (nhap tay), field survey (khao sat thuc dia), smartphone sensor capture (ghi nhan tu dien thoai).
2. Lop quan tri nguon va chat luong: Evidence Tier E1-E5, RQS, provenance chain, duplicate check (kiem tra trung lap), outlier check (kiem tra gia bat thuong).
3. Lop hoc may va dinh gia: P-CONF classifier, AVM-PREDICT regressor, quantile interval, conformal calibration, comparable engine, adjustment ledger.
4. Lop API/backend: FastAPI endpoints cho predict, valuation v2, pipeline, data quality, research lab, explainability va SDEV.
5. Lop frontend: giao dien cho nguoi dung va admin, gom Prediction, DataQuality, ResearchLab, MapExplorer, ExplainabilityDashboard va DataSources.

So do logic:

```text
Du lieu goc
-> Lam sach va chuan hoa
-> Evidence Tier E1-E5
-> RQS cho tung ban ghi
-> P-CONF classifier cho do tin cay du doan
-> AVM-PREDICT regressor cho gia trung tam
-> Quantile heads + grouped conformal calibration cho khoang gia
-> Valuation 9-gate + adjustment ledger
-> Output: gia, khoang gia, confidence, warning, comparables, giai thich
```

## 6. Bang chung du lieu hien co

### 6.1 Live DB ngay 14/05/2026

So lieu doc truc tiep tu SQLite `real_estate_avm.db`:

| Chi so | Gia tri | Cach hieu |
|---|---:|---|
| Tong ban ghi trong `properties` | 3,560 | Bao gom ca archived (da luu tru/khong active). |
| Ban ghi active | 3,269 | Ban ghi dang duoc dung trong he thong. |
| Ban ghi trainable basic | 3,269 | Co price, area_m2, price_per_m2 hop le. |
| Public collected | 3,000 | Du lieu cong khai tu website/nguon ngoai. |
| Self collected | 269 | Du lieu tu nhap/khao sat/noi bo. |
| Verified | 2,686 | Ban ghi co verification_status = verified. |
| Pending | 583 | Ban ghi dang cho xac minh. |
| Co source_url | 3,080 | Co duong dan nguon ro rang. |
| Provenance chain steps | 9,900 | Tong so buoc truy vet nguon trong bang provenance_chains. |
| Matched pairs | 21,206 | Cap ghep listing-buyer trong bang matched_pairs. |
| Potential matched pairs | 9,189 | Cap ghep co is_potential_match = 1. |

Phan bo theo quan:

| Khu vuc | So ban ghi |
|---|---:|
| Ha Noi - Quan Thanh Xuan | 599 |
| Ha Noi - Quan Cau Giay | 584 |
| TP. Ho Chi Minh - Quan Tan Binh | 539 |
| Ha Noi - Quan Dong Da | 521 |
| TP. Ho Chi Minh - Quan 7 | 513 |
| TP. Ho Chi Minh - Quan Binh Thanh | 513 |

Phan bo Evidence Tier (cap bang chung) trong live DB:

| Tier | So ban ghi | Giai nghia |
|---|---:|---|
| E1 | 91 | Bang chung rat cao. |
| E2 | 2,603 | Bang chung cao, co xac minh/truy vet manh. |
| E3 | 523 | Bang chung trung binh, co public source va mot phan validation. |
| E4 | 39 | Bang chung thap, co trace nhung anchor yeu. |
| E5 | 13 | Bang chung rat thap hoac nguon can canh bao. |

Ghi chu quan trong: bang `buyer_requirements` trong live DB hien tai = 0, trong khi bao cao cu nhac den 568/600 buyer requirements. Vi vay bao cao 80% chi nen noi "matched_pairs da ton tai 21,206 cap" va "SDEV can tai nap hoac dong bo lai buyer requirements truoc bao cao cuoi", khong nen khang dinh live DB hien co 568 buyer requirements neu khong co snapshot kem theo.

### 6.2 Snapshot model tot va snapshot moi nhat

| Metadata | Vai tro trong bao cao | Records/profile | Best model | Test MAE | Test MAPE | Test R2 |
|---|---|---:|---|---:|---:|---:|
| `metadata_20260503_185414.json` | Snapshot metric tot de chung minh pipeline hoc duoc | 3,037 | ReliabilityAwareGradientBoosting | 804,022,708 VND | 14.20% | 0.765 |
| `metadata_20260504_144753.json` | Snapshot can bang hon ve R2/MAE | 3,231 | ReliabilityAwareGradientBoosting | 776,510,801 VND | 16.09% | 0.845 |
| `metadata_20260514_105910.json` | Retrain gan nhat truoc ban cuoi | 3,269 | ReliabilityAwareGradientBoosting | 3,356,046,060 VND | 38.38% | 0.678 |
| `metadata_20260514_110830.json` | Retrain moi nhat sau cleanup | 3,269 | ReliabilityAwareGradientBoosting | 3,821,908,079 VND | 45.18% | 0.598 |

Cach giai thich de khong bi bat be:

- Khong noi "model hien tai dat MAPE 14.2%" neu dang chay latest model 14/05/2026.
- Noi dung dung: "Snapshot on dinh ngay 03/05/2026 dat MAPE 14.2%; retrain moi nhat ngay 14/05/2026 sau khi thay doi data quality/tier cho MAPE cao hon, nen 20% con lai se tap trung on dinh lai bo train, giam nhieu label va chon model registry phu hop."
- Viec metric xau di khong phai that bai cua de tai, ma la bang chung he thong co audit trung thuc: khi du lieu/tier thay doi, metric duoc bao cao lai thay vi che giau.

## 7. Chuan noi bo CVX-BDS/IoT 1.1-VN

De tai xay dung mot chuan noi bo ten CVX-BDS/IoT 1.1-VN Research Extension. Chuan nay khong phai chuan quoc te co san, ma la bien the rieng cua do an, ke thua tinh than tu valuation (dinh gia), data quality (chat luong du lieu) va trustworthy AI (AI dang tin cay).

Bon diem chinh cua chuan:

1. Tach market signal (tin hieu thi truong) va market truth (gia tri thi truong da xac minh).
2. Gan Evidence Tier E1-E5 cho moi ban ghi.
3. Tinh RQS (Record Quality Score - diem chat luong ban ghi) de tao sample weight (trong so mau khi train).
4. Sinh khoang gia theo Neff (Effective Sample Size - so mau hieu dung), anchor share (ty le mau E1/E2) va median RQS (trung vi diem chat luong).

### 7.1 Evidence Tier E1-E5

| Tier | Goc y tuong | Bien the trong de tai | Ly do phu hop |
|---|---|---|---|
| E1 | Bang chung manh trong dinh gia thuc dia | Field/self-collected da verified, co nguoi xac minh va bang chung | Bat dong san Viet Nam thieu giao dich cong khai, nen bang chung thuc dia la neo quan trong. |
| E2 | Nguon co xac minh doc lap | Verified record co source traceability manh | Phu hop khi co URL/source/screenshot/nguoi xac minh. |
| E3 | Public record co validation mot phan | Listing cong khai co source va IoT/anh/field context | Chap nhan listing nhu tin hieu, khong coi la su that tuyet doi. |
| E4 | Public signal yeu | Listing co trace nhung anchor yeu | Van dung de tham khao, nhung trong so thap. |
| E5 | Du lieu it bang chung | Thieu truy vet hoac can canh bao manh | Giam nguy co mo hinh hoc theo du lieu nhieu. |

### 7.2 RQS - Record Quality Score

Cong thuc trong code `quality_assessment.py`:

```text
RQS = 0.25 * P + 0.25 * V + 0.20 * M + 0.15 * C + 0.15 * T - Penalty
```

Trong do:

- P (Provenance score - diem truy vet nguon): co source_name, source_url, thoi diem crawl, screenshot, nguoi thu thap.
- V (Verification score - diem xac minh): verified/pending/unverified, co verified_by, verified_at, verification_note.
- M (Market anchor score - diem neo thi truong): do manh cua evidence tier, co price_per_m2, phap ly, IoT.
- C (Completeness score - diem day du): co du property_type, province, district, area, price, legal_status, toa do, image/evidence.
- T (Timeliness score - diem moi du lieu): du lieu cang moi cang diem cao.
- Penalty (diem phat): thieu gia, thieu dien tich, outlier gia/m2, khong co source_url/screenshot, thieu toa do.

Luat chan:

- E1 cap toi da 10.0.
- E2 cap toi da 9.0.
- E3 cap toi da 8.0.
- E4 cap toi da 6.5.
- E5 cap toi da 4.0, tru truong hop public auction asset evidence (bang chung dau gia cong khai) duoc xu ly dac biet.

### 7.3 Training weight - trong so mau khi train

Cong thuc trong code:

```text
training_weight = clamp(((RQS / 10) ^ 1.45) * (0.65 + evidence_weight) * strong_tier_multiplier, 0.15, 3.0)
```

Y nghia:

- Mau co RQS cao va evidence weight cao duoc hoc manh hon.
- Mau co RQS thap van co the tham gia train, nhung anh huong bi giam.
- He thong khong xoa het du lieu yeu, ma dung chung voi trong so thap de phu hop boi canh Viet Nam con thieu du lieu giao dich that.

### 7.4 CS - Case Confidence Score

Cong thuc trong code:

```text
CS = 0.35 * S_volume + 0.40 * S_quality + 0.25 * S_completeness
```

Trong do:

- S_volume (diem do sau mau): tinh tu Neff thay vi raw count.
- S_quality (diem chat luong tap so sanh): trung binh co trong so cua RQS trong tap comparable.
- S_completeness (diem day du): ket hop ho so dau vao va tap so sanh.

Luat chan cua CS:

- Khong co E1/E2 trong tap so sanh: cap toi da 7.0.
- Neff < 30: cap toi da 5.5.
- Median RQS < 5: output_mode = reference_only (chi nen xem tham khao).
- Chi co mot nguon va khong co anchor: cap xuong thap hon de tranh thien lech don nguon.

### 7.5 Neff - Effective Sample Size

Cong thuc:

```text
Neff = sum(alpha_i * evidence_weight_i * (RQS_i / 10))
```

Trong do:

- alpha_i = similarity_i * time_weight_i * evidence_weight_i * quality_weight_i.
- similarity_i (do tuong dong) tinh tu vi tri, dien tich va thong tin bat dong san.
- time_weight_i (trong so thoi gian) cao hon voi du lieu moi.
- evidence_weight_i (trong so bang chung) lay tu E1-E5.
- RQS_i la diem chat luong ban ghi thu i.

Bang diem volume:

| Neff | Diem volume | Cach hieu |
|---:|---:|---|
| >= 800 | 10.0 | Tap mau hieu dung rat manh. |
| >= 300 | 8.0 | Tap mau tot. |
| >= 100 | 6.0 | Dat muc toi thieu on. |
| >= 30 | 4.5 | Co mau nhung con han che. |
| >= 10 | 2.8 | Chi tham khao co dieu kien. |
| < 10 | 1.2 | Can canh bao manh. |

## 8. Danh muc thuat toan can trinh bay

Phan nay gom tat ca thuat toan xuat hien trong Research Lab, backend va pipeline train.

### 8.1 AVM-PREDICT - thuat toan du doan gia

Muc tieu: du doan fair_market_value (gia thi truong hop ly), quick_sale (gia ban nhanh), recommended_listing (gia niem yet de xuat), optimistic_ask (gia ky vong cao), va range_low/range_high (khoang gia).

Nguon goc:

- Goc thu 1: hedonic pricing (dinh gia theo dac trung tai san), tuc gia duoc giai thich bang dien tich, vi tri, phong ngu, phap ly va dac trung tai san.
- Goc thu 2: tree-based ensemble regression (hoi quy bang tap cay quyet dinh), gom RandomForest, GradientBoosting va XGBoost.
- Goc thu 3: sales comparison approach (phuong phap so sanh bat dong san tuong dong) trong dinh gia bat dong san.

Bien the trong de tai:

- Them quality features (dac trung chat luong du lieu) nhu RQS, provenance_score, verification_score, evidence_weight.
- Them output P-CONF tu nhanh 1 vao feature set cua nhanh 2.
- Khong train ngang nhau tren moi ban ghi, ma dung sample_weight dua tren RQS va evidence tier.
- Sau khi co gia trung tam, he thong tao khoang gia bang quantile interval va conformal calibration.
- Sau khi co fair_market_value, valuation engine sinh 4 scenario: quick_sale, recommended_listing, optimistic_ask va confidence range.

Ly do phu hop:

- Bat dong san la du lieu dang bang (tabular data - du lieu co cot dong ro rang), tree-based models phu hop hon deep learning phuc tap khi du lieu chua qua lon.
- Gia rao o Viet Nam co nhieu, nen them RQS/evidence weight giup giam tac dong cua ban ghi yeu.
- Nguoi dung can khoang gia va giai thich, khong chi mot con so.

Pseudo-code:

```text
Input: ho_so_bat_dong_san
features = FeatureEngineer(ho_so_bat_dong_san)
support = ComparableEngine.find_comparables(ho_so_bat_dong_san)
quality = D_TRUST.assess(support, ho_so_bat_dong_san)
p_conf = P_CONF.predict(quality_features)
price_mid = ReliabilityAwareGradientBoosting.predict(features + p_conf)
interval = QuantileHeads + GroupedConformalCalibration(price_mid, p_conf)
valuation = AdjustmentLedger.apply(price_mid, support, legal, environment, geometry)
Output: price_mid, price_low, price_high, confidence_grade, warnings, comparables
```

### 8.2 P-CONF - muc do tin cay du doan

Muc tieu: tra loi cau hoi "du doan nay co du co so thong ke va du mau gan giong khong".

Nguon goc:

- ID3 (Iterative Dichotomiser 3 - cay quyet dinh dung entropy/information gain) va C4.5 (cay quyet dinh mo rong tu ID3) truyen cam hung cho EntropyTree.
- CART (Classification and Regression Tree - cay phan lop/hoi quy dung Gini impurity) truyen cam hung cho GiniTree.
- RandomForestClassifier (rung cay phan lop) truyen cam hung cho HybridConfidenceForest.

Bien the trong de tai:

- Nhan A/B/C/D khong chi dua vao RQS, ma dua vao sample-depth gate (nguong kiem soat so mau gan giong).
- Muc A yeu cau effective_sample_size >= 800, good quality, multi-source support va stable market.
- Muc B yeu cau effective_sample_size >= 300 va chat luong chap nhan duoc.
- Muc C ap dung khi effective_sample_size >= 100, hoac >= 30 neu support_quality du.
- Muc D ap dung khi sparse support (tap ho tro qua mong).
- Candidate models: EntropyTree, GiniTree, HybridConfidenceForest.
- Chon model theo macro F1 (F1 trung binh theo lop, tranh thien lech lop lon) tren validation set.

Dac trung dau vao cua P-CONF:

| Nhom | Feature |
|---|---|
| Volume | support_volume_score, district_support_count, province_support_count, property_type_support_count, effective_sample_size |
| Quality | support_quality_score, support_anchor_share, support_source_count, support_volatility |
| Input completeness | input_completeness_score, input_iot_signal_count, input_has_legal_status, input_has_coordinates, input_has_furnishing |
| Risk hint | local_price_gap_ratio, self_collected_hint |

Pseudo-code:

```text
if Neff >= 800 and support_quality >= 7.0 and completeness >= 6.5 and source_count >= 2 and volatility <= 0.35:
    label = A
elif Neff >= 300 and support_quality >= 6.0 and source_count >= 2:
    label = B
elif Neff >= 100 or (Neff >= 30 and support_quality >= 5.5):
    label = C
else:
    label = D
```

Ly do phu hop:

- Giao vien co the hoi "vi sao du lieu co nguon tot ma tin cay du doan van thap". Cau tra loi: vi P-CONF do kha nang du doan, nen so mau gan giong la dieu kien chinh.
- Cac model cay de giai thich bang rule, phu hop bao ve hoc thuat.
- Tach P-CONF khoi D-TRUST giup khong lan lon giua "du lieu co nguon" va "du doan co chac".

### 8.3 D-TRUST - do tin cay du lieu

Muc tieu: tra loi cau hoi "ban ghi nay va tap support co dang tin khong".

Nguon goc:

- Data quality scoring (cham diem chat luong du lieu) trong cac he thong du lieu.
- Provenance tracking (truy vet nguon goc) trong data governance (quan tri du lieu).
- Evidence weighting (trong so bang chung) trong dinh gia va nghien cuu thuc nghiem.

Bien the trong de tai:

- Dinh nghia Evidence Tier E1-E5 rieng cho thi truong bat dong san Viet Nam.
- Tinh RQS theo 5 thanh phan P/V/M/C/T va Penalty.
- Tinh CS cho ca mot ca dinh gia bang volume, quality va completeness.
- Ap dung caps (luat chan) de khong cho he thong qua tu tin khi khong co E1/E2, Neff thap hoac single-source bias.

Ly do phu hop:

- Thi truong Viet Nam thieu gia giao dich cong khai, nen phai danh gia nguon va bang chung truoc khi tin vao gia.
- Listing online co the bi overasking, nen RQS/Evidence Tier lam bo loc nhieu.
- D-TRUST la lop giai trinh, giup hoi dong thay duoc he thong khong "hoc may mu quang".

### 8.4 EntropyTree

Goc thuat toan:

- EntropyTree dua tren entropy (do hon loan thong tin) va information gain (do giam entropy khi tach du lieu), tu tuong cua ID3/C4.5.

Bien the trong de tai:

- Dung `DecisionTreeClassifier(criterion="entropy")`.
- Gioi han max_depth, min_samples_split va min_samples_leaf de tranh overfitting (hoc qua khit).
- Dung class_weight="balanced" de lop it mau khong bi bo qua.

Ly do phu hop:

- De giai thich bang tree rules.
- Dung lam baseline cho classifier do tin cay A/B/C/D.

### 8.5 GiniTree

Goc thuat toan:

- GiniTree dua tren Gini impurity (do pha tron nhan trong mot nut), thuong gan voi CART.

Bien the trong de tai:

- Dung `DecisionTreeClassifier(criterion="gini")`.
- Tang max_depth len 7 va min_samples co kiem soat.
- So sanh voi EntropyTree de xem criterion nao phu hop hon voi label P-CONF.

Ly do phu hop:

- CART la thuat toan co tinh giao trinh, de bao ve.
- GiniTree giup doi chieu ket qua voi EntropyTree, tranh chi co mot cay.

### 8.6 HybridConfidenceForest

Goc thuat toan:

- RandomForestClassifier (rung cay phan lop) la ensemble (tap hop nhieu mo hinh) cua nhieu decision trees (cay quyet dinh), dung bagging (lay mau bootstrap va tong hop nhieu cay).

Bien the trong de tai:

- Dung 180 trees, max_depth = 9, min_samples_split = 16, min_samples_leaf = 6.
- Dung class_weight="balanced_subsample" de can bang lop trong tung bootstrap sample.
- Dung lam ung vien on dinh hon EntropyTree/GiniTree.

Ly do phu hop:

- Neu cay don le de bi nhieu, forest giup on dinh hon.
- Van co the trich tree_rules dai dien de giai thich trong Research Lab.

### 8.7 QualityWeightedRandomForest

Goc thuat toan:

- RandomForestRegressor (rung cay hoi quy) du doan gia tri lien tuc bang trung binh cua nhieu cay hoi quy.

Bien the trong de tai:

- Dung sample_weight tu RQS/evidence tier thay vi moi mau co trong so bang nhau.
- Dung max_features="sqrt" va bootstrap=True de giam overfitting.
- Dat ten QualityWeightedRandomForest vi diem khac biet la quality-weighted learning (hoc co trong so chat luong).

Ly do phu hop:

- Bat dong san co quan he phi tuyen (non-linear - khong phai duong thang don gian), RandomForest bat duoc tuong tac giua vi tri, dien tich, loai tai san.
- Lam baseline manh cho tabular data.

### 8.8 ReliabilityAwareGradientBoosting

Goc thuat toan:

- GradientBoostingRegressor (hoi quy boosting theo gradient) hoc tuan tu nhieu cay nho, moi cay sua phan sai cua cac cay truoc.

Bien the trong de tai:

- Dung sample_weight theo RQS/evidence.
- Dua P-CONF outputs vao feature set: confidence_stage1_score, confidence_prob_a, confidence_prob_b, confidence_prob_c, confidence_prob_d.
- Dung n_estimators=260, learning_rate=0.05, max_depth=6, subsample=0.85.
- Chon model theo validation MAE, khong chon theo ten thuat toan pho bien.

Ly do phu hop:

- Thuc nghiem trong metadata cho thay day la model tot nhat o nhieu snapshot.
- GradientBoosting co kha nang hoc sai so phuc tap nhung van phu hop du lieu dang bang.
- Co the ket hop sample_weight de giam anh huong cua listing chat luong thap.

### 8.9 ConfidenceWeightedXGBoost

Goc thuat toan:

- XGBoost (Extreme Gradient Boosting - boosting cay co regularization) la gradient boosting toi uu manh, co regularization (rang buoc do phuc tap) de giam overfitting.

Bien the trong de tai:

- Dung sample_weight theo RQS/evidence.
- Dung regularization: reg_alpha, reg_lambda, gamma, min_child_weight va max_delta_step.
- Dung subsample va colsample_bytree de tranh model bi phu thuoc qua muc vao mot tap dac trung.
- Ban tai lieu research cu tung de xuat objective `reg:pseudohubererror` de robust voi outlier; code moi nhat dang dung `reg:squarederror` trong `pipeline.py` sau dot cleanup Round 22.

Ly do phu hop:

- XGBoost la benchmark manh cho du lieu dang bang, nen can co trong nghien cuu de doi chieu.
- Ket qua hien tai khong tot bang GradientBoosting, nen de tai trung thuc khong chon XGBoost chi vi no pho bien.

### 8.10 Quantile interval heads

Goc thuat toan:

- Quantile regression (hoi quy phan vi) du doan cac phan vi cua phan phoi, vi du q10 (can duoi 10%) va q90 (can tren 90%).

Bien the trong de tai:

- Dung GradientBoostingRegressor voi loss="quantile".
- alpha=0.10 cho lower head (dau can duoi).
- alpha=0.90 cho upper head (dau can tren).
- Train voi sample_weight neu model ho tro.

Ly do phu hop:

- Gia bat dong san khong nen tra ve mot diem duy nhat.
- Khoang gia the hien bat dinh va giup nguoi dung khong hieu nham do chinh xac.

### 8.11 Grouped conformal calibration

Goc thuat toan:

- Conformal prediction (du doan conformal) tao khoang du doan dua tren residual (sai so con lai) cua validation set, co tinh chat bao phu tot hon khi du lieu phu hop.

Bien the trong de tai:

- Khong dung mot residual chung cho moi truong hop.
- Nhom residual theo trust band A/B/C/D.
- Tinh ratio_q90 (phan vi 90% cua ti le sai so) va ratio_median (trung vi ti le sai so) cho tung band.
- Neu band khong co mau thi dung fallback ratio.

Pseudo-code:

```text
residual_ratio = abs(y_true - y_pred) / max(abs(y_true), 1)
for band in [A, B, C, D]:
    band_values = residual_ratio where confidence_signal in band
    ratio_q90 = quantile(band_values, 0.90)
    ratio_median = median(band_values)
```

Ly do phu hop:

- Du lieu bat dong san co do tin cay khac nhau theo khu vuc va chat luong nguon.
- Band D khong nen co khoang hep nhu band A.
- Day la lop chong "ao tuong chac chan".

### 8.12 Comparable Engine

Goc thuat toan:

- Sales comparison approach (phuong phap so sanh tai san tuong dong) trong dinh gia bat dong san.
- Similarity scoring (cham diem tuong dong) trong truy xuat thong tin.

Bien the trong de tai:

Comparable Engine co 5 lop:

1. Candidate Retrieval (lay ung vien): tim ban ghi cung khu vuc/loai tai san.
2. Similarity Scoring (cham tuong dong): tinh geo, geometry, access, legal, evidence, recency.
3. Adjustment Normalization (chuan hoa dieu chinh): dieu chinh gia comparable ve tai san muc tieu.
4. Evidence Ranking (xep hang bang chung): uu tien E1/E2 truoc, sau do moi den similarity.
5. Explanation Rendering (giai thich): sinh ly do vi sao chon comparable.

Cong thuc overall similarity:

```text
similarity = 0.20*geo + 0.15*geometry + 0.15*access + 0.15*legal + 0.20*evidence + 0.15*recency
```

Ly do phu hop:

- Bat dong san phu thuoc manh vao vi tri va tai san tuong dong.
- Evidence ranking giup khong de mot comparable rat giong nhung nguon yeu lan at comparable co bang chung manh.

### 8.13 Haversine distance

Goc thuat toan:

- Haversine formula (cong thuc khoang cach tren mat cau) tinh khoang cach giua hai toa do lat/lng (vi do/kinh do).

Bien the trong de tai:

- Dung de tinh geo_proximity_score trong Comparable Engine.
- Dung de tinh distance_to_center va KNN price density trong FeatureEngineer.

Cong thuc tom tat:

```text
a = sin^2(dlat/2) + cos(lat1)*cos(lat2)*sin^2(dlon/2)
c = 2*asin(sqrt(a))
distance = R*c, voi R = 6371 km
```

Ly do phu hop:

- Khoang cach dia ly anh huong truc tiep den gia nha.
- Haversine phu hop khi dung lat/lng.

### 8.14 KNN price density

Goc thuat toan:

- KNN (K-Nearest Neighbors - k hang xom gan nhat) tim cac diem gan nhat theo toa do.

Bien the trong de tai:

- Khong dung KNN lam model chinh.
- Dung KNN de tao feature `knn5_price_density` va `knn10_price_density`, tuc gia/m2 trung binh cua 5 va 10 diem gan nhat.

Ly do phu hop:

- Gia bat dong san co tinh vi mo (micro-market - thi truong cuc bo).
- KNN density giup model biet khu vuc xung quanh dang co mat bang gia nao.

### 8.15 Adjustment Ledger

Goc thuat toan:

- Adjustment ledger (so cai dieu chinh) dua tren logic appraisal (dinh gia) truyen thong: moi yeu to phap ly, vi tri, moi truong, hinh hoc tao mot delta (muc tang/giam).

Bien the trong de tai:

- Co 40+ factor trong `adjustment_registry.py`.
- Tach layer MARKET (anh huong gia thi truong) va FIT (muc do phu hop voi nguoi mua/persona).
- Moi factor co factor_code, group, asset_types, delta_pct_base, confidence_base, rationale_template, evidence_requirement.
- Legal/environment adjustments tu Gate 4 va Gate 6 duoc inject vao Gate 8 valuation.

Ly do phu hop:

- Hoi dong co the hoi "vi sao gia thay doi". Ledger tra loi bang tung dong dieu chinh.
- Tieng noi cua mo hinh va nghiep vu dinh gia duoc ket hop.

### 8.16 9-GATE Pipeline

Muc tieu: dam bao moi request dinh gia di qua chuoi kiem soat co audit trail (dau vet kiem tra).

9 gate:

| Gate | Ten | Vai tro |
|---:|---|---|
| 1 | INTAKE | Kiem tra truong bat buoc, asset type, area. |
| 2 | NORMALIZE | Chuan hoa tinh/thanh, quan/huyen, don vi, toa do. |
| 3 | CLASSIFY | Xac dinh workflow LAND/TOWNHOUSE/APARTMENT va completeness. |
| 4 | LEGAL | Danh gia phap ly, co the BLOCK neu rui ro cao. |
| 5 | GEOMETRY | Phan tich hinh hoc dat, skip voi loai khong can. |
| 6 | ENVIRONMENT | Danh gia rui ro moi truong va yeu to tich cuc. |
| 7 | COMPARABLE | Tim comparable, tier breakdown, anchor count. |
| 8 | VALUATION | Chay valuation engine, adjustment ledger, confidence. |
| 9 | FIT | Lop persona/belief, tach khoi gia thi truong. |

Ly do phu hop:

- Tranh viec request thieu du lieu van cho ra ket qua nhu that.
- Moi gate co PASS/WARN/BLOCK/SKIP va warnings.
- De demo va bao ve vi co audit trail ro rang.

### 8.17 IMPACT - Comparable-SHAP Impact Ledger

Goc thuat toan:

- SHAP (SHapley Additive exPlanations - giai thich dong gop dac trung theo ly thuyet Shapley).
- What-if analysis (phan tich neu-thi): thay doi truong dau vao de xem anh huong gia va tin cay.

Bien the trong de tai:

- Chon comparable pool truoc, sau do dung comparable-pool background cho SHAP.
- Chuyen SHAP value thanh delta % (ty le tac dong), clamp hien thi +/-15% de tranh bieu do qua cuc doan.
- Tach price effect (tac dong len gia) va confidence loss (mat diem tin cay do thieu du lieu).
- Sinh 3 scenario: current, full_info, max_credibility.

Ly do phu hop:

- Nguoi dung khong chi hoi "gia bao nhieu" ma hoi "vi sao".
- Thieu toa do/phap ly co the vua lam gia kho du doan, vua lam giam tin cay; IMPACT tach hai tac dong nay.

### 8.18 SDEV - Supply-Demand Equilibrium Valuation

Goc thuat toan:

- Cung-cau trong kinh te hoc: gia chap nhan nam gan vung giao nhau giua ask (gia nguoi ban muon) va bid (gia nguoi mua san sang tra).

Bien the trong de tai:

- Cluster (cum thi truong) = district x area_band x bedrooms.
- Ask distribution (phan phoi gia rao) lay tu listings.
- Bid distribution (phan phoi ngan sach mua) lay tu buyer requirements neu co.
- Dung q25-q75 (tu phan vi 25% den 75%) de tinh overlap.
- Neu co overlap thi mid_price = midpoint cua vung overlap.
- Neu khong co overlap thi dung weighted compromise (thoa hiep co trong so).
- Tinh acceptance_score tu overlap, ask reliability, bid reliability va data sufficiency.

Cong thuc acceptance_score:

```text
acceptance_score =
    0.35 * overlap_score
  + 0.20 * ask_bid_overlap_score
  + 0.20 * ask_reliability
  + 0.20 * bid_reliability
  + 0.25 * data_sufficiency
```

Ly do phu hop:

- Gia rao ban chua chac la gia giao dich; SDEV bo sung goc nhin nguoi mua.
- Trong bao cao phai ghi ro SDEV hien la proxy (uoc luong thay the) cho market-acceptable price (gia thi truong co the chap nhan), khong phai gia giao dich that.
- Live DB hien co matched_pairs nhung buyer_requirements = 0, nen phan SDEV can duoc trinh bay la module da co va can tai nap demand data trong 20% con lai.

### 8.19 Explainability Dashboard

Muc tieu: hien thi giai thich mo hinh va sai so.

Thanh phan:

- SHAP global feature importance (do quan trong tong the cua dac trung).
- SHAP waterfall (dong gop tung feature cho mot du doan).
- Residual analysis (phan tich sai so con lai).
- Calibration chart (bieu do hieu chinh khoang du doan).
- Model comparison (so sanh MAPE/R2 giua model).
- Prediction distribution (phan phoi sai so).
- SHAP beeswarm (phan bo SHAP theo feature).

Ly do phu hop:

- AVM can minh bach, nhat la khi dung cho quyet dinh tai chinh.
- Giai thich SHAP giup hoi dong thay model khong phai black box (hop den) hoan toan.

### 8.20 Research Lab algorithms

Research Lab trong frontend gom cac track:

| Track | Ten day du | Vai tro |
|---|---|---|
| AVM-PREDICT | Comparable-weighted ML Valuation | Du doan gia + khoang gia. |
| P-CONF | Prediction Confidence Gate | Muc do tin cay du doan A/B/C/D. |
| D-TRUST | Evidence Provenance Scorer | Do tin cay du lieu va provenance. |
| IMPACT | Comparable-SHAP Impact Ledger | Giai thich tac dong gia va mat tin cay. |
| 9-GATE | Locked Pipeline Governance | Kiem soat luong dinh gia tu dau vao den dau ra. |
| Calibration | Grouped conformal by trust band | Hieu chinh khoang gia theo band. |

## 9. Quy trinh train ML 2 tang

### 9.1 So do train

```text
Dataset goc
-> Data cleaning (lam sach)
-> Feature engineering (tao dac trung)
-> RQS + Evidence Tier + sample_weight
-> Split 70/15/15 (train/validation/test)
-> Stage 1: P-CONF classifier
-> Chen confidence score/probabilities vao feature set
-> Stage 2: Price regressor
-> Quantile heads cho can duoi/can tren
-> Grouped conformal calibration
-> Luu model, metadata, metrics, tree rules
```

### 9.2 Tai sao dung train/validation/test

- Training set (tap train): dung de hoc tham so.
- Validation set (tap validation): dung de chon model tot nhat va hieu chinh.
- Test set (tap test): dung de bao cao ket qua cuoi, khong dung de chon model.

Viec tach 70/15/15 giup tranh data leakage (ro ri du lieu), tuc thong tin cua test set bi dung trong train lam metric dep gia.

### 9.3 Ket qua candidate models

Trong cac snapshot tot, ReliabilityAwareGradientBoosting duoc chon nhieu lan vi validation MAE va test metric tot hon.

Bang tom tat:

| Model | Vai tro | Nhan xet |
|---|---|---|
| QualityWeightedRandomForest | Baseline manh, on dinh | Tot cho doi chieu, nhung co snapshot kem hon GradientBoosting. |
| ReliabilityAwareGradientBoosting | Model chinh | Tot nhat trong nhieu metadata, phu hop du lieu dang bang va sample weight. |
| ConfidenceWeightedXGBoost | Model nang cao de doi chieu | Da thu, nhung khong phai luc nao tot; khong ep chon neu metric thap. |

## 10. Ket qua chuc nang he thong

### 10.1 Backend

Da co cac endpoint/chuc nang:

- `/api/predict` cho legacy prediction (du doan cu).
- `/api/v2/valuation` cho valuation v2 (dinh gia co 4 scenario va adjustment ledger).
- `/api/v2/pipeline` cho 9-gate pipeline.
- `/api/data-quality/evaluate` cho data quality assessment (danh gia do tin cay du lieu).
- `/api/research-lab/overview` cho Research Lab.
- `/api/v2/explain/*` cho Explainability Dashboard.
- `/api/v2/sdev` hoac transaction/SDEV endpoints tuy route cu the trong backend.

### 10.2 Frontend

Da co cac man hinh:

- Prediction: form du doan, ket qua valuation, comparable, pipeline trail.
- DataQuality: cham diem du lieu dau vao.
- ResearchLab: giai thich thuat toan va train pipeline.
- MapExplorer: ban do theo price tier va confidence view.
- ExplainabilityDashboard: SHAP, residual, calibration, model comparison.
- DataSources/RecordExplorer: quan tri nguon va ban ghi, uu tien admin.

### 10.3 Output cua he thong

Mot ket qua du doan tot phai co:

- Gia trung tam.
- Can duoi/can tren.
- Confidence grade A/B/C/D.
- Evidence tier/tier breakdown cua comparable.
- Warnings (canh bao).
- Recommendations/next_actions (khuyen nghi bo sung du lieu).
- Adjustment ledger (yeu to tang/giam gia).
- Comparable records (cac tai san so sanh).
- Explanation (giai thich bang SHAP/ledger/rule).

## 11. Diem da hoan thanh o moc 80%

| Hang muc | Trang thai | Bang chung |
|---|---|---|
| Kien truc he thong | Da co | README, SPEC, source tree. |
| Database active 3,000+ | Da co | Live DB 3,269 active/trainable. |
| Evidence Tier E1-E5 | Da co | Live DB co E1-E5, TAXONOMY-03-EVIDENCE. |
| RQS/CS/Neff | Da co | `src/backend/quality_assessment.py`. |
| Train ML 2 tang | Da co | `src/ml/pipeline.py`, metadata model. |
| P-CONF classifier | Da co | EntropyTree/GiniTree/HybridConfidenceForest. |
| Price regressor | Da co | QualityWeightedRandomForest/GradientBoosting/XGBoost. |
| Interval prediction | Da co | Quantile heads + grouped conformal calibration. |
| Comparable engine | Da co | `src/domain/comparable/engine.py`. |
| 9-gate pipeline | Da co | `src/domain/valuation/pipeline_orchestrator.py`. |
| Adjustment ledger | Da co | `src/domain/valuation/adjustment_registry.py`. |
| SHAP/Impact | Da co | Explainability dashboard, ImpactEngine. |
| SDEV | Da co code/module | `src/domain/valuation/sdev_engine.py`, matched_pairs = 21,206. |
| Research Lab | Da co | `frontend/src/pages/admin/ResearchLab.jsx`. |

## 12. Han che can viet trung thuc

1. Gia rao ban online khong phai gia giao dich thuc.
2. Snapshot metric tot nhat va latest retrain co ket qua khac nhau, can trinh bay tach rieng.
3. Bang `buyer_requirements` trong live DB hien tai = 0, nen SDEV demand-side can duoc tai nap/kiem tra lai.
4. Model retrain 14/05/2026 co MAPE cao, can on dinh lai du lieu train va chon candidate production theo model registry.
5. Evidence Tier trong live DB va training quality summary co the khac nhau vi mot ben la cot DB live, mot ben la profile tinh trong pipeline.
6. Chua co expert ratings (danh gia chuyen gia) that du 150 mau de xem nhu ground truth (du lieu tham chieu). Day la muc tieu 20% con lai.
7. SDEV la proxy cho market-acceptable price, khong phai gia giao dich that.

## 13. Ke hoach 20% con lai

| Viec can lam | Muc tieu | Ly do |
|---|---|---|
| Chot model production | Chon snapshot/candidate theo registry, khong chi lay latest | Tranh metric bi xau do retrain tam thoi. |
| Dong bo buyer_requirements | Tai nap hoac phuc hoi demand data | SDEV can buyer/bid distribution. |
| Expert validation | 3 chuyen gia x 50 tai san = 150 ratings | Co ground truth doc lap. |
| Bo sung E1/E2 self-collected | Tang anchor thuc dia | Giam phu thuoc listing online. |
| Chay lai calibration | Co sample A/B/C/D tot hon | Khoang gia dang tin hon. |
| Chup screenshot UI | Prediction, DataQuality, ResearchLab, MapExplorer, Explainability | Phuc vu slide bao cao. |
| Viet phu luc API/output | Them response mau | De hoi dong doi chieu voi san pham that. |

## 14. Cau tra loi ngan cho cac cau hoi de bi bat be

### Hoi: Tai sao khong chi dung XGBoost?

Tra loi: Nhom co thu XGBoost nhung chon model theo validation/test metrics. XGBoost manh nhung khong mac dinh tot nhat voi moi bo du lieu. Snapshot hien cho thay ReliabilityAwareGradientBoosting on dinh hon, nen chon theo bang chung thay vi theo ten thuat toan.

### Hoi: Gia rao ban co phai ground truth khong?

Tra loi: Khong. Gia rao ban chi la market signal. Do an xu ly van de nay bang Evidence Tier, RQS, sample weight, confidence interval va SDEV de tranh xem listing price la su that tuyet doi.

### Hoi: Muc do tin cay du doan va do tin cay du lieu khac nhau the nao?

Tra loi: Do tin cay du lieu do ban ghi co truy vet/xac minh tot khong. Muc do tin cay du doan do ca dinh gia co du mau gan giong va on dinh khong. Du lieu co nguon tot van co the du doan thap neu khu vuc qua it mau.

### Hoi: Vi sao dung khoang gia thay vi mot gia?

Tra loi: Thi truong bat dong san co nhieu bat dinh, dac biet khi gia rao khong phai gia giao dich. Khoang gia cho nguoi dung thay muc bat dinh; band A hep hon, band D rong hon.

### Hoi: Conformal calibration la gi trong de tai?

Tra loi: Sau khi model du doan, nhom tinh residual ratio tren validation set va gom theo band A/B/C/D. Band co sai so cao se co khoang gia rong hon. Muc tieu la tranh model qua tu tin.

### Hoi: SHAP co vai tro gi?

Tra loi: SHAP giai thich dac trung nao keo gia len/xuong. Trong de tai, SHAP duoc ket hop voi comparable pool va adjustment ledger de giai thich theo boi canh bat dong san, khong chi la bieu do ky thuat.

### Hoi: SDEV co phai gia giao dich that khong?

Tra loi: Khong. SDEV uoc luong market-acceptable price, tuc vung gia co kha nang duoc thi truong chap nhan dua tren ask va bid. Khi chua co buyer requirements live, SDEV can duoc trinh bay nhu module da co va can dong bo demand data.

### Hoi: Tai sao metric moi nhat xau hon snapshot cu?

Tra loi: Vi du lieu va policy tier da thay doi sau cleanup/retrain. Bao cao tach ro snapshot tot nhat va latest retrain. 20% con lai se on dinh lai bo train, chon model registry phu hop va bo sung expert validation. Nhom khong cherry-pick va khong che giau regression.

## 15. Ket luan moc 80%

Tai moc 80%, de tai da hoan thanh phan loi cua mot he thong AVM co kha nang:

- thu thap va quan tri du lieu bat dong san;
- cham diem do tin cay du lieu bang Evidence Tier, RQS va CS;
- train mo hinh hai tang de tach tin cay du doan va du doan gia;
- tao khoang gia co hieu chinh theo trust band;
- giai thich ket qua bang comparable, adjustment ledger va SHAP;
- hien thi Research Lab de trinh bay thuat toan minh bach.

Diem can nhan manh khi bao cao: dong gop cua de tai khong nam o viec chi dung mot model ML, ma nam o viec bien bai toan du lieu bat dong san nhieu thanh mot pipeline co kiem soat: data trust, prediction confidence, interval valuation va explainability. Day la huong phu hop voi thi truong Viet Nam, noi gia rao ban online co ich nhung khong the duoc coi la gia thi truong dung tuyet doi.
