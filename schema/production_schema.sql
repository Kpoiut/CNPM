-- ============================================================================
-- Real Estate AVM — Production Database Schema
-- SSMS-compatible SQL script (SQLite + SQL Server syntax)
-- Generated: 2026-04-16
-- Total Tables: 7 | Columns: 100+
-- ============================================================================

-- ============================================================================
-- TABLE: properties (Primary Model — 60 columns)
-- ============================================================================
CREATE TABLE IF NOT EXISTS properties (
    -- Primary Key
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Data Origin & Status
    data_origin_type        VARCHAR(50)  NOT NULL DEFAULT 'public_collected',
    record_status          VARCHAR(50)  NOT NULL DEFAULT 'raw',
    verification_status    VARCHAR(50)  DEFAULT 'unverified',

    -- Basic Property Info
    property_type          VARCHAR(50)  NOT NULL,
    province_city          VARCHAR(100) NOT NULL,
    district              VARCHAR(100) NOT NULL,
    ward                  VARCHAR(100),
    street_or_project     VARCHAR(255),
    area_m2               REAL         NOT NULL,
    bedrooms              INTEGER      DEFAULT 0,
    bathrooms             INTEGER      DEFAULT 0,
    floor_count           INTEGER      DEFAULT 1,
    frontage_m            REAL,
    legal_status          VARCHAR(50),
    furnishing            VARCHAR(50),
    price                 REAL         NOT NULL,
    price_per_m2          REAL,
    listing_date          DATETIME,
    latitude              REAL,
    longitude             REAL,
    area_type             VARCHAR(50),

    -- Amenities
    distance_to_market    REAL,
    distance_to_school    REAL,
    distance_to_hospital  REAL,
    distance_to_main_road REAL,
    near_supermarket      INTEGER,          -- 0/1 as INTEGER (SQLite bool)
    near_school           INTEGER,
    near_hospital         INTEGER,
    near_main_road        INTEGER,

    -- Source Tracking
    source_name          VARCHAR(200) NOT NULL,
    source_url           VARCHAR(500),
    source_page_title    VARCHAR(255),
    source_collected_at  DATETIME,
    source_access_method VARCHAR(50),         -- 'scraper' | 'batch_generator' | 'demo_seed'
    source_screenshot_path VARCHAR(255),

    -- Provenance
    source_domain         VARCHAR(200),
    source_category      VARCHAR(50),         -- 'scraper' | 'field_survey' | 'demo'
    source_crawl_at      DATETIME,
    source_etag         VARCHAR(64),
    source_last_modified VARCHAR(100),
    raw_source_content  TEXT,
    data_collection_status VARCHAR(50) DEFAULT 'pending',
    collection_attempt_count INTEGER    DEFAULT 0,
    last_collection_attempt DATETIME,
    verification_note   TEXT,

    -- Verification
    verified_by          VARCHAR(100),
    verified_at          DATETIME,

    -- Self-Collected Fields
    collected_by         VARCHAR(100),
    collected_at        DATETIME,
    collection_method   VARCHAR(50),
    collector_contact   VARCHAR(100),
    field_note          TEXT,
    form_submission_id  VARCHAR(100),
    evidence_photo_path  VARCHAR(255),

    -- IoT / Smartphone Data
    gps_lat             REAL,
    gps_lng             REAL,
    noise_level         REAL,
    capture_time        DATETIME,
    phone_device        VARCHAR(100),
    gps_accuracy        REAL,
    sensor_source       VARCHAR(50),         -- 'real_field_survey' | 'simulated'
    iot_note            TEXT,
    light_level         REAL,
    temperature         REAL,
    humidity            REAL,
    os_version          VARCHAR(50),
    app_version         VARCHAR(20),
    area_quality_score  REAL,
    field_notes        TEXT,
    field_photos        TEXT,                -- JSON array
    image_url           VARCHAR(500),
    image_urls          TEXT,                -- JSON array
    iot_device_id       VARCHAR(100),
    iot_collected_at    DATETIME,
    verification_notes TEXT,

    -- Evidence Tier (E1-E5)
    evidence_tier              VARCHAR(2),
    evidence_tier_updated_at   DATETIME,

    -- Metadata mở rộng (Round 17)
    collection_timestamp  DATETIME,           -- When record was added to DB
    data_source_region    VARCHAR(50),        -- 'hanoi' | 'hcmc'
    source_region        VARCHAR(50),        -- Province-level region label

    -- Timestamps
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_updated_at      DATETIME,
    description          TEXT,

    -- Archive metadata (nullable — only set when archived)
    archive_reason       TEXT,
    archived_at          DATETIME
);

