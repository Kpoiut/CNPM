"""SQLAlchemy models for Real Estate AVM - Research Standard Version."""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from src.backend.database import Base
import enum


class DataOriginType(str, enum.Enum):
    PUBLIC_COLLECTED = "public_collected"  # Lấy từ nguồn công khai
    SELF_COLLECTED = "self_collected"       # Tự thu thập
    SYSTEM_DEMO = "system_demo"             # Chỉ để demo UI


class RecordStatus(str, enum.Enum):
    RAW = "raw"                    # Dữ liệu thô
    PENDING_REVIEW = "pending_review"  # Chờ xác minh
    VERIFIED = "verified"          # Đã xác minh
    REJECTED = "rejected"          # Bị từ chối
    ARCHIVED = "archived"          # Lưu trữ


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class CollectionMethodType(str, enum.Enum):
    GOOGLE_FORM_VERIFIED = "google_form_verified"
    MANUAL_VERIFIED_FROM_PUBLIC = "manual_verified_from_public_listing"
    FIELD_SURVEY = "field_survey"
    APP_USER_SUBMISSION = "app_user_submission"
    SMARTPHONE_SENSOR_CAPTURE = "smartphone_sensor_capture"


class AreaTypeEnum(str, enum.Enum):
    URBAN_CENTER = "urban_center"
    SUBURBAN = "suburban"
    URBAN_FRINGE = "urban_fringe"
    RURAL = "rural"


class DataCollectionStatus(str, enum.Enum):
    """Trạng thái thu thập dữ liệu — dùng cho provenance tracking."""
    PENDING = "pending"              # Chờ thu thập
    COLLECTING = "collecting"       # Đang thu thập
    COLLECTED = "collected"         # Đã thu thập thành công
    FAILED = "failed"               # Thu thập thất bại
    UNDER_REVIEW = "under_review"   # Đang được review
    DEDUPED = "deduped"             # Bị loại bỏ do trùng lặp
    VALIDATED = "validated"          # Đã validate


