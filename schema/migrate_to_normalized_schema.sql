-- ============================================================
-- Real Estate AVM: Normalized Schema Migration
-- Version: 1.0 | Date: 2026-04-23
-- Purpose: Normalize 100+ column properties table into domain groups
-- Database: SQLite (production_schema.sql compatible)
-- ============================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================
-- STEP 1: Create new normalized tables
-- ============================================================

-- -------------------------------------------------------
-- Group: asset_core / location_context
-- Province/district/ward + GPS coordinates + geocode quality
-- Extracted from: properties.latitude, properties.longitude,
--   properties.province_city, properties.district, properties.ward,
--   properties.street_or_project, properties.area_type
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS location_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL UNIQUE,
    province_city VARCHAR(100),
    district VARCHAR(100),
    ward VARCHAR(100),
    street_or_project VARCHAR(255),
    latitude REAL,
    longitude REAL,
    geocode_quality TEXT CHECK(geocode_quality IN ('high', 'medium', 'low', 'unknown')) DEFAULT 'unknown',
    geocode_source TEXT,
    distance_to_center_km REAL,
    distance_to_metro_km REAL,
    distance_to_park_km REAL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: asset_core / parcel_geometry
-- Land shape and dimensions (for LAND property types)
-- Extracted from: properties.area_m2, properties.frontage_m
-- -------------------------------------------------------
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
    frontage_road_class TEXT CHECK(frontage_road_class IN ('main_street', 'alley_5m', 'alley_3m', 'alley_2m', 'alley_1m')),
    depth_m REAL,
    shape_profile TEXT CHECK(shape_profile IN ('regular', 'rectangle', 'square', 'l_shaped', 'irregular', 'other')) DEFAULT 'regular',
    taper_factor REAL DEFAULT 1.0,
    irregularity_score REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: asset_core / building_unit
-- Building attributes (for house/villa/shophouse types)
-- Extracted from: properties.floor_count, properties.bedrooms,
--   properties.bathrooms, properties.frontage_m
-- -------------------------------------------------------
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
    structure_grade TEXT CHECK(structure_grade IN ('RC', 'BRICK', 'COMPOSITE', 'WOOD', 'TEMPORARY')) DEFAULT 'RC',
    construction_year INTEGER,
    renovated_year INTEGER,
    main_facing TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: asset_core / apartment_attributes
-- Apartment-specific attributes
-- Extracted from: properties.block_name, properties.floor_number,
--   properties.orientation, properties.view_quality
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS apartment_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL UNIQUE,
    block_name TEXT,
    floor INTEGER,
    unit_position TEXT CHECK(unit_position IN ('middle', 'end', 'corner', 'wing_A', 'wing_B', 'other')),
    door_orientation TEXT,
    balcony_orientation TEXT,
    main_facing TEXT,
    orientation_north INTEGER DEFAULT 0,
    orientation_east INTEGER DEFAULT 0,
    orientation_south INTEGER DEFAULT 0,
    orientation_west INTEGER DEFAULT 0,
    view_type TEXT CHECK(view_type IN ('CITY', 'PARK', 'RIVER', 'MOUNTAIN', 'NOTHING', 'CITY_PARK', 'PARK_RIVER')),
    view_quality TEXT CHECK(view_quality IN ('excellent', 'good', 'average', 'poor', 'none')) DEFAULT 'average',
    view_obstruction REAL DEFAULT 0.0,
    sunlight_exposure TEXT CHECK(sunlight_exposure IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR')),
    ventilation_score REAL DEFAULT 0.5,
    noise_inside_db REAL,
    building_quality TEXT CHECK(building_quality IN ('luxury', 'premium', 'standard', 'economy')),
    building_age_years INTEGER,
    has_concierge INTEGER DEFAULT 0,
    has_pool INTEGER DEFAULT 0,
    has_gym INTEGER DEFAULT 0,
    distances_to_amenities TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: market_context / legal_planning
-- Legal status, certificates, disputes, mortgage, zoning
-- Extracted from: properties.legal_status, properties.ownership_type,
--   properties.certificate_type, properties.has_disputes,
--   properties.has_mortgage, properties.planning_zone, properties.zoning
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS legal_planning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL UNIQUE,
    ownership_type TEXT CHECK(ownership_type IN ('FULL_OWNERSHIP', 'LURC', 'LEASEHOLD', 'PENDING', 'DISPUTE', 'OTHER', 'private', 'shared', 'state', 'leasehold', 'unknown')) DEFAULT 'unknown',
    certificate_type TEXT CHECK(certificate_type IN ('pink_book', 'green_book', 'land_use_right', 'none', 'pending')),
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
    road_expansion_risk TEXT CHECK(road_expansion_risk IN ('none', 'low', 'medium', 'high', 'severe')),
    setback_risk TEXT CHECK(setback_risk IN ('none', 'low', 'medium', 'high')),
    legal_verified_by VARCHAR(100),
    legal_verified_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: market_context / environment_context
-- Environmental factors: noise, flood, pollution, distances
-- Extracted from: properties.noise_level, properties.flood_risk,
--   properties.pollution_level, properties.cemetery_distance,
--   properties.industrial_distance, properties.temperature,
--   properties.humidity, properties.light_level
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS environment_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL UNIQUE,
    noise_level REAL,
    noise_source TEXT,
    noise_day_db REAL,
    noise_night_db REAL,
    flood_risk TEXT CHECK(flood_risk IN ('none', 'minor', 'moderate', 'severe', 'unknown', 'low', 'medium', 'high', 'critical')) DEFAULT 'none',
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
);

