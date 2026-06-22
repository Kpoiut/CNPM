"""Add operational value to the PostgreSQL catalog and prediction history.

Revision ID: 20260622_0010
Revises: 20260621_0009
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op


revision = "20260622_0010"
down_revision = "20260621_0009"
branch_labels = None
depends_on = None


COLUMN_COMMENTS = {
    "public.valuation_runs.request_id": "Correlation id duy nhất để truy vết một lần dự đoán xuyên API, log và feedback.",
    "public.valuation_runs.account_id": "Account thực hiện dự đoán; NULL chỉ dành cho luồng public được cho phép.",
    "public.valuation_runs.source_endpoint": "Endpoint/engine tạo bản ghi dự đoán canonical.",
    "public.valuation_runs.request_latency_ms": "Thời gian xử lý backend của lần dự đoán, đơn vị millisecond.",
    "public.valuation_runs.model_version_snapshot": "Version model thực sự phục vụ tại thời điểm dự đoán.",
    "public.valuation_runs.input_features_json": "Input đã chuẩn hóa để audit và tái tạo mẫu training sau xác minh.",
    "public.valuation_runs.result_json": "Output đầy đủ của engine tại thời điểm dự đoán.",
    "public.valuation_runs.actual_price_vnd": "Giá giao dịch/tham chiếu thực tế do user hoặc admin bổ sung.",
    "public.valuation_runs.feedback_verification_status": "Trạng thái kiểm duyệt giá thật: not_submitted, pending_review, verified hoặc rejected.",
    "public.valuation_runs.training_eligible": "Chỉ true khi feedback và input đã qua policy xác minh để xét retrain.",
    "public.valuation_runs.training_exclusion_reason": "Lý do bản ghi chưa hoặc không được phép vào training queue.",
    "public.valuation_runs.training_run_id": "Training run đã sử dụng feedback này; NULL nghĩa là chưa dùng.",
    "public.valuation_runs.training_used_at": "Thời điểm feedback được đưa vào một training run.",
    "public.collection_sources.source_key": "Domain/key canonical dùng nối cấu hình nguồn với properties.source_domain.",
    "public.collection_sources.source_type": "Kiểu tích hợp: scraper, api, manual_entry hoặc field_survey.",
    "public.collection_sources.rate_limit_seconds": "Khoảng nghỉ tối thiểu giữa hai request tới nguồn.",
    "public.collection_sources.is_active": "Cho phép collector chạy với nguồn này.",
    "public.collection_sources.is_approved": "Nguồn đã được phê duyệt dùng trong pipeline production.",
    "public.collection_sources.total_records": "Tổng property hiện có trong PostgreSQL theo source_domain.",
    "public.collection_sources.successful_records": "Số property không archived hiện có theo source_domain.",
    "public.collection_sources.failed_records": "Tổng lần thu thập thất bại do collector ghi nhận.",
    "public.collection_sources.last_run_status": "Trạng thái lần chạy gần nhất: success, partial hoặc failed.",
}


def _quote(value: str) -> str:
    return value.replace("'", "''")


def _ensure_check(name: str, expression: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{name}'
                  AND conrelid = 'public.valuation_runs'::regclass
            ) THEN
                ALTER TABLE public.valuation_runs
                ADD CONSTRAINT {name} CHECK ({expression}) NOT VALID;
            END IF;
        END $$;
        """
    )
    op.execute(f"ALTER TABLE public.valuation_runs VALIDATE CONSTRAINT {name}")


def _refresh_collection_source_stats() -> None:
    op.execute(
        """
        WITH actual AS (
            SELECT
                source_domain,
                COUNT(*)::integer AS total_records,
                COUNT(*) FILTER (WHERE record_status <> 'archived')::integer
                    AS successful_records
            FROM public.properties
            WHERE source_domain IS NOT NULL AND btrim(source_domain) <> ''
            GROUP BY source_domain
        )
        UPDATE public.collection_sources AS source
        SET total_records = actual.total_records,
            successful_records = actual.successful_records,
            updated_at = now()
        FROM actual
        WHERE source.source_key = actual.source_domain
          AND (
              source.total_records IS DISTINCT FROM actual.total_records
              OR source.successful_records IS DISTINCT FROM actual.successful_records
          )
        """
    )


