"""
Research & Dataset schemas.
"""

from typing import Any, Dict, List

from pydantic import BaseModel


class ResearchLabAccessRequest(BaseModel):
    access_code: str


class ResearchLabAccessResponse(BaseModel):
    granted: bool
    token: str | None = None
    expires_at: str | None = None
    session_minutes: int | None = None
    message: str


class ResearchLabCodeResponse(BaseModel):
    code: str
    expires_at: str
    ttl_seconds: int
    message: str


class ResearchLabOverviewResponse(BaseModel):
    model_status: Dict[str, Any] | None = None
    standard_name: str
    training_flow_tree: Dict[str, Any]
    confidence_stage: Dict[str, Any]
    price_stage: Dict[str, Any]
    quality_summary: Dict[str, Any]
    calibration: Dict[str, Any]
    notes: List[str]


class DatasetStats(BaseModel):
    """Model for dataset statistics — Research Standard."""
    total: int
    self_collected: int
    self_collected_ratio: float
    verified_records: int
    iot_records: int
    iot_ratio: float
    by_property_type: Dict[str, int]
    by_province: Dict[str, int]
    meets_requirement: bool


class BaselineComparison(BaseModel):
    """Model for baseline comparison."""
    baseline_name: str
    baseline_metrics: Dict[str, Any]
    improved_metrics: Dict[str, Any]
    improvement: Dict[str, Any]
