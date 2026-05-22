# Domain Schema v2.0 — Bounded Module Architecture

> **Phiên bản:** 2.0 | **Trạng thái:** KHÓA | **Ngày:** 2026-04-22
> **Dựa trên:** Product Spec v1 + 4 Taxonomy files
> **Migrate từ:** 9 bảng cũ (Property, ModelVersion, AuditLog, DataSource, BaselineModel, Prediction, PredictionHistory, ProvenanceChain, CollectionSource)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ASSET INTAKE LAYER                       │
│  property_asset → location_context → parcel_geometry       │
│  building_unit → apartment_attributes                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    MARKET CONTEXT LAYER                     │
│  legal_planning → environment_context → access_context      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    OVERLAY LAYER                            │
│  spiritual_history → persona_profile                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 VALUATION OUTPUT LAYER                      │
│  valuation_run ← valuation_adjustment ← evidence_asset      │
│                         ↓                                   │
│                  confidence_band                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    TRAINING LAYER                           │
│  training_run ← training_sample ← address, property_image   │
└─────────────────────────────────────────────────────────────┘
```

---

## Module 1: property_asset

**Bảng gốc:** `properties` (phần core — giữ lại)

**Mục đích:** Asset identity và loại tài sản. KHÔNG chứa thông tin vị trí, hình dạng, hay giá.

```sql
CREATE TABLE property_asset (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_class     VARCHAR(20) NOT NULL,      -- RESIDENTIAL|COMMERCIAL|LAND|INDUSTRIAL|MIXED
    asset_type      VARCHAR(30) NOT NULL,     -- APARTMENT|TOWNHOUSE|VILLA|LAND_URBAN...
    asset_subtype   VARCHAR(30),               -- APT_STANDARD|LAND_LEGAL_STREET...
    purpose         VARCHAR(30),             -- PRIMARY_RESIDENCE|INVESTMENT|RENTAL|COMMERCIAL
    status          VARCHAR(20) DEFAULT 'active',  -- active|archived|demo|pending
    source_system   VARCHAR(20),              -- legacy_properties|manual|api|scraper
    legacy_id       INTEGER,                  -- FK sang bảng cũ properties.id
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),

    CONSTRAINT chk_asset_class CHECK (asset_class IN ('RESIDENTIAL','COMMERCIAL','LAND','INDUSTRIAL','MIXED')),
    CONSTRAINT chk_asset_type CHECK (asset_type IN (
        'APARTMENT','TOWNHOUSE','VILLA','ROWHOUSE','PENTHOUSE','STUDIO',
        'SHOPHOUSE','OFFICE_TEL','RETAIL_UNIT','WAREHOUSE',
        'LAND_URBAN','LAND_SUBURBAN','LAND_AGRICULTURAL','LAND_PROJECT',
        'HOTEL','RESORT','CONDO_HOTEL'
    ))
);

CREATE INDEX idx_property_asset_type ON property_asset(asset_type);
CREATE INDEX idx_property_asset_class ON property_asset(asset_class);
CREATE INDEX idx_property_asset_status ON property_asset(status);
CREATE INDEX idx_property_asset_legacy ON property_asset(legacy_id) WHERE legacy_id IS NOT NULL;
```

**Chuyển đổi từ bảng cũ:**
- `property_type` → `asset_type` (map sang taxonomy mới)
- `record_status` → `status` (map: raw→pending, verified→active, rejected→archived)
- `verification_status` → giữ trong bảng riêng (legal_planning)

---

## Module 2: location_context

**Mục đích:** Thông tin vị trí địa lý. Tách riêng để có thể update độc lập.

```sql
CREATE TABLE location_context (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Province/District/Ward
    province_city        VARCHAR(100) NOT NULL,
    district             VARCHAR(100) NOT NULL,
    ward                 VARCHAR(100),
    street_or_project    VARCHAR(255),
    
    -- Coordinates
    latitude             FLOAT,
    longitude            FLOAT,
    geocode_quality      VARCHAR(20) DEFAULT 'unknown',  -- high|medium|low|unknown
    geocode_source       VARCHAR(50),                   -- google|mapbox|nominatim|manual
    
    -- Distance metrics (cache)
    distance_to_center_km    FLOAT,     -- Cách trung tâm thành phố
    distance_to_metro_km     FLOAT,     -- Cách metro gần nhất
    distance_to_park_km      FLOAT,     -- Cách công viên gần nhất
    
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),

    CONSTRAINT chk_lat CHECK (latitude BETWEEN 8 AND 24),   -- VN lat range
    CONSTRAINT chk_lng CHECK (longitude BETWEEN 102 AND 110) -- VN lng range
);

