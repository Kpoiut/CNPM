"""Consolidate predictions and remove legacy schema clutter.

Revision ID: 20260621_0006
Revises: 20260621_0005
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260621_0006"
down_revision = "20260621_0005"
branch_labels = None
depends_on = None


ACTIVE_ARCHIVED_TABLES = (
    "buyer_requirements",
    "matched_pairs",
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
)


def _column_names(table: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table, schema="public")
    }


def _add_column(column: sa.Column) -> None:
    if column.name not in _column_names("valuation_runs"):
        op.add_column("valuation_runs", column, schema="public")


def _restore_active_tables() -> None:
    for table in ACTIVE_ARCHIVED_TABLES:
        op.execute(
            f"""
            DO $$ BEGIN
                IF to_regclass('public.{table}') IS NULL
                   AND to_regclass('archive_empty.{table}') IS NOT NULL THEN
                    ALTER TABLE archive_empty.{table} SET SCHEMA public;
                END IF;
            END $$;
            """
        )


def _extend_valuation_runs() -> None:
    _add_column(sa.Column("request_id", sa.String(80)))
    _add_column(sa.Column("source_endpoint", sa.String(50)))
    _add_column(sa.Column("account_id", sa.Integer(), sa.ForeignKey("auth_accounts.id", ondelete="SET NULL")))
    _add_column(sa.Column("model_version_snapshot", sa.String(50)))
    _add_column(sa.Column("model_name", sa.String(100)))
    _add_column(sa.Column("request_status", sa.String(30), server_default="completed"))
    _add_column(sa.Column("request_latency_ms", sa.Float()))
    _add_column(sa.Column("result_json", sa.JSON()))
    _add_column(sa.Column("feature_importance_json", sa.JSON()))
    _add_column(sa.Column("comparable_records_json", sa.JSON()))
    _add_column(sa.Column("actual_price_evidence_ref", sa.String(500)))
    _add_column(sa.Column("feedback_by_account_id", sa.Integer(), sa.ForeignKey("auth_accounts.id", ondelete="SET NULL")))
    _add_column(sa.Column("feedback_verification_status", sa.String(30), server_default="not_submitted"))
    _add_column(sa.Column("feedback_verified_at", sa.DateTime()))
    _add_column(sa.Column("feedback_verified_by_account_id", sa.Integer(), sa.ForeignKey("auth_accounts.id", ondelete="SET NULL")))
    _add_column(sa.Column("training_exclusion_reason", sa.String(255)))
    _add_column(sa.Column("training_run_id", sa.Integer()))

    op.execute(
        """
        UPDATE public.valuation_runs
        SET request_id = COALESCE(request_id, 'legacy-v2-' || id::text),
            source_endpoint = COALESCE(source_endpoint, 'api_v2_valuation'),
            model_version_snapshot = COALESCE(model_version_snapshot, engine_version),
            model_name = COALESCE(model_name, 'ValuationEngine'),
            request_status = COALESCE(request_status, 'completed'),
            feedback_verification_status = COALESCE(feedback_verification_status, 'not_submitted'),
            training_exclusion_reason = CASE
                WHEN input_features_json IS NULL THEN 'historical_input_unavailable'
                ELSE training_exclusion_reason
            END
        """
    )

    op.alter_column("valuation_runs", "request_id", nullable=False, schema="public")
    op.alter_column("valuation_runs", "source_endpoint", nullable=False, schema="public")
    op.alter_column("valuation_runs", "request_status", nullable=False, schema="public")
    op.alter_column("valuation_runs", "fair_market_value_vnd", nullable=True, schema="public")
    op.create_unique_constraint("uq_valuation_runs_request_id", "valuation_runs", ["request_id"], schema="public")
    op.create_index("ix_valuation_runs_account_created", "valuation_runs", ["account_id", "created_at"], schema="public")
    op.create_index("ix_valuation_runs_source_endpoint", "valuation_runs", ["source_endpoint"], schema="public")
    op.create_index("ix_valuation_runs_feedback_status", "valuation_runs", ["feedback_verification_status"], schema="public")
    op.create_index("ix_valuation_runs_training_run_id", "valuation_runs", ["training_run_id"], schema="public")


def _migrate_legacy_prediction_rows() -> None:
    if "prediction_history" not in sa.inspect(op.get_bind()).get_table_names(schema="public"):
        return
    op.execute(
        """
        INSERT INTO public.valuation_runs (
            request_id, source_endpoint, model_version_id, model_version_snapshot,
            model_name, engine_version, request_status, fair_market_value_vnd,
            expected_range_low_vnd, expected_range_high_vnd, input_features_json,
            result_json, feature_importance_json, comparable_records_json,
            legacy_prediction_id, training_eligible, training_exclusion_reason,
            created_at
        )
        SELECT
            'legacy-predict-' || ph.id::text,
            'api_predict',
            mv.id,
            ph.model_version,
            ph.model_name,
            'legacy-ml',
            'completed',
            ph.predicted_price,
            ph.confidence_low,
            ph.confidence_high,
            jsonb_build_object('legacy_raw', ph.input_features_json),
            jsonb_build_object('explanation', ph.explanation_text),
            jsonb_build_object('legacy_raw', ph.feature_importance_json),
            jsonb_build_object('legacy_raw', ph.similar_records_json),
            ph.id,
            false,
            'historical_feedback_unverified',
            ph.created_at
        FROM public.prediction_history ph
        LEFT JOIN public.model_versions mv ON mv.model_version = ph.model_version
        ON CONFLICT (request_id) DO NOTHING
        """
    )


def _create_management_views() -> None:
    op.execute("DROP VIEW IF EXISTS management.prediction_history")
    op.execute(
        """
        CREATE VIEW management.prediction_history AS
        SELECT
            vr.id AS prediction_id,
            vr.request_id,
            vr.source_endpoint,
            vr.account_id,
            a.username AS account_username,
            vr.created_at AS predicted_at,
            vr.request_status,
            vr.request_latency_ms,
            vr.property_id,
            vr.input_features_json,
            vr.fair_market_value_vnd AS predicted_price_vnd,
            vr.expected_range_low_vnd,
            vr.expected_range_high_vnd,
            vr.overall_confidence,
            vr.confidence_grade,
            vr.comparable_count,
            vr.actual_price_vnd,
            vr.actual_price_recorded_at,
            vr.actual_price_source,
            vr.actual_price_evidence_ref,
            vr.feedback_verification_status,
            vr.training_eligible,
            vr.training_exclusion_reason,
            vr.training_used_at,
            vr.training_run_id,
            COALESCE(vr.model_version_snapshot, mv.model_version) AS model_version,
            COALESCE(vr.model_name, mv.model_name) AS model_name,
            vr.engine_version
        FROM public.valuation_runs vr
        LEFT JOIN public.model_versions mv ON mv.id = vr.model_version_id
        LEFT JOIN public.auth_accounts a ON a.id = vr.account_id
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW management.training_feedback_candidates AS
        SELECT
            vr.id AS valuation_run_id,
            vr.request_id,
            vr.account_id,
            vr.input_features_json,
            vr.actual_price_vnd AS target_price_vnd,
            vr.actual_price_source,
            vr.actual_price_recorded_at,
            vr.model_version_snapshot AS prediction_model_version,
            vr.training_run_id,
            vr.training_used_at
        FROM public.valuation_runs vr
        WHERE vr.training_eligible
          AND vr.feedback_verification_status = 'verified'
          AND vr.actual_price_vnd >= 500000000
          AND vr.input_features_json IS NOT NULL
        """
    )
    op.execute(
        "COMMENT ON TABLE public.valuation_runs IS "
        "'Nguồn duy nhất lưu mọi lần dự đoán, account, model/engine, input/output và feedback phục vụ retraining.'"
    )
    op.execute(
        "COMMENT ON VIEW management.training_feedback_candidates IS "
        "'Chỉ các feedback đã xác minh, đủ input và đạt ngưỡng giá mới được đưa vào hàng đợi training.'"
    )


def _remove_legacy_objects() -> None:
    op.execute("DROP TABLE IF EXISTS public.prediction_history CASCADE")
    op.execute("DROP TABLE IF EXISTS public.predictions CASCADE")
    op.execute("DROP SCHEMA IF EXISTS compatibility CASCADE")
    op.execute("DROP SCHEMA IF EXISTS archive_empty CASCADE")


def _grant_runtime_access() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON public.valuation_runs TO real_estate_avm_app;
                GRANT SELECT ON management.prediction_history TO real_estate_avm_app;
                GRANT SELECT ON management.training_feedback_candidates TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Migration 0006 chỉ hỗ trợ PostgreSQL")
    _restore_active_tables()
    _extend_valuation_runs()
    _migrate_legacy_prediction_rows()
    _create_management_views()
    _remove_legacy_objects()
    _grant_runtime_access()


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.training_feedback_candidates")
    op.execute("DROP VIEW IF EXISTS management.prediction_history")
