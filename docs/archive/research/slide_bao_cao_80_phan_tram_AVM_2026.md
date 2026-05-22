---
marp: true
paginate: true
size: 16:9
---

# Bao cao tien do 80%

De tai: He thong AVM bat dong san bang hoc may ket hop IoT

Ten day du: Automated Valuation Model (mo hinh dinh gia tu dong)

---

# 1. Van de nghien cuu

- Gia rao ban online khong mac dinh la gia giao dich thuc.
- Du lieu bat dong san Viet Nam bi phan tan, thieu truy vet va de bi overasking (rao cao hon gia co the giao dich).
- Neu train truc tiep tren listing price (gia rao), mo hinh co the hoc theo nhieu.
- Giai phap cua nhom: du doan gia kem do tin cay, khoang gia va giai thich.

Ghi chu thuyet trinh: noi ro "listing price la market signal, khong phai market truth".

---

# 2. Ket qua 80% da dat

- Live DB: 3,269 ban ghi active/trainable trong 6 quan.
- Public collected: 3,000; self collected: 269.
- Evidence Tier: E1=91, E2=2,603, E3=523, E4=39, E5=13.
- Provenance chain: 9,900 buoc truy vet.
- Matched pairs: 21,206 cap cung-cau.
- Da co ML pipeline 2 tang, Research Lab, DataQuality, Prediction, MapExplorer, Explainability Dashboard.

---

# 3. Pham vi du lieu

6 khu vuc:

- Ha Noi: Quan Cau Giay, Quan Thanh Xuan, Quan Dong Da.
- TP. Ho Chi Minh: Quan 7, Quan Binh Thanh, Quan Tan Binh.

Phan bo active:

- Thanh Xuan: 599.
- Cau Giay: 584.
- Tan Binh: 539.
- Dong Da: 521.
- Quan 7: 513.
- Binh Thanh: 513.

---

# 4. Kien truc tong the

```text
Du lieu goc
-> Evidence Tier + RQS
-> P-CONF classifier
-> AVM-PREDICT regressor
-> Quantile interval + conformal calibration
-> 9-gate valuation pipeline
-> Output: gia, khoang gia, confidence, giai thich
```

Ghi chu: nhan manh he thong khong chi la ML model, ma la pipeline co governance (kiem soat).

---

# 5. Thuat ngu cot loi

- AVM: Automated Valuation Model - mo hinh dinh gia tu dong.
- RQS: Record Quality Score - diem chat luong tung ban ghi.
- P-CONF: Prediction Confidence - muc do tin cay cua du doan.
- D-TRUST: Data Trust - do tin cay cua du lieu.
- Neff: Effective Sample Size - so mau hieu dung.
- SHAP: giai thich dong gop tung dac trung vao du doan.

---

# 6. Evidence Tier E1-E5

| Tier | Y nghia |
|---|---|
| E1 | Bang chung rat cao, field/self-collected verified |
| E2 | Nguon verified, traceability manh |
| E3 | Public record co validation mot phan |
| E4 | Listing co trace nhung anchor yeu |
| E5 | It bang chung, can canh bao |

Muc tieu: khong de du lieu kem chat luong anh huong ngang voi du lieu co bang chung manh.

---

# 7. RQS - diem chat luong ban ghi

Cong thuc:

```text
RQS = 0.25P + 0.25V + 0.20M + 0.15C + 0.15T - Penalty
```

Trong do:

- P: provenance score - diem truy vet nguon.
- V: verification score - diem xac minh.
- M: market anchor - diem neo thi truong.
- C: completeness - diem day du.
- T: timeliness - diem do moi du lieu.

---

# 8. CS - diem tin cay ca dinh gia

Cong thuc:

```text
CS = 0.35*S_volume + 0.40*S_quality + 0.25*S_completeness
```

Luat chan:

- Khong co E1/E2: khong duoc xep qua cao.
- Neff < 30: chi nen tham khao.
- Median RQS < 5: output reference_only.
- Mot nguon duy nhat: canh bao single-source bias.

