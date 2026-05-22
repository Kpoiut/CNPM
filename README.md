# Real Estate Decision Intelligence — AVM Platform

Hệ thống định giá bất động sản với 3 lớp output:
- **Market Valuation**: fair_market_value, quick_sale, listing_price, optimistic_ask
- **Adjustment Ledger**: từng yếu tố tăng/giảm giá (% + VND + confidence)
- **Fit Suitability**: persona fit, phong thủy, gia đình

## Công nghệ

- **Backend**: FastAPI, SQLAlchemy, scikit-learn, XGBoost
- **Frontend**: React 18, Recharts, Vite
- **Database**: SQLite
- **ML**: RandomForest, GradientBoosting, Confidence Classifier

## Cấu trúc dự án (Production Tree)

```
real-estate-avm/
├── .env.example              # Env template
├── .gitignore
├── README.md
├── requirements.txt
├── real_estate_avm.db      # Production DB
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
├── models/                  # Trained ML models (*.pkl)
│
├── schema/                 # DB schema (production_schema.sql)
│
├── scripts/                # ★ PRODUCTION SCRIPTS (5 files)
│   ├── retrain_v2.py      # ML training (real data only)
│   ├── seed_data.py        # Seed demo data
│   ├── run_collector.py   # Web scraping
│   ├── fix_quality.py      # Quality assessment
│   ├── fix_frontend.py     # Frontend utilities
│   └── archive/           # Legacy scripts (r16/r15 — DO NOT edit)
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
# 1. Seed data + train
python scripts/retrain_v2.py --preview
python scripts/retrain_v2.py --real-train

# 2. Backend
uvicorn src.backend.main:app --reload --port 8004

# 3. Frontend
cd frontend && npm run dev
```

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| POST | `/api/v2/valuation` | Valuation v2 (4 scenario + adjustment ledger) |
| GET | `/api/v2/factors` | List all adjustment factors |
| POST | `/api/predict` | Legacy prediction |
| GET | `/api/provinces` | Provinces + districts |
| GET | `/api/dataset/stats` | Dataset statistics |

## Evidence Tier System

| Tier | Nguồn | Trọng số ML |
|------|--------|-------------|
| E1 | Giấy tờ gốc + khảo sát thực địa | 1.0 |
| E2 | Field survey + verified | 0.85 |
| E3 | Giấy tờ xác minh | 0.65 |
| E4 | Tin rao đã xác minh | 0.35 |
| E5 | Tin rao chưa xác minh | 0.15 |

## Scope

ML train trên 6 quận: Hà Nội (Cầu Giấy, Thanh Xuân, Đống Đa) + TP.HCM (Quận 7, Bình Thạnh, Tân Bình).

Mở rộng scope = retrain model.
