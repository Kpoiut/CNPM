"""
FastAPI Router for Community Module (V-FINAL Architecture).
Full API: Claims, Comments, Challenges, Appeals, Court, Bonds, Reputation, Private Funnel.
Admin endpoints return full metadata (DTS, ring, coalition). User endpoints are black-box compliant.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query as QP
from sqlalchemy.orm import Session
from typing import Optional

from src.backend.database import get_db
from src.backend.auth.dependencies import get_current_user, require_admin, get_optional_user
from src.backend.auth.models import User
from . import models, schemas
from .services import (
    execute_fast_scan_pipeline, ReputationEngine, CommentRiskLayer,
    AbuseDetectionEngine, ClaimCourtService, AppealService,
    PredictionBondService, AITrainingFirewall, PrivateKnowledgeFunnel,
    TrustGraphEngine, auto_detect_claim_type,
)

router = APIRouter(prefix="/api/community", tags=["community"])


# ─── Helpers ─────────────────────────────────────────
def _user_view(claim, db) -> dict:
    """Black-box response — hides internal metadata."""
    author = db.query(User).filter(User.id == claim.author_id).first()
    ev = db.query(models.ClaimEvidence).filter(models.ClaimEvidence.claim_id == claim.id).count()
    cm = db.query(models.CommunityComment).filter(models.CommunityComment.claim_id == claim.id).count()
    ch = db.query(models.Challenge).filter(models.Challenge.target_claim_id == claim.id).count()
    return dict(
        id=claim.id, author_id=claim.author_id,
        author_name=author.username if author else f"User#{claim.author_id}",
        claim_type=claim.claim_type, content=claim.content, status=claim.status,
        created_at=claim.created_at,
        evidence_count=ev, comment_count=cm, challenge_count=ch,
    )


def _admin_view(claim, db) -> dict:
    """Full admin view — includes DTS, ring, coalition, trust."""
    base = _user_view(claim, db)
    base.update(
        dts_score=claim.dts_score,
        distribution_ring=claim.distribution_ring,
        topic_sensitivity_score=claim.topic_sensitivity_score,
        coalition_risk_score=claim.coalition_risk_score,
        trust_distance_scope=claim.trust_distance_scope,
        conflict_flags=claim.conflict_flags,
        author_rep_score=getattr(claim, 'author_rep_score', None),
    )
    return base


# ═══════════════════════════════════════════════════
# CLAIMS
# ═══════════════════════════════════════════════════

@router.post("/claims")
def create_claim(
    claim_in: schemas.ClaimCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User posts → Shadow Pending → AI Fast Scan async."""
    detected_type = claim_in.claim_type.value if claim_in.claim_type else auto_detect_claim_type(claim_in.content)
    new_claim = models.Claim(
        author_id=current_user.id,
        claim_type=detected_type,
        content=claim_in.content,
        status=models.ClaimStatus.SHADOW_PENDING.value,
        distribution_ring=0,
        conflict_flags=claim_in.conflict_flags or [],
    )
    if detected_type in [models.ClaimType.LEGAL_ZONING.value, models.ClaimType.FORECAST.value]:
        new_claim.topic_sensitivity_score = 0.8
    db.add(new_claim); db.commit(); db.refresh(new_claim)
    if claim_in.evidence:
        for ev in claim_in.evidence:
            db.add(models.ClaimEvidence(
                claim_id=new_claim.id, evidence_type=ev.evidence_type,
                evidence_url=ev.evidence_url, metadata_json=ev.metadata_json, source_mode=ev.source_mode,
            ))
        db.commit()
    background_tasks.add_task(execute_fast_scan_pipeline, new_claim.id, db)
    return _user_view(new_claim, db)


@router.get("/claims/{claim_id}")
def get_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_optional_user)):
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(404, "Claim không tồn tại")
    if current_user and current_user.role == "admin":
        return _admin_view(claim, db)
    return _user_view(claim, db)


# ═══════════════════════════════════════════════════
# FEED
# ═══════════════════════════════════════════════════

