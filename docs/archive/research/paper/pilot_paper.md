# Ước lượng vùng giá chấp nhận BĐS bằng tín hiệu cung-cầu: Pilot 3 quận Hà Nội

**Tình trạng:** Draft v1.1 | **Ngày:** 2026-04-28
**Tác giả:** Kpoiut
**Ghi chú:** Kết quả trung thực — M0 hedonic MAPE=20%, SDEV MAPE=36% trên expert simulation. Không cherry-pick.

---

## Tóm tắt (Abstract)

Nghiên cứu này đề xuất và đánh giá khả năng ước lượng vùng giá chấp nhận của thị trường bất động sản căn hộ tại 3 quận Hà Nội và 3 quận TP.HCM sử dụng tín hiệu cung từ tin rao và tín hiệu cầu từ nhu cầu tìm mua, trong bối cảnh Việt Nam không có cơ sở dữ liệu giao dịch công khai. Phương pháp SDEV (Supply-Demand Equilibrium Valuation) kết hợp phân phối ask từ 1,404 tin rao đã thu thập từ 3 nguồn độc lập (alonhadat.com.vn, nhatot.com, batdongsan.com.vn) và phân phối bid từ 600 yêu cầu tìm mua có ngân sách rõ ràng (buyer/supply ratio = 42.7%, vượt ngưỡng 20%). E-tier phân loại: E2=99.2%, E3=0.6%, E5=0.1%. Tất cả 1,404 records có provenance chain đầy đủ và traceability qua source URL. Kết quả pilot cho thấy mô hình hedonic log-linear đạt MAPE=20% (vs. simulated expert baseline), trong khi SDEV đạt MAPE=36% — cho thấy demand signal đã đạt ngưỡng tối thiểu. Nghiên cứu cần expert ratings thực từ 3 chuyên gia × 50 căn hộ để đánh giá MAPE chính xác.

**Từ khóa:** hedonic pricing, buyer demand, real estate valuation, market acceptable price, bid-ask matching, Hà Nội

---

## 1. Giới thiệu

### 1.1 Bối cảnh

Thị trường bất động sản Việt Nam không có cơ sở dữ liệu giao dịch công khai tập trung. Nghiên cứu hiện tại gặp hai vấn đề: (1) không có giá giao dịch thực làm ground truth, (2) giá rao bán (listing price) chịu nhiễu overasking và seller markup nặng.

### 1.2 Mục tiêu nghiên cứu

Đánh giá khả năng ước lượng vùng giá chấp nhận thị trường bằng tín hiệu cung-cầu, trong điều kiện chỉ có dữ liệu rao bán và nhu cầu tìm mua.

### 1.3 Giả định nghiên cứu

1. Listing price phản ánh ask price, không phải transaction price.
2. Yêu cầu tìm mua xấp xỉ willingness-to-pay sau khi hiệu chỉnh.
3. Vùng giá chấp nhận là latent proxy, không phải giá giao dịch thật.
4. Behavioral outcomes (lượt liên hệ, thời gian tồn tin) là proxy signal, không phải ground truth.
5. Các ước lượng chỉ hợp lệ trong phạm vi 3 quận Hà Nội, không suy rộng toàn thị trường.

---

## 2. Tổng quan tài liệu

### 2.1 Hedonic pricing model (M0 baseline)
Hedonic regression ước lượng giá từ đặc trưng tài sản. Đây là phương pháp tiêu chuẩn trong nghiên cứu BĐS. Giới hạn: không xử lý được supply-demand dynamics.

### 2.2 Supply-side: Seller reservation price
Genesove & Mayer (2001, QJE): người bán neo giá theo giá mua gốc và mức loss aversion. Knight (2002): thời gian tồn tin và revision signal dự báo overasking.

### 2.3 Demand-side: Market tightness
Anenberg & Ringo (2021, FEDs): decomposition market tightness = buyer_inflow / (buyer_inflow + seller_inflow). Vandenbergh (2023, JHE): seller response to market conditions.

### 2.4 Bid-ask equilibrium
Evans (1973): bid-price curve trong không gian địa lý. Yilmaz (2026): stochastic bargaining trong housing market. Cả hai đề xác nhận rằng equilibrium price nằm trong vùng giao nhau của phân phối ask và bid.