---

# 9. Tach P-CONF va D-TRUST

P-CONF (muc do tin cay du doan):

- Co du mau gan giong khong.
- Cum du lieu co on dinh khong.
- A yeu cau so mau gan giong/effective support rat cao.

D-TRUST (do tin cay du lieu):

- Ban ghi co nguon khong.
- Co xac minh, anh, IoT, provenance khong.
- Tier E1-E5 va RQS cao hay thap.

---

# 10. Quy trinh train ML 2 tang

```text
Dataset
-> Feature engineering
-> RQS + sample_weight
-> Split 70/15/15
-> Stage 1: Confidence classifier
-> Stage 2: Price regressor
-> Quantile heads
-> Grouped conformal calibration
```

Ly do: tach bai toan "du lieu co tin cay khong" va "gia du doan bao nhieu".

---

# 11. Stage 1 - P-CONF

Candidate models:

- EntropyTree: cay quyet dinh dung entropy.
- GiniTree: cay quyet dinh dung Gini impurity.
- HybridConfidenceForest: RandomForestClassifier on dinh hon cay don.

Nhan dau ra: A/B/C/D.

Chon model theo macro F1 tren validation set.

---

# 12. Stage 2 - AVM-PREDICT

Candidate regressors:

- QualityWeightedRandomForest.
- ReliabilityAwareGradientBoosting.
- ConfidenceWeightedXGBoost.

Bien the cua nhom:

- Dung sample_weight tu RQS va Evidence Tier.
- Chen P-CONF score/probabilities vao feature set.
- Chon model theo validation MAE, khong chon theo ten pho bien.

---

# 13. Ket qua model

| Snapshot | Records | Best model | MAPE | R2 |
|---|---:|---|---:|---:|
| 03/05/2026 | 3,037 | ReliabilityAwareGradientBoosting | 14.20% | 0.765 |
| 04/05/2026 | 3,231 | ReliabilityAwareGradientBoosting | 16.09% | 0.845 |
| 14/05/2026 latest | 3,269 | ReliabilityAwareGradientBoosting | 45.18% | 0.598 |

Ghi chu: khong tron snapshot tot voi latest retrain. 20% con lai la on dinh lai metric.

---

# 14. Interval prediction

He thong khong tra mot gia duy nhat.

Thanh phan:

- Quantile heads: q10 va q90 de sinh can duoi/can tren.
- Grouped conformal calibration: hieu chinh residual theo band A/B/C/D.
- Band A hep hon; band D rong hon.

Muc tieu: tranh tao cam giac chac chan gia khi du lieu con yeu.

---

# 15. Comparable Engine

5 lop xu ly:

1. Candidate retrieval - lay ung vien.
2. Similarity scoring - cham diem tuong dong.
3. Adjustment normalization - chuan hoa dieu chinh.
4. Evidence ranking - uu tien E1/E2.
5. Explanation rendering - giai thich ly do chon.

Dung Haversine (khoang cach toa do) va evidence score trong similarity.

---

# 16. 9-GATE Pipeline

| Gate | Vai tro |
|---|---|
| INTAKE | kiem tra dau vao |
| NORMALIZE | chuan hoa |
| CLASSIFY | chon workflow |
| LEGAL | phap ly |
| GEOMETRY | hinh hoc |
| ENVIRONMENT | moi truong |
| COMPARABLE | so sanh |
| VALUATION | dinh gia |
| FIT | phu hop persona |

Moi gate co PASS/WARN/BLOCK/SKIP.

---

# 17. Adjustment Ledger

Output khong chi la gia.

Moi factor co:

- factor_code - ma yeu to.
- group - nhom yeu to.
- delta_pct_base - ty le tang/giam.
- confidence_base - do tin cay cua factor.
- rationale_template - cau giai thich.
- evidence_requirement - bang chung toi thieu.