CREATE INDEX idx_location_property ON location_context(property_asset_id);
CREATE INDEX idx_location_province ON location_context(province_city);
CREATE INDEX idx_location_district ON location_context(province_city, district);
CREATE INDEX idx_location_geo ON location_context(latitude, longitude);
```

**Chuyển đổi:**
- `latitude/longitude` từ bảng cũ → giữ
- `province_city/district/ward/street_or_project` từ bảng cũ → giữ
- Thêm `geocode_quality` để track chất lượng geocoding

---

## Module 3: parcel_geometry

**Mục đích:** Hình dạng và kích thước đất. Chỉ dùng cho LAND types.

```sql
CREATE TABLE parcel_geometry (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Area
    area_official_m2    FLOAT,        -- Diện tích theo sổ đỏ
    area_measured_m2    FLOAT,       -- Diện tích đo thực tế (nếu khác)
    area_diff_pct       FLOAT,      -- Chênh lệch % (area_diff = area_measured - area_official)
    
    -- Polygon (PostGIS geometry — lưu trong bảng geometry_features)
    polygon_json        JSONB,       -- [{lat, lng}, {lat, lng}, ...] cho frontend
    vertices_count      INTEGER,    -- Số đỉnh
    edges_json          JSONB,       -- [{length_m, azimuth_deg}, ...]
    
    -- Frontage
    frontage_segments   JSONB,      -- [{width_m, road_class}, ...] — có thể nhiều mặt tiền
    frontage_total_m     FLOAT,      -- Tổng chiều rộng mặt tiền
    frontage_road_class  VARCHAR(20), -- main_street|alley_5m|alley_3m|alley_2m|alley_1m
    
    -- Depth profile
    depth_min_m          FLOAT,      -- Chiều sâu tối thiểu
    depth_max_m          FLOAT,      -- Chiều sâu tối đa
    depth_avg_m          FLOAT,      -- Chiều sâu trung bình
    depth_variation_pct  FLOAT,      -- (depth_max - depth_min) / depth_avg * 100
    
    -- Shape classification
    taper_type           VARCHAR(20), -- uniform|nö_hậu|thóp_hậu|reverse_taper|irregular
    irregularity_score   FLOAT,      -- 0 (vuông) → 1 (hoàn toàn méo), computed
    nö_hậu_score         FLOAT,      -- 0 → 1, vuông vắn = 1
    thóp_hậu_score       FLOAT,      -- 0 → 1, bị thắt = 1
    
    -- Special features
    has_alley_branch     BOOLEAN,    -- Có hẻm phụ tách ra
    alley_branch_count   INTEGER,   -- Số hẻm phụ
    corner_plot          BOOLEAN,    -- Đất góc (2+ mặt tiền)
    
    -- Reference (không dùng cho land: để NULL)
    reference_length_m   FLOAT,      -- Chiều dài reference cho so sánh
    
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_area_positive CHECK (area_official_m2 > 0),
    CONSTRAINT chk_taper CHECK (taper_type IN ('uniform','nö_hậu','thóp_hậu','reverse_taper','irregular'))
);

CREATE INDEX idx_parcel_asset ON parcel_geometry(property_asset_id);
CREATE INDEX idx_parcel_taper ON parcel_geometry(taper_type);
CREATE INDEX idx_parcel_irregularity ON parcel_geometry(irregularity_score);
```

**Computation:**

```python
def compute_geometry_scores(vertices: list[tuple[float, float]], edges: list[float]) -> dict:
    """
    1. Tính area từ polygon (Shoelace formula)
    2. Tính nö_hậu_score = ideal_area / actual_area (vuông = 1.0)
    3. Tính thóp_hậu_score từ min_width / max_width
    4. Tính irregularity từ perimeter_ratio
    """
    # Implementation in src/domain/valuation/geometry_calculator.py
```

---

## Module 4: building_unit

**Mục đích:** Thông tin công trình trên đất (nhà phố, villa, etc.)

```sql
CREATE TABLE building_unit (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Size
    built_area_m2        FLOAT,      -- Diện tích xây dựng
    usable_area_m2       FLOAT,      -- Diện tích sử dụng (có thể < built_area)
    
    -- Floors
    floor_count          INTEGER DEFAULT 1,
    floor_actual         INTEGER,    -- Số tầng thực tế (có thể khác với floor_count)
    has_basement         BOOLEAN DEFAULT FALSE,
    basement_area_m2     FLOAT,
    has_attic            BOOLEAN DEFAULT FALSE,
    attic_area_m2        FLOAT,
    basement_count       INTEGER DEFAULT 0,
    
    -- Rooms
    bedrooms             INTEGER,
    bathrooms            INTEGER,
    other_rooms          JSONB,      -- {"kitchen": 1, "living_room": 1, "study": 1, ...}
    
    -- Facade
    facade_count          INTEGER DEFAULT 1,  -- 1=một mặt tiền, 2=góc, 3=ngõ mở
    frontage_m            FLOAT,
    
    -- Structure
    structure_grade      VARCHAR(20), -- RC (reinforced concrete)|BRICK|COMPOSITE|WOOD|TEMPORARY
    construction_year    INTEGER,      -- Năm xây dựng (ước tính nếu không biết)
    construction_quality VARCHAR(20),  -- premium|standard|budget
    
    -- Orientation
    main_facing          VARCHAR(20), -- NORTH|SOUTH|EAST|WEST|NORTHEAST|...|NORTHWEST
    
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_floor_positive CHECK (floor_count > 0 AND floor_count <= 100),
    CONSTRAINT chk_structure CHECK (structure_grade IN ('RC','BRICK','COMPOSITE','WOOD','TEMPORARY'))
);

