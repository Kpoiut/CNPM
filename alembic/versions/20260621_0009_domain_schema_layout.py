"""Organize live PostgreSQL tables into production domain schemas.

Revision ID: 20260621_0009
Revises: 20260621_0008
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op


revision = "20260621_0009"
down_revision = "20260621_0008"
branch_labels = None
depends_on = None


DOMAIN_TABLES = {
    "auth": ("auth_accounts", "auth_account_sessions", "auth_refresh_tokens"),
    "ml": ("dataset_versions", "training_runs", "training_metrics", "model_versions"),
    "operations": ("audit_logs", "migration_rejected_rows"),
    "community": (
        "reputation_ledger",
        "claims",
        "claim_evidence",
        "community_comments",
        "challenges",
        "claim_court_sessions",
        "prediction_bonds",
        "coalition_flags",
        "ai_training_candidates",
        "appeal_cases",
        "private_insights",
    ),
}

MANAGEMENT_VIEWS = (
    "database_catalog",
    "prediction_history",
    "training_feedback_candidates",
    "model_registry",
    "training_history",
    "property_dataset_full",
)


def _drop_management_views() -> None:
    for view_name in MANAGEMENT_VIEWS:
        op.execute(f"DROP VIEW IF EXISTS management.{view_name} CASCADE")


def _move_table(table_name: str, source_schema: str, target_schema: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('{target_schema}.{table_name}') IS NULL
               AND to_regclass('{source_schema}.{table_name}') IS NOT NULL THEN
                ALTER TABLE {source_schema}.{table_name} SET SCHEMA {target_schema};
            END IF;
        END $$;
        """
    )


