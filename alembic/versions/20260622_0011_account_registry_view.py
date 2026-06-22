"""Expose account registry with prediction and feedback value.

Revision ID: 20260622_0011
Revises: 20260622_0010
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op


revision = "20260622_0011"
down_revision = "20260622_0010"
branch_labels = None
depends_on = None


def _create_account_registry() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW management.account_registry AS
        WITH session_stats AS (
            SELECT
                user_id AS account_id,
                COUNT(*)::bigint AS total_sessions,
                COUNT(*) FILTER (WHERE NOT is_revoked)::bigint AS active_sessions,
                MAX(created_at) AS latest_session_at
            FROM auth.auth_account_sessions
            GROUP BY user_id
        ),
        prediction_stats AS (
            SELECT
                account_id,
                COUNT(*)::bigint AS prediction_count,
                COUNT(*) FILTER (WHERE actual_price_vnd IS NOT NULL)::bigint
                    AS feedback_count,
                COUNT(*) FILTER (
                    WHERE feedback_verification_status = 'verified'
                )::bigint AS verified_feedback_count,
                COUNT(*) FILTER (WHERE training_eligible)::bigint
                    AS training_eligible_feedback_count,
                MAX(created_at) AS latest_prediction_at
            FROM public.valuation_runs
            WHERE account_id IS NOT NULL
            GROUP BY account_id
        )
        SELECT
            account.id AS account_id,
            account.username,
            account.email,
            account.role,
            account.is_active,
            account.created_at,
            account.last_login,
            COALESCE(session_stats.total_sessions, 0) AS total_sessions,
            COALESCE(session_stats.active_sessions, 0) AS active_sessions,
            session_stats.latest_session_at,
            COALESCE(prediction_stats.prediction_count, 0) AS prediction_count,
            COALESCE(prediction_stats.feedback_count, 0) AS feedback_count,
            COALESCE(prediction_stats.verified_feedback_count, 0)
                AS verified_feedback_count,
            COALESCE(prediction_stats.training_eligible_feedback_count, 0)
                AS training_eligible_feedback_count,
            prediction_stats.latest_prediction_at,
            CASE
                WHEN NOT account.is_active THEN 'inactive'
                WHEN account.last_login IS NULL
                     AND COALESCE(session_stats.total_sessions, 0) = 0
                    THEN 'registered_not_logged_in'
                WHEN COALESCE(prediction_stats.prediction_count, 0) = 0
                    THEN 'active_no_prediction'
                WHEN COALESCE(prediction_stats.training_eligible_feedback_count, 0) > 0
                    THEN 'active_training_signal'
                ELSE 'active_prediction_history'
            END AS account_state
        FROM auth.auth_accounts AS account
        LEFT JOIN session_stats ON session_stats.account_id = account.id
        LEFT JOIN prediction_stats ON prediction_stats.account_id = account.id
        ORDER BY account.created_at DESC, account.id DESC
        """
    )
    op.execute(
        "COMMENT ON VIEW management.account_registry IS "
        "'Account production kèm session, lịch sử dự đoán và tín hiệu feedback dùng cho retraining.'"
    )


def upgrade() -> None:
    _create_account_registry()
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT ON management.account_registry TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.account_registry")
