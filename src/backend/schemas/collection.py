"""
Collection schemas — Data collection & provenance endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CollectRequest(BaseModel):
    province_city: str
    district: str
    property_type: str
    count: int


class CollectStatusResponse(BaseModel):
    total: int
    processed: int
    saved: int
    failed: int
    errors: List[str]
    status: str


class ProvenanceNodeResponse(BaseModel):
    """Single node in provenance chain."""
    node_id: str
    step_type: str
    actor: str
    timestamp: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    metadata: Dict[str, Any]


class ProvenanceChainResponse(BaseModel):
    """Full provenance chain for a property."""
    chain_id: str
    property_id: Optional[int] = None
    nodes: List[ProvenanceNodeResponse]
    total_steps: int
    chain_hash: str