-- Indexes for properties
CREATE INDEX IF NOT EXISTS idx_properties_record_status   ON properties(record_status);
CREATE INDEX IF NOT EXISTS idx_properties_evidence_tier    ON properties(evidence_tier);
CREATE INDEX IF NOT EXISTS idx_properties_district        ON properties(district);
CREATE INDEX IF NOT EXISTS idx_properties_province       ON properties(province_city);
CREATE INDEX IF NOT EXISTS idx_properties_property_type  ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_properties_verification  ON properties(verification_status);
CREATE INDEX IF NOT EXISTS idx_properties_source_method ON properties(source_access_method);
CREATE INDEX IF NOT EXISTS idx_properties_source_url     ON properties(source_url);
CREATE INDEX IF NOT EXISTS idx_properties_price          ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_listing_date   ON properties(listing_date);
CREATE INDEX IF NOT EXISTS idx_properties_created_at      ON properties(created_at);
CREATE INDEX IF NOT EXISTS idx_properties_sensor_source  ON properties(sensor_source);
CREATE INDEX IF NOT EXISTS idx_properties_collection_ts ON properties(collection_timestamp);
CREATE INDEX IF NOT EXISTS idx_properties_data_region   ON properties(data_source_region);

-- ============================================================================
-- TABLE: model_versions
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_versions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version         VARCHAR(50)  NOT NULL UNIQUE,
    model_name            VARCHAR(100),
    train_start_date      DATETIME,
    train_end_date        DATETIME,
    trained_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    train_record_count    INTEGER,
    verified_record_count INTEGER,
    self_collected_ratio  REAL,
    mae                   REAL,
    rmse                  REAL,
    r2                    REAL,
    model_path            VARCHAR(255),
    notes                 TEXT
);

-- ============================================================================
-- TABLE: audit_logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id       INTEGER,
    table_name      VARCHAR(50),
    action_type     VARCHAR(50) NOT NULL,    -- CREATE | UPDATE | DELETE | VERIFY | REJECT
    changed_by      VARCHAR(100),
    changed_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    old_value_json  TEXT,
    new_value_json   TEXT,
    change_note      TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_record_id  ON audit_logs(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON audit_logs(changed_at);

-- ============================================================================
-- TABLE: data_sources
-- ============================================================================
CREATE TABLE IF NOT EXISTS data_sources (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name           VARCHAR(200) NOT NULL,
    source_url           VARCHAR(500),
    source_type           VARCHAR(50),
    total_records         INTEGER      DEFAULT 0,
    verified_records     INTEGER      DEFAULT 0,
    self_collected_records INTEGER    DEFAULT 0,
    last_collected_at     DATETIME,
    collection_frequency  VARCHAR(50),
    is_active             INTEGER     DEFAULT 1,
    notes                 TEXT,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLE: provenance_chains (Audit Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS provenance_chains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER NOT NULL,
    step            VARCHAR(50) NOT NULL,   -- CRAWLED | PARSED | VALIDATED | ENRICHED | VERIFIED | IMPORTED
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    actor           VARCHAR(100) NOT NULL,  -- system:scraper | user:admin | system:generator
    input_hash      VARCHAR(64),
    output_hash     VARCHAR(64),
    source          VARCHAR(200),
    verify_url      VARCHAR(500),
    metadata_json   TEXT,
    prev_step_id    INTEGER REFERENCES provenance_chains(id)
);

CREATE INDEX IF NOT EXISTS idx_prov_property_id ON provenance_chains(property_id);
CREATE INDEX IF NOT EXISTS idx_prov_step        ON provenance_chains(step);
CREATE INDEX IF NOT EXISTS idx_prov_timestamp   ON provenance_chains(timestamp);

-- ============================================================================
-- TABLE: collection_sources (Scraper Config)
-- ============================================================================
CREATE TABLE IF NOT EXISTS collection_sources (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key            VARCHAR(200) NOT NULL UNIQUE,
    source_name           VARCHAR(200) NOT NULL,
    source_type           VARCHAR(50),
    base_url             VARCHAR(500),
    rate_limit_seconds   INTEGER DEFAULT 2,
    requires_proxy       INTEGER DEFAULT 0,
    is_active            INTEGER DEFAULT 1,
    is_approved          INTEGER DEFAULT 0,
    total_records        INTEGER DEFAULT 0,
    successful_records   INTEGER DEFAULT 0,
    failed_records      INTEGER DEFAULT 0,
    last_run_at          DATETIME,
    last_run_status      VARCHAR(50),
    notes                TEXT,
    approved_by          VARCHAR(100),
    approved_at          DATETIME,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLE: predictions
-- ============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER,
    input_features  TEXT,
    predicted_price REAL         NOT NULL,
    confidence      REAL,
    model_used      VARCHAR(50),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pred_property_id ON predictions(property_id);

-- ============================================================================
-- TABLE: prediction_history
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_history (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id             INTEGER,
    input_features_json     TEXT,
    predicted_price         REAL         NOT NULL,
    confidence_low          REAL,
    confidence_high         REAL,
    model_version           VARCHAR(50),
    model_name              VARCHAR(100),
    feature_importance_json TEXT,
    similar_records_json    TEXT,
    explanation_text        TEXT,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ph_property_id ON prediction_history(property_id);
CREATE INDEX IF NOT EXISTS idx_ph_model_ver  ON prediction_history(model_version);

-- ============================================================================
-- TABLE: baseline_models (Legacy)
-- ============================================================================
CREATE TABLE IF NOT EXISTS baseline_models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL,
    repo_url    VARCHAR(500),
    license     VARCHAR(50),
    metrics     TEXT,
    is_active   INTEGER DEFAULT 1,
    notes       TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SAMPLE SEED DATA (6 quận production-ready)
-- ============================================================================
-- Không có seed data ở đây — dữ liệu sinh bởi generate_production_data.py

-- ============================================================================
-- VIEW: v_active_properties (Lọc active records)
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_active_properties AS
SELECT * FROM properties
WHERE record_status NOT IN ('archived')
  AND price IS NOT NULL
  AND price > 0
  AND property_type IS NOT NULL;

-- ============================================================================
-- VIEW: v_tier_distribution
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_tier_distribution AS
SELECT
    evidence_tier                        AS tier,
    COUNT(*)                            AS record_count,
    ROUND(COUNT(*) * 100.0 /
        (SELECT COUNT(*) FROM properties
         WHERE record_status NOT IN ('archived')), 1) AS percentage
FROM properties
WHERE record_status NOT IN ('archived')
GROUP BY evidence_tier
ORDER BY evidence_tier;

-- ============================================================================
-- VIEW: v_production_summary
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_production_summary AS
SELECT
    district,
    data_source_region,
    evidence_tier,
    COUNT(*) AS record_count,
    ROUND(AVG(price), 0)           AS avg_price,
    ROUND(AVG(price_per_m2), 0)     AS avg_price_m2,
    ROUND(AVG(area_m2), 1)          AS avg_area
FROM properties
WHERE record_status NOT IN ('archived')
GROUP BY district, data_source_region, evidence_tier
ORDER BY district, evidence_tier;

-- ============================================================================
-- SQL Server / SSMS VERSION (if migrating to SQL Server)
-- Copy everything below this line for SSMS
-- ============================================================================
-- NOTE: SQLite uses INTEGER + AUTOINCREMENT
-- SQL Server uses IDENTITY(1,1) and BIT instead of INTEGER for bools

-- ============================================================================
-- NORMALIZED SCHEMA APPENDIX (v1.0 — 2026-04-23)
-- From: SPEC-PRODUCTION.md Part 3 + SCHEMA.md v2.0
-- Purpose: Normalize flat properties table into domain-grouped tables
-- Database: SQLite compatible (INTEGER PKs, TEXT for JSON)
-- Migration script: migrate_to_normalized_schema.sql
-- ============================================================================

-- -------------------------------------------------------
-- Group: asset_core / location_context
-- Province/district/ward + GPS + geocode quality
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
-- Noise, flood, pollution, distances to amenities
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
-- Road width, alley, parking, public transport access
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
-- Valuation run records (AVM engine output)
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
-- 4 scenarios per valuation run
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
-- Group: overlay / spiritual_history
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
-- Group: training / training_run
-- ML model training metadata
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

-- ============================================================================
-- NORMALIZED SCHEMA INDEXES (v1.0 — 2026-04-23)
-- All indexes from SPEC-PRODUCTION.md section 3.3 + extras from SCHEMA.md
-- ============================================================================

-- Geo queries
CREATE INDEX IF NOT EXISTS idx_location_coords ON location_context(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_location_geocode ON location_context(geocode_quality);
CREATE INDEX IF NOT EXISTS idx_location_cluster ON location_context(district);
CREATE INDEX IF NOT EXISTS idx_location_province ON location_context(province_city);
CREATE INDEX IF NOT EXISTS idx_location_province_district ON location_context(province_city, district);

-- Property lookups (extended)
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

-- ============================================================================
-- NORMALIZED SCHEMA VIEWS (v1.0)
-- Convenient joins over the normalized structure
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_property_full AS
SELECT
    p.id,
    p.property_type,
    p.province_city,
    p.district,
    p.ward,
    p.street_or_project,
    p.area_m2,
    p.price,
    p.price_per_m2,
    p.record_status,
    lc.latitude,
    lc.longitude,
    lc.geocode_quality,
    pg.shape_profile,
    pg.area_official_m2,
    pg.frontage_m,
    bu.floor_count,
    bu.bedrooms,
    bu.bathrooms,
    bu.structure_grade,
    bu.construction_year,
    aa.floor AS apt_floor,
    aa.block_name,
    aa.view_quality,
    lp.ownership_type,
    lp.certificate_type,
    lp.dispute_flag,
    lp.mortgage_flag,
    lp.planning_zone,
    ec.flood_risk,
    ec.noise_level,
    ac.road_width_m,
    ac.alley_width_m,
    ac.access_class,
    p.created_at,
    p.updated_at
FROM properties p
LEFT JOIN location_context lc ON lc.property_id = p.id
LEFT JOIN parcel_geometry pg ON pg.property_id = p.id
LEFT JOIN building_unit bu ON bu.property_id = p.id
LEFT JOIN apartment_attributes aa ON aa.property_id = p.id
LEFT JOIN legal_planning lp ON lp.property_id = p.id
LEFT JOIN environment_context ec ON ec.property_id = p.id
LEFT JOIN access_context ac ON ac.property_id = p.id
WHERE p.record_status NOT IN ('archived');

CREATE VIEW IF NOT EXISTS v_valuation_summary AS
SELECT
    vr.id,
    vr.property_id,
    vr.engine_version,
    vr.fair_market_value_vnd,
    vr.quick_sale_value_vnd,
    vr.recommended_listing_vnd,
    vr.overall_confidence,
    vr.confidence_grade,
    vr.evidence_tier,
    vr.run_at,
    p.property_type,
    p.district,
    p.price AS listed_price
FROM valuation_runs vr
JOIN properties p ON p.id = vr.property_id
ORDER BY vr.run_at DESC;

-- ============================================================================
-- END OF NORMALIZED SCHEMA APPENDIX
-- ============================================================================
