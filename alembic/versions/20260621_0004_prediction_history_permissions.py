"""Grant runtime access to restored prediction history objects.

Revision ID: 20260621_0004
Revises: 20260621_0003
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op


revision = "20260621_0004"
down_revision = "20260621_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_roles
                WHERE rolname = 'real_estate_avm_app'
            ) THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                    ON public.prediction_history TO real_estate_avm_app;
                GRANT SELECT
                    ON management.prediction_history TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_roles
                WHERE rolname = 'real_estate_avm_app'
            ) THEN
                REVOKE SELECT
                    ON management.prediction_history FROM real_estate_avm_app;
            END IF;
        END $$;
        """
    )
