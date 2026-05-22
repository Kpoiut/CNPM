"""Fit/Suitability domain modules."""
from src.domain.fit.feng_shui import FengShuiEngine, FengShuiInput, FengShuiResult
from src.domain.fit.suitability import SuitabilityEngine, PersonaProfile, FitScore

__all__ = [
    "FengShuiEngine",
    "FengShuiInput",
    "FengShuiResult",
    "SuitabilityEngine",
    "PersonaProfile",
    "FitScore",
]
