"""Widen valuation request ids for prefixed lineage identifiers.

Revision ID: 20260621_0007
Revises: 20260621_0006
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260621_0007"
down_revision = "20260621_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.training_feedback_candidates")
    op.execute("DROP VIEW IF EXISTS management.prediction_history")
    op.alter_column(
        "valuation_runs",
        "request_id",
        existing_type=sa.String(36),
        type_=sa.String(80),
        existing_nullable=False,
        schema="public",
    )
    _create_management_views()


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.training_feedback_candidates")
    op.execute("DROP VIEW IF EXISTS management.prediction_history")
    op.alter_column(
        "valuation_runs",
        "request_id",
        existing_type=sa.String(80),
        type_=sa.String(36),
        existing_nullable=False,
        schema="public",
    )
    _create_management_views()


def _create_management_views() -> None:
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
        CREATE VIEW management.training_feedback_candidates AS
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
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT ON management.prediction_history TO real_estate_avm_app;
                GRANT SELECT ON management.training_feedback_candidates TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )
