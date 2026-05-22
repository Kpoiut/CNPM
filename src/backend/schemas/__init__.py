"""
Backend schemas — Pydantic request/response models.
Dùng centralized schemas thay vì định nghĩa inline trong main.py.
"""

from .property import PropertyBase, PropertyCreate, PropertyResponse
from .prediction import PredictionRequest, PredictionResponse, DataQualityResponse
from .research import (
    ResearchLabAccessRequest,
    ResearchLabAccessResponse,
    ResearchLabCodeResponse,
    ResearchLabOverviewResponse,
    DatasetStats,
    BaselineComparison,
)
from .collection import CollectRequest, CollectStatusResponse, ProvenanceNodeResponse, ProvenanceChainResponse

__all__ = [
    # Property
    "PropertyBase",
    "PropertyCreate",
    "PropertyResponse",
    # Prediction
    "PredictionRequest",
    "PredictionResponse",
    "DataQualityResponse",
    # Research
    "ResearchLabAccessRequest",
    "ResearchLabAccessResponse",
    "ResearchLabCodeResponse",
    "ResearchLabOverviewResponse",
    "DatasetStats",
    "BaselineComparison",
    # Collection
    "CollectRequest",
    "CollectStatusResponse",
    "ProvenanceNodeResponse",
    "ProvenanceChainResponse",
]
