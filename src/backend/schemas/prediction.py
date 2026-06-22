"""
Prediction schemas — Pydantic models cho prediction endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class PredictionRequest(BaseModel):
    """Model for prediction request with IoT options."""
    property_type: str
    province_city: str
    district: str
    ward: Optional[str] = None
    area_m2: float = Field(..., gt=0)
    bedrooms: int = Field(default=0, ge=0)
    bathrooms: int = Field(default=0, ge=0)
    floor_count: Optional[int] = 1
    frontage_m: Optional[float] = None
    legal_status: Optional[str] = None
    furnishing: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_type: Optional[str] = None
    # IoT features (optional for prediction)
    noise_level: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_level: Optional[float] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None

    @field_validator('property_type')
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        if v not in ['house', 'apartment', 'land', 'townhouse', 'villa']:
            raise ValueError('property_type must be house, apartment, land, townhouse, or villa')
        return v


class PredictionResponse(BaseModel):
    """Model for prediction response with full explainability."""
    model_config = ConfigDict(protected_namespaces=())

    predicted_price: float
    price_per_m2: float
    confidence_low: Optional[float] = None
    confidence_high: Optional[float] = None
    model_used: str
    confidence: Optional[float] = None
    input_features: Dict[str, Any]
    prediction_id: Optional[int] = None
    request_id: Optional[str] = None

    # Training provenance
    model_version: Optional[str] = None
    trained_at: Optional[str] = None
    train_start_date: Optional[str] = None
    train_end_date: Optional[str] = None
    total_train_records: Optional[int] = None
    verified_train_records: Optional[int] = None
    self_collected_ratio: Optional[float] = None

    # Data used
    same_property_type_count: Optional[int] = None
    same_province_count: Optional[int] = None
    same_district_count: Optional[int] = None

    # Feature importance
    feature_importance: Optional[Dict[str, float]] = None

    # Comparable records
    comparable_records: Optional[List[Dict[str, Any]]] = None

    # Images and visualization
    property_images: Optional[List[Dict[str, Any]]] = None

    # Source attribution and provenance
    source_attribution: Optional[str] = None
    data_provenance: Optional[Dict[str, Any]] = None

    # Prediction citation
    citation: Optional[Dict[str, Any]] = None

    # Algorithm info
    algorithm: Optional[str] = None
    preprocessing: Optional[Dict[str, Any]] = None
    features_used: Optional[List[str]] = None
    data_quality_assessment: Optional[Dict[str, Any]] = None
    interval_analysis: Optional[Dict[str, Any]] = None


class DataQualityResponse(BaseModel):
    """Standalone response for evaluating input data reliability."""
    model_config = ConfigDict(protected_namespaces=())

    matched_province: str
    request_summary: Dict[str, Any]
    assessment: Dict[str, Any]
