"""Allow controlled account edits from the pgAdmin-visible projection.

Revision ID: 20260622_0014
Revises: 20260622_0013
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op


revision = "20260622_0014"
down_revision = "20260622_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION management.refresh_public_accounts_snapshot()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF current_setting('avm.skip_account_snapshot_refresh', true) = '1' THEN
                RETURN NULL;
            END IF;
            PERFORM management.refresh_public_accounts_snapshot_now();
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION management.apply_public_account_edit()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, auth, operations, pg_temp
        AS $$
        BEGIN
            -- Snapshot refreshes originate inside another trigger and must not write back.
            IF pg_trigger_depth() > 1 THEN
                RETURN NEW;
            END IF;

            IF NEW.account_id IS DISTINCT FROM OLD.account_id THEN
                RAISE EXCEPTION 'account_id is immutable; edit username, email, role or is_active only';
            END IF;
            IF NEW.role NOT IN ('user', 'admin') THEN
                RAISE EXCEPTION 'role must be user or admin';
            END IF;
            IF NULLIF(BTRIM(NEW.username), '') IS NULL THEN
                RAISE EXCEPTION 'username cannot be empty';
            END IF;
            IF ROW(
                NEW.created_at,
                NEW.last_login,
                NEW.total_sessions,
                NEW.active_sessions,
                NEW.latest_session_at,
                NEW.prediction_count,
                NEW.feedback_count,
                NEW.verified_feedback_count,
                NEW.training_eligible_feedback_count,
                NEW.latest_prediction_at,
                NEW.account_state
            ) IS DISTINCT FROM ROW(
                OLD.created_at,
                OLD.last_login,
                OLD.total_sessions,
                OLD.active_sessions,
                OLD.latest_session_at,
                OLD.prediction_count,
                OLD.feedback_count,
                OLD.verified_feedback_count,
                OLD.training_eligible_feedback_count,
                OLD.latest_prediction_at,
                OLD.account_state
            ) THEN
                RAISE EXCEPTION 'derived account metrics are read-only; edit auth fields only';
            END IF;

            NEW.username := BTRIM(NEW.username);
            NEW.email := NULLIF(LOWER(BTRIM(NEW.email)), '');

            PERFORM set_config('avm.skip_account_snapshot_refresh', '1', true);

            UPDATE auth.auth_accounts
            SET username = NEW.username,
                email = NEW.email,
                role = NEW.role,
                is_active = NEW.is_active
            WHERE id = OLD.account_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'auth account % no longer exists', OLD.account_id;
            END IF;

            INSERT INTO operations.audit_logs (
                record_id,
                table_name,
                action_type,
                changed_by,
                old_value_json,
                new_value_json,
                change_note
            ) VALUES (
                OLD.account_id,
                'auth.auth_accounts',
                'PGADMIN_ACCOUNT_UPDATE',
                'db:' || session_user,
                jsonb_build_object(
                    'username', OLD.username,
                    'email', OLD.email,
                    'role', OLD.role,
                    'is_active', OLD.is_active
                )::text,
                jsonb_build_object(
                    'username', NEW.username,
                    'email', NEW.email,
                    'role', NEW.role,
                    'is_active', NEW.is_active
                )::text,
                'Controlled edit through public.accounts; auth.auth_accounts remains canonical.'
            );

            NEW.refreshed_at := now();
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_apply_public_account_edit ON public.accounts")
    op.execute(
        """
        CREATE TRIGGER trg_apply_public_account_edit
        BEFORE UPDATE ON public.accounts
        FOR EACH ROW
        EXECUTE FUNCTION management.apply_public_account_edit()
        """
    )
    op.execute(
        """
        COMMENT ON TABLE public.accounts IS
        'PgAdmin account registry. Editable: username, email, role, is_active. '
        'Derived session/prediction columns are read-only and refresh from canonical domain tables.'
        """
    )
    for column in ("username", "email", "role", "is_active"):
        op.execute(
            f"COMMENT ON COLUMN public.accounts.{column} IS "
            "'Editable in pgAdmin; trigger writes through to auth.auth_accounts and creates an audit log.'"
        )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT UPDATE (username, email, role, is_active)
                    ON public.accounts TO real_estate_avm_app;
                GRANT EXECUTE ON FUNCTION management.apply_public_account_edit()
                    TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_apply_public_account_edit ON public.accounts")
    op.execute("DROP FUNCTION IF EXISTS management.apply_public_account_edit()")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION management.refresh_public_accounts_snapshot()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM management.refresh_public_accounts_snapshot_now();
            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        """
        COMMENT ON TABLE public.accounts IS
        'Bang read-model de pgAdmin thay account trong public.Tables; '
        'nguon ghi chinh van la auth.auth_accounts.'
        """
    )
