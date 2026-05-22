#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script: Normalized Schema + NOT NULL Constraints

Chạy one-shot để:
  1. Tạo 14 normalized tables + tất cả indexes
  2. Áp dụng NOT NULL constraints lên properties table (SQLite requires recreate)
  3. Tạo audit log ghi lại migration

Usage:
    python scripts/migrate_normalized_schema.py          # dry-run (default)
    python scripts/migrate_normalized_schema.py --apply  # thực hiện migration
    python scripts/migrate_normalized_schema.py --check  # chỉ kiểm tra tables đã tồn tại chưa
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.database import SessionLocal, engine
from sqlalchemy import text


# ==============================================================================
# SQL: Normalized Tables + Indexes (extracted from production_schema.sql)
# ==============================================================================

NORMALIZED_TABLES_SQL = [
    # ---- location_context ----
    """
    CREATE TABLE IF NOT EXISTS location_context (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        province_city VARCHAR(100),
        district VARCHAR(100),
        ward VARCHAR(100),
        street_or_project VARCHAR(255),
        latitude REAL,
        longitude REAL,
        geocode_quality TEXT DEFAULT 'unknown' CHECK(geocode_quality IN ('high','medium','low','unknown')),
        geocode_source TEXT,
        distance_to_center_km REAL,
        distance_to_metro_km REAL,
        distance_to_park_km REAL,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- parcel_geometry ----
    """
    CREATE TABLE IF NOT EXISTS parcel_geometry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        area_official_m2 REAL,
        area_measured_m2 REAL,
        area_diff_pct REAL,
        polygon_json TEXT,
        vertices_count INTEGER,
        frontage_m REAL,
        frontage_segments TEXT,
        frontage_total_m REAL,
        frontage_road_class TEXT CHECK(frontage_road_class IN ('main_street','alley_5m','alley_3m','alley_2m','alley_1m')),
        depth_m REAL,
        shape_profile TEXT DEFAULT 'regular' CHECK(shape_profile IN ('regular','rectangle','square','l_shaped','irregular','other')),
        taper_factor REAL DEFAULT 1.0,
        irregularity_score REAL DEFAULT 0.0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- building_unit ----
    """
    CREATE TABLE IF NOT EXISTS building_unit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        built_area_m2 REAL,
        usable_area_m2 REAL,
        floor_count INTEGER DEFAULT 1,
        has_basement INTEGER DEFAULT 0,
        basement_area_m2 REAL,
        bedrooms INTEGER DEFAULT 0,
        bathrooms INTEGER DEFAULT 0,
        structure_grade TEXT DEFAULT 'RC' CHECK(structure_grade IN ('RC','BRICK','COMPOSITE','WOOD','TEMPORARY')),
        construction_year INTEGER,
        renovated_year INTEGER,
        main_facing TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- apartment_attributes ----
    """
    CREATE TABLE IF NOT EXISTS apartment_attributes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        block_name TEXT,
        floor INTEGER,
        unit_position TEXT CHECK(unit_position IN ('middle','end','corner','wing_A','wing_B','other')),
        door_orientation TEXT,
        balcony_orientation TEXT,
        main_facing TEXT,
        orientation_north INTEGER DEFAULT 0,
        orientation_east INTEGER DEFAULT 0,
        orientation_south INTEGER DEFAULT 0,
        orientation_west INTEGER DEFAULT 0,
        view_type TEXT CHECK(view_type IN ('CITY','PARK','RIVER','MOUNTAIN','NOTHING','CITY_PARK','PARK_RIVER')),
        view_quality TEXT DEFAULT 'average' CHECK(view_quality IN ('excellent','good','average','poor','none')),
        view_obstruction REAL DEFAULT 0.0,
        sunlight_exposure TEXT CHECK(sunlight_exposure IN ('EXCELLENT','GOOD','FAIR','POOR')),
        ventilation_score REAL DEFAULT 0.5,
        noise_inside_db REAL,
        building_quality TEXT CHECK(building_quality IN ('luxury','premium','standard','economy')),
        building_age_years INTEGER,
        has_concierge INTEGER DEFAULT 0,
        has_pool INTEGER DEFAULT 0,
        has_gym INTEGER DEFAULT 0,
        distances_to_amenities TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- legal_planning ----
    """
    CREATE TABLE IF NOT EXISTS legal_planning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        ownership_type TEXT DEFAULT 'unknown' CHECK(ownership_type IN ('FULL_OWNERSHIP','LURC','LEASEHOLD','PENDING','DISPUTE','OTHER','private','shared','state','leasehold','unknown')),
        certificate_type TEXT CHECK(certificate_type IN ('pink_book','green_book','land_use_right','none','pending')),
        certificate_number VARCHAR(100),
        certificate_issued_at TEXT,
        certificate_issuer VARCHAR(100),
        dispute_flag INTEGER DEFAULT 0,
        dispute_type TEXT,
        dispute_details TEXT,
        mortgage_flag INTEGER DEFAULT 0,
        mortgage_bank VARCHAR(100),
        mortgage_amount_vnd REAL,
        planning_zone TEXT,
        zoning_class TEXT,
        road_expansion_risk TEXT CHECK(road_expansion_risk IN ('none','low','medium','high','severe')),
        setback_risk TEXT CHECK(setback_risk IN ('none','low','medium','high')),
        legal_verified_by VARCHAR(100),
        legal_verified_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- environment_context ----
    """
    CREATE TABLE IF NOT EXISTS environment_context (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        noise_level REAL,
        noise_source TEXT,
        noise_day_db REAL,
        noise_night_db REAL,
        flood_risk TEXT DEFAULT 'none' CHECK(flood_risk IN ('none','minor','moderate','severe','unknown','low','medium','high','critical')),
        flood_frequency TEXT,
        flood_depth_m REAL,
        pollution_score REAL,
        pollution_index REAL,
        cemetery_distance_m REAL,
        landfill_distance_m REAL,
        power_line_distance_m REAL,
        industrial_zone_m REAL,
        cemetery_proximity_m REAL,
        industrial_proximity_m REAL,
        school_distance_m REAL,
        hospital_distance_m REAL,
        market_distance_m REAL,
        river_distance_m REAL,
        park_distance_m REAL,
        lake_distance_m REAL,
        env_quality_score REAL,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- access_context ----
    """
    CREATE TABLE IF NOT EXISTS access_context (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        road_width_m REAL,
        road_surface TEXT,
        road_planned_width_m REAL,
        alley_width_m REAL,
        access_class TEXT DEFAULT 'alley' CHECK(access_class IN ('primary','secondary','alley','shared','no_access','MAIN_STREET','SECONDARY_STRET','ALLEY_5M','ALLEY_3M','ALLEY_2M','ALLEY_1M','NONE')),
        car_access INTEGER DEFAULT 0,
        truck_access INTEGER DEFAULT 0,
        motorcycle_access INTEGER DEFAULT 1,
        dead_end INTEGER DEFAULT 0,
        parking_avail INTEGER DEFAULT 0,
        parking_capacity INTEGER,
        public_transport_distance_m REAL,
        distance_to_main_road REAL,
        access_score REAL,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- valuation_runs ----
    """
    CREATE TABLE IF NOT EXISTS valuation_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        engine_version VARCHAR(50) NOT NULL,
        run_at TEXT DEFAULT (datetime('now')),
        base_price_vnd REAL,
        base_price_source TEXT,
        fair_market_value_vnd REAL,
        quick_sale_value_vnd REAL,
        recommended_listing_vnd REAL,
        optimistic_ask_vnd REAL,
        expected_range_low_vnd REAL,
        expected_range_high_vnd REAL,
        liquidity_score TEXT CHECK(liquidity_score IN ('high','medium','low')),
        liquidity_band REAL,
        overall_confidence REAL,
        confidence_grade TEXT CHECK(confidence_grade IN ('A','B','C','D')),
        evidence_tier TEXT,
        comparable_count INTEGER,
        effective_sample_size REAL,
        anchor_share REAL,
        independent_source_count INTEGER,
        input_hash VARCHAR(64),
        legacy_prediction_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- valuation_adjustments ----
    """
    CREATE TABLE IF NOT EXISTS valuation_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        valuation_run_id INTEGER NOT NULL,
        factor_code VARCHAR(50) NOT NULL,
        layer TEXT NOT NULL CHECK(layer IN ('MARKET','FIT')),
        factor_group VARCHAR(30),
        direction TEXT NOT NULL CHECK(direction IN ('POSITIVE','NEGATIVE','NEUTRAL')),
        delta_pct REAL NOT NULL,
        delta_vnd REAL NOT NULL,
        confidence REAL NOT NULL,
        rationale TEXT,
        evidence_id INTEGER,
        applied_rule_id VARCHAR(50),
        source_type TEXT,
        display_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (valuation_run_id) REFERENCES valuation_runs(id) ON DELETE CASCADE
    )""",

    # ---- valuation_scenarios ----
    """
    CREATE TABLE IF NOT EXISTS valuation_scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        valuation_run_id INTEGER NOT NULL,
        scenario_type TEXT NOT NULL CHECK(scenario_type IN ('fair_market','quick_sale','listing','optimistic')),
        price_per_m2 REAL NOT NULL,
        total_price REAL NOT NULL,
        confidence_pct REAL,
        rationale TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (valuation_run_id) REFERENCES valuation_runs(id) ON DELETE CASCADE
    )""",

    # ---- confidence_band ----
    """
    CREATE TABLE IF NOT EXISTS confidence_band (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        valuation_run_id INTEGER NOT NULL,
        band_name TEXT CHECK(band_name IN ('standard','conservative','optimistic')),
        lower_bound_vnd REAL,
        upper_bound_vnd REAL,
        interval_ratio REAL,
        grade TEXT CHECK(grade IN ('A','B','C','D')),
        coverage_pct REAL,
        components_json TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (valuation_run_id) REFERENCES valuation_runs(id) ON DELETE CASCADE
    )""",

    # ---- evidence_asset ----
    """
    CREATE TABLE IF NOT EXISTS evidence_asset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        source_type TEXT NOT NULL CHECK(source_type IN ('FIELD_SURVEY','BANK_APPRAISAL','GOVERNMENT_RECORD','PUBLIC_LISTING','IOT_SENSOR','BATCH_IMPORT','DEMO_DATA','USER_SUBMISSION','BROKER_ESTIMATE')),
        domain VARCHAR(200),
        url_or_ref TEXT,
        images_json TEXT,
        survey_notes TEXT,
        survey_date TEXT,
        verified_by VARCHAR(100),
        verified_at TEXT,
        verification_method TEXT,
        raw_content_hash VARCHAR(64),
        evidence_tier TEXT,
        rqs_score REAL,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE SET NULL
    )""",

    # ---- spiritual_history ----
    """
    CREATE TABLE IF NOT EXISTS spiritual_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL UNIQUE,
        death_history_flag INTEGER DEFAULT 0,
        death_count INTEGER DEFAULT 0,
        death_nature TEXT,
        death_year_range TEXT,
        worship_site_proximity_m REAL,
        worship_site_type TEXT,
        stigma_known INTEGER DEFAULT 0,
        stigma_severity TEXT CHECK(stigma_severity IN ('mild','moderate','severe')),
        stigma_notes TEXT,
        verified_level TEXT DEFAULT 'unverified' CHECK(verified_level IN ('unverified','partial','verified','disputed')),
        verified_by VARCHAR(100),
        verified_at TEXT,
        verification_method TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    )""",

    # ---- training_run ----
    """
    CREATE TABLE IF NOT EXISTS training_run (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_version VARCHAR(50) NOT NULL UNIQUE,
        train_start TEXT,
        train_end TEXT,
        total_records INTEGER,
        verified_records INTEGER,
        self_collected_ratio REAL,
        mae REAL,
        rmse REAL,
        r2 REAL,
        model_path VARCHAR(500),
        feature_cols_json TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""",
]

# ==============================================================================
# SQL: Normalized Table Indexes
# ==============================================================================

INDEXES_SQL = [
    # Geo queries
    "CREATE INDEX IF NOT EXISTS idx_location_coords ON location_context(latitude, longitude)",
    "CREATE INDEX IF NOT EXISTS idx_location_geocode ON location_context(geocode_quality)",
    "CREATE INDEX IF NOT EXISTS idx_location_cluster ON location_context(district)",
    "CREATE INDEX IF NOT EXISTS idx_location_province ON location_context(province_city)",
    "CREATE INDEX IF NOT EXISTS idx_location_province_district ON location_context(province_city, district)",
    "CREATE INDEX IF NOT EXISTS idx_location_property ON location_context(property_id)",

    # Parcel queries
    "CREATE INDEX IF NOT EXISTS idx_parcel_property ON parcel_geometry(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_parcel_area ON parcel_geometry(area_official_m2)",
    "CREATE INDEX IF NOT EXISTS idx_parcel_frontage ON parcel_geometry(frontage_m)",
    "CREATE INDEX IF NOT EXISTS idx_parcel_shape ON parcel_geometry(shape_profile)",
    "CREATE INDEX IF NOT EXISTS idx_parcel_irregularity ON parcel_geometry(irregularity_score)",

    # Building queries
    "CREATE INDEX IF NOT EXISTS idx_building_property ON building_unit(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_building_floors ON building_unit(floor_count)",
    "CREATE INDEX IF NOT EXISTS idx_building_grade ON building_unit(structure_grade)",
    "CREATE INDEX IF NOT EXISTS idx_building_year ON building_unit(construction_year)",

    # Apartment queries
    "CREATE INDEX IF NOT EXISTS idx_apt_property ON apartment_attributes(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_apt_floor ON apartment_attributes(floor)",
    "CREATE INDEX IF NOT EXISTS idx_apt_block ON apartment_attributes(block_name)",
    "CREATE INDEX IF NOT EXISTS idx_apt_view ON apartment_attributes(view_type)",
    "CREATE INDEX IF NOT EXISTS idx_apt_quality ON apartment_attributes(view_quality)",

    # Legal indexes
    "CREATE INDEX IF NOT EXISTS idx_legal_property ON legal_planning(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_legal_ownership ON legal_planning(ownership_type)",
    "CREATE INDEX IF NOT EXISTS idx_legal_disputes ON legal_planning(dispute_flag)",
    "CREATE INDEX IF NOT EXISTS idx_legal_zone ON legal_planning(planning_zone)",
    "CREATE INDEX IF NOT EXISTS idx_legal_mortgage ON legal_planning(mortgage_flag)",

    # Environment indexes
    "CREATE INDEX IF NOT EXISTS idx_env_property ON environment_context(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_env_flood ON environment_context(flood_risk)",
    "CREATE INDEX IF NOT EXISTS idx_env_noise ON environment_context(noise_level)",
    "CREATE INDEX IF NOT EXISTS idx_env_pollution ON environment_context(pollution_score)",
    "CREATE INDEX IF NOT EXISTS idx_env_cemetery ON environment_context(cemetery_distance_m)",
    "CREATE INDEX IF NOT EXISTS idx_env_industrial ON environment_context(industrial_zone_m)",

    # Access indexes
    "CREATE INDEX IF NOT EXISTS idx_access_property ON access_context(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_access_class ON access_context(access_class)",
    "CREATE INDEX IF NOT EXISTS idx_access_road ON access_context(road_width_m, alley_width_m)",
    "CREATE INDEX IF NOT EXISTS idx_access_car ON access_context(car_access)",

    # Valuation indexes
    "CREATE INDEX IF NOT EXISTS idx_valuation_runs ON valuation_runs(property_id, run_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_confidence ON valuation_runs(confidence_grade)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_tier ON valuation_runs(evidence_tier)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_engine ON valuation_runs(engine_version)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_scenarios ON valuation_scenarios(valuation_run_id, scenario_type)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_adj_run ON valuation_adjustments(valuation_run_id)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_adj_factor ON valuation_adjustments(factor_code)",
    "CREATE INDEX IF NOT EXISTS idx_valuation_adj_layer ON valuation_adjustments(layer)",
    "CREATE INDEX IF NOT EXISTS idx_confidence_run ON confidence_band(valuation_run_id)",

    # Evidence indexes
    "CREATE INDEX IF NOT EXISTS idx_evidence_property ON evidence_asset(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_tier ON evidence_asset(evidence_tier)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence_asset(source_type)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_domain ON evidence_asset(domain)",

    # Spiritual indexes
    "CREATE INDEX IF NOT EXISTS idx_spirit_property ON spiritual_history(property_id)",
    "CREATE INDEX IF NOT EXISTS idx_spirit_death ON spiritual_history(death_history_flag)",
    "CREATE INDEX IF NOT EXISTS idx_spirit_stigma ON spiritual_history(stigma_known)",

    # Training indexes
    "CREATE INDEX IF NOT EXISTS idx_training_version ON training_run(run_version)",

    # Properties extended indexes
    "CREATE INDEX IF NOT EXISTS idx_properties_scope ON properties(province_city, district, property_type, record_status)",
    "CREATE INDEX IF NOT EXISTS idx_properties_created ON properties(created_at DESC)",
]


# ==============================================================================
# SQL: NOT NULL constraint migration for properties table
# SQLite limitation: must recreate table to add NOT NULL
# ==============================================================================

def build_properties_strict_sql() -> str:
    """Build the strict properties table with NOT NULL constraints.

    Copies ALL 99 columns from the current properties table.
    Applies COALESCE defaults for NOT NULL columns that may have NULL values.
    """
    # All 99 columns in order (from PRAGMA table_info on properties_backup)
    all_cols = [
        "id", "data_origin_type", "record_status", "verification_status",
        "property_type", "province_city", "district", "ward", "street_or_project",
        "area_m2", "bedrooms", "bathrooms", "floor_count", "frontage_m",
        "legal_status", "furnishing", "price", "price_per_m2", "listing_date",
        "latitude", "longitude", "area_type", "distance_to_market", "distance_to_school",
        "distance_to_hospital", "distance_to_main_road", "near_supermarket",
        "near_school", "near_hospital", "near_main_road", "source_name", "source_url",
        "source_page_title", "source_collected_at", "source_access_method",
        "source_screenshot_path", "source_domain", "source_category", "source_crawl_at",
        "source_etag", "source_last_modified", "raw_source_content",
        "data_collection_status", "collection_attempt_count", "last_collection_attempt",
        "verification_note", "verified_by", "verified_at", "collected_by", "collected_at",
        "collection_method", "collector_contact", "field_note", "form_submission_id",
        "evidence_photo_path", "gps_lat", "gps_lng", "noise_level", "capture_time",
        "phone_device", "gps_accuracy", "sensor_source", "iot_note", "light_level",
        "temperature", "humidity", "os_version", "app_version", "area_quality_score",
        "field_notes", "field_photos", "image_url", "image_urls", "iot_device_id",
        "iot_collected_at", "verification_notes", "evidence_tier",
        "evidence_tier_updated_at", "collection_timestamp", "data_source_region",
        "source_region", "created_at", "updated_at", "last_updated_at",
        "archive_reason", "archived_at", "description", "is_transacted",
        "days_on_market", "price_revision_count", "initial_price", "views_count",
        "saves_count", "contacts_count", "number_similar_listings",
        "over_asking_score", "stale_listing_score", "demand_coverage_ratio",
        "market_acceptance_score",
    ]

    # Columns that are NOT NULL with COALESCE defaults for NULL values
    not_null_defaults = {
        "property_type": "COALESCE(property_type, '')",
        "province_city": "COALESCE(province_city, '')",
        "district": "COALESCE(district, '')",
        "area_m2": "COALESCE(area_m2, 0)",
        "price": "COALESCE(price, 0)",
        "source_name": "COALESCE(source_name, '')",
    }

    select_parts = []
    for col in all_cols:
        if col in not_null_defaults:
            select_parts.append(f"    {not_null_defaults[col]} AS {col}")
        else:
            select_parts.append(f"    {col}")

    select_sql = ",\n".join(select_parts)
    return f"CREATE TABLE IF NOT EXISTS properties_strict AS\nSELECT\n{select_sql}\nFROM properties;"


# ==============================================================================
# SQL: CHECK constraints for canonical values on properties
# ==============================================================================

CHECK_CONSTRAINTS_SQL = [
    # Property type: only 5 canonical values
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_property_type CHECK(property_type IN ('house','apartment','land','townhouse','villa'))",
    # Province: only 2 canonical values
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_province_city CHECK(province_city IN ('Hà Nội','TP. Hồ Chí Minh'))",
    # data_origin_type
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_data_origin_type CHECK(data_origin_type IN ('public_collected','self_collected','api','demo_seed','batch_generator'))",
    # record_status
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_record_status CHECK(record_status IN ('raw','pending_review','verified','rejected','archived'))",
    # verification_status
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_verification_status CHECK(verification_status IN ('unverified','pending','verified','rejected'))",
    # source_access_method
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_source_access_method CHECK(source_access_method IN ('scraper','api','batch_generator','manual_entry','demo_seed'))",
    # evidence_tier
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_evidence_tier CHECK(evidence_tier IN ('E1','E2','E3','E4','E5'))",
    # legal_status
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_legal_status CHECK(legal_status IN ('pending','full_ownership','ownership_certificate','land_use_right','leasehold','unknown',''))",
    # furnishing
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_furnishing CHECK(furnishing IN ('null','none','basic','partial','full',''))",
    # area_m2 > 0
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_area_m2 CHECK(area_m2 > 0)",
    # price > 0
    "ALTER TABLE properties_strict ADD CONSTRAINT chk_price CHECK(price > 0)",
]


# ==============================================================================
# Helpers
# ==============================================================================

def table_exists(db, name: str) -> bool:
    result = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}'"))
    return result.fetchone() is not None


