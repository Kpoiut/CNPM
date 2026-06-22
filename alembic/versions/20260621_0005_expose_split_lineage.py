"""Expose dataset and split checksums in management views.

Revision ID: 20260621_0005
Revises: 20260621_0004
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op


revision = "20260621_0005"
down_revision = "20260621_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
            mv.metadata_path,
            dv.checksum_sha256 AS dataset_checksum_sha256,
            tr.notes AS split_manifest_summary
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
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'mape'
            ) AS test_mape,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'mae'
            ) AS test_mae,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'rmse'
            ) AS test_rmse,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'r2'
            ) AS test_r2,
            dv.checksum_sha256 AS dataset_checksum_sha256,
            tr.notes AS split_manifest_summary
        FROM public.training_runs tr
        JOIN public.dataset_versions dv ON dv.id = tr.dataset_version_id
        LEFT JOIN public.training_metrics tm ON tm.training_run_id = tr.id
        GROUP BY tr.id, dv.snapshot_key, dv.record_count, dv.checksum_sha256
        """
    )


def downgrade() -> None:
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
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'mape'
            ) AS test_mape,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'mae'
            ) AS test_mae,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'rmse'
            ) AS test_rmse,
            MAX(tm.metric_value) FILTER (
                WHERE tm.split_name = 'test' AND tm.metric_name = 'r2'
            ) AS test_r2
        FROM public.training_runs tr
        JOIN public.dataset_versions dv ON dv.id = tr.dataset_version_id
        LEFT JOIN public.training_metrics tm ON tm.training_run_id = tr.id
        GROUP BY tr.id, dv.snapshot_key, dv.record_count
        """
    )
