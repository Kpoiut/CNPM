"""
Pydantic Schemas for Community Module (V-FINAL).
Covers: Claims, Comments, Challenges, Appeals, Court, Bonds, Reputation, Private Funnel.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import ClaimType


# ─── Evidence ───
class ClaimEvidenceCreate(BaseModel):
    evidence_type: str
    evidence_url: str
    metadata_json: Optional[Dict[str, Any]] = {}
    source_mode: Optional[str] = "public"


# ─── Claims ───
class ClaimCreate(BaseModel):
    claim_type: Optional[ClaimType] = None  # AI auto-detects if not provided
    content: str
    evidence: Optional[List[ClaimEvidenceCreate]] = []
    conflict_flags: Optional[List[str]] = []


class ClaimResponse(BaseModel):
    id: int
    author_id: int
    claim_type: str
    content: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Comments ───
class CommentCreate(BaseModel):
    content: str


# ─── Challenges ───
class ChallengeCreate(BaseModel):
    reason_type: str  # wrong_fact, fake_evidence, market_manipulation, misleading
    argument_content: str


# ─── Appeals ───
class AppealCreate(BaseModel):
    reason: str


# ─── Court ───
class CourtVote(BaseModel):
    verdict: str  # true, false, misleading, inconclusive


# ─── Bonds ───
class BondCreate(BaseModel):
    prediction_direction: str  # up, down
    stake_amount: float


# ─── Private Insight ───
class PrivateInsightCreate(BaseModel):
    content: str
    area_hint: Optional[str] = None


# ─── Feed Response ───
class DashboardFeedResponse(BaseModel):
    claims: list
    total_count: Optional[int] = 0
    page: Optional[int] = 1