@router.get("/feed")
def get_community_feed(
    tab: str = "all",
    page: int = QP(1, ge=1),
    limit: int = QP(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Feed segmentation. tab=all shows unified user feed (non-quarantined)."""
    q = db.query(models.Claim)
    if tab == "all":
        q = q.filter(models.Claim.status.notin_([
            models.ClaimStatus.SHADOW_PENDING.value,
            models.ClaimStatus.ARCHIVED.value,
            models.ClaimStatus.TRAINING_EXCLUDED.value,
        ]))
    elif tab == "discussion":
        q = q.filter(models.Claim.claim_type == models.ClaimType.OPINION.value)
    elif tab == "market_signals":
        q = q.filter(models.Claim.status.in_([models.ClaimStatus.LIMITED_LIVE.value, models.ClaimStatus.EXPANDED_LIVE.value]))
    elif tab == "verified_insights":
        q = q.filter(models.Claim.status.in_([models.ClaimStatus.RESOLVED_TRUE.value, models.ClaimStatus.TRAINING_ELIGIBLE.value]))
    elif tab == "under_dispute":
        q = q.filter(models.Claim.status.in_([models.ClaimStatus.DISPUTED.value, models.ClaimStatus.UNDER_JURY_REVIEW.value]))
    else:
        q = q.filter(models.Claim.status.notin_([models.ClaimStatus.SHADOW_PENDING.value, models.ClaimStatus.ARCHIVED.value]))

    total = q.count()
    claims = q.order_by(models.Claim.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"claims": [_user_view(c, db) for c in claims], "total_count": total, "page": page}


# ═══════════════════════════════════════════════════
# COMMENTS
# ═══════════════════════════════════════════════════

@router.post("/claims/{claim_id}/comments")
def post_comment(claim_id: int, body: schemas.CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim: raise HTTPException(404)
    cmt = models.CommunityComment(claim_id=claim_id, author_id=user.id, content=body.content)
    CommentRiskLayer.evaluate(cmt, db)
    db.add(cmt); db.commit(); db.refresh(cmt)
    return {"id": cmt.id, "content": cmt.content, "author_name": user.username, "created_at": cmt.created_at,
            "is_claim_lite": cmt.is_claim_lite}


@router.get("/claims/{claim_id}/comments")
def list_comments(claim_id: int, db: Session = Depends(get_db)):
    cmts = db.query(models.CommunityComment).filter(models.CommunityComment.claim_id == claim_id)\
        .order_by(models.CommunityComment.created_at.asc()).all()
    out = []
    for c in cmts:
        a = db.query(User).filter(User.id == c.author_id).first()
        out.append({"id": c.id, "content": c.content, "author_name": a.username if a else "?",
                     "created_at": c.created_at, "is_claim_lite": c.is_claim_lite})
    return out


# ═══════════════════════════════════════════════════
# CHALLENGES
# ═══════════════════════════════════════════════════

@router.post("/claims/{claim_id}/challenges")
def post_challenge(claim_id: int, body: schemas.ChallengeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim: raise HTTPException(404)
    AbuseDetectionEngine.check_targeted_discredit(user.id, claim.author_id, db)
    ch = models.Challenge(target_claim_id=claim_id, challenger_id=user.id,
                          reason_type=body.reason_type, argument_content=body.argument_content, status="open")
    db.add(ch); db.commit(); db.refresh(ch)
    if db.query(models.Challenge).filter(models.Challenge.target_claim_id == claim_id).count() >= 3:
        claim.status = models.ClaimStatus.DISPUTED.value
        db.commit()
    return {"id": ch.id, "status": ch.status}


@router.get("/claims/{claim_id}/challenges")
def list_challenges(claim_id: int, db: Session = Depends(get_db)):
    chs = db.query(models.Challenge).filter(models.Challenge.target_claim_id == claim_id).all()
    out = []
    for c in chs:
        a = db.query(User).filter(User.id == c.challenger_id).first()
        out.append({"id": c.id, "reason_type": c.reason_type, "argument_content": c.argument_content,
                     "challenger_name": a.username if a else "?", "status": c.status, "created_at": c.created_at})
    return out


# ═══════════════════════════════════════════════════
# APPEALS
# ═══════════════════════════════════════════════════

@router.post("/claims/{claim_id}/appeals")
def submit_appeal(claim_id: int, body: schemas.AppealCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim: raise HTTPException(404)
    if claim.author_id != user.id: raise HTTPException(403, "Chỉ tác giả mới được kháng cáo")
    return AppealService.create(claim, user.id, body.reason, db)


@router.put("/appeals/{appeal_id}/accept")
def accept_appeal(appeal_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return AppealService.accept(appeal_id, admin.id, db)


@router.put("/appeals/{appeal_id}/reject")
def reject_appeal(appeal_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return AppealService.reject(appeal_id, admin.id, db)


# ═══════════════════════════════════════════════════
# COURT
# ═══════════════════════════════════════════════════

@router.post("/claims/{claim_id}/court")
def open_court(claim_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim: raise HTTPException(404)
    return ClaimCourtService.open_session(claim, db)


@router.post("/court/{session_id}/vote")
def cast_vote(session_id: int, body: schemas.CourtVote, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ClaimCourtService.cast_vote(session_id, user.id, body.verdict, db)


@router.post("/court/process-verdicts")
def process_verdicts(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return ClaimCourtService.process_all(db)


# ═══════════════════════════════════════════════════
# BONDS
# ═══════════════════════════════════════════════════

@router.post("/claims/{claim_id}/bonds")
def place_bond(claim_id: int, body: schemas.BondCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return PredictionBondService.place(claim_id, user.id, body.prediction_direction, body.stake_amount, db)


# ═══════════════════════════════════════════════════
# REPUTATION
# ═══════════════════════════════════════════════════

@router.get("/reputation/me")
def my_reputation(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rep = db.query(models.ReputationLedger).filter(models.ReputationLedger.user_id == user.id).first()
    if not rep:
        rep = ReputationEngine.initialize(user.id, db)
    tier = "expert" if rep.global_score >= 500 else ("trusted" if rep.global_score >= 200 else "standard")
    return {"global_score": rep.global_score, "verifier_score": rep.verifier_score,
            "forecaster_score": rep.forecaster_score, "data_score": rep.data_contribution_score,
            "local_score": rep.local_influence_score, "tier": tier, "sanctions": rep.active_sanctions}


# ═══════════════════════════════════════════════════
# PRIVATE KNOWLEDGE FUNNEL (Anonymous)
# ═══════════════════════════════════════════════════

@router.post("/private-insight")
def submit_private_insight(body: schemas.PrivateInsightCreate, db: Session = Depends(get_db)):
    return PrivateKnowledgeFunnel.submit(body.content, body.area_hint, db)


# ═══════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════

@router.post("/admin/run-coalition-scan")
def run_coalition_scan(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return TrustGraphEngine.run_full_scan(db)


@router.get("/admin/training-candidates")
def get_training_candidates(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return AITrainingFirewall.get_candidates(db)


@router.get("/admin/feed")
def admin_feed(
    tab: str = "all",
    page: int = QP(1, ge=1),
    limit: int = QP(20, ge=1, le=50),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin feed — returns full metadata (DTS, ring, coalition)."""
    q = db.query(models.Claim)
    if tab == "all":
        pass  # All posts, including shadow pending
    elif tab == "discussion":
        q = q.filter(models.Claim.claim_type == models.ClaimType.OPINION.value)
    elif tab == "market_signals":
        q = q.filter(models.Claim.status.in_([models.ClaimStatus.LIMITED_LIVE.value, models.ClaimStatus.EXPANDED_LIVE.value]))
    elif tab == "verified_insights":
        q = q.filter(models.Claim.status.in_([models.ClaimStatus.RESOLVED_TRUE.value, models.ClaimStatus.TRAINING_ELIGIBLE.value]))
    elif tab == "under_dispute":
        q = q.filter(models.Claim.status.in_([models.ClaimStatus.DISPUTED.value, models.ClaimStatus.UNDER_JURY_REVIEW.value]))

    total = q.count()
    claims = q.order_by(models.Claim.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"claims": [_admin_view(c, db) for c in claims], "total_count": total, "page": page}