class Property(Base):
    """Property model - Research Standard with full traceability."""
    __tablename__ = "properties"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # =====================
    # DATA ORIGIN & STATUS (Quy tắc 1, 5)
    # =====================
    data_origin_type = Column(String(50), nullable=False, default=DataOriginType.PUBLIC_COLLECTED.value)
    record_status = Column(String(50), nullable=False, default=RecordStatus.RAW.value)
    verification_status = Column(String(50), default=VerificationStatus.UNVERIFIED.value)

    # =====================
    # BASIC PROPERTY INFO
    # =====================
    property_type = Column(String(50), nullable=False, index=True)
    province_city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    ward = Column(String(100), index=True)
    street_or_project = Column(String(255))

    # Area and rooms
    area_m2 = Column(Float, nullable=False)
    bedrooms = Column(Integer, default=0)
    bathrooms = Column(Integer, default=0)
    floor_count = Column(Integer, default=1)
    frontage_m = Column(Float)

    # Legal and furnishing
    legal_status = Column(String(50))
    furnishing = Column(String(50))

    # Price
    price = Column(Float, nullable=False)
    price_per_m2 = Column(Float)
    listing_date = Column(DateTime)
    is_transacted = Column(Boolean, default=False)  # True = giao dịch thực tế, False = giá rao bán

    # Location
    latitude = Column(Float)
    longitude = Column(Float)

    # Area type
    area_type = Column(String(50))

    # Nearby amenities
    distance_to_market = Column(Float)
    distance_to_school = Column(Float)
    distance_to_hospital = Column(Float)
    distance_to_main_road = Column(Float)
    near_supermarket = Column(Boolean)
    near_school = Column(Boolean)
    near_hospital = Column(Boolean)
    near_main_road = Column(Boolean)

    # =====================
    # SOURCE TRACKING (Quy tắc 2 - Bắt buộc có nguồn)
    # =====================
    source_name = Column(String(200), nullable=False)  # Tên nguồn
    source_url = Column(String(500))  # Link gốc
    source_page_title = Column(String(255))  # Tiêu đề trang nguồn
    source_collected_at = Column(DateTime)  # Thời điểm lấy từ nguồn
    source_access_method = Column(String(50))  # Cách truy cập (manual, api, scrape)
    source_screenshot_path = Column(String(255))  # Đường dẫn ảnh chụp màn hình

    # =====================
    # PROVENANCE FIELDS (Nguồn gốc bắt buộc - Phase 2)
    # =====================
    source_domain = Column(String(200))  # Domain gốc (e.g., "alonhadat.com.vn")
    source_category = Column(String(50))  # Loại: scraper, api, manual_entry, field_survey
    source_crawl_at = Column(DateTime)  # Thời điểm crawl
    source_etag = Column(String(64))  # ETag header để check độ trùng lặp
    source_last_modified = Column(String(100))  # Last-Modified header
    raw_source_content = Column(Text)  # JSON lưu raw response từ nguồn
    data_collection_status = Column(String(50), default=DataCollectionStatus.PENDING.value)
    collection_attempt_count = Column(Integer, default=0)  # Số lần thử thu thập
    last_collection_attempt = Column(DateTime)  # Lần thử cuối

    # Verification
    verification_status = Column(String(50), default="unverified")
    verification_note = Column(Text)
    verified_by = Column(String(100))
    verified_at = Column(DateTime)

    # =====================
    # SELF-COLLECTED FIELDS (Quy tắc 3, 4)
    # =====================
    collected_by = Column(String(100))  # Ai thu thập
    collected_at = Column(DateTime)  # Thu lúc nào
    collection_method = Column(String(50))  # Thu bằng cách nào
    collector_contact = Column(String(100))  # Liên hệ người thu thập
    field_note = Column(Text)  # Ghi chú thực địa

    # Evidence
    form_submission_id = Column(String(100))  # ID form submission
    evidence_photo_path = Column(String(255))  # Đường dẫn ảnh minh chứng

    # =====================
    # IoT/SMARTPHONE DATA
    # =====================
    gps_lat = Column(Float)
    gps_lng = Column(Float)
    noise_level = Column(Float)
    capture_time = Column(DateTime)
    phone_device = Column(String(100))
    gps_accuracy = Column(Float)
    sensor_source = Column(String(50))
    iot_note = Column(Text)

    # Additional IoT
    light_level = Column(Float)
    temperature = Column(Float)
    humidity = Column(Float)
    os_version = Column(String(50))
    app_version = Column(String(20))
    area_quality_score = Column(Float)
    field_notes = Column(Text)
    field_photos = Column(Text)

    # Image URLs (stored as JSON array)
    image_url = Column(String(500))  # Primary image URL
    image_urls = Column(Text)  # Multiple images as JSON array

    # IoT Device Info
    iot_device_id = Column(String(100))  # Device that collected IoT
    iot_collected_at = Column(DateTime)  # When IoT was collected

    # Verification enhanced
    verification_notes = Column(Text)

    # =====================
    # EVIDENCE TIER (E1-E5) — Stored in DB for ML training + transparency
    # =====================
    evidence_tier = Column(String(2), nullable=True, index=True)  # E1, E2, E3, E4, E5
    evidence_tier_updated_at = Column(DateTime, nullable=True)      # When tier was last computed

    # =====================
    # PRODUCTION METADATA (Round 17)
    # =====================
    collection_timestamp = Column(DateTime, nullable=True)  # When record was added to DB
    data_source_region = Column(String(50), nullable=True)  # 'hanoi' | 'hcmc'
    source_region = Column(String(50), nullable=True)         # Province-level label

    # =====================
    # TIMESTAMPS
    # =====================
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_updated_at = Column(DateTime)

    # Archive metadata
    archive_reason = Column(Text, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    # Description
    description = Column(Text)

    # =====================
    # SUPPLY-DEMAND MODEL COLUMNS
    # =====================
    # Demand signals (scraped from listing platforms)
    days_on_market = Column(Integer)  # Số ngày tồn tại trên sàn
    price_revision_count = Column(Integer, default=0)  # Số lần giảm giá
    initial_price = Column(Float)  # Giá ban đầu trước khi giảm
    views_count = Column(Integer, default=0)  # Lượt xem tin rao
    saves_count = Column(Integer, default=0)  # Lượt lưu tin
    contacts_count = Column(Integer, default=0)  # Lượt liên hệ chủ
    number_similar_listings = Column(Integer, default=0)  # Số tin tương tự

    # Computed scores (from supply-demand model)
    over_asking_score = Column(Float)  # listing_price - median_buyer_budget
    stale_listing_score = Column(Float)  # Hàm tăng theo days_on_market
    demand_coverage_ratio = Column(Float)  # buyers_can_afford / similar_listings
    market_acceptance_score = Column(Float)  # overlap_score + demand_weight - stale_penalty

    def __repr__(self):
        return f"<Property(id={self.id}, {self.property_type} in {self.district}, status={self.record_status})>"


class ModelVersion(Base):
    """Model version tracking (Quy tắc 8)"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String(50), nullable=False)
    model_name = Column(String(100))

    # Training window
    train_start_date = Column(DateTime)
    train_end_date = Column(DateTime)
    trained_at = Column(DateTime, server_default=func.now())

    # Training data stats
    train_record_count = Column(Integer)
    verified_record_count = Column(Integer)
    self_collected_ratio = Column(Float)

    # Metrics
    mae = Column(Float)
    rmse = Column(Float)
    r2 = Column(Float)

    # Model file
    model_path = Column(String(255))

    # Notes
    notes = Column(Text)

    def __repr__(self):
        return f"<ModelVersion(id={self.id}, version={self.model_version}, r2={self.r2})>"


class AuditLog(Base):
    """Audit log for all data changes (Quy tắc 10, 18)"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, index=True)
    table_name = Column(String(50))

    action_type = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, VERIFY, REJECT
    changed_by = Column(String(100))
    changed_at = Column(DateTime, server_default=func.now())

    old_value_json = Column(Text)
    new_value_json = Column(Text)
    change_note = Column(Text)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action_type}, at={self.changed_at})>"