def _create_collection_source_health() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW management.collection_source_health AS
        WITH actual AS (
            SELECT
                source_domain,
                COUNT(*)::bigint AS actual_records,
                COUNT(*) FILTER (
                    WHERE record_status <> 'archived' AND price > 0 AND area_m2 > 0
                )::bigint AS training_ready_records,
                COUNT(*) FILTER (WHERE verification_status = 'verified')::bigint
                    AS verified_records,
                MAX(COALESCE(source_collected_at, source_crawl_at, collected_at, created_at))
                    AS latest_data_at
            FROM public.properties
            WHERE source_domain IS NOT NULL AND btrim(source_domain) <> ''
            GROUP BY source_domain
        )
        SELECT
            source.id,
            source.source_key,
            source.source_name,
            source.source_type,
            source.base_url,
            source.is_active,
            source.is_approved,
            source.rate_limit_seconds,
            COALESCE(actual.actual_records, 0) AS actual_records,
            COALESCE(actual.training_ready_records, 0) AS training_ready_records,
            COALESCE(actual.verified_records, 0) AS verified_records,
            source.failed_records,
            source.last_run_at,
            source.last_run_status,
            actual.latest_data_at,
            CASE
                WHEN NOT source.is_active THEN 'disabled'
                WHEN COALESCE(actual.actual_records, 0) = 0 THEN 'no_data'
                WHEN source.total_records IS DISTINCT FROM COALESCE(actual.actual_records, 0)
                    THEN 'counter_mismatch'
                WHEN source.is_approved THEN 'healthy'
                ELSE 'pending_approval'
            END AS data_state
        FROM public.collection_sources AS source
        LEFT JOIN actual ON actual.source_domain = source.source_key
        ORDER BY source.source_key
        """
    )
    op.execute(
        "COMMENT ON VIEW management.collection_source_health IS "
        "'Tình trạng nguồn thu thập từ cấu hình và số record thực tế trong PostgreSQL.'"
    )


def _create_database_catalog() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW management.database_catalog AS
        SELECT
            namespace.nspname AS schema_name,
            class.relname AS object_name,
            CASE class.relkind
                WHEN 'r' THEN 'table'
                WHEN 'v' THEN 'view'
                WHEN 'm' THEN 'materialized_view'
                ELSE class.relkind::text
            END AS object_type,
            CASE
                WHEN class.relkind = 'r'
                    THEN COALESCE(stats.n_live_tup, GREATEST(class.reltuples, 0)::bigint, 0)
                ELSE 0::bigint
            END AS estimated_rows,
            CASE WHEN class.relkind = 'r' THEN pg_total_relation_size(class.oid) END AS total_bytes,
            obj_description(class.oid, 'pg_class') AS purpose,
            ARRAY(
                SELECT attribute.attname
                FROM pg_index AS index_meta
                JOIN LATERAL unnest(index_meta.indkey) WITH ORDINALITY
                    AS key_column(attnum, position) ON true
                JOIN pg_attribute AS attribute
                  ON attribute.attrelid = index_meta.indrelid
                 AND attribute.attnum = key_column.attnum
                WHERE index_meta.indrelid = class.oid AND index_meta.indisprimary
                ORDER BY key_column.position
            ) AS primary_key_columns,
            (
                SELECT COUNT(*) FROM pg_constraint AS constraint_meta
                WHERE constraint_meta.conrelid = class.oid
                  AND constraint_meta.contype = 'f'
            ) AS foreign_key_count,
            (
                SELECT COUNT(*) FROM pg_index AS index_meta
                WHERE index_meta.indrelid = class.oid
            ) AS index_count,
            CASE
                WHEN class.relkind IN ('v', 'm') THEN 'derived_view'
                WHEN COALESCE(stats.n_live_tup, GREATEST(class.reltuples, 0)::bigint, 0) = 0
                    THEN 'empty_ready'
                ELSE 'active_data'
            END AS data_state,
            GREATEST(stats.last_analyze, stats.last_autoanalyze) AS last_analyzed_at
        FROM pg_class AS class
        JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
        LEFT JOIN pg_stat_user_tables AS stats ON stats.relid = class.oid
        WHERE namespace.nspname IN (
            'public', 'auth', 'ml', 'community', 'operations', 'management'
        )
          AND class.relkind IN ('r', 'v', 'm')
          AND class.relname NOT LIKE 'pg_%'
        ORDER BY
            CASE namespace.nspname
                WHEN 'public' THEN 1 WHEN 'auth' THEN 2 WHEN 'ml' THEN 3
                WHEN 'community' THEN 4 WHEN 'operations' THEN 5
                WHEN 'management' THEN 6 ELSE 7
            END,
            class.relname
        """
    )
    op.execute(
        "COMMENT ON VIEW management.database_catalog IS "
        "'Mục lục PostgreSQL cho pgAdmin: purpose, row estimate, dung lượng, PK/FK/index và trạng thái dữ liệu.'"
    )


