# PostgreSQL Production Catalog

> Revision hiện hành: `20260621_0009`. Alembic là nguồn sự thật duy nhất cho DDL.

## Domain schemas

| Schema | Nội dung |
|---|---|
| `public` | AVM core: property, valuation, provenance, source, expert và demand |
| `auth` | Account, session và refresh token |
| `ml` | Dataset version, training lineage, metrics và model registry |
| `community` | Community claim/evidence/reputation workflow |
| `operations` | Audit và rejected-row quarantine |
| `management` | Read-only operator views |

## Public core tables

| Table | Purpose |
|---|---|
| `public.properties` | Master dataset bất động sản |
| `public.valuation_runs` | Nguồn duy nhất lưu prediction, latency, account, model, feedback và training usage |
| `public.provenance_chains` | Hash/evidence chain cho property |
| `public.collection_sources` | Nguồn thu thập được phê duyệt |
| `public.expert_properties` | Property được chọn review |
| `public.expert_ratings` | Expert ground truth |
| `public.buyer_requirements` | Demand inputs |
| `public.matched_pairs` | Supply-demand matches |
| `public.alembic_version` | Migration revision |

## Auth tables

- `auth.auth_accounts`
- `auth.auth_account_sessions`
- `auth.auth_refresh_tokens`

## ML tables

- `ml.dataset_versions`
- `ml.training_runs`
- `ml.training_metrics`
- `ml.model_versions`

## Operations tables

- `operations.audit_logs`
- `operations.migration_rejected_rows`

## Management views

- `management.database_catalog`
- `management.property_dataset_full`
- `management.prediction_history`
- `management.training_feedback_candidates`
- `management.model_registry`
- `management.training_history`

## Invariants

1. Runtime URL phải là `postgresql+psycopg://`.
2. Mọi schema change đi qua Alembic; app runtime không `create_all`.
3. `valuation_runs.request_id` unique và dài tối thiểu 80 ký tự.
4. Prediction history không có bảng trùng; management history là view từ `valuation_runs`.
5. Model active lấy theo `ACTIVE_MODEL.json` và registry, không lấy candidate mới nhất.
6. Feedback chỉ vào training queue sau khi verified, có actual price và input features.
7. Domain tables không quay lại `public`; production DB test bảo vệ invariant này.

## Operator commands

```bash
python -m alembic current
python -m alembic upgrade head
python scripts/audit_postgres_catalog.py --exact-counts
pytest tests/production/test_database_release_gate.py -vv
```

Chi tiết vận hành, backup, release và incident response nằm tại `docs/runbooks/SPEC-PRODUCTION.md`.
