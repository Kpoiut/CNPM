"""Restore prediction history as an active production table.

Revision ID: 20260621_0003
Revises: 20260621_0002
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260621_0003"
down_revision = "20260621_0002"
branch_labels = None
depends_on = None


def _restore_prediction_history_table() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF to_regclass('public.prediction_history') IS NULL
               AND to_regclass('archive_empty.prediction_history') IS NOT NULL THEN
                ALTER TABLE archive_empty.prediction_history SET SCHEMA public;
            END IF;
        END $$;
        """
    )

    inspector = sa.inspect(op.get_bind())
    if "prediction_history" not in inspector.get_table_names(schema="public"):
        op.create_table(
            "prediction_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id")),
            sa.Column("input_features_json", sa.Text()),
            sa.Column("predicted_price", sa.Float(), nullable=False),
            sa.Column("confidence_low", sa.Float()),
            sa.Column("confidence_high", sa.Float()),
            sa.Column("model_version", sa.String(50)),
            sa.Column("model_name", sa.String(100)),
            sa.Column("feature_importance_json", sa.Text()),
            sa.Column("similar_records_json", sa.Text()),
            sa.Column("explanation_text", sa.Text()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prediction_history_id "
        "ON public.prediction_history (id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prediction_history_property_id "
        "ON public.prediction_history (property_id)"
    )
def _create_unified_management_view() -> None:
    op.execute("DROP VIEW IF EXISTS management.prediction_history")
    op.execute(
        """
        CREATE VIEW management.prediction_history AS
        SELECT
            'api_v2_valuation'::text AS source_endpoint,
            vr.id AS prediction_id,
            vr.created_at AS predicted_at,
            vr.property_id,
            vr.input_features_json::text AS input_features_json,
            vr.fair_market_value_vnd AS predicted_price_vnd,
            vr.expected_range_low_vnd,
            vr.expected_range_high_vnd,
            vr.overall_confidence,
            vr.confidence_grade,
            vr.comparable_count,
            vr.actual_price_vnd,
            vr.actual_price_recorded_at,
            vr.training_eligible,
            vr.training_used_at,
            mv.model_version,
            mv.model_name
        FROM public.valuation_runs vr
        LEFT JOIN public.model_versions mv ON mv.id = vr.model_version_id

        UNION ALL

        SELECT
            'api_predict'::text AS source_endpoint,
            ph.id AS prediction_id,
            ph.created_at AS predicted_at,
            ph.property_id,
            ph.input_features_json,
            ph.predicted_price AS predicted_price_vnd,
            ph.confidence_low AS expected_range_low_vnd,
            ph.confidence_high AS expected_range_high_vnd,
            NULL::double precision AS overall_confidence,
            NULL::character varying AS confidence_grade,
            NULL::integer AS comparable_count,
            NULL::double precision AS actual_price_vnd,
            NULL::timestamp without time zone AS actual_price_recorded_at,
            false AS training_eligible,
            NULL::timestamp without time zone AS training_used_at,
            ph.model_version,
            ph.model_name
        FROM public.prediction_history ph
        """
    )
    op.execute(
        """
        COMMENT ON VIEW management.prediction_history IS
        'Lịch sử hợp nhất từ /api/predict và /api/v2/valuation, kèm model và phản hồi giá thực tế.'
        """
    )


def upgrade() -> None:
    _restore_prediction_history_table()
    _create_unified_management_view()


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.prediction_history")
    op.execute(
        """
        CREATE VIEW management.prediction_history AS
        SELECT
            vr.id AS prediction_id,
            vr.created_at AS predicted_at,
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
            vr.training_eligible,
            vr.training_used_at,
            mv.model_version,
            mv.model_name
        FROM public.valuation_runs vr
        LEFT JOIN public.model_versions mv ON mv.id = vr.model_version_id
        """
    )
