"""Read-only PostgreSQL catalog audit for operators and migration checks."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import inspect, text


PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))
for env_name in (".env", ".env.postgres.local"):
    env_path = PROJECT_ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break

from src.backend.database import engine  # noqa: E402


def _json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows(connection, sql: str) -> list[dict]:
    return [
        {key: _json_safe(value) for key, value in row.items()}
        for row in connection.execute(text(sql)).mappings().all()
    ]


def audit_catalog(*, exact_counts: bool = False) -> dict:
    inspector = inspect(engine)
    visible_schemas = (
        "public",
        "auth",
        "ml",
        "community",
        "operations",
        "management",
    )
    schemas = [
        schema
        for schema in visible_schemas
        if schema in inspector.get_schema_names()
    ]
    objects: list[dict] = []

    summaries = {}
    with engine.connect() as connection:
        catalog_rows = _rows(
            connection,
            """
            SELECT schema_name, object_name, estimated_rows, total_bytes, purpose,
                   primary_key_columns, foreign_key_count, index_count, data_state,
                   last_analyzed_at
            FROM management.database_catalog
            """,
        )
        catalog_by_key = {
            (row["schema_name"], row["object_name"]): row
            for row in catalog_rows
        }

        for schema in schemas:
            for table in sorted(inspector.get_table_names(schema=schema)):
                metadata = catalog_by_key.get((schema, table), {})
                row_count = (
                    connection.execute(
                        text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                    ).scalar_one()
                    if exact_counts
                    else metadata.get("estimated_rows", 0)
                )
                objects.append(
                    {
                        "schema": schema,
                        "name": table,
                        "kind": "table",
                        "rows": int(row_count),
                        "row_count_mode": "exact" if exact_counts else "estimated",
                        "primary_key_columns": metadata.get("primary_key_columns", []),
                        "foreign_keys": int(metadata.get("foreign_key_count", 0)),
                        "index_count": int(metadata.get("index_count", 0)),
                        "total_bytes": metadata.get("total_bytes"),
                        "purpose": metadata.get("purpose"),
                        "data_state": metadata.get("data_state"),
                        "last_analyzed_at": metadata.get("last_analyzed_at"),
                    }
                )

            for view in sorted(inspector.get_view_names(schema=schema)):
                metadata = catalog_by_key.get((schema, view), {})
                row_count = (
                    connection.execute(
                        text(f'SELECT COUNT(*) FROM "{schema}"."{view}"')
                    ).scalar_one()
                    if exact_counts
                    else metadata.get("estimated_rows", 0)
                )
                objects.append(
                    {
                        "schema": schema,
                        "name": view,
                        "kind": "view",
                        "rows": int(row_count),
                        "row_count_mode": "exact" if exact_counts else "estimated",
                        "primary_key_columns": [],
                        "foreign_keys": None,
                        "index_count": 0,
                        "total_bytes": metadata.get("total_bytes"),
                        "purpose": metadata.get("purpose"),
                        "data_state": metadata.get("data_state"),
                        "last_analyzed_at": metadata.get("last_analyzed_at"),
                    }
                )

        if engine.dialect.name == "postgresql" and "management" in schemas:
            summaries = {
                "dataset": _rows(
                    connection,
                    """
                    SELECT
                        COUNT(*) AS total_records,
                        COUNT(*) FILTER (
                            WHERE record_status <> 'archived'
                              AND price > 0
                              AND area_m2 > 0
                        ) AS training_eligible_records,
                        COUNT(*) FILTER (
                            WHERE verification_status = 'verified'
                        ) AS verified_records
                    FROM management.property_dataset_full
                    """,
                )[0],
                "prediction_by_endpoint": _rows(
                    connection,
                    """
                    SELECT source_endpoint, COUNT(*) AS prediction_count
                    FROM management.prediction_history
                    GROUP BY source_endpoint
                    ORDER BY source_endpoint
                    """,
                ),
                "active_model": _rows(
                    connection,
                    """
                    SELECT model_version, model_name, status, mape, mae, r2,
                           dataset_version, dataset_records
                    FROM management.model_registry
                    WHERE is_active
                    ORDER BY trained_at DESC
                    LIMIT 1
                    """,
                ),
                "latest_training_runs": _rows(
                    connection,
                    """
                    SELECT run_version, dataset_version, dataset_records,
                           train_record_count, validation_record_count,
                           test_record_count, test_mape, test_mae, test_r2,
                           dataset_checksum_sha256, split_manifest_summary,
                           finished_at
                    FROM management.training_history
                    ORDER BY finished_at DESC NULLS LAST
                    LIMIT 5
                    """,
                ),
            }

    return {
        "dialect": engine.dialect.name,
        "summaries": summaries,
        "objects": objects,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exact-counts",
        action="store_true",
        help="Dùng COUNT(*) cho evidence CI; bỏ cờ này để audit production nhẹ hơn.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            audit_catalog(exact_counts=args.exact_counts),
            ensure_ascii=False,
            indent=2,
        )
    )