def _create_management_views(auth_schema: str = "auth", ml_schema: str = "ml") -> None:
    op.execute(
        f"""
        CREATE VIEW management.model_registry AS
        SELECT
            mv.id, mv.model_version, mv.model_name, mv.status, mv.is_active,
            mv.trained_at, mv.mae, mv.mape, mv.rmse, mv.r2,
            mv.improvement_mape_pct_points,
            tr.run_version AS training_run,
            dv.snapshot_key AS dataset_version,
            dv.record_count AS dataset_records,
            mv.model_path, mv.metadata_path,
            dv.checksum_sha256 AS dataset_checksum_sha256,
            tr.notes AS split_manifest_summary
        FROM {ml_schema}.model_versions mv
        LEFT JOIN {ml_schema}.training_runs tr ON tr.id = mv.training_run_id
        LEFT JOIN {ml_schema}.dataset_versions dv ON dv.id = tr.dataset_version_id
        """
    )
    op.execute(
        f"""
        CREATE VIEW management.prediction_history AS
        SELECT
            vr.id AS prediction_id, vr.request_id, vr.source_endpoint,
            vr.account_id, a.username AS account_username,
            vr.created_at AS predicted_at, vr.request_status, vr.request_latency_ms,
            vr.property_id, vr.input_features_json,
            vr.fair_market_value_vnd AS predicted_price_vnd,
            vr.expected_range_low_vnd, vr.expected_range_high_vnd,
            vr.overall_confidence, vr.confidence_grade, vr.comparable_count,
            vr.actual_price_vnd, vr.actual_price_recorded_at, vr.actual_price_source,
            vr.actual_price_evidence_ref, vr.feedback_verification_status,
            vr.training_eligible, vr.training_exclusion_reason, vr.training_used_at,
            vr.training_run_id,
            COALESCE(vr.model_version_snapshot, mv.model_version) AS model_version,
            COALESCE(vr.model_name, mv.model_name) AS model_name,
            vr.engine_version
        FROM public.valuation_runs vr
        LEFT JOIN {ml_schema}.model_versions mv ON mv.id = vr.model_version_id
        LEFT JOIN {auth_schema}.auth_accounts a ON a.id = vr.account_id
        """
    )
    op.execute("CREATE VIEW management.property_dataset_full AS SELECT * FROM public.properties")
    op.execute(
        """
        CREATE VIEW management.training_feedback_candidates AS
        SELECT
            vr.id AS valuation_run_id, vr.request_id, vr.account_id,
            vr.input_features_json, vr.actual_price_vnd AS target_price_vnd,
            vr.actual_price_source, vr.actual_price_recorded_at,
            vr.model_version_snapshot AS prediction_model_version,
            vr.training_run_id, vr.training_used_at
        FROM public.valuation_runs vr
        WHERE vr.training_eligible
          AND vr.feedback_verification_status = 'verified'
          AND vr.actual_price_vnd >= 500000000
          AND vr.input_features_json IS NOT NULL
        """
    )
    op.execute(
        f"""
        CREATE VIEW management.training_history AS
        SELECT
            tr.id, tr.run_version, tr.status, tr.algorithm, tr.started_at, tr.finished_at,
            tr.train_record_count, tr.validation_record_count, tr.test_record_count,
            dv.snapshot_key AS dataset_version, dv.record_count AS dataset_records,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'mape'
            ) AS test_mape,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'mae'
            ) AS test_mae,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'rmse'
            ) AS test_rmse,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'r2'
            ) AS test_r2,
            dv.checksum_sha256 AS dataset_checksum_sha256,
            tr.notes AS split_manifest_summary
        FROM {ml_schema}.training_runs tr
        JOIN {ml_schema}.dataset_versions dv ON dv.id = tr.dataset_version_id
        LEFT JOIN {ml_schema}.training_metrics tm ON tm.training_run_id = tr.id
        GROUP BY tr.id, dv.snapshot_key, dv.record_count, dv.checksum_sha256
        """
    )
    op.execute(
        """
        CREATE VIEW management.database_catalog AS
        SELECT
            n.nspname AS schema_name,
            c.relname AS object_name,
            CASE c.relkind
                WHEN 'r' THEN 'table'
                WHEN 'v' THEN 'view'
                WHEN 'm' THEN 'materialized_view'
                ELSE c.relkind::text
            END AS object_type,
            c.reltuples::bigint AS estimated_rows,
            CASE WHEN c.relkind = 'r' THEN pg_total_relation_size(c.oid) ELSE NULL END AS total_bytes,
            obj_description(c.oid, 'pg_class') AS purpose
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'auth', 'ml', 'community', 'operations', 'management')
          AND c.relkind IN ('r', 'v', 'm')
          AND c.relname NOT LIKE 'pg_%'
        ORDER BY
            CASE n.nspname
                WHEN 'public' THEN 1 WHEN 'auth' THEN 2 WHEN 'ml' THEN 3
                WHEN 'community' THEN 4 WHEN 'operations' THEN 5
                WHEN 'management' THEN 6 ELSE 7
            END,
            c.relname
        """
    )

    comments = {
        "model_registry": "Registry model production/candidate và metric chính từ schema ml.",
        "prediction_history": "Lịch sử dự đoán theo account, model, feedback và training lineage.",
        "property_dataset_full": "Dataset property đầy đủ phục vụ audit và quản trị.",
        "training_feedback_candidates": "Feedback giá thật đã verified và đủ điều kiện xem xét retrain.",
        "training_history": "Lịch sử training, dataset snapshot và test metrics.",
        "database_catalog": "Mục lục toàn bộ domain schema production cho pgAdmin.",
    }
    for view_name, comment in comments.items():
        op.execute(f"COMMENT ON VIEW management.{view_name} IS '{comment}'")


def _grant_application_access() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT USAGE ON SCHEMA public, auth, ml, community, operations, management
                    TO real_estate_avm_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA
                    public, auth, ml, community, operations TO real_estate_avm_app;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA
                    public, auth, ml, community, operations TO real_estate_avm_app;
                GRANT SELECT ON ALL TABLES IN SCHEMA management TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for schema_name in DOMAIN_TABLES:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

    _drop_management_views()
    for schema_name, tables in DOMAIN_TABLES.items():
        for table_name in tables:
            _move_table(table_name, "public", schema_name)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'valuation_runs_training_run_id_fkey'
                  AND conrelid = 'public.valuation_runs'::regclass
            ) THEN
                ALTER TABLE public.valuation_runs
                ADD CONSTRAINT valuation_runs_training_run_id_fkey
                FOREIGN KEY (training_run_id) REFERENCES ml.training_runs(id)
                ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )
    _create_management_views()
    _grant_application_access()


def downgrade() -> None:
    _drop_management_views()
    op.execute(
        "ALTER TABLE public.valuation_runs DROP CONSTRAINT IF EXISTS valuation_runs_training_run_id_fkey"
    )
    for schema_name, tables in reversed(tuple(DOMAIN_TABLES.items())):
        for table_name in reversed(tables):
            _move_table(table_name, schema_name, "public")
    _create_management_views(auth_schema="public", ml_schema="public")
    for schema_name in reversed(tuple(DOMAIN_TABLES)):
        op.execute(f"DROP SCHEMA IF EXISTS {schema_name}")