CREATE INDEX idx_building_asset ON building_unit(property_asset_id);
CREATE INDEX idx_building_floors ON building_unit(floor_count);
CREATE INDEX idx_building_facade ON building_unit(facade_count);
```

**Chuyển đổi:**
- `floor_count`, `bedrooms`, `bathrooms`, `frontage_m` từ bảng cũ → giữ
- Thêm `structure_grade`, `construction_year`, `main_facing` (mới)

---

## Module 5: apartment_attributes

**Mục đích:** Thuộc tính riêng của căn hộ (chỉ dùng cho APARTMENT type)

```sql
CREATE TABLE apartment_attributes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Location in building
    block_name          VARCHAR(50),  -- Tên block/tower (A, B, C...)
    floor               INTEGER NOT NULL,
    unit_position       VARCHAR(20),  -- middle|end|corner|wing_A|wing_B
    
    -- Orientation
    door_orientation    VARCHAR(20),  -- Hướng cửa chính (8 hướng)
    balcony_orientation  VARCHAR(20), -- Hướng ban công
    main_facing          VARCHAR(20),  -- Hướng nhìn chính
    
    -- View
    view_type           VARCHAR(30), -- CITY|PARK|RIVER|MOUNTAIN|NOTHING|CITY_PARK
    view_obstruction    FLOAT,       -- 0 (clear) → 1 (blocked), % view bị che
    
    -- Proximity to amenities
    elevator_distance    VARCHAR(10), -- very_close|close|medium|far|very_far
    trash_room_distance  VARCHAR(10),
    core_distance        VARCHAR(10), -- Lõi kỹ thuật
    stair_distance       VARCHAR(10),
    
    -- Layout quality
    layout_score         FLOAT,      -- 0 → 1, bố cục tốt = 1
    layout_flags         JSONB,      -- {"balcony_bedroom": True, "kitchen_connected": True, ...}
    bedrooms             INTEGER,
    bathrooms            INTEGER,
    has_utilities_room   BOOLEAN,
    
    -- Environmental
    sunlight_exposure    VARCHAR(20), -- EXCELLENT|GOOD|FAIR|POOR (nắng Tây = POOR)
    ventilation_score    FLOAT,      -- 0 → 1, thông thoáng = 1
    noise_inside_db      FLOAT,      -- Tiếng ồn trong căn (dB)
    
    -- Building quality (áp dụng cho toàn block)
    building_quality     VARCHAR(20), -- luxury|premium|standard|economy
    building_age_years   INTEGER,
    has_concierge        BOOLEAN,
    has_pool             BOOLEAN,
    has_gym              BOOLEAN,
    
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_floor CHECK (floor >= -3 AND floor <= 100),  -- -3 = basement
    CONSTRAINT chk_view CHECK (view_type IN ('CITY','PARK','RIVER','MOUNTAIN','NOTHING','CITY_PARK','PARK_RIVER'))
);

CREATE INDEX idx_apt_asset ON apartment_attributes(property_asset_id);
CREATE INDEX idx_apt_floor ON apartment_attributes(floor);
CREATE INDEX idx_apt_block ON apartment_attributes(block_name);
CREATE INDEX idx_apt_view ON apartment_attributes(view_type);
```

---

## Module 6: legal_planning

**Mục đích:** Pháp lý và quy hoạch. Nguồn EVIDENCE chính cho market valuation.

```sql
CREATE TABLE legal_planning (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Ownership
    ownership_type      VARCHAR(30), -- FULL_OWNERSHIP|LURC|LEASEHOLD|PENDING|DISPUTE|OTHER
    certificate_number   VARCHAR(100),
    certificate_issued_at DATE,
    certificate_issuer  VARCHAR(100), -- Cơ quan cấp sổ
    
    -- Status
    dispute_flag        BOOLEAN DEFAULT FALSE,
    dispute_type        VARCHAR(50), -- boundary|inheritance|planning|other
    dispute_notes       TEXT,
    
    mortgage_flag       BOOLEAN DEFAULT FALSE,
    mortgage_bank       VARCHAR(100),
    mortgage_amount_vnd BIGINT,
    
    -- Planning
    planning_zone       VARCHAR(30), -- RESIDENTIAL|COMMERCIAL|MIXED|INDUSTRIAL|AGRICULTURAL|PARK|ROAD
    planning_subzone    VARCHAR(50),
    
    -- Risk flags
    road_expansion_risk  VARCHAR(10), -- none|low|medium|high|severe
    road_expansion_m     FLOAT,      -- Độ rộng quy hoạch mở đường
    setback_risk         VARCHAR(10), -- none|low|medium|high
    setback_front_m      FLOAT,      -- Lộ giới trước nhà (quy hoạch)
    setback_back_m       FLOAT,      -- Lộ giới sau
    height_limit_m      FLOAT,       -- Giới hạn chiều cao theo quy hoạch
    
    -- Land use
    land_use_purpose    VARCHAR(100),
    land_use_certified  BOOLEAN DEFAULT FALSE,
    
    -- Evidence
    legal_evidence_ids  UUID[],      -- FK sang evidence_asset
    legal_verified_by   VARCHAR(100),
    legal_verified_at   TIMESTAMP,
    
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_ownership CHECK (ownership_type IN (
        'FULL_OWNERSHIP','LURC','LEASEHOLD','PENDING','DISPUTE','OTHER'
    ))
);