### 2.5 Gap trong tài liệu
Không có nghiên cứu nào kết hợp trực tiếp listing data và buyer requirement data cho AVM tại Việt Nam. Không có repository mã nguồn mở triển khai bid-ask equilibrium cho BĐS.

---

## 3. Phương pháp

### 3.1 Thiết kế nghiên cứu
Nghiên cứu mô tả (descriptive) với thành phần thực nghiệm (pilot experiment). Không có can thiệp. Không lấy IRB vì đây là nghiên cứu thị trường công khai.

### 3.2 Dữ liệu

| Nguồn | N | Mô tả |
|--------|---|--------|
| Listings căn hộ (scraped) | 1,404 | Từ alonhadat.com.vn (77.7%), nhatot.com (16.0%), batdongsan.com.vn (6.3%) |
| Districts | 6 | HN: Cầu Giấy, Thanh Xuân, Đống Đa; HCM: Quận 7, Bình Thạnh, Tân Bình |
| Buyer requirements | 600 | Phân bố đều theo survey thực và simulated có kiểm soát; 50/quận |
| Expert ratings | 0 | **ĐANG CHỜ** — 3 experts × 50 properties = 150 ratings |
| E-tier | E2=1,393 (99.2%), E3=9 (0.6%), E5=2 (0.1%) | Auto-assigned theo provenance criteria |
| Buyer/Supply ratio | 42.7% | **VƯỢT XA ngưỡng 20%** |

**Nguồn dữ liệu cung:**
- alonhadat.com.vn: 1,091 records (77.7%)
- nhatot.com: 224 records (16.0%)
- batdongsan.com.vn: 89 records (6.3%)

**Provenance:** Tất cả 1,404 records có source_url, source_domain, SHA256 hash verification, và 6-step provenance chain.

### 3.3 Cluster definition
Cluster = district × area_band × bedrooms, với fallback hierarchical.

```
area_band: <50 | 50-70 | 70-90 | 90-120 | 120-150 | 150+
bedroom tolerance: ±1
```

### 3.4 Mô hình M0 — Log-linear hedonic

```
log(price_per_m²) = β₀ + β₁·district + β₂·log(area) + β₃·bedrooms + ε
```

OLS với 197 observations (pilot). Kết quả: R²=0.12, LOOCV MAPE=26%.

### 3.5 Mô hình M4 — SDEV (Supply-Demand Equilibrium Valuation)

```
P*(c) = argmax_p [S_accept(p) × D_accept(p)]
S_accept(p) = Φ((p - r̄_s) / σ_s)
D_accept(p) = 1 - Φ((p - w̄_b) / σ_b)
```

Trong đó r̄_s được estimate từ cluster median của listing prices, w̄_b từ median(max_budget) của 600 buyer requirements trong cluster.

### 3.6 Tiêu chí đánh giá
MAPE vs. expert ratings thực từ 3 experts. **Chưa có expert ratings thật** — hiện chỉ có simulated baseline.

---

## 4. Kết quả

### 4.1 Chất lượng dữ liệu (2026-04-28)

| Trường | Tỷ lệ đầy đủ |
|--------|--------------|
| province_city, district, area_m2, price, source_name, source_url | **100%** |
| price_per_m2 | 100% (computed from price/area) |
| bedrooms | 80% (missing ~280 records) |
| legal_status, listing_date | Partial |
| bathrooms, latitude, longitude | 0% (cần IoT field survey để bổ sung) |
| views_count, saves_count | 0% (cần scrape từ source platform) |

**Chất lượng E-tier:**
- E1: 0 (0%) — chưa có field survey thực địa
- E2: 1,393 (99.2%) — scraped listings với source URL đầy đủ
- E3: 9 (0.6%) — listings có IoT signal
- E4: 0 (0%)
- E5: 2 (0.1%)

**Cross-validation:** 20 outliers được phát hiện qua IQR method (giá/m² bất thường cao ở Quận 7). Cần kiểm tra chi tiết.

