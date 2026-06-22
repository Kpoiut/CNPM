"""Expose pgAdmin-friendly account and valuation views.

Revision ID: 20260622_0012
Revises: 20260622_0011
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op


revision = "20260622_0012"
down_revision = "20260622_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE public.valuation_runs
        SET run_at = COALESCE(run_at, created_at, now())
        WHERE run_at IS NULL
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.account_registry AS
        SELECT *
        FROM management.account_registry
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.accounts AS
        SELECT *
        FROM management.account_registry
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW public.valuation_runs_readable AS
        SELECT
            vr.id,
            vr.request_id,
            COALESCE(vr.run_at, vr.created_at) AS predicted_at,
            vr.source_endpoint,
            vr.request_status,
            vr.request_latency_ms,
            vr.account_id,
            account.username AS account_username,
            account.email AS account_email,
            account.role AS account_role,
            vr.model_name,
            vr.engine_version,
            vr.model_version_snapshot,
            vr.fair_market_value_vnd,
            vr.quick_sale_value_vnd,
            vr.recommended_listing_vnd,
            vr.expected_range_low_vnd,
            vr.expected_range_high_vnd,
            vr.confidence_grade,
            vr.overall_confidence,
            vr.evidence_tier,
            vr.comparable_count,
            vr.actual_price_vnd,
            vr.feedback_verification_status,
            vr.training_eligible,
            vr.training_exclusion_reason,
            vr.created_at
        FROM public.valuation_runs AS vr
        LEFT JOIN management.account_registry AS account
            ON account.account_id = vr.account_id
        ORDER BY COALESCE(vr.run_at, vr.created_at) DESC, vr.id DESC
        """
    )
    op.execute(
        "COMMENT ON VIEW public.account_registry IS "
        "'View pgAdmin de thay account, session, prediction_count va feedback training signal trong public schema.'"
    )
    op.execute(
        "COMMENT ON VIEW public.accounts IS "
        "'Alias doc duoc cua management.account_registry; khong tao bang account trung lap.'"
    )
    op.execute(
        "COMMENT ON VIEW public.valuation_runs_readable IS "
        "'View lich su du doan de doc nhanh tren pgAdmin: account, thoi gian, gia tri du doan, feedback va training signal.'"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT ON public.account_registry TO real_estate_avm_app;
                GRANT SELECT ON public.accounts TO real_estate_avm_app;
                GRANT SELECT ON public.valuation_runs_readable TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS public.valuation_runs_readable")
    op.execute("DROP VIEW IF EXISTS public.accounts")
    op.execute("DROP VIEW IF EXISTS public.account_registry")