CREATE INDEX idx_legal_asset ON legal_planning(property_asset_id);
CREATE INDEX idx_legal_ownership ON legal_planning(ownership_type);
CREATE INDEX idx_legal_dispute ON legal_planning(dispute_flag);
CREATE INDEX idx_legal_planning_zone ON legal_planning(planning_zone);
```

---

## Module 7: environment_context

**Mục đích:** Môi trường xung quanh và các rủi ro tự nhiên.

```sql
CREATE TABLE environment_context (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Flood risk
    flood_risk          VARCHAR(10) DEFAULT 'unknown', -- none|minor|moderate|severe|unknown
    flood_frequency     VARCHAR(20), -- never|rarely|seasonal|annual|frequent
    flood_depth_m       FLOAT,      -- Độ sâu ngập ước tính
    flood_source        VARCHAR(30), -- historical|modelled|both|none
    
    -- Nearby hazards (khoảng cách)
    cemetery_distance_m     FLOAT,
    landfill_distance_m     FLOAT,
    power_line_distance_m   FLOAT,
    industrial_zone_m       FLOAT,
    
    -- Pollution
    pollution_score     FLOAT,      -- 0 (sạch) → 1 (ô nhiễm nặng)
    air_quality_index   INTEGER,   -- AQI
    
    -- Noise
    noise_day_db        FLOAT,     -- Tiếng ồn ban ngày (dB)
    noise_night_db      FLOAT,     -- Tiếng ồn ban đêm (dB)
    noise_source        VARCHAR(30), -- road|construction|industrial|airport|railway|none
    
    -- Positive features
    river_distance_m     FLOAT,
    park_distance_m      FLOAT,
    lake_distance_m      FLOAT,
    school_distance_m    FLOAT,
    hospital_distance_m  FLOAT,
    market_distance_m    FLOAT,
    metro_distance_m      FLOAT,
    
    -- Environmental scores
    env_quality_score    FLOAT GENERATED ALWAYS AS (
        CASE
            WHEN flood_risk = 'none' AND pollution_score < 0.3 AND noise_day_db < 60 THEN 0.9
            WHEN flood_risk = 'minor' AND pollution_score < 0.5 THEN 0.7
            WHEN flood_risk IN ('moderate','severe') THEN 0.4
            ELSE 0.5
        END
    ) STORED,
    
    evidence_ids        UUID[],
    survey_date         DATE,
    
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_flood CHECK (flood_risk IN ('none','minor','moderate','severe','unknown')),
    CONSTRAINT chk_noise_db CHECK (noise_day_db IS NULL OR (noise_day_db >= 20 AND noise_day_db <= 120))
);

CREATE INDEX idx_env_asset ON environment_context(property_asset_id);
CREATE INDEX idx_env_flood ON environment_context(flood_risk);
CREATE INDEX idx_env_pollution ON environment_context(pollution_score);
```

---

## Module 8: access_context

**Mục đích:** Đường vào và khả năng tiếp cận.

```sql
CREATE TABLE access_context (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Road class
    road_class          VARCHAR(20), -- MAIN_STREET|SECONDARY_STREET|ALLEY_5M|ALLEY_3M|ALLEY_2M|ALLEY_1M
    road_width_m        FLOAT,       -- Chiều rộng đường hiện tại
    road_surface        VARCHAR(20), -- ASPHALT|CONCRETE|GRAVEL|DIRT
    road_planned_width_m FLOAT,      -- Chiều rộng theo quy hoạch
    
    -- Access flags
    car_access          BOOLEAN,     -- Ô tô vào được
    truck_access        BOOLEAN,     -- Xe tải vào được
    motorcycle_access   BOOLEAN DEFAULT TRUE,
    dead_end            BOOLEAN DEFAULT FALSE,
    
    -- Alley specifics
    alley_type          VARCHAR(20), -- NONE|FRONT|PASS_THROUGH|CUL_DE_SAC|LOOP
    alley_branch_count   INTEGER DEFAULT 0,
    alley_depth_m        FLOAT,      -- Chiều dài hẻm
    
    -- Access score
    access_score        FLOAT GENERATED ALWAYS AS (
        CASE road_class
            WHEN 'MAIN_STREET' THEN 1.0
            WHEN 'SECONDARY_STREET' THEN 0.85
            WHEN 'ALLEY_5M' THEN 0.75
            WHEN 'ALLEY_3M' THEN 0.55
            WHEN 'ALLEY_2M' THEN 0.35
            WHEN 'ALLEY_1M' THEN 0.15
            ELSE 0.5
        END * CASE WHEN car_access THEN 1.0 WHEN truck_access THEN 0.9 ELSE 0.7 END
    ) STORED,
    
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_road_class CHECK (road_class IN (
        'MAIN_STREET','SECONDARY_STREET','ALLEY_5M','ALLEY_3M','ALLEY_2M','ALLEY_1M','NONE'
    ))
);

