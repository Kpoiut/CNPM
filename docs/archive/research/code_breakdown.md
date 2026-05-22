# PHÂN BIỆT CODE BASELINE VÀ CODE NHÓM PHÁT TRIỂN

## Tổng quan

Dự án này sử dụng baseline từ các repo công khai và phát triển thêm các tính năng mới.

---

## PHẦN 1: CODE TỪ BASELINE (KHÔNG TÍNH VÀO SỐ DÒNG CODE MỚI)

### 1.1 Baseline: California Housing Price Prediction
- **Thư mục**: `external/baselines/california-housing-price-prediction/`
- **License**: Apache-2.0
- **Nguồn**: https://github.com/nitish9413/CALIFORNIA-HOUSING-PRICE-PREDICTION

Các file gốc (GIỮ NGUYÊN, KHÔNG SỬA):
- `external/baselines/california-housing-price-prediction/app.py`
- `external/baselines/california-housing-price-prediction/housing/__init__.py`
- `external/baselines/california-housing-price-prediction/housing/components/*.py`
- `external/baselines/california-housing-price-prediction/housing/config/*.py`
- `external/baselines/california-housing-price-prediction/housing/entity/*.py`
- `external/baselines/california-housing-price-prediction/housing/constant/*.py`
- `external/baselines/california-housing-price-prediction/housing/exception/*.py`
- `external/baselines/california-housing-price-prediction/housing/logger/*.py`
- `external/baselines/california-housing-price-prediction/housing/pipeline/*.py`
- `external/baselines/california-housing-price-prediction/housing/util/*.py`

### 1.2 Baseline: House Price Prediction (Flask)
- **Thư mục**: `external/baselines/house-price-prediction-flask/`
- **License**: MIT
- **Nguồn**: https://github.com/MdJafirAshraf/House-price-prediction-using-flask

Các file gốc (GIỮ NGUYÊN):
- `external/baselines/house-price-prediction-flask/app.py`
- `external/baselines/house-price-prediction-flask/house.py`
- `external/baselines/house-price-prediction-flask/house_data.csv`
- `external/baselines/house-price-prediction-flask/model.pkl`

### 1.3 Baseline: MLOps House Price Predictor
- **Thư mục**: `external/baselines/mlops-house-price-predictor/`
- **License**: MIT
- **Nguồn**: https://github.com/mlopsbootcamp/house-price-predictor

Các file gốc (GIỮ NGUYÊN):
- `external/baselines/mlops-house-price-predictor/src/api/*.py`
- `external/baselines/mlops-house-price-predictor/src/data/*.py`
- `external/baselines/mlops-house-price-predictor/src/features/*.py`
- `external/baselines/mlops-house-price-predictor/src/models/*.py`
- `external/baselines/mlops-house-price-predictor/streamlit_app/*.py`

---

## PHẦN 2: CODE NHÓM TỰ PHÁT TRIỂN (TÍNH VÀO SỐ DÒNG CODE MỚI)

### 2.1 Backend Core
| File | Mô tả | Số dòng |
|------|-------|----------|
| `src/backend/database.py` | Database configuration | ~25 |
| `src/backend/models.py` | SQLAlchemy models với self-collected fields | ~90 |
| `src/backend/main.py` | FastAPI REST API | ~400 |

### 2.2 Scripts
| File | Mô tả | Số dòng |
|------|-------|----------|
| `scripts/seed_data.py` | Seed data với 3-5% self-collected | ~150 |
| `scripts/train_model.py` | Model training script | ~150 |
| `scripts/evaluate_model.py` | Model evaluation script | ~130 |
| `scripts/import_csv.py` | CSV import với validation | ~180 |
| `scripts/export_self_collected.py` | Export self-collected data | ~100 |
| `scripts/setup_baselines.py` | Setup baselines | ~90 |

### 2.3 Frontend React
| File | Mô tả | Số dòng |
|------|-------|----------|
| `frontend/src/App.jsx` | Main app component | ~40 |
| `frontend/src/main.jsx` | Entry point | ~10 |
| `frontend/src/index.css` | Global styles | ~180 |
| `frontend/src/pages/Prediction.jsx` | Prediction page | ~180 |
| `frontend/src/pages/Dashboard.jsx` | Statistics page | ~100 |
| `frontend/src/pages/SelfCollected.jsx` | Self-collected management | ~200 |
| `frontend/src/pages/Baselines.jsx` | Baselines info page | ~80 |
| `frontend/src/pages/About.jsx` | About page | ~100 |

### 2.4 Documentation
| File | Mô tả |
|------|-------|
| `README.md` | Project documentation |
| `baseline_sources.md` | Baseline sources |
| `docs/baseline_comparison_plan.md` | Baseline comparison plan |
| `docs/license_and_attribution.md` | License and attribution |
| `docs/how_to_collect_3_to_5_percent_data.md` | Data collection guide |
| `docs/reproducibility.md` | Reproducibility guide |
| `docs/experiment_results.md` | Experiment results |

---

## TỔNG KẾT

- **Tổng số dòng code baseline gốc**: ~3000+ dòng (giữ nguyên, không tính)
- **Tổng số dòng code nhóm tự phát triển**: ~2000 dòng (trong giới hạn 1500-8000 dòng)
- **Số baseline sử dụng**: 3 repos với license rõ ràng

---

## LƯU Ý QUAN TRỌNG

1. **Baseline code** - Đặt trong `external/baselines/`, giữ nguyên, không sửa trực tiếp
2. **Code mới** - Đặt trong `src/`, `scripts/`, `frontend/src/`
3. **Patch files** - Nếu cần sửa baseline để chạy, tạo patch trong `patches/`
4. **Giới hạn code mới**: Tối đa 1500 dòng code mới tự viết thêm (không tính baseline clone)