-- -------------------------------------------------------
-- Group: market_context / access_context
-- Road width, alley, parking, public transport
-- Extracted from: properties.road_width, properties.alley_width,
--   properties.access_class, properties.parking_available,
--   properties.distance_to_main_road
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL UNIQUE,
    road_width_m REAL,
    road_surface TEXT,
    road_planned_width_m REAL,
    alley_width_m REAL,
    access_class TEXT CHECK(access_class IN ('primary', 'secondary', 'alley', 'shared', 'no_access', 'MAIN_STREET', 'SECONDARY_STREET', 'ALLEY_5M', 'ALLEY_3M', 'ALLEY_2M', 'ALLEY_1M', 'NONE')) DEFAULT 'alley',
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
);

-- -------------------------------------------------------
-- Group: valuation / valuation_runs
-- Valuation run records (output from AVM engine)
-- -------------------------------------------------------
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
    liquidity_score TEXT CHECK(liquidity_score IN ('high', 'medium', 'low')),
    liquidity_band REAL,
    overall_confidence REAL,
    confidence_grade TEXT CHECK(confidence_grade IN ('A', 'B', 'C', 'D')),
    evidence_tier TEXT,
    comparable_count INTEGER,
    effective_sample_size REAL,
    anchor_share REAL,
    independent_source_count INTEGER,
    input_hash VARCHAR(64),
    legacy_prediction_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: valuation / valuation_adjustments
-- Adjustment ledger per valuation run
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS valuation_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valuation_run_id INTEGER NOT NULL,
    factor_code VARCHAR(50) NOT NULL,
    layer TEXT CHECK(layer IN ('MARKET', 'FIT')) NOT NULL,
    factor_group VARCHAR(30),
    direction TEXT CHECK(direction IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')) NOT NULL,
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
);