CREATE INDEX idx_access_asset ON access_context(property_asset_id);
CREATE INDEX idx_access_class ON access_context(road_class);
CREATE INDEX idx_access_car ON access_context(car_access);
```

---

## Module 9: spiritual_history

**Mục đích:** Lịch sử tâm linh của đất/nhà. KHÔNG ảnh hưởng market value, chỉ ảnh hưởng fit score.

```sql
CREATE TABLE spiritual_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    death_history_flag      BOOLEAN DEFAULT FALSE,
    death_count             INTEGER DEFAULT 0,
    death_nature            VARCHAR(50), -- natural|accident|unknown
    death_year_range        VARCHAR(30), -- "1990-1995" | NULL
    
    worship_site_proximity_m  FLOAT,  -- Đền/chùa/nhà thờ gần nhất
    worship_site_type          VARCHAR(20), -- temple|church|mosque|pagoda|shrine|none
    
    stigma_known             BOOLEAN DEFAULT FALSE,
    stigma_severity          VARCHAR(10), -- mild|moderate|severe
    stigma_notes             TEXT,
    
    verified_level          VARCHAR(20) DEFAULT 'unverified', -- unverified|partial|verified|disputed
    verified_by             VARCHAR(100),
    verified_at             TIMESTAMP,
    verification_method     VARCHAR(30), -- field_visit|local_interview|document|hearsay
    
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at             TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_verified CHECK (verified_level IN ('unverified','partial','verified','disputed'))
);

CREATE INDEX idx_spirit_asset ON spiritual_history(property_asset_id);
CREATE INDEX idx_spirit_death ON spiritual_history(death_history_flag);
CREATE INDEX idx_spirit_stigma ON spiritual_history(stigma_known);
```

---

## Module 10: persona_profile

**Mục đích:** Profile của người mua tiềm năng. Không bắt buộc — có thể anonymous.

```sql
CREATE TABLE persona_profile (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Archetype
    buyer_archetype     VARCHAR(30), -- FIRST_HOME|UPGRADER|INVESTOR|SPECULATOR|RETIREE|ANONYMOUS
    
    -- Budget
    budget_min_vnd      BIGINT,
    budget_max_vnd       BIGINT,
    budget_band          VARCHAR(20), -- BELOW_2B|2B_TO_5B|5B_TO_10B|10B_TO_20B|ABOVE_20B
    
    -- Timeline
    holding_horizon      VARCHAR(20), -- FLIP_12M|SHORT_3Y|MEDIUM_5Y|LONG_10Y|FOREVER
    
    -- Feng shui
    feng_shui_sensitivity VARCHAR(20) DEFAULT 'NONE', -- NONE|LOW|MEDIUM|HIGH|CRITICAL
    birth_year            INTEGER,    -- Để tính hướng phong thủy
    element_preference    VARCHAR(10), -- WOOD|FIRE|EARTH|METAL|WATER|NONE
    
    -- Lifestyle
    liquidity_preference VARCHAR(20), -- MAX_LIQUID|PREFER_LIQUID|BALANCED|PREFER_APPRECIATION
    family_structure      VARCHAR(30), -- SINGLE|COUPLE_NO_KIDS|COUPLE_WITH_KIDS|LARGE_FAMILY|ELDERLY_PARENTS
    noise_tolerance       VARCHAR(20) DEFAULT 'NEUTRAL',
    view_preference       VARCHAR(20),
    
    -- Investment
    investment_profile    VARCHAR(30), -- RENTAL_YIELD|CAPITAL_APPRECIATION|BALANCED_RETURN
    location_flexibility  VARCHAR(20), -- CBD_ONLY|DISTRICT_FLEXIBLE|CITY_WIDE|SUBURBS_OK
    
    -- Age & occupation
    age_group             VARCHAR(20),
    occupation_type       VARCHAR(30),
    
    -- Audit
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_archetype CHECK (buyer_archetype IN (
        'FIRST_HOME','UPGRADER','INVESTOR','SPECULATOR','RETIREE','ANONYMOUS'
    ))
);

