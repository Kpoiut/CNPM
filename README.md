# Real Estate Decision Intelligence — AVM Platform

Hệ thống định giá bất động sản với 3 lớp output:
- **Market Valuation**: fair_market_value, quick_sale, listing_price, optimistic_ask
- **Adjustment Ledger**: từng yếu tố tăng/giảm giá (% + VND + confidence)
- **Fit Suitability**: persona fit, phong thủy, gia đình

## Công nghệ

- **Backend**: FastAPI, SQLAlchemy, scikit-learn, XGBoost
- **Frontend**: React 18, Recharts, Vite
- **Database**: PostgreSQL/PostGIS cho toàn bộ runtime production và integration test
- **ML**: RandomForest, GradientBoosting, Confidence Classifier

## Cấu trúc dự án (Production Tree)

```
real-estate-avm/
├── .env.example              # Env template
├── .gitignore
├── README.md
├── requirements.txt
├── requirements-dev.txt      # Test, coverage và workbook tooling
├── docker-compose.yml      # PostgreSQL/PostGIS + backend + frontend production stack
├── alembic/                 # Nguồn duy nhất quản lý PostgreSQL schema
│
├── src/                     # ★ SOURCE CODE — tất cả production code ở đây
│   ├── config/              # Canonical config (province names, base prices)
│   ├── ml/                 # ML pipeline + feature engineering
│   ├── domain/             # Business logic
│   │   ├── valuation/      # Valuation engine + adjustment registry
│   │   ├── comparable/     # Comparable search engine
│   │   └── fit/           # Persona fit, feng shui suitability
│   └── backend/            # FastAPI app
│       ├── main.py         # API routes
│       ├── models.py       # SQLAlchemy models
│       ├── database.py
│       ├── api_v2/        # v2 API endpoints
│       └── ...
│
├── frontend/                # React app (Vite)
│   ├── src/
│   │   ├── pages/         # 14 pages
│   │   └── components/
│   │       └── valuation/  # Valuation forms + result cards + charts
│   ├── package.json
│   └── vite.config.mjs
│
├── models/                  # Active pointer, audited model artifacts và metadata
│
├── scripts/                # Production/admin scripts
│   ├── retrain_v2.py       # ML training from PostgreSQL clean data
│   ├── sync_ml_registry.py # Sync metadata artifacts into lineage tables
│   ├── run_migrations.py   # Migration helper
│   ├── backup_postgres.py  # PostgreSQL backup helper
│   ├── quality/            # Workbook generator + production test catalogue validator
│   └── local/              # Local launch scripts
│
├── tests/                  # Unit + integration tests
│   ├── unit/valuation/
│   └── integration/
│
├── docs/                   # ★ DOCUMENTATION
│   ├── SPEC.md             # Product spec v1
│   ├── SCHEMA.md           # Domain schema v2
│   ├── TAXONOMY/           # Asset/Factor/Evidence/Persona taxonomies
│   └── archive/
│       ├── research/      # Research docs (round 1-16)
│       ├── thesis/        # Thesis documents
│       ├── rubric_tmp/     # Rubric artifacts
│       ├── databases/     # Old DB snapshots
│       └── logs/          # Old server logs
│
└── uploads/                # User uploads (images, etc.)
```

## Chạy nhanh

```bash
# 1. Cài dependency dev, cấu hình PostgreSQL 18 local, migrate, rồi kiểm tra dữ liệu
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
pwsh -ExecutionPolicy Bypass -File scripts/local/VERIFY_POSTGRES18_REALTIME.ps1
python scripts/retrain_v2.py --dry-run

# 2. Backend
uvicorn src.backend.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm run dev

# 4. Production frontend gate
cd frontend && npm run build:check
```

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v2/valuation` | Valuation v2 (4 scenario + adjustment ledger) |
| GET | `/api/v2/factors` | List all adjustment factors |
| GET | `/api/v2/valuation/runs` | Lịch sử dự đoán theo account/quyền |
| GET | `/api/provinces` | Provinces + districts |
| GET | `/api/dataset/stats` | Dataset statistics |

`POST /api/predict` chỉ còn compatibility route đã đánh dấu deprecated; client mới dùng `/api/v2/valuation`.

## Evidence Tier System

| Tier | Nguồn | Trọng số ML |
|------|--------|-------------|
| E1 | Giấy tờ gốc + khảo sát thực địa | 1.0 |
| E2 | Field survey + verified | 0.85 |
| E3 | Giấy tờ xác minh | 0.65 |
| E4 | Tin rao đã xác minh | 0.35 |
| E5 | Tin rao chưa xác minh | 0.15 |

## Production Notes

- `models/ACTIVE_MODEL.json` là con trỏ model đang phục vụ. Metric serving phải lấy theo active model, không lấy candidate mới nhất nếu chưa activate.
- Git chỉ mở cho artifact model đã audit: `model_20260504_144753.pkl` và `model_20260621_162930.pkl`; mọi `.pkl` khác vẫn bị ignore để tránh rác/candidate chưa kiểm chứng.
- PostgreSQL local cho pgAdmin 4 bản 18 chạy ở `127.0.0.1:5433/real_estate_avm`; app dùng role `real_estate_avm_app` từ `.env`, không dùng SQLite.
- PostgreSQL head `20260622_0014` chia schema theo domain: `public` (10 bảng lõi có `accounts` projection), `auth`, `ml`, `community`, `operations`, `management`.
- `public.valuation_runs` là bảng duy nhất lưu dự đoán; `management.prediction_history` là view đọc lịch sử, không còn bảng `predictions`/`prediction_history` trùng lặp.
- Google OAuth 2.0 dùng env `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`; không commit secret thật.
- CI/CD nằm trong `.github/workflows/ci.yml`; frontend build có bundle budget gate, backend chạy PostgreSQL/PostGIS thật, Docker smoke upload log/evidence. Quality gate bên thứ ba dùng SonarCloud trong `.github/workflows/third-party-quality.yml`.
- Runbook chuẩn duy nhất: `docs/runbooks/SPEC-PRODUCTION.md`; test catalogue: `docs/testing/AVM_Production_Test_Cases.xlsx`.

## Scope

ML train trên 6 quận: Hà Nội (Cầu Giấy, Thanh Xuân, Đống Đa) + TP.HCM (Quận 7, Bình Thạnh, Tân Bình).

Mở rộng scope = retrain model.