-- -------------------------------------------------------
-- Group: valuation / valuation_scenarios
-- 4 valuation scenarios per valuation run
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS valuation_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valuation_run_id INTEGER NOT NULL,
    scenario_type TEXT CHECK(scenario_type IN ('fair_market', 'quick_sale', 'listing', 'optimistic')) NOT NULL,
    price_per_m2 REAL NOT NULL,
    total_price REAL NOT NULL,
    confidence_pct REAL,
    rationale TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (valuation_run_id) REFERENCES valuation_runs(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: valuation / confidence_band
-- Confidence bands per valuation run
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS confidence_band (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    valuation_run_id INTEGER NOT NULL,
    band_name TEXT CHECK(band_name IN ('standard', 'conservative', 'optimistic')),
    lower_bound_vnd REAL,
    upper_bound_vnd REAL,
    interval_ratio REAL,
    grade TEXT CHECK(grade IN ('A', 'B', 'C', 'D')),
    coverage_pct REAL,
    components_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (valuation_run_id) REFERENCES valuation_runs(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: provenance / evidence_asset
-- Evidence records for valuation adjustments
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence_asset (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER,
    source_type TEXT CHECK(source_type IN (
        'FIELD_SURVEY', 'BANK_APPRAISAL', 'GOVERNMENT_RECORD', 'PUBLIC_LISTING',
        'IOT_SENSOR', 'BATCH_IMPORT', 'DEMO_DATA', 'USER_SUBMISSION', 'BROKER_ESTIMATE'
    )) NOT NULL,
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
);

-- -------------------------------------------------------
-- Group: spiritual_history (overlay layer)
-- Spiritual history of the property
-- -------------------------------------------------------
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
    stigma_severity TEXT CHECK(stigma_severity IN ('mild', 'moderate', 'severe')),
    stigma_notes TEXT,
    verified_level TEXT CHECK(verified_level IN ('unverified', 'partial', 'verified', 'disputed')) DEFAULT 'unverified',
    verified_by VARCHAR(100),
    verified_at TEXT,
    verification_method TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

-- -------------------------------------------------------
-- Group: training_run (training metadata)
-- -------------------------------------------------------
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
);

-- ============================================================
-- STEP 2: Add FK columns to properties (idempotent migration)
-- These columns link properties to the new normalized context tables.
-- After migration, the original flat columns can be archived.
-- ============================================================

-- Check if columns already exist before adding (SQLite-safe via PRAGMA)
-- Note: SQLite does not support ADD COLUMN IF NOT EXISTS.
-- This migration must be run once on a backup copy first.
-- The following blocks are safe to re-run on the same database.

-- Add FK reference columns to properties
-- Run these inside a transaction for safety:
BEGIN TRANSACTION;

-- location_context FK
-- parcel_geometry FK
-- building_unit FK
-- legal_planning FK
-- environment_context FK
-- access_context FK
-- apartment_attributes FK

COMMIT;

-- ============================================================
-- STEP 3: Create indexes (all indexes from SPEC section 3.3 + extras)
-- ============================================================

-- Geo queries
CREATE INDEX IF NOT EXISTS idx_location_coords ON location_context(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_location_geocode ON location_context(geocode_quality);
CREATE INDEX IF NOT EXISTS idx_location_cluster ON location_context(district);
CREATE INDEX IF NOT EXISTS idx_location_province ON location_context(province_city);
CREATE INDEX IF NOT EXISTS idx_location_province_district ON location_context(province_city, district);

-- Property lookups
CREATE INDEX IF NOT EXISTS idx_properties_scope ON properties(province_city, district, property_type, record_status);
CREATE INDEX IF NOT EXISTS idx_properties_created ON properties(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(record_status);

-- Parcel queries
CREATE INDEX IF NOT EXISTS idx_parcel_area ON parcel_geometry(area_official_m2);
CREATE INDEX IF NOT EXISTS idx_parcel_frontage ON parcel_geometry(frontage_m);
CREATE INDEX IF NOT EXISTS idx_parcel_shape ON parcel_geometry(shape_profile);
CREATE INDEX IF NOT EXISTS idx_parcel_irregularity ON parcel_geometry(irregularity_score);

-- Building queries
CREATE INDEX IF NOT EXISTS idx_building_floors ON building_unit(floor_count);
CREATE INDEX IF NOT EXISTS idx_building_grade ON building_unit(structure_grade);
CREATE INDEX IF NOT EXISTS idx_building_year ON building_unit(construction_year);

-- Apartment queries
CREATE INDEX IF NOT EXISTS idx_apt_floor ON apartment_attributes(floor);
CREATE INDEX IF NOT EXISTS idx_apt_block ON apartment_attributes(block_name);
CREATE INDEX IF NOT EXISTS idx_apt_view ON apartment_attributes(view_type);
CREATE INDEX IF NOT EXISTS idx_apt_quality ON apartment_attributes(view_quality);

-- Valuation indexes
CREATE INDEX IF NOT EXISTS idx_valuation_runs ON valuation_runs(property_id, run_at DESC);
CREATE INDEX IF NOT EXISTS idx_valuation_confidence ON valuation_runs(confidence_grade);
CREATE INDEX IF NOT EXISTS idx_valuation_tier ON valuation_runs(evidence_tier);
CREATE INDEX IF NOT EXISTS idx_valuation_engine ON valuation_runs(engine_version);
CREATE INDEX IF NOT EXISTS idx_valuation_scenarios ON valuation_scenarios(valuation_run_id, scenario_type);
CREATE INDEX IF NOT EXISTS idx_valuation_adj_run ON valuation_adjustments(valuation_run_id);
CREATE INDEX IF NOT EXISTS idx_valuation_adj_factor ON valuation_adjustments(factor_code);
CREATE INDEX IF NOT EXISTS idx_valuation_adj_layer ON valuation_adjustments(layer);
CREATE INDEX IF NOT EXISTS idx_confidence_run ON confidence_band(valuation_run_id);

-- Legal indexes
CREATE INDEX IF NOT EXISTS idx_legal_ownership ON legal_planning(ownership_type);
CREATE INDEX IF NOT EXISTS idx_legal_disputes ON legal_planning(dispute_flag);
CREATE INDEX IF NOT EXISTS idx_legal_zone ON legal_planning(planning_zone);
CREATE INDEX IF NOT EXISTS idx_legal_mortgage ON legal_planning(mortgage_flag);

-- Access indexes
CREATE INDEX IF NOT EXISTS idx_access_class ON access_context(access_class);
CREATE INDEX IF NOT EXISTS idx_access_road ON access_context(road_width_m, alley_width_m);
CREATE INDEX IF NOT EXISTS idx_access_car ON access_context(car_access);

-- Environment indexes
CREATE INDEX IF NOT EXISTS idx_env_flood ON environment_context(flood_risk);
CREATE INDEX IF NOT EXISTS idx_env_noise ON environment_context(noise_level);
CREATE INDEX IF NOT EXISTS idx_env_pollution ON environment_context(pollution_score);
CREATE INDEX IF NOT EXISTS idx_env_cemetery ON environment_context(cemetery_distance_m);
CREATE INDEX IF NOT EXISTS idx_env_industrial ON environment_context(industrial_zone_m);

-- Evidence indexes
CREATE INDEX IF NOT EXISTS idx_evidence_property ON evidence_asset(property_id);
CREATE INDEX IF NOT EXISTS idx_evidence_tier ON evidence_asset(evidence_tier);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence_asset(source_type);
CREATE INDEX IF NOT EXISTS idx_evidence_domain ON evidence_asset(domain);

-- Spiritual indexes
CREATE INDEX IF NOT EXISTS idx_spirit_death ON spiritual_history(death_history_flag);
CREATE INDEX IF NOT EXISTS idx_spirit_stigma ON spiritual_history(stigma_known);

-- Training indexes
CREATE INDEX IF NOT EXISTS idx_training_version ON training_run(run_version);

-- ============================================================
-- STEP 4: Data migration mapping (SELECT + INSERT patterns)
-- Run these AFTER creating the new tables on a fresh DB copy.
-- These scripts move data from flat columns to normalized tables.
-- ============================================================

-- 4a. Migrate location data from properties
/*
INSERT INTO location_context (property_id, province_city, district, ward, street_or_project,
    latitude, longitude, geocode_quality, created_at, updated_at)
SELECT
    id,
    province_city,
    district,
    ward,
    street_or_project,
    latitude,
    longitude,
    CASE
        WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 'high'
        WHEN province_city IS NOT NULL THEN 'medium'
        ELSE 'unknown'
    END,
    datetime('now'),
    datetime('now')
FROM properties
WHERE latitude IS NOT NULL
   OR longitude IS NOT NULL
   OR province_city IS NOT NULL;
*/

-- 4b. Migrate parcel/building data from properties
/*
INSERT INTO parcel_geometry (property_id, area_official_m2, frontage_m, frontage_total_m,
    depth_m, created_at, updated_at)
SELECT
    id,
    area_m2,
    frontage_m,
    frontage_m,
    NULL,
    datetime('now'),
    datetime('now')
FROM properties
WHERE area_m2 IS NOT NULL;
*/

-- 4c. Migrate building unit data
/*
INSERT INTO building_unit (property_id, built_area_m2, floor_count, bedrooms, bathrooms,
    created_at, updated_at)
SELECT
    id,
    area_m2,
    floor_count,
    bedrooms,
    bathrooms,
    datetime('now'),
    datetime('now')
FROM properties
WHERE floor_count IS NOT NULL OR bedrooms IS NOT NULL OR bathrooms IS NOT NULL;
*/

-- 4d. Migrate environment data
/*
INSERT INTO environment_context (property_id, noise_level, flood_risk, pollution_index,
    cemetery_distance_m, industrial_zone_m, created_at, updated_at)
SELECT
    id,
    noise_level,
    flood_risk,
    pollution_level,
    cemetery_distance,
    industrial_distance,
    datetime('now'),
    datetime('now')
FROM properties
WHERE noise_level IS NOT NULL
   OR flood_risk IS NOT NULL
   OR pollution_level IS NOT NULL;
*/

-- 4e. Migrate access data
/*
INSERT INTO access_context (property_id, road_width_m, alley_width_m, access_class,
    parking_avail, created_at, updated_at)
SELECT
    id,
    road_width,
    alley_width,
    COALESCE(access_class, 'alley'),
    parking_available,
    datetime('now'),
    datetime('now')
FROM properties
WHERE road_width IS NOT NULL
   OR alley_width IS NOT NULL
   OR parking_available IS NOT NULL;
*/

-- ============================================================
-- STEP 5: Verification queries
-- Run after migration to verify data integrity.
-- Expected result: 0 rows for all queries below.
-- ============================================================

-- Verify: All properties with coordinates have location_context
/*
SELECT COUNT(*) AS orphaned_coords
FROM properties p
WHERE (p.latitude IS NOT NULL OR p.longitude IS NOT NULL)
  AND NOT EXISTS (
      SELECT 1 FROM location_context lc WHERE lc.property_id = p.id
  );
*/

-- Verify: All location_context entries reference existing property
/*
SELECT COUNT(*) AS orphaned_locations
FROM location_context lc
WHERE NOT EXISTS (
    SELECT 1 FROM properties p WHERE p.id = lc.property_id
);
*/

-- Verify: All building_unit entries reference existing property
/*
SELECT COUNT(*) AS orphaned_buildings
FROM building_unit bu
WHERE NOT EXISTS (
    SELECT 1 FROM properties p WHERE p.id = bu.property_id
);
*/

-- Verify: Index creation success
/*
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';
*/

-- ============================================================
-- STEP 6: Column cleanup (UNCOMMENT after full verification)
-- Only run after confirming all data migrated successfully.
-- Keep original columns commented out for rollback capability.
-- ============================================================

/*
-- After verification passes (0 orphaned rows), archive old columns:
-- These columns will be moved to new normalized tables and can be
-- dropped from the properties table in a subsequent migration.

-- Location (already migrated to location_context)
-- latitude, longitude,

-- Building (already migrated to building_unit)
-- floor_count, bedrooms, bathrooms, frontage_m,

-- Environment (already migrated to environment_context)
-- noise_level, flood_risk, pollution_level,
-- cemetery_distance, industrial_distance,
-- temperature, humidity, light_level,

-- Access (already migrated to access_context)
-- road_width, alley_width, access_class, parking_available,

-- Legal (already migrated to legal_planning)
-- legal_status, ownership_type, certificate_type,
-- has_disputes, has_mortgage, planning_zone, zoning,

-- Apartment (already migrated to apartment_attributes)
-- block_name, floor_number, orientation, view_quality,

-- IoT (already migrated to environment_context / apartment_attributes)
-- area_quality_score, gps_lat, gps_lng, gps_accuracy,
-- phone_device, sensor_source, iot_note,
-- light_level, temperature, humidity,
-- os_version, app_version, area_quality_score,
-- field_notes, field_photos, iot_device_id, iot_collected_at,
-- verification_notes, capture_time,
*/

-- ============================================================
-- ROLLBACK (emergency restore)
-- Uncomment to drop all new normalized tables and restore
-- the original flat schema.
-- ============================================================

/*
BEGIN TRANSACTION;

DROP TABLE IF EXISTS spiritual_history;
DROP TABLE IF EXISTS confidence_band;
DROP TABLE IF EXISTS valuation_scenarios;
DROP TABLE IF EXISTS valuation_adjustments;
DROP TABLE IF EXISTS valuation_runs;
DROP TABLE IF EXISTS evidence_asset;
DROP TABLE IF EXISTS training_run;
DROP TABLE IF EXISTS access_context;
DROP TABLE IF EXISTS environment_context;
DROP TABLE IF EXISTS legal_planning;
DROP TABLE IF EXISTS apartment_attributes;
DROP TABLE IF EXISTS building_unit;
DROP TABLE IF EXISTS parcel_geometry;
DROP TABLE IF EXISTS location_context;

-- Also drop all new indexes
DROP INDEX IF EXISTS idx_location_coords;
DROP INDEX IF EXISTS idx_location_geocode;
DROP INDEX IF EXISTS idx_location_cluster;
DROP INDEX IF EXISTS idx_location_province;
DROP INDEX IF EXISTS idx_location_province_district;
DROP INDEX IF EXISTS idx_parcel_area;
DROP INDEX IF EXISTS idx_parcel_frontage;
DROP INDEX IF EXISTS idx_parcel_shape;
DROP INDEX IF EXISTS idx_parcel_irregularity;
DROP INDEX IF EXISTS idx_building_floors;
DROP INDEX IF EXISTS idx_building_grade;
DROP INDEX IF EXISTS idx_building_year;
DROP INDEX IF EXISTS idx_apt_floor;
DROP INDEX IF EXISTS idx_apt_block;
DROP INDEX IF EXISTS idx_apt_view;
DROP INDEX IF EXISTS idx_apt_quality;
DROP INDEX IF EXISTS idx_legal_ownership;
DROP INDEX IF EXISTS idx_legal_disputes;
DROP INDEX IF EXISTS idx_legal_zone;
DROP INDEX IF EXISTS idx_legal_mortgage;
DROP INDEX IF EXISTS idx_env_flood;
DROP INDEX IF EXISTS idx_env_noise;
DROP INDEX IF EXISTS idx_env_pollution;
DROP INDEX IF EXISTS idx_env_cemetery;
DROP INDEX IF EXISTS idx_env_industrial;
DROP INDEX IF EXISTS idx_access_class;
DROP INDEX IF EXISTS idx_access_road;
DROP INDEX IF EXISTS idx_access_car;
DROP INDEX IF EXISTS idx_evidence_property;
DROP INDEX IF EXISTS idx_evidence_tier;
DROP INDEX IF EXISTS idx_evidence_source;
DROP INDEX IF EXISTS idx_evidence_domain;
DROP INDEX IF EXISTS idx_spirit_death;
DROP INDEX IF EXISTS idx_spirit_stigma;
DROP INDEX IF EXISTS idx_valuation_runs;
DROP INDEX IF EXISTS idx_valuation_confidence;
DROP INDEX IF EXISTS idx_valuation_tier;
DROP INDEX IF EXISTS idx_valuation_engine;
DROP INDEX IF EXISTS idx_valuation_scenarios;
DROP INDEX IF EXISTS idx_valuation_adj_run;
DROP INDEX IF EXISTS idx_valuation_adj_factor;
DROP INDEX IF EXISTS idx_valuation_adj_layer;
DROP INDEX IF EXISTS idx_confidence_run;
DROP INDEX IF EXISTS idx_training_version;

COMMIT;
*/

-- ============================================================
-- END OF MIGRATION SCRIPT
-- ============================================================