CREATE INDEX idx_persona_archetype ON persona_profile(buyer_archetype);
CREATE INDEX idx_persona_budget ON persona_profile(budget_band);
CREATE INDEX idx_persona_feng_shui ON persona_profile(feng_shui_sensitivity);
```

---

## Module 11: valuation_run (OUTPUT — QUAN TRỌNG)

**Mục đích:** Kết quả định giá của một lần chạy engine.

```sql
CREATE TABLE valuation_run (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    -- Engine info
    engine_version      VARCHAR(20) NOT NULL,  -- v2_alpha, v2_beta
    run_at              TIMESTAMP DEFAULT NOW(),
    
    -- Base price (từ comparable base hoặc model)
    base_price_vnd      BIGINT,
    base_price_source   VARCHAR(30), -- comparable|model|hybrid
    
    -- Scenario outputs
    fair_market_value_vnd      BIGINT NOT NULL,
    quick_sale_value_vnd       BIGINT,
    recommended_listing_vnd    BIGINT,
    optimistic_ask_vnd         BIGINT,
    expected_range_low_vnd     BIGINT,
    expected_range_high_vnd    BIGINT,
    
    -- Liquidity
    liquidity_score     VARCHAR(10), -- high|medium|low
    liquidity_band       FLOAT,      -- 0 → 1, cao = dễ bán
    
    -- Confidence (từ quality assessment)
    overall_confidence  FLOAT,      -- 0 → 1
    confidence_grade     VARCHAR(1), -- A|B|C|D
    evidence_tier        VARCHAR(2), -- E1|E2|E3|E4|E5
    
    -- Comparable stats
    comparable_count    INTEGER,
    effective_sample_size FLOAT,
    anchor_share        FLOAT,
    independent_source_count INTEGER,
    
    -- Input hash (để truy ngược input)
    input_hash          VARCHAR(64),  -- SHA256 of input
    
    -- Persona used (nếu có)
    persona_profile_id   UUID REFERENCES persona_profile(id),
    
    -- Legacy reference (để migrate)
    legacy_prediction_id INTEGER,
    
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_valuation_asset ON valuation_run(property_asset_id);
CREATE INDEX idx_valuation_date ON valuation_run(run_at DESC);
CREATE INDEX idx_valuation_confidence ON valuation_run(confidence_grade);
CREATE INDEX idx_valuation_persona ON valuation_run(persona_profile_id);
```

---

## Module 12: valuation_adjustment

**Mục đích:** Từng adjustment factor trong ledger.

```sql
CREATE TABLE valuation_adjustment (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    valuation_run_id    UUID NOT NULL REFERENCES valuation_run(id) ON DELETE CASCADE,
    
    -- Factor identity
    factor_code         VARCHAR(30) NOT NULL,  -- LEGAL_FULL|ALLEY_3M|FLOOD_SEVERE...
    layer               VARCHAR(20) NOT NULL,   -- MARKET|FIT
    factor_group        VARCHAR(20),           -- L1_LEGAL|L2_GEOM|L3_ACCESS...
    
    -- Adjustment values
    direction           VARCHAR(10) NOT NULL,   -- POSITIVE|NEGATIVE|NEUTRAL
    delta_pct           FLOAT NOT NULL,        -- e.g., 0.04 = +4%
    delta_vnd           BIGINT NOT NULL,        -- e.g., 260_000_000
    
    -- Evidence
    confidence          FLOAT NOT NULL,          -- 0 → 1
    rationale           TEXT,                    -- Human-readable explanation
    evidence_id         UUID REFERENCES evidence_asset(id),
    applied_rule_id     VARCHAR(50),            -- Rule that generated this adjustment
    
    -- Source tracking
    source_type         VARCHAR(30), -- comparable|model|rule|manual
    comparable_ids      INTEGER[],   -- Comparable records used
    
    -- Sequence (thứ tự hiển thị)
    display_order       INTEGER DEFAULT 0,
    
    created_at          TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_layer CHECK (layer IN ('MARKET','FIT')),
    CONSTRAINT chk_direction CHECK (direction IN ('POSITIVE','NEGATIVE','NEUTRAL')),
    CONSTRAINT chk_factor_code CHECK (factor_code IN (
        -- Legal
        'LEGAL_FULL','LEGAL_LURC','LEGAL_PENDING','LEGAL_DISPUTE','LEGAL_MORTGAGE',
        'PLANNING_ROAD_EXPAND','PLANNING_SETBACK','PLANNING_COMMERCIAL','PLANNING_GREEN',
        -- Geometry
        'GEOM_NÖHẬU','GEOM_THOP_HAU','GEOM_THOP_HAU_SEVERE','GEOM_TAPER_MINOR','GEOM_TAPER_SEVERE',
        'GEOM_IRREGULAR','GEOM_CORNER_PLOT','DEPTH_60_PLUS','DEPTH_20_MINUS',
        -- Access
        'ACCESS_MAIN_STREET','ACCESS_ALLEY_5M','ACCESS_ALLEY_3M','ACCESS_ALLEY_2M','ACCESS_ALLEY_1M',
        'ACCESS_DEAD_END','ACCESS_ALLEY_BRANCH','ACCESS_TRUCK',
        -- Environment
        'ENV_FLOOD_NONE','ENV_FLOOD_MINOR','ENV_FLOOD_SEVERE',
        'ENV_CEMETERY_200M','ENV_LANDFILL_500M','ENV_POWER_LINE',
        'NOISE_DAY_65DB','NOISE_NIGHT_55DB',
        -- Building
        'BLDG_NEW_5Y','BLDG_MID_10Y','BLDG_OLD_20Y','BLDG_VERY_OLD_20Y+',
        'BLDG_STRUCTURE_RC','BLDG_FLOORS_OPTIMAL','BLDG_FLOORS_EXCEED','BLDG_ATTIC','BLDG_BASEMENT',
        -- Apartment
        'APT_VIEW_RIVER','APT_VIEW_PARK','APT_VIEW_CITY','APT_NO_VIEW',
        'APT_FLOOR_HIGH_15+','APT_FLOOR_LOW_3-','APT_FLOOR_MID_4-14',
        'APT_ELEVATOR_CLOSE','APT_ELEVATOR_FAR','APT_TRASH_NEAR','APT_CORE_ADJACENT',
        'APT_SUNLIGHT_WEST_STRONG','APT_SUNLIGHT_GOOD',
        'APT_VENTILATION_GOOD','APT_VENTILATION_POOR','APT_LAYOUT_OPEN','APT_LAYOUT_FRAGMENTED',
        -- Feng Shui
        'FS_AGE_COMPATIBLE','FS_AGE_INCOMPATIBLE','FS_ELEMENT_*',
        -- Spiritual
        'SPIRIT_DEATH_RECORDED','SPIRIT_WORSHIP_NEAR','SPIRIT_STIGMA_KNOWN','SPIRIT_HISTORY_CLEAN',
        -- Lifestyle
        'FAM_*,LIFE_*,LIQUIDITY_*,INVEST_*'
    ))
);

CREATE INDEX idx_adj_valuation ON valuation_adjustment(valuation_run_id);
CREATE INDEX idx_adj_factor ON valuation_adjustment(factor_code);
CREATE INDEX idx_adj_layer ON valuation_adjustment(layer);
```

---

## Module 13: evidence_asset

**Mục đích:** Nguồn bằng chứng cho từng adjustment.

```sql
CREATE TABLE evidence_asset (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID REFERENCES property_asset(id),
    
    -- Source
    source_type         VARCHAR(30) NOT NULL,  -- FIELD_SURVEY|BANK_APPRAISAL|PUBLIC_LISTING|IOT_SENSOR...
    url_or_ref          TEXT,
    domain              VARCHAR(200),         -- Domain gốc (alonhadat.com.vn)
    
    -- Images
    images_json         JSONB,   -- [{type, path, gps_lat, gps_lng, caption}, ...]
    
    -- Survey
    survey_notes        TEXT,
    survey_date         DATE,
    
    -- Verification
    verified_by         VARCHAR(100),
    verified_at         TIMESTAMP,
    verification_method VARCHAR(30), -- onsite|document|photo|remote
    
    -- Raw content hash (cho provenance)
    raw_content_hash    VARCHAR(64),
    
    -- Evidence tier (computed)
    evidence_tier       VARCHAR(2),  -- E1|E2|E3|E4|E5
    rqs_score           FLOAT,      -- Record Quality Score
    
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_source_type CHECK (source_type IN (
        'FIELD_SURVEY','BANK_APPRAISAL','GOVERNMENT_RECORD','PUBLIC_LISTING',
        'IOT_SENSOR','BATCH_IMPORT','DEMO_DATA','USER_SUBMISSION','BROKER_ESTIMATE'
    ))
);

CREATE INDEX idx_evidence_asset ON evidence_asset(property_asset_id);
CREATE INDEX idx_evidence_tier ON evidence_asset(evidence_tier);
CREATE INDEX idx_evidence_source ON evidence_asset(source_type);
CREATE INDEX idx_evidence_domain ON evidence_asset(domain);
```

---

## Module 14: address (Giữ từ migration)

```sql
CREATE TABLE address (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    full_address        TEXT NOT NULL,
    province_city       VARCHAR(100),
    district            VARCHAR(100),
    ward                VARCHAR(100),
    street              VARCHAR(255),
    
    geocoded_lat        FLOAT,
    geocoded_lng        FLOAT,
    geocode_method      VARCHAR(30),
    geocode_accuracy_m  FLOAT,
    
    created_at          TIMESTAMP DEFAULT NOW()
);
```

---

## Module 15: property_image (Giữ từ migration)

```sql
CREATE TABLE property_image (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_asset_id   UUID NOT NULL REFERENCES property_asset(id) ON DELETE CASCADE,
    
    image_url           TEXT,
    local_path          VARCHAR(500),
    image_type          VARCHAR(30), -- exterior|interior|floor_plan|site_plan|aerial|other
    caption             TEXT,
    
    gps_lat             FLOAT,
    gps_lng             FLOAT,
    
    width_px            INTEGER,
    height_px           INTEGER,
    
    uploaded_by         VARCHAR(100),
    uploaded_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_img_asset ON property_image(property_asset_id);
CREATE INDEX idx_img_type ON property_image(image_type);
```

---

## Module 16: confidence_band

```sql
CREATE TABLE confidence_band (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    valuation_run_id    UUID NOT NULL REFERENCES valuation_run(id) ON DELETE CASCADE,
    
    band_name           VARCHAR(30), -- standard|conservative|optimistic
    lower_bound_vnd     BIGINT,
    upper_bound_vnd     BIGINT,
    interval_ratio      FLOAT,
    
    grade               VARCHAR(1),
    coverage_pct        FLOAT,  -- % comparable trong band
    
    components_json     JSONB,  -- {support_volume: 8.0, data_quality: 7.2, ...}
    rules_applied       TEXT[],
    
    created_at          TIMESTAMP DEFAULT NOW()
);
```

---

## Module 17: training_run (Training metadata)

```sql
CREATE TABLE training_run (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    run_version         VARCHAR(20) NOT NULL,
    train_start         TIMESTAMP,
    train_end           TIMESTAMP,
    
    -- Data stats
    total_records       INTEGER,
    verified_records    INTEGER,
    self_collected_ratio FLOAT,
    
    -- Model metrics
    mae                 FLOAT,
    rmse                FLOAT,
    r2                  FLOAT,
    
    -- Model file
    model_path          VARCHAR(500),
    feature_cols_json   JSONB,
    
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_train_version ON training_run(run_version);
```

---

## Migration Map (Từ 9 bảng cũ)

| Bảng cũ | → Module mới | Ghi chú |
|---|---|---|
| `properties` | `property_asset` (core) + 4 context tables | Map property_type → asset_type theo taxonomy |
| `Property.area_m2` | `parcel_geometry.area_official_m2` (nếu LAND) hoặc `building_unit.built_area_m2` (nếu nhà) | |
| `Property.lat/lng` | `location_context` | Tách riêng |
| `Property.price` | `valuation_run.base_price_vnd` | |
| `Property.evidence_tier` | `evidence_asset.evidence_tier` | |
| `ModelVersion` | `training_run` | Map 1:1 |
| `AuditLog` | Ghi vào `valuation_adjustment.created_at` | Không cần bảng riêng |
| `DataSource` | `evidence_asset.domain` + `evidence_asset.source_type` | Map 1:1 |
| `BaselineModel` | BỎ | Không dùng nữa |
| `Prediction` | `valuation_run` | Map 1:1 |
| `PredictionHistory` | `valuation_run` + `valuation_adjustment` | Map 1:N |
| `ProvenanceChain` | `evidence_asset.raw_content_hash` + provenance JSON | |
| `CollectionSource` | `evidence_asset.source_type` | Map |

---

## Computed Columns (tự động tính)

```sql
-- Trong valuation_adjustment:
total_market_delta_vnd GENERATED ALWAYS AS (
    SELECT SUM(delta_vnd) FROM valuation_adjustment 
    WHERE valuation_run_id = id AND layer = 'MARKET'
) STORED

-- Trong property_asset:
latest_valuation_id GENERATED ALWAYS AS (
    SELECT id FROM valuation_run 
    WHERE property_asset_id = property_asset.id 
    ORDER BY run_at DESC LIMIT 1
) STORED

-- Trong evidence_asset:
quality_band GENERATED ALWAYS AS (
    CASE 
        WHEN rqs_score >= 8.5 THEN 'A'
        WHEN rqs_score >= 7.0 THEN 'B'
        WHEN rqs_score >= 5.5 THEN 'C'
        ELSE 'D'
    END
) STORED
```

---

## Indexes for Performance

```sql
-- Composite indexes for common queries
CREATE INDEX idx_valuation_asset_date ON valuation_run(property_asset_id, run_at DESC);
CREATE INDEX idx_evidence_tier_source ON evidence_asset(evidence_tier, source_type);
CREATE INDEX idx_adj_factor_layer ON valuation_adjustment(factor_code, layer);
CREATE INDEX idx_location_geo_box ON location_context(
    (latitude BETWEEN 20.5 AND 21.5),
    (longitude BETWEEN 104.5 AND 106.5)
);

-- Partial indexes for filtered queries
CREATE INDEX idx_property_active ON property_asset(id) WHERE status = 'active';
CREATE INDEX idx_valuation_high_conf ON valuation_run(id) WHERE confidence_grade IN ('A','B');
```

---

*Migration script: `migrations/001_init_schema_v2.sql`*
*Code generator: `src/domain/generators/schema_v2_generator.py`*