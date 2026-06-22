"""
Community & Knowledge Ledger Models (V-FINAL Architecture)
This module implements the Domain Data Schema defined in the Trust-Driven AVM Blueprint.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from src.backend.database import Base


class ClaimType(str, enum.Enum):
    OPINION = "opinion"
    FIELD_OBSERVATION = "field_observation"
    DATA_FACT = "data_fact"
    LEGAL_ZONING = "legal_zoning"
    FORECAST = "forecast"
    RECOMMENDATION = "recommendation"


class ClaimStatus(str, enum.Enum):
    DRAFTED = "drafted"
    SHADOW_PENDING = "shadow_pending"
    LIMITED_LIVE = "limited_live"
    EXPANDED_LIVE = "expanded_live"
    DISPUTED = "disputed"
    UNDER_JURY_REVIEW = "under_jury_review"
    RESOLVED_TRUE = "resolved_true"
    RESOLVED_MISLEADING = "resolved_misleading"
    RESOLVED_FALSE = "resolved_false"
    ARCHIVED = "archived"
    TRAINING_ELIGIBLE = "training_eligible"
    TRAINING_EXCLUDED = "training_excluded"


class LinkSafetyStatus(str, enum.Enum):
    PENDING = "pending"
    GREEN_SAFE = "green_safe"
    RED_DANGER = "red_danger"


class VerdictType(str, enum.Enum):
    TRUE = "true"
    MISLEADING = "misleading"
    FALSE = "false"
    INCONCLUSIVE = "inconclusive"


class ReputationLedger(Base):
    __tablename__ = "reputation_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_accounts.id"), unique=True, index=True, nullable=False)
    
    global_score = Column(Float, default=100.0)
    area_scores = Column(JSON, default=dict)       # e.g., {"District_9": 150.0, "Thu_Duc": 80.0}
    content_scores = Column(JSON, default=dict)    # e.g., {"legal": 120.0, "field": 200.0}
    
    verifier_score = Column(Float, default=50.0)   # Power to challenge/verify
    forecaster_score = Column(Float, default=50.0) # Power to make predictions
    data_contribution_score = Column(Float, default=0.0)
    local_influence_score = Column(Float, default=0.0)
    active_sanctions = Column(Integer, default=0)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("auth_accounts.id"), index=True, nullable=False)
    
    # Core Definition
    claim_type = Column(String(50), nullable=False) # e.g. opinion, forecast...
    content = Column(Text, nullable=False)
    
    # State Machine & Routing
    status = Column(String(50), default=ClaimStatus.DRAFTED.value, index=True)
    distribution_ring = Column(Integer, default=0)  # 0: Shadow, 1: Local, 2: Relevant, 3: Distant, 4: Global
    dts_score = Column(Float, default=0.0)          # Distribution Trust Score
    
    # Deep Field Design
    topic_sensitivity_score = Column(Float, default=0.0)
    coalition_risk_score = Column(Float, default=0.0)
    trust_distance_scope = Column(Float, default=1.0)
    conflict_flags = Column(JSON, default=list)     # Any COI flags
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    
    evidence_type = Column(String(50)) # "image", "link", "document"
    evidence_url = Column(Text, nullable=False)
    
    # Proof validation
    evidence_quality_score = Column(Float, default=0.0)
    metadata_json = Column(JSON, default=dict)      # GPS, EXIF
    link_safety_status = Column(String(50), default=LinkSafetyStatus.PENDING.value)
    
    source_mode = Column(String(50), default="public") # "public" or "anonymous"
    created_at = Column(DateTime, default=func.now())


class CommunityComment(Base):
    __tablename__ = "community_comments"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    author_id = Column(Integer, ForeignKey("auth_accounts.id"))
    content = Column(Text, nullable=False)
    
    # Comment Risk Layer
    is_claim_lite = Column(Boolean, default=False)
    promoted_to_claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True) # If it escalates to full claim
    
    created_at = Column(DateTime, default=func.now())


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    target_claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    challenger_id = Column(Integer, ForeignKey("auth_accounts.id"))
    
    reason_type = Column(String(100)) # "fake_evidence", "market_manipulation", "wrong_fact"
    argument_content = Column(Text)
    evidence_id = Column(Integer, ForeignKey("claim_evidence.id"), nullable=True)
    
    status = Column(String(50), default="pending") # "pending", "accepted", "rejected"
    created_at = Column(DateTime, default=func.now())


class ClaimCourtSession(Base):
    __tablename__ = "claim_court_sessions"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    
    session_level = Column(String(50)) # "community_jury", "domain_reviewer", "admin_override"
    jury_member_ids = Column(JSON, default=list)
    voting_result_json = Column(JSON, default=dict)
    
    final_verdict = Column(String(50)) # VerdictType
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())


class PredictionBond(Base):
    __tablename__ = "prediction_bonds"

    id = Column(Integer, primary_key=True, index=True)
    forecaster_id = Column(Integer, ForeignKey("auth_accounts.id"))
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"))
    
    staked_points = Column(Float, nullable=False)
    validation_date = Column(DateTime, nullable=False)
    
    outcome = Column(String(50), default="pending") # "won", "lost", "pending"
    created_at = Column(DateTime, default=func.now())


class CoalitionFlag(Base):
    __tablename__ = "coalition_flags"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(String(100), index=True)
    involved_user_ids = Column(JSON, default=list)
    
    risk_level = Column(String(50)) # "low", "medium", "high"
    action_taken = Column(String(100))
    detected_at = Column(DateTime, default=func.now())


class AiTrainingCandidate(Base):
    __tablename__ = "ai_training_candidates"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    
    validation_source = Column(String(50)) # "admin", "jury", "expert_direct"
    eligibility_status = Column(Boolean, default=False)
    training_status_reason = Column(Text)  # e.g., "Exclude: new evidence emerged", "Include: Verified by Jury"
    
    evaluated_at = Column(DateTime, default=func.now())


class AppealCase(Base):
    __tablename__ = "appeal_cases"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("auth_accounts.id"))
    
    appeal_reason = Column(Text, nullable=False)
    status = Column(String(50), default="open") # "open", "accepted_rollback", "rejected"
    admin_notes = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)


class PrivateInsight(Base):
    """Anonymous Knowledge Funnel — Isolated schema for anonymous market signals (§7)."""
    __tablename__ = "private_insights"

    id = Column(Integer, primary_key=True, index=True)
    content_encrypted = Column(Text, nullable=False)  # Column-level encryption
    area_hint = Column(String(200), nullable=True)
    
    signal_type = Column(String(50), default="market_tip")  # "market_tip", "fraud_report", "price_anomaly"
    processing_status = Column(String(50), default="pending")  # "pending", "processed", "aggregated", "discarded"
    aggregate_signal_id = Column(String(100), nullable=True)  # Links to public aggregate signal
    
    created_at = Column(DateTime, default=func.now())