class DataSource(Base):
    """Data source tracking (Quy tắc 6, 7)"""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(200), nullable=False)
    source_url = Column(String(500))
    source_type = Column(String(50))  # website, api, manual, field_survey

    # Stats
    total_records = Column(Integer, default=0)
    verified_records = Column(Integer, default=0)
    self_collected_records = Column(Integer, default=0)

    # Last collection
    last_collected_at = Column(DateTime)
    collection_frequency = Column(String(50))  # daily, weekly, monthly, one_time

    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DataSource(id={self.id}, name={self.source_name})>"


class BaselineModel(Base):
    """Baseline model tracking - legacy"""
    __tablename__ = "baseline_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    repo_url = Column(String(500))
    license = Column(String(50))
    metrics = Column(Text)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Prediction(Base):
    """Prediction history model - legacy compatibility"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, index=True)
    input_features = Column(Text)
    predicted_price = Column(Float, nullable=False)
    confidence = Column(Float)
    model_used = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


class PredictionHistory(Base):
    """Prediction history with full traceability"""
    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), index=True)

    # Input features
    input_features_json = Column(Text)

    # Prediction result
    predicted_price = Column(Float, nullable=False)
    confidence_low = Column(Float)
    confidence_high = Column(Float)

    # Model info
    model_version = Column(String(50))
    model_name = Column(String(100))

    # Feature importance
    feature_importance_json = Column(Text)

    # Similar records used
    similar_records_json = Column(Text)

    # Explanation
    explanation_text = Column(Text)

    # Timestamp
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<PredictionHistory(id={self.id}, price={self.predicted_price})>"


class ValuationRun(Base):
    """Valuation run history — every /api/v2/valuation call is persisted."""
    __tablename__ = "valuation_runs"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), index=True, nullable=True)
    engine_version = Column(String(20))
    run_at = Column(DateTime, server_default=func.now())
    base_price_vnd = Column(Float)
    base_price_source = Column(String(50))
    fair_market_value_vnd = Column(Float, nullable=False)
    quick_sale_value_vnd = Column(Float)
    recommended_listing_vnd = Column(Float)
    optimistic_ask_vnd = Column(Float)
    expected_range_low_vnd = Column(Float)
    expected_range_high_vnd = Column(Float)
    liquidity_score = Column(String(20))
    liquidity_band = Column(Float)
    overall_confidence = Column(Float)
    confidence_grade = Column(String(5))
    evidence_tier = Column(String(5))
    comparable_count = Column(Integer)
    effective_sample_size = Column(Float)
    anchor_share = Column(Float)
    independent_source_count = Column(Integer)
    input_hash = Column(String(64))
    legacy_prediction_id = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ValuationRun(id={self.id}, fmv={self.fair_market_value_vnd})>"


class ProvenanceChain(Base):
    """
    Provenance chain cho mỗi bản ghi.
    Mỗi bước thu thập/xử lý được log với hash để detect tampering.
    """
    __tablename__ = "provenance_chains"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), index=True, nullable=False)

    # Step info
    step = Column(String(50), nullable=False)  # crawled, parsed, validated, enriched, verified
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # Actor
    actor = Column(String(100), nullable=False)  # "system:DataCollector", "user:admin", "user:reviewer"

    # Hash chain
    input_hash = Column(String(64))  # SHA256 của input tại bước này
    output_hash = Column(String(64))  # SHA256 của output sau bước này

    # Source
    source = Column(String(200))  # Nguồn tại bước này

    # Verification
    verify_url = Column(String(500))  # URL để verify online (nếu có)
    metadata_json = Column(Text)  # Chi tiết bước (JSON)

    # Previous step link
    prev_step_id = Column(Integer, ForeignKey("provenance_chains.id"), nullable=True)

    def __repr__(self):
        return f"<ProvenanceChain(id={self.id}, property_id={self.property_id}, step={self.step})>"


class CollectionSource(Base):
    """
    Quản lý nguồn thu thập dữ liệu.
    Thay thế BaselineModel — mỗi nguồn được phê duyệt là 1 record.
    """
    __tablename__ = "collection_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_key = Column(String(200), unique=True, nullable=False)  # e.g., "alonhadat.com.vn"
    source_name = Column(String(200), nullable=False)
    source_type = Column(String(50))  # scraper, api, manual_entry, field_survey
    base_url = Column(String(500))

    # Rate limiting
    rate_limit_seconds = Column(Integer, default=2)
    requires_proxy = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)

    # Stats
    total_records = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    last_run_at = Column(DateTime)
    last_run_status = Column(String(50))  # success, failed, partial

    # Notes
    notes = Column(Text)
    approved_by = Column(String(100))
    approved_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CollectionSource(id={self.id}, key={self.source_key}, approved={self.is_approved})>"


class BuyerRequirement(Base):
    """
    Yêu cầu tìm mua BĐS từ phía cầu.
    Thu thập từ: tin đăng "cần mua", khảo sát, dữ liệu tìm kiếm, nhóm Facebook.
    """
    __tablename__ = "buyer_requirements"

    id = Column(Integer, primary_key=True, index=True)

    # Property requirements
    property_type = Column(String(50))
    province_city = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    ward = Column(String(100))
    project_preference = Column(String(255))

    # Area and budget
    min_area = Column(Float)
    max_area = Column(Float)
    min_budget = Column(Float, nullable=False)  # VND
    max_budget = Column(Float, nullable=False)  # VND

    # Features
    bedrooms = Column(Integer)
    legal_requirement = Column(String(50))  # ownership_certificate, land_use_right, any

    # Urgency
    urgency = Column(String(50), default="normal")  # urgent, normal, flexible

    # Source
    source_type = Column(String(50))  # survey, facebook_group, search_data, tin_can_mua
    source_url = Column(String(500))
    source_description = Column(Text)

    # Metadata
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_date = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<BuyerRequirement(id={self.id}, {self.property_type} in {self.district}, budget={self.min_budget/1e9:.1f}-{self.max_budget/1e9:.1f}B)>"


class MatchedPair(Base):
    """
    Kết quả matching giữa listing (cung) và buyer requirement (cầu).
    Dùng để tính Market Acceptable Price.
    """
    __tablename__ = "matched_pairs"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("properties.id"), index=True)
    request_id = Column(Integer, ForeignKey("buyer_requirements.id"), index=True)

    # Match scores
    location_match_score = Column(Float, default=0)  # 0-1: same district/ward/project
    area_match_score = Column(Float, default=0)  # 0-1: area falls within buyer's range
    budget_gap = Column(Float, default=0)  # listing_price - max_budget (negative = affordable)
    feature_match_score = Column(Float, default=0)  # 0-1: bedrooms, legal, etc.

    # Aggregate
    is_potential_match = Column(Boolean, default=False)  # Combined threshold
    overlap_score = Column(Float, default=0)  # Combined score 0-1

    # Grouping
    match_group = Column(String(100))  # group key for aggregation

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<MatchedPair(listing={self.listing_id}, request={self.request_id}, overlap={self.overlap_score:.2f})>"


class ExpertRating(Base):
    """
    Expert rating records cho ground truth evaluation.
    3 experts × N properties → median of medians = expert ground truth.
    """
    __tablename__ = "expert_ratings"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), index=True, nullable=False)
    expert_id = Column(String(50), nullable=False, index=True)
    expert_name = Column(String(100), nullable=False)

    # Individual expert judgment
    expert_low = Column(Float, nullable=False)   # Giá thấp nhất hợp lý (VND)
    expert_mid = Column(Float, nullable=False)   # Giá trung bình hợp lý (VND)
    expert_high = Column(Float, nullable=False)  # Giá cao nhất hợp lý (VND)
    confidence = Column(String(20))             # low | medium | high
    comment = Column(Text)

    # Metadata
    rated_at = Column(DateTime, server_default=func.now())
    source = Column(String(50))                  # expert_form | csv_import | api
    batch_id = Column(String(50))                # để group các đợt đánh giá

    def __repr__(self):
        return f"<ExpertRating(prop={self.property_id}, expert={self.expert_id}, mid={self.expert_mid/1e9:.2f}B)>"


class ExpertProperty(Base):
    """
    Properties selected for expert evaluation.
    Mỗi property cần được đánh giá bởi 3 experts.
    """
    __tablename__ = "expert_properties"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), index=True, nullable=False, unique=True)
    district = Column(String(100), nullable=False)
    area_m2 = Column(Float, nullable=False)
    bedrooms = Column(Integer)

    # Status tracking
    status = Column(String(20), default="pending")   # pending | in_progress | completed | skipped
    assigned_experts = Column(String(200))           # JSON: ["expert_1","expert_2","expert_3"]
    completed_count = Column(Integer, default=0)
    ratings_collected = Column(Integer, default=0)

    # Aggregated result (after all 3 experts rated)
    aggregated_low = Column(Float)
    aggregated_mid = Column(Float)
    aggregated_high = Column(Float)
    aggregated_confidence = Column(String(20))

    # Selection metadata
    cluster_key = Column(String(100))               # district::NBR để đảm bảo coverage
    selected_at = Column(DateTime, server_default=func.now())
    selected_by = Column(String(100))                # auto | manual

    def __repr__(self):
        return f"<ExpertProperty(prop={self.property_id}, status={self.status}, completed={self.completed_count}/3)>"