Giai thich duoc vi sao gia tang/giam.

---

# 18. IMPACT va SHAP

IMPACT = Comparable-SHAP Impact Ledger.

Quy trinh:

- Chon comparable pool.
- Chay ML prediction.
- Tinh SHAP voi background la comparable pool.
- Doi SHAP thanh delta %.
- Tach price effect va confidence loss.

Dung de tra loi: yeu to nao keo gia len/xuong va truong nao thieu lam giam tin cay.

---

# 19. SDEV

SDEV = Supply-Demand Equilibrium Valuation.

Y tuong:

- Ask distribution: gia rao ban cua nguoi ban.
- Bid distribution: ngan sach/nhu cau cua nguoi mua.
- Vung gia chap nhan nam gan overlap giua ask va bid.

Live DB co matched_pairs = 21,206, nhung buyer_requirements hien = 0. Can dong bo lai demand data truoc bao cao cuoi.

---

# 20. Research Lab

Research Lab hien thi:

- AVM-PREDICT: du doan gia.
- P-CONF: muc do tin cay du doan.
- D-TRUST: do tin cay du lieu.
- IMPACT: giai thich tac dong.
- Calibration: hieu chinh khoang gia.
- Training Pipeline: cay quy trinh train.

Vai tro: giup demo thuat toan minh bach va tranh noi chung chung.

---

# 21. Giao dien da co

- Prediction: du doan, comparable, pipeline trail.
- DataQuality: cham do tin cay du lieu.
- ResearchLab: giai thich thuat toan.
- MapExplorer: ban do theo price tier/confidence.
- ExplainabilityDashboard: SHAP, residual, calibration, model compare.
- DataSources/RecordExplorer: quan tri nguon va truy vet ban ghi.

---

# 22. Diem trung thuc can noi truoc

- Gia rao khong phai gia giao dich thuc.
- Snapshot 03/05 co MAPE 14.20%, latest retrain 14/05 co MAPE 45.18%.
- Buyer requirements live hien tai = 0, SDEV can dong bo lai demand table.
- Chua co expert ratings thuc du 150 mau.
- Do an dang o moc 80%, 20% con lai tap trung validation va on dinh metric.

---

# 23. Ke hoach 20% con lai

1. Chot model production theo model registry.
2. Dong bo lai buyer requirements cho SDEV.
3. Lay 150 expert ratings: 3 chuyen gia x 50 tai san.
4. Bo sung E1/E2 self-collected.
5. Chay lai calibration A/B/C/D.
6. Chup screenshot UI va dong goi API response sample.

---

# 24. Ket luan

Dong gop chinh:

- Khong chi du doan gia, ma danh gia do tin cay du lieu va do tin cay du doan.
- Bien listing online thanh market signal co trong so, khong coi la market truth.
- Ket qua la khoang gia, confidence, warning, comparable va giai thich.
- Phu hop boi canh Viet Nam, noi du lieu giao dich thuc kho tiep can.

---

# 25. Cau hoi de bi hoi

Q: Tai sao khong dung moi XGBoost?

A: Nhom da thu XGBoost, RandomForest va GradientBoosting. Chon model theo validation/test metrics. Hien ReliabilityAwareGradientBoosting tot hon trong nhieu snapshot.

Q: Tai sao model moi nhat xau hon?

A: Sau cleanup/tier policy, du lieu thay doi. Nhom bao cao tach snapshot va latest retrain, khong cherry-pick. 20% con lai la on dinh train set va metric.

---

# 26. Cau hoi de bi hoi tiep

Q: Tin cay du doan va tin cay du lieu khac nhau the nao?

A: Tin cay du lieu la ban ghi co nguon/xac minh khong. Tin cay du doan la ca dinh gia co du mau gan giong de suy luan khong.

Q: SDEV co phai gia giao dich that khong?

A: Khong. SDEV la proxy cho market-acceptable price, can buyer data va expert validation de ket luan manh hon.