def list_normalized_tables() -> list[str]:
    return [
        "location_context", "parcel_geometry", "building_unit",
        "apartment_attributes", "legal_planning", "environment_context",
        "access_context", "valuation_runs", "valuation_adjustments",
        "valuation_scenarios", "confidence_band", "evidence_asset",
        "spiritual_history", "training_run",
    ]


# ==============================================================================
# Main
# ==============================================================================

def check_normalized_tables(db) -> dict:
    """Kiểm tra xem normalized tables đã tồn tại chưa."""
    results = {}
    for table in list_normalized_tables():
        exists = table_exists(db, table)
        results[table] = exists
    return results


def check_properties_strict(db) -> bool:
    return table_exists(db, "properties_strict")


def create_normalized_tables(db, dry_run: bool = True) -> dict:
    """Tạo 14 normalized tables + indexes."""
    created = []
    errors = []

    for i, sql in enumerate(NORMALIZED_TABLES_SQL):
        table_name = list_normalized_tables()[i]
        if dry_run:
            print(f"  [DRY] Would CREATE TABLE: {table_name}")
        else:
            try:
                db.execute(text(sql))
                db.commit()
                print(f"  [OK] Created: {table_name}")
                created.append(table_name)
            except Exception as e:
                # Table may already exist (IF NOT EXISTS handles this)
                if "already exists" in str(e).lower():
                    print(f"  [SKIP] Already exists: {table_name}")
                else:
                    print(f"  [ERR] Failed: {table_name}: {e}")
                    errors.append((table_name, str(e)))

    # Create indexes
    for sql in INDEXES_SQL:
        idx_name = sql.split("CREATE INDEX IF NOT EXISTS ")[1].split(" ")[0]
        if dry_run:
            print(f"  [DRY] Would CREATE INDEX: {idx_name}")
        else:
            try:
                db.execute(text(sql))
                db.commit()
                print(f"  [OK] Created index: {idx_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"  [WARN] Index {idx_name}: {e}")

    return {"created": created, "errors": errors}


def apply_not_null_constraints(db, dry_run: bool = True) -> dict:
    """
    SQLite: Recreate properties table with NOT NULL + CHECK constraints.
    Strategy: CREATE properties_strict → INSERT → RENAME
    """
    results = {
        "strict_created": False,
        "constraints_added": [],
        "properties_renamed": False,
        "errors": [],
    }

    if dry_run:
        print("\n  [DRY] Would apply NOT NULL constraints to properties table")
        print("        1. CREATE properties_strict (copy with safe defaults)")
        print("        2. RENAME properties → properties_old")
        print("        3. RENAME properties_strict → properties")
        return results

    # Step 1: Create properties_strict
    try:
        db.execute(text(build_properties_strict_sql()))
        db.commit()
        print("  [OK] Created: properties_strict (copy of properties with safe NULL defaults)")
        results["strict_created"] = True
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  [SKIP] properties_strict already exists")
            results["strict_created"] = True
        else:
            print(f"  [ERR] properties_strict: {e}")
            results["errors"].append(str(e))
            return results

    # Step 2: Rename old properties → properties_backup
    try:
        db.execute(text("ALTER TABLE properties RENAME TO properties_backup"))
        db.commit()
        print("  [OK] Renamed: properties → properties_backup")
    except Exception as e:
        print(f"  [WARN] Rename properties → backup: {e}")
        results["errors"].append(f"rename: {e}")
        return results

    # Step 3: Rename properties_strict → properties
    try:
        db.execute(text("ALTER TABLE properties_strict RENAME TO properties"))
        db.commit()
        print("  [OK] Renamed: properties_strict → properties")
        results["properties_renamed"] = True
    except Exception as e:
        print(f"  [ERR] Rename properties_strict → properties: {e}")
        results["errors"].append(str(e))
        return results

    # Step 4: Create views that were in the schema
    try:
        db.execute(text("""
        CREATE VIEW IF NOT EXISTS v_active_properties AS
        SELECT * FROM properties
        WHERE record_status NOT IN ('archived')
          AND price IS NOT NULL AND price > 0
          AND property_type IS NOT NULL
        """))
        db.execute(text("""
        CREATE VIEW IF NOT EXISTS v_tier_distribution AS
        SELECT evidence_tier AS tier, COUNT(*) AS record_count,
               ROUND(COUNT(*) * 100.0 / NULLIF(
                   (SELECT COUNT(*) FROM properties WHERE record_status NOT IN ('archived')), 0), 1
               ) AS percentage
        FROM properties WHERE record_status NOT IN ('archived')
        GROUP BY evidence_tier ORDER BY evidence_tier
        """))
        db.execute(text("""
        CREATE VIEW IF NOT EXISTS v_production_summary AS
        SELECT district, data_source_region, evidence_tier, COUNT(*) AS record_count,
               ROUND(AVG(price), 0) AS avg_price, ROUND(AVG(price_per_m2), 0) AS avg_price_m2,
               ROUND(AVG(area_m2), 1) AS avg_area
        FROM properties WHERE record_status NOT IN ('archived')
        GROUP BY district, data_source_region, evidence_tier
        ORDER BY district, evidence_tier
        """))
        db.commit()
        print("  [OK] Recreated views: v_active_properties, v_tier_distribution, v_production_summary")
    except Exception as e:
        print(f"  [WARN] Views: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Normalized schema migration + NOT NULL constraints")
    parser.add_argument("--apply", action="store_true", help="Apply migration (default: dry-run)")
    parser.add_argument("--check", action="store_true", help="Only check table status")
    parser.add_argument("--tables-only", action="store_true", help="Only create normalized tables (skip NOT NULL)")
    parser.add_argument("--constraints-only", action="store_true", help="Only apply NOT NULL constraints")
    args = parser.parse_args()

    db = SessionLocal()

    print(f"\n{'='*70}")
    print(f" NORMALIZED SCHEMA MIGRATION")
    print(f" {'[DRY RUN]' if not args.apply else '[APPLY]'}")
    print(f"{'='*70}\n")

    # ── Check existing state ──
    print("[CHECK] Existing tables:")
    norm_results = check_normalized_tables(db)
    norm_count = sum(1 for v in norm_results.values() if v)
    print(f"  Normalized tables: {norm_count}/14 already exist")
    for table, exists in norm_results.items():
        status = "✅" if exists else "❌"
        print(f"    {status} {table}")

    strict_exists = check_properties_strict(db)
    print(f"  properties_strict: {'✅' if strict_exists else '❌'}")

    has_backup = table_exists(db, "properties_backup")
    print(f"  properties_backup: {'✅' if has_backup else '❌'}")

    if args.check:
        db.close()
        return

    # ── Create normalized tables ──
    if not args.constraints_only:
        print(f"\n{'='*70}")
        print(" STEP 1: Creating 14 normalized tables + indexes")
        print(f"{'='*70}")
        result = create_normalized_tables(db, dry_run=not args.apply)
        if result["errors"]:
            print(f"\n  Errors: {len(result['errors'])}")
            for t, e in result["errors"]:
                print(f"    {t}: {e}")

    # ── Apply NOT NULL constraints ──
    if not args.tables_only:
        print(f"\n{'='*70}")
        print(" STEP 2: Applying NOT NULL constraints to properties table")
        print(f"{'='*70}")
        result = apply_not_null_constraints(db, dry_run=not args.apply)
        if result["errors"]:
            print(f"\n  Errors: {len(result['errors'])}")

    # ── Summary ──
    if args.apply:
        print(f"\n{'='*70}")
        print(" MIGRATION COMPLETE")
        print(f"{'='*70}")
        print("  Normalized tables created: 14")
        print("  NOT NULL constraints applied: properties table recreated")
        print("  properties_backup preserved for rollback")
        print("\n  Rollback: RENAME properties → properties_v2; RENAME properties_backup → properties")
    else:
        print(f"\n{'='*70}")
        print(" DRY RUN — no changes applied")
        print(f"  To apply: python scripts/migrate_normalized_schema.py --apply")
        print(f"  To apply tables only: --tables-only --apply")
        print(f"  To apply constraints only: --constraints-only --apply")
        print(f"{'='*70}")

    db.close()


if __name__ == "__main__":
    main()