def upgrade() -> None:
    _ensure_check(
        "ck_valuation_runs_non_negative_latency",
        "request_latency_ms IS NULL OR request_latency_ms >= 0",
    )
    _ensure_check(
        "ck_valuation_runs_confidence_range",
        "overall_confidence IS NULL OR overall_confidence BETWEEN 0 AND 1",
    )
    _ensure_check(
        "ck_valuation_runs_positive_prices",
        "fair_market_value_vnd IS NULL OR fair_market_value_vnd > 0",
    )
    _ensure_check(
        "ck_valuation_runs_valid_expected_range",
        "expected_range_low_vnd IS NULL OR expected_range_high_vnd IS NULL "
        "OR expected_range_low_vnd <= expected_range_high_vnd",
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_valuation_runs_training_feedback_queue
        ON public.valuation_runs (created_at DESC)
        INCLUDE (request_id, account_id, actual_price_vnd)
        WHERE training_eligible
          AND feedback_verification_status = 'verified'
          AND training_used_at IS NULL
        """
    )

    _refresh_collection_source_stats()
    _create_collection_source_health()
    _create_database_catalog()

    for qualified_name, comment in COLUMN_COMMENTS.items():
        op.execute(f"COMMENT ON COLUMN {qualified_name} IS '{_quote(comment)}'")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'real_estate_avm_app') THEN
                GRANT SELECT ON management.collection_source_health TO real_estate_avm_app;
                GRANT SELECT ON management.database_catalog TO real_estate_avm_app;
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS management.collection_source_health")
    op.execute("DROP INDEX IF EXISTS public.ix_valuation_runs_training_feedback_queue")
    for constraint_name in (
        "ck_valuation_runs_valid_expected_range",
        "ck_valuation_runs_positive_prices",
        "ck_valuation_runs_confidence_range",
        "ck_valuation_runs_non_negative_latency",
    ):
        op.execute(
            f"ALTER TABLE public.valuation_runs DROP CONSTRAINT IF EXISTS {constraint_name}"
        )

    for qualified_name in COLUMN_COMMENTS:
        op.execute(f"COMMENT ON COLUMN {qualified_name} IS NULL")

    op.execute("DROP VIEW IF EXISTS management.database_catalog")
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
            CASE WHEN c.relkind = 'r' THEN pg_total_relation_size(c.oid) END AS total_bytes,
            obj_description(c.oid, 'pg_class') AS purpose
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'auth', 'ml', 'community', 'operations', 'management')
          AND c.relkind IN ('r', 'v', 'm')
          AND c.relname NOT LIKE 'pg_%'
        ORDER BY c.relname
        """
    )
