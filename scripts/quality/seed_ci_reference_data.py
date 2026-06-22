"""Seed minimal production-like reference data for CI PostgreSQL gates.

This script is intentionally small and idempotent. It does not replace the real
production dataset; it gives fresh CI databases enough account, property, buyer
requirement and match rows for release-gate tests and Nova contextual answers.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import text


os.environ.setdefault("JWT_SECRET_KEY", "ci-reference-seed-jwt-secret")

from src.backend.auth.service import hash_password  # noqa: E402
from src.backend.database import engine  # noqa: E402


CI_PASSWORD = "CodexCiReference!2026"


def _reference_accounts() -> list[dict[str, object]]:
    hashed = hash_password(CI_PASSWORD)
    rows = [
        {
            "username": "ci_admin",
            "email": "ci-admin@example.test",
            "role": "admin",
            "hashed_password": hashed,
        }
    ]
    rows.extend(
        {
            "username": f"ci_user_{idx:02d}",
            "email": f"ci-user-{idx:02d}@example.test",
            "role": "user",
            "hashed_password": hashed,
        }
        for idx in range(1, 13)
    )
    return rows


def _reference_properties(now: datetime) -> list[dict[str, object]]:
    raw_rows = [
        ("townhouse", "Phu Thuan", "Huynh Tan Phat", 7.70, 126.5, 3, 2, 3.0),
        ("land", "Phu Thuan", "Huynh Tan Phat", 7.20, 57.0, 3, 3, 4.1),
        ("townhouse", "Tan Phu", "Huynh Tan Phat", 7.00, 115.0, 3, 1, 5.0),
        ("townhouse", "Binh Thuan", "Huynh Tan Phat", 6.90, 45.0, 3, 4, 5.5),
        ("townhouse", "Phu My", "Huynh Tan Phat", 6.80, 55.0, 4, 4, 5.7),
        ("apartment", "Tan Phong", "River Valley", 2.00, 35.0, 2, 2, 4.0),
        ("apartment", "Tan Quy", "Reference Apartment", 1.90, 49.0, 2, 1, 4.3),
        ("townhouse", "Phu Thuan", "Huynh Tan Phat", 1.86, 21.0, 2, 2, 3.0),
        ("townhouse", "Tan Thuan Tay", "Huynh Tan Phat", 1.75, 19.0, 1, 2, 2.4),
        ("townhouse", "Tan Kieng", "Tran Xuan Soan", 4.50, 52.0, 3, 3, 4.0),
        ("townhouse", "Tan Hung", "Nguyen Thi Thap", 5.20, 64.0, 3, 3, 4.2),
        ("apartment", "Tan Phong", "Nguyen Luong Bang", 3.20, 68.0, 2, 1, 5.0),
    ]
    rows: list[dict[str, object]] = []
    for idx, (ptype, ward, street, price_billion, area, bedrooms, floors, frontage) in enumerate(raw_rows, 1):
        price = int(price_billion * 1_000_000_000)
        rows.append(
            {
                "property_type": ptype,
                "province_city": "TP. Ho Chi Minh",
                "district": "Quận 7",
                "ward": ward,
                "street_or_project": street,
                "area_m2": area,
                "bedrooms": bedrooms,
                "bathrooms": max(1, bedrooms - 1),
                "floor_count": floors,
                "frontage_m": frontage,
                "legal_status": "ownership_certificate",
                "price": price,
                "price_per_m2": price / area,
                "listing_date": now,
                "is_transacted": False,
                "source_name": "ci_reference_dataset",
                "source_url": f"https://example.test/ci-reference/{idx}",
                "source_page_title": f"CI reference property {idx}",
                "source_collected_at": now,
                "source_access_method": "ci_seed",
                "source_domain": "example.test",
                "source_category": "ci_reference",
                "record_status": "verified",
                "verification_status": "verified",
                "data_origin_type": "system_demo",
                "evidence_tier": "E3",
                "evidence_tier_updated_at": now,
                "collection_timestamp": now,
                "data_source_region": "hcmc",
                "source_region": "TP. Ho Chi Minh",
                "description": "CI production-like reference row for release gates.",
            }
        )
    return rows


def seed() -> dict[str, int]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    property_ids: list[int] = []
    account_ids: list[int] = []

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM public.matched_pairs WHERE match_group LIKE 'ci_reference_%'"))
        connection.execute(text("DELETE FROM public.buyer_requirements WHERE source_type = 'ci_reference_profile'"))
        connection.execute(text("DELETE FROM public.properties WHERE source_name = 'ci_reference_dataset'"))

        for account in _reference_accounts():
            account_id = connection.execute(
                text(
                    """
                    INSERT INTO auth.auth_accounts (
                        username, email, hashed_password, role, is_active, created_at
                    )
                    VALUES (
                        :username, :email, :hashed_password, :role, true, now()
                    )
                    ON CONFLICT (username) DO UPDATE SET
                        email = EXCLUDED.email,
                        hashed_password = EXCLUDED.hashed_password,
                        role = EXCLUDED.role,
                        is_active = true
                    RETURNING id
                    """
                ),
                account,
            ).scalar_one()
            account_ids.append(int(account_id))

        for prop in _reference_properties(now):
            property_id = connection.execute(
                text(
                    """
                    INSERT INTO public.properties (
                        property_type, province_city, district, ward, street_or_project,
                        area_m2, bedrooms, bathrooms, floor_count, frontage_m,
                        legal_status, price, price_per_m2, listing_date, is_transacted,
                        source_name, source_url, source_page_title, source_collected_at,
                        source_access_method, source_domain, source_category,
                        record_status, verification_status, data_origin_type,
                        evidence_tier, evidence_tier_updated_at, collection_timestamp,
                        data_source_region, source_region, description
                    )
                    VALUES (
                        :property_type, :province_city, :district, :ward, :street_or_project,
                        :area_m2, :bedrooms, :bathrooms, :floor_count, :frontage_m,
                        :legal_status, :price, :price_per_m2, :listing_date, :is_transacted,
                        :source_name, :source_url, :source_page_title, :source_collected_at,
                        :source_access_method, :source_domain, :source_category,
                        :record_status, :verification_status, :data_origin_type,
                        :evidence_tier, :evidence_tier_updated_at, :collection_timestamp,
                        :data_source_region, :source_region, :description
                    )
                    RETURNING id
                    """
                ),
                prop,
            ).scalar_one()
            property_ids.append(int(property_id))

        request_id = connection.execute(
            text(
                """
                INSERT INTO public.buyer_requirements (
                    property_type, province_city, district, ward, project_preference,
                    min_area, max_area, min_budget, max_budget, bedrooms,
                    legal_requirement, urgency, source_type, source_url,
                    source_description, is_active, notes
                )
                VALUES (
                    'townhouse', 'TP. Ho Chi Minh', 'Quận 7', NULL, NULL,
                    35, 130, 1800000000, 8000000000, 3,
                    'ownership_certificate', 'normal', 'ci_reference_profile', NULL,
                    'CI production-like buyer profile for release gates.', true,
                    'Seeded by scripts/quality/seed_ci_reference_data.py'
                )
                RETURNING id
                """
            )
        ).scalar_one()

        for idx, property_id in enumerate(property_ids[:8], 1):
            connection.execute(
                text(
                    """
                    INSERT INTO public.matched_pairs (
                        listing_id, request_id, location_match_score, area_match_score,
                        budget_gap, feature_match_score, is_potential_match,
                        overlap_score, match_group
                    )
                    VALUES (
                        :listing_id, :request_id, 1.0, :area_score,
                        :budget_gap, :feature_score, true, :overlap_score, :match_group
                    )
                    """
                ),
                {
                    "listing_id": property_id,
                    "request_id": int(request_id),
                    "area_score": max(0.45, 1.0 - idx * 0.04),
                    "budget_gap": -50_000_000 * idx,
                    "feature_score": max(0.5, 1.0 - idx * 0.05),
                    "overlap_score": max(0.45, 0.95 - idx * 0.04),
                    "match_group": f"ci_reference_{property_id}_{request_id}",
                },
            )

        connection.execute(text("SELECT management.refresh_public_accounts_snapshot_now()"))

        summary = {
            "accounts": connection.execute(text("SELECT COUNT(*)::int FROM public.accounts")).scalar_one(),
            "properties": connection.execute(
                text("SELECT COUNT(*)::int FROM public.properties WHERE source_name = 'ci_reference_dataset'")
            ).scalar_one(),
            "buyer_requirements": connection.execute(
                text("SELECT COUNT(*)::int FROM public.buyer_requirements WHERE source_type = 'ci_reference_profile'")
            ).scalar_one(),
            "matched_pairs": connection.execute(
                text("SELECT COUNT(*)::int FROM public.matched_pairs WHERE match_group LIKE 'ci_reference_%'")
            ).scalar_one(),
        }

    return {key: int(value) for key, value in summary.items()}


if __name__ == "__main__":
    print(seed())
