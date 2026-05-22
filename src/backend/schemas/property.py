"""
Property schemas — Pydantic models cho property CRUD.
"""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PropertyBase(BaseModel):
    """Base property model."""
    property_type: str = Field(..., description="Type: house, apartment, land, townhouse, villa")
    province_city: str
    district: str
    ward: Optional[str] = None
    street_or_project: Optional[str] = None
    area_m2: float = Field(..., gt=0, description="Area in square meters")
    bedrooms: Optional[int] = Field(default=0, ge=0)
    bathrooms: Optional[int] = Field(default=0, ge=0)
    floor_count: Optional[int] = Field(default=1, ge=0)
    frontage_m: Optional[float] = Field(None, ge=0)
    legal_status: Optional[str] = None
    furnishing: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_type: Optional[str] = None
    distance_to_market: Optional[float] = None
    distance_to_school: Optional[float] = None
    distance_to_hospital: Optional[float] = None
    distance_to_main_road: Optional[float] = None
    near_supermarket: Optional[bool] = None
    near_school: Optional[bool] = None
    near_hospital: Optional[bool] = None
    near_main_road: Optional[bool] = None


class PropertyCreate(PropertyBase):
    """Model for creating a property with IoT features."""
    price: Optional[float] = None
    listing_date: Optional[datetime] = None
    description: Optional[str] = None

    # IoT/Smartphone features
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_accuracy: Optional[float] = None
    capture_time: Optional[datetime] = None
    capture_date: Optional[date] = None
    noise_level: Optional[float] = None
    light_level: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    phone_device: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    field_notes: Optional[str] = None
    area_quality_score: Optional[float] = None

    # Self-collected data fields
    is_self_collected: bool = False
    collection_method: Optional[str] = None
    collected_by: Optional[str] = None
    verification_note: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    @field_validator('property_type')
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        valid_types = ['house', 'apartment', 'land', 'townhouse', 'villa']
        if v not in valid_types:
            raise ValueError(f'property_type must be one of: {valid_types}')
        return v


class PropertyResponse(PropertyBase):
    """Model for property response with IoT fields."""
    id: int
    price: float
    price_per_m2: Optional[float] = None
    listing_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # IoT fields
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_accuracy: Optional[float] = None
    capture_time: Optional[datetime] = None
    noise_level: Optional[float] = None
    light_level: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    phone_device: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    field_notes: Optional[str] = None
    area_quality_score: Optional[float] = None
    image_url: Optional[str] = None
    data_origin_type: Optional[str] = None
    record_status: Optional[str] = None
    verification_status: Optional[str] = None
    evidence_tier: Optional[str] = None

    # Self-collected fields
    collection_method: Optional[str] = None
    collected_by: Optional[str] = None
    collected_at: Optional[datetime] = None
    verification_note: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    model_config = {"from_attributes": True}
