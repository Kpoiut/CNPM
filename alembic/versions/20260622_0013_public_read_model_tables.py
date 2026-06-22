"""Create pgAdmin-visible read-model tables with real values.

Revision ID: 20260622_0013
Revises: 20260622_0012
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op


revision = "20260622_0013"
down_revision = "20260622_0012"
branch_labels = None
depends_on = None


def _create_accounts_read_model() -> None:
    op.execute("DROP VIEW IF EXISTS public.accounts")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.accounts (
            account_id integer PRIMARY KEY,
            username character varying(100) NOT NULL,
            email character varying(200),
            role character varying(20) NOT NULL,
            is_active boolean NOT NULL,
            created_at timestamp without time zone,
            last_login timestamp without time zone,
            total_sessions bigint NOT NULL DEFAULT 0,
            active_sessions bigint NOT NULL DEFAULT 0,
            latest_session_at timestamp without time zone,
            prediction_count bigint NOT NULL DEFAULT 0,
            feedback_count bigint NOT NULL DEFAULT 0,
            verified_feedback_count bigint NOT NULL DEFAULT 0,
            training_eligible_feedback_count bigint NOT NULL DEFAULT 0,
            latest_prediction_at timestamp without time zone,
            account_state text NOT NULL,
            refreshed_at timestamp without time zone NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE public.accounts IS "
        "'Bang read-model de pgAdmin thay account trong public.Tables; nguon ghi chinh van la auth.auth_accounts.'"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION management.refresh_public_accounts_snapshot_now()
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO public.accounts (
                account_id, username, email, role, is_active, created_at, last_login,
                total_sessions, active_sessions, latest_session_at, prediction_count,
                feedback_count, verified_feedback_count, training_eligible_feedback_count,
                latest_prediction_at, account_state, refreshed_at
            )
            SELECT
                account_id, username, email, role, is_active, created_at, last_login,
                total_sessions, active_sessions, latest_session_at, prediction_count,
                feedback_count, verified_feedback_count, training_eligible_feedback_count,
                latest_prediction_at, account_state, now()
            FROM management.account_registry
            ON CONFLICT (account_id) DO UPDATE SET
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active,
                created_at = EXCLUDED.created_at,
                last_login = EXCLUDED.last_login,
                total_sessions = EXCLUDED.total_sessions,
                active_sessions = EXCLUDED.active_sessions,
                latest_session_at = EXCLUDED.latest_session_at,
                prediction_count = EXCLUDED.prediction_count,
                feedback_count = EXCLUDED.feedback_count,
                verified_feedback_count = EXCLUDED.verified_feedback_count,
                training_eligible_feedback_count = EXCLUDED.training_eligible_feedback_count,
                latest_prediction_at = EXCLUDED.latest_prediction_at,
                account_state = EXCLUDED.account_state,
                refreshed_at = EXCLUDED.refreshed_at;

            DELETE FROM public.accounts snapshot
            WHERE NOT EXISTS (
                SELECT 1 FROM auth.auth_accounts account
                WHERE account.id = snapshot.account_id
            );
        END;
        $$;
        """
    )
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
    for schema_table, trigger_name in (
        ("auth.auth_accounts", "trg_refresh_public_accounts_after_auth"),
        ("auth.auth_account_sessions", "trg_refresh_public_accounts_after_sessions"),
        ("public.valuation_runs", "trg_refresh_public_accounts_after_valuations"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {schema_table}")
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            AFTER INSERT OR UPDATE OR DELETE ON {schema_table}
            FOR EACH STATEMENT
            EXECUTE FUNCTION management.refresh_public_accounts_snapshot()
            """
        )
    op.execute("SELECT management.refresh_public_accounts_snapshot_now()")


def _seed_buyer_requirements_and_matches() -> None:
    op.execute(
        """
        INSERT INTO public.buyer_requirements (
            property_type, province_city, district, ward, project_preference,
            min_area, max_area, min_budget, max_budget, bedrooms,
            legal_requirement, urgency, source_type, source_url,
            source_description, is_active, notes
        )
        WITH profiles AS (
            SELECT
                property_type,
                province_city,
                district,
                percentile_cont(0.20) WITHIN GROUP (ORDER BY area_m2)::numeric AS min_area,
                percentile_cont(0.80) WITHIN GROUP (ORDER BY area_m2)::numeric AS max_area,
                percentile_cont(0.20) WITHIN GROUP (ORDER BY price)::numeric AS min_budget,
                percentile_cont(0.75) WITHIN GROUP (ORDER BY price)::numeric AS max_budget,
                percentile_cont(0.50) WITHIN GROUP (ORDER BY COALESCE(bedrooms, 2))::integer AS bedrooms,
                COUNT(*) AS sample_count
            FROM public.properties
            WHERE COALESCE(record_status, 'active') <> 'archived'
              AND price > 0
              AND area_m2 > 0
              AND property_type IS NOT NULL
              AND province_city IS NOT NULL
              AND district IS NOT NULL
            GROUP BY property_type, province_city, district
            HAVING COUNT(*) >= 10
        )
        SELECT
            property_type,
            province_city,
            district,
            NULL,
            NULL,
            GREATEST(10, ROUND(min_area::numeric, 1)),
            GREATEST(ROUND(min_area::numeric, 1), ROUND(max_area::numeric, 1)),
            GREATEST(100000000, ROUND(min_budget::numeric, -6)),
            GREATEST(ROUND(min_budget::numeric, -6), ROUND(max_budget::numeric, -6)),
            bedrooms,
            'any',
            CASE WHEN sample_count >= 100 THEN 'normal' ELSE 'flexible' END,
            'production_reference_profile',
            NULL,
            'Buyer demand read-model derived from real property distribution for supply-demand matching.',
            true,
            'Auto-seeded by Alembic 20260622_0013 so matched_pairs table has production reference value.'
        FROM profiles
        WHERE NOT EXISTS (
            SELECT 1 FROM public.buyer_requirements
            WHERE source_type = 'production_reference_profile'
        )
        """
    )
    op.execute(
        """
        INSERT INTO public.matched_pairs (
            listing_id, request_id, location_match_score, area_match_score,
            budget_gap, feature_match_score, is_potential_match,
            overlap_score, match_group
        )
        WITH candidates AS (
            SELECT
                p.id AS listing_id,
                br.id AS request_id,
                1.0::double precision AS location_match_score,
                CASE
                    WHEN p.area_m2 BETWEEN br.min_area AND br.max_area THEN 1.0
                    ELSE GREATEST(
                        0.0,
                        1.0 - ABS(p.area_m2 - ((br.min_area + br.max_area) / 2.0))
                              / GREATEST(1.0, br.max_area - br.min_area)
                    )
                END AS area_match_score,
                (p.price - br.max_budget)::double precision AS budget_gap,
                CASE
                    WHEN p.bedrooms IS NULL OR br.bedrooms IS NULL THEN 0.8
                    ELSE GREATEST(0.0, 1.0 - ABS(p.bedrooms - br.bedrooms) * 0.2)
                END AS bedroom_match_score,
                ROW_NUMBER() OVER (
                    PARTITION BY br.id
                    ORDER BY ABS(p.price - ((br.min_budget + br.max_budget) / 2.0)), p.id
                ) AS rn
            FROM public.properties p
            JOIN public.buyer_requirements br
              ON br.is_active
             AND br.property_type = p.property_type
             AND br.province_city = p.province_city
             AND br.district = p.district
             AND p.area_m2 BETWEEN br.min_area AND br.max_area
             AND p.price BETWEEN br.min_budget AND br.max_budget
            WHERE COALESCE(p.record_status, 'active') <> 'archived'
              AND p.price > 0
              AND p.area_m2 > 0
              AND br.source_type = 'production_reference_profile'
        ),
        scored AS (
            SELECT
                listing_id,
                request_id,
                location_match_score,
                area_match_score,
                budget_gap,
                ((location_match_score + area_match_score + bedroom_match_score) / 3.0)
                    AS feature_match_score,
                rn
            FROM candidates
            WHERE rn <= 15
        )
        SELECT
            listing_id,
            request_id,
            ROUND(location_match_score::numeric, 3),
            ROUND(area_match_score::numeric, 3),
            ROUND(budget_gap::numeric, -6),
            ROUND(feature_match_score::numeric, 3),
            feature_match_score >= 0.45 AND budget_gap <= 0,
            ROUND(
                GREATEST(0.0, LEAST(1.0, feature_match_score * (1.0 - GREATEST(0.0, budget_gap) / 10000000000.0)))::numeric,
                3
            ),
            'reference_' || listing_id || '_' || request_id
        FROM scored
        WHERE NOT EXISTS (
            SELECT 1 FROM public.matched_pairs mp
            WHERE mp.listing_id = scored.listing_id
              AND mp.request_id = scored.request_id
        )
        """
    )


def upgrade() -> None:
    _create_accounts_read_model()
    _seed_buyer_requirements_and_matches()
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT ON public.accounts TO real_estate_avm_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON public.buyer_requirements TO real_estate_avm_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON public.matched_pairs TO real_estate_avm_app;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    for schema_table, trigger_name in (
        ("public.valuation_runs", "trg_refresh_public_accounts_after_valuations"),
        ("auth.auth_account_sessions", "trg_refresh_public_accounts_after_sessions"),
        ("auth.auth_accounts", "trg_refresh_public_accounts_after_auth"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {schema_table}")
    op.execute("DROP FUNCTION IF EXISTS management.refresh_public_accounts_snapshot()")
    op.execute("DROP FUNCTION IF EXISTS management.refresh_public_accounts_snapshot_now()")
    op.execute("DROP TABLE IF EXISTS public.accounts")
    op.execute(
        """
        CREATE OR REPLACE VIEW public.accounts AS
        SELECT *
        FROM management.account_registry
        """
    )
