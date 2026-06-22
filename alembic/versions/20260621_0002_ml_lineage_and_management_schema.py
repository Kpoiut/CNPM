"""Add ML lineage and a clean operator-facing PostgreSQL schema.

Revision ID: 20260621_0002
Revises: 20260620_0001
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260621_0002"
down_revision = "20260620_0001"
branch_labels = None
depends_on = None


LEGACY_EMPTY_OBJECTS = (
    "access_context",
    "ai_training_candidates",
    "apartment_attributes",
    "appeal_cases",
    "baseline_models",
    "building_unit",
    "buyer_requirements",
    "challenges",
    "claim_court_sessions",
    "claim_evidence",
    "claims",
    "coalition_flags",
    "community_comments",
    "confidence_band",
    "data_sources",
    "environment_context",
    "evidence_asset",
    "legal_planning",
    "location_context",
    "matched_pairs",
    "parcel_geometry",
    "prediction_bonds",
    "prediction_history",
    "predictions",
    "private_insights",
    "reputation_ledger",
    "spiritual_history",
    "training_run",
    "valuation_adjustments",
    "valuation_scenarios",
)


def _table_names(schema: str = "public") -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=schema))


def _column_names(table: str, schema: str = "public") -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table, schema=schema)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _column_names(table):
        op.add_column(table, column)


def _create_lineage_tables() -> None:
    tables = _table_names()
    if "dataset_versions" not in tables:
        op.create_table(
            "dataset_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("snapshot_key", sa.String(100), nullable=False),
            sa.Column("source_table", sa.String(100), nullable=False, server_default="properties"),
            sa.Column("record_count", sa.Integer(), nullable=False),
            sa.Column("eligible_record_count", sa.Integer()),
            sa.Column("selection_query", sa.Text()),
            sa.Column("checksum_sha256", sa.String(64)),
            sa.Column("notes", sa.Text()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("snapshot_key", name="uq_dataset_versions_snapshot_key"),
        )
        op.create_index("ix_dataset_versions_snapshot_key", "dataset_versions", ["snapshot_key"])
        op.create_index("ix_dataset_versions_checksum_sha256", "dataset_versions", ["checksum_sha256"])

    tables = _table_names()
    if "training_runs" not in tables:
        op.create_table(
            "training_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_version", sa.String(50), nullable=False),
            sa.Column("dataset_version_id", sa.Integer(), nullable=False),
            sa.Column("parent_training_run_id", sa.Integer()),
            sa.Column("status", sa.String(30), nullable=False, server_default="completed"),
            sa.Column("algorithm", sa.String(120)),
            sa.Column("random_seed", sa.Integer()),
            sa.Column("train_record_count", sa.Integer()),
            sa.Column("validation_record_count", sa.Integer()),
            sa.Column("test_record_count", sa.Integer()),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("finished_at", sa.DateTime()),
            sa.Column("artifact_path", sa.String(500)),
            sa.Column("metadata_path", sa.String(500)),
            sa.Column("notes", sa.Text()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
            sa.ForeignKeyConstraint(["parent_training_run_id"], ["training_runs.id"]),
            sa.UniqueConstraint("run_version", name="uq_training_runs_run_version"),
        )
        op.create_index("ix_training_runs_run_version", "training_runs", ["run_version"])
        op.create_index("ix_training_runs_dataset_version_id", "training_runs", ["dataset_version_id"])
        op.create_index("ix_training_runs_status", "training_runs", ["status"])

    tables = _table_names()
    if "training_metrics" not in tables:
        op.create_table(
            "training_metrics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("training_run_id", sa.Integer(), nullable=False),
            sa.Column("split_name", sa.String(30), nullable=False),
            sa.Column("metric_name", sa.String(50), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["training_run_id"], ["training_runs.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("training_run_id", "split_name", "metric_name", name="uq_training_metric"),
        )
        op.create_index("ix_training_metrics_training_run_id", "training_metrics", ["training_run_id"])
        op.create_index("ix_training_metrics_metric_name", "training_metrics", ["metric_name"])


def _extend_existing_tables() -> None:
    for column in (
        sa.Column("training_run_id", sa.Integer(), sa.ForeignKey("training_runs.id"), nullable=True),
        sa.Column("parent_model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=True),
        sa.Column("mape", sa.Float()),
        sa.Column("median_ae", sa.Float()),
        sa.Column("status", sa.String(30), nullable=False, server_default="candidate"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("improvement_mape_pct_points", sa.Float()),
        sa.Column("activated_at", sa.DateTime()),
        sa.Column("metadata_path", sa.String(500)),
        sa.Column("artifact_sha256", sa.String(64)),
    ):
        _add_column_if_missing("model_versions", column)

    for column in (
        sa.Column("model_version_id", sa.Integer(), sa.ForeignKey("model_versions.id"), nullable=True),
        sa.Column("input_features_json", sa.JSON()),
        sa.Column("actual_price_vnd", sa.Float()),
        sa.Column("actual_price_recorded_at", sa.DateTime()),
        sa.Column("actual_price_source", sa.String(100)),
        sa.Column("training_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("training_used_at", sa.DateTime()),
    ):
        _add_column_if_missing("valuation_runs", column)

    op.execute("CREATE INDEX IF NOT EXISTS ix_model_versions_training_run_id ON public.model_versions (training_run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_versions_status ON public.model_versions (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_versions_is_active ON public.model_versions (is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_valuation_runs_model_version_id ON public.valuation_runs (model_version_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_valuation_runs_training_eligible ON public.valuation_runs (training_eligible)")


def _separate_compatibility_objects() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS archive_empty")
    op.execute("CREATE SCHEMA IF NOT EXISTS compatibility")

    for name in LEGACY_EMPTY_OBJECTS:
        op.execute(
            sa.text(
                f"""
                DO $$
                DECLARE object_kind \"char\";
                DECLARE object_rows bigint;
                BEGIN
                    SELECT c.relkind INTO object_kind
                    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relname = '{name}';

                    IF object_kind = 'r' THEN
                        EXECUTE 'SELECT COUNT(*) FROM public.\"{name}\"' INTO object_rows;
                        IF object_rows = 0 THEN
                            EXECUTE 'ALTER TABLE public.\"{name}\" SET SCHEMA archive_empty';
                            EXECUTE 'CREATE OR REPLACE VIEW compatibility.\"{name}\" AS SELECT * FROM archive_empty.\"{name}\"';
                        END IF;
                    ELSIF object_kind = 'v' THEN
                        EXECUTE 'ALTER VIEW public.\"{name}\" SET SCHEMA compatibility';
                    END IF;
                END $$;
                """
            )
        )

    for legacy_auth_view in ("users", "user_sessions", "refresh_tokens"):
        op.execute(
            f"""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relname = '{legacy_auth_view}' AND c.relkind = 'v'
                ) THEN
                    ALTER VIEW public.\"{legacy_auth_view}\" SET SCHEMA compatibility;
                END IF;
            END $$;
            """
        )

    op.execute("SELECT set_config('search_path', 'public,compatibility', false)")
    op.execute(
        """
        DO $$ BEGIN
            EXECUTE format(
                'ALTER ROLE %I IN DATABASE %I SET search_path = public, compatibility',
                current_user,
                current_database()
            );
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                ALTER ROLE real_estate_avm_app IN DATABASE real_estate_avm
                    SET search_path = public, compatibility;
            END IF;
        END $$;
        """
    )


def _create_management_views() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS management")
    op.execute(
        """
        CREATE OR REPLACE VIEW management.property_dataset_full AS
        SELECT * FROM public.properties
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW management.prediction_history AS
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
    op.execute(
        """
        CREATE OR REPLACE VIEW management.model_registry AS
        SELECT
            mv.id,
            mv.model_version,
            mv.model_name,
            mv.status,
            mv.is_active,
            mv.trained_at,
            mv.mae,
            mv.mape,
            mv.rmse,
            mv.r2,
            mv.improvement_mape_pct_points,
            tr.run_version AS training_run,
            dv.snapshot_key AS dataset_version,
            dv.record_count AS dataset_records,
            mv.model_path,
            mv.metadata_path
        FROM public.model_versions mv
        LEFT JOIN public.training_runs tr ON tr.id = mv.training_run_id
        LEFT JOIN public.dataset_versions dv ON dv.id = tr.dataset_version_id
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW management.training_history AS
        SELECT
            tr.id,
            tr.run_version,
            tr.status,
            tr.algorithm,
            tr.started_at,
            tr.finished_at,
            tr.train_record_count,
            tr.validation_record_count,
            tr.test_record_count,
            dv.snapshot_key AS dataset_version,
            dv.record_count AS dataset_records,
            MAX(tm.metric_value) FILTER (WHERE tm.split_name = 'test' AND tm.metric_name = 'mape') AS test_mape,
            MAX(tm.metric_value) FILTER (WHERE tm.split_name = 'test' AND tm.metric_name = 'mae') AS test_mae,
            MAX(tm.metric_value) FILTER (WHERE tm.split_name = 'test' AND tm.metric_name = 'rmse') AS test_rmse,
            MAX(tm.metric_value) FILTER (WHERE tm.split_name = 'test' AND tm.metric_name = 'r2') AS test_r2
        FROM public.training_runs tr
        JOIN public.dataset_versions dv ON dv.id = tr.dataset_version_id
        LEFT JOIN public.training_metrics tm ON tm.training_run_id = tr.id
        GROUP BY tr.id, dv.snapshot_key, dv.record_count
        """
    )
    op.execute("COMMENT ON SCHEMA management IS 'Vùng quản trị dễ đọc; chỉ chứa dữ liệu vận hành có giá trị.'")
    op.execute("COMMENT ON VIEW management.property_dataset_full IS 'Toàn bộ 3.000+ mẫu bất động sản đang dùng.'")
    op.execute("COMMENT ON VIEW management.prediction_history IS 'Mỗi lần định giá, model sử dụng và phản hồi giá thực tế phục vụ retraining.'")
    op.execute("COMMENT ON VIEW management.model_registry IS 'Danh mục model, metric, dataset và trạng thái active.'")
    op.execute("COMMENT ON VIEW management.training_history IS 'Lịch sử train và metric test theo từng chu kỳ.'")


def _grant_runtime_access() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT USAGE ON SCHEMA public, compatibility, archive_empty, management TO real_estate_avm_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO real_estate_avm_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA compatibility TO real_estate_avm_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA archive_empty TO real_estate_avm_app;
                GRANT SELECT ON ALL TABLES IN SCHEMA management TO real_estate_avm_app;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public, archive_empty TO real_estate_avm_app;
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    _create_lineage_tables()
    _extend_existing_tables()
    _separate_compatibility_objects()
    _create_management_views()
    _grant_runtime_access()


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP SCHEMA IF EXISTS management CASCADE")
    # Compatibility/archive schemas intentionally remain: downgrading must not
    # destroy archived data or silently reintroduce clutter into public.