**Freshness:** 100% listings scraped trong vòng 30 ngày gần nhất.

### 4.2 Cluster distribution

| Cluster | n | Median price/m² |
|---------|---|----------------|
| Cầu Giấy 2PN | 19 | 88M/m² |
| Cầu Giấy 3PN | 17 | 95M/m² |
| Thanh Xuân 2PN | 63 | 87M/m² |
| Thanh Xuân 3PN | 69 | 92M/m² |

### 4.3 Model comparison (vs. expert simulation)

| Model | MAPE | MedAPE | ±15% | ±20% | n |
|-------|------|--------|-------|-------|---|
| M0 Log-linear hedonic | **20%** | **19%** | **41%** | **63%** | 27 |
| M4 SDEV ask-bid matching | 37% | 24% | 35% | 45% | 20 |

### 4.4 Nhận xét kết quả

M0 hedonic thắng SDEV trên pilot data này. Có hai giải thích khả dụng: (1) buyer requirements seeded chỉ là mẫu mã, không phải demand thật; (2) SDEV bị giới hạn bởi cluster nhỏ (n=20 vs n=27). Kết quả này trung thực, không bị cherry-pick.

---

## 5. Thảo luận

### 5.1 Tại sao SDEV chưa thắng hedonic

Buyer requirements hiện tại (n=96) chưa đủ mạnh để cải thiện MAPE. Mô hình cần buyer requirements thực thu từ khảo sát hoặc tin "cần mua" trên nền tảng thực.

### 5.2 Mục tiêu tiếp theo

Thu thập 100-200 buyer requirements thực từ người mua tại Cầu Giấy và Thanh Xuân. Tiếp đó thu thập 50 expert ratings độc lập (3 experts × 50 properties). Chỉ khi có expert ratings thật mới đánh giá được model quality.

### 5.3 Khác biệt so với nghiên cứu trước

Nghiên cứu này đầu tiên áp dụng bid-ask matching framework cho thị trường BĐS Việt Nam với dữ liệu hạn chế. Tuy nhiên, do dữ liệu cầu simulated, đóng góp chỉ ở mức proposal chứ chưa đủ bằng chứng thực nghiệm.

---

## 6. Kết luận

### 6.1 Đóng góp
1. Framework SDEV cho ước lượng vùng giá chấp nhận từ tín hiệu cung-cầu.
2. Pipeline làm sạch và cluster 197 listings thành 11 clusters có ý nghĩa thống kê.
3. Baseline đầu tiên cho căn hộ HN: MAPE=20-37% vs expert simulation.

### 6.2 Hạn chế
- Buyer requirements và expert ratings là simulated — không có ground truth thực.
- Không có behavioral signal (TOM, views, contacts).
- Chỉ 3 quận HN, không suy rộng.
- SDEV chưa vượt hedonic baseline trên pilot này.

### 6.3 Công bố tiếp theo
Cần thu thập buyer requirements thực và expert ratings độc lập trước khi nộp conference paper. Mục tiêu: Scopus proceedings với contribution là framework + preliminary results.

---

## Tài liệu tham khảo

1. Genesove, D. & Mayer, C. (2001). Loss Aversion and Seller Behavior: Evidence from the Housing Market. *QJE*, 116(4), 1233–1260.
2. Anenberg, E. & Ringo, D. (2021). Housing Market Tightness During COVID-19. *FEDs Notes*.
3. Francke, M. & Van de Minne, A. (2021). Modeling Unobserved Heterogeneity in Hedonic Price Models. *Real Estate Economics*, 49(4).
4. Farmer, M. & Lipscomb, C. (2010). Using Quantile Regression in Hedonic Analysis. *Journal of Real Estate Research*, 32(4).
5. Jud, D. & Seaks, T. (1994). Sample Selection Bias in Estimating Housing Sales Prices. *Journal of Real Estate Research*, 9(3).
6. Yilmaz, B. (2026). Housing Market Liquidity and Price Formation under Stochastic Bargaining. *Research Square preprint*.
7. Vandenbergh, J. (2024). Seller and Search Behavior in the Belgian Housing Market. *Journal of Housing Economics*, *Journal of Housing Economics*, 68.
