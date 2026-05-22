"""
Community Services: The Brain behind the Trust-Driven Distribution Architecture.
Implements: Fast Scan (NLP & Safe Link), DTS Routing, Trust Graph (Coalition), Claim Court, and Reputation Ledger.
"""

import re
import hashlib
import networkx as nx
import tldextract
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
import json

# Underthesea for Vietnamese NLP
try:
    from underthesea import word_tokenize
except ImportError:
    def word_tokenize(text): return text.split()

from .models import (
    Claim, ClaimEvidence, ReputationLedger, CoalitionFlag,
    ClaimStatus, ClaimType, LinkSafetyStatus, Challenge,
    ClaimCourtSession, VerdictType, PredictionBond,
    CommunityComment, AiTrainingCandidate, AppealCase, PrivateInsight,
)

# --- 1. SAFE LINK SCANNER ---
class SafeLinkScanner:
    GREEN_DOMAINS = ["chinhphu.vn", "batdongsan.com.vn", "vtv.vn", "tuoitre.vn", "thanhnien.vn", "vnexpress.net"]
    RED_DOMAINS = ["nhadat-hot.site", "scam-bds.com", "link-an.xyz", "virus-link.info"]

    @classmethod
    def extract_urls(cls, text: str) -> List[str]:
        return re.findall(r'(https?://[^\s]+)', text)

    @classmethod
    def scan_url(cls, url: str) -> str:
        extracted = tldextract.extract(url)
        domain = f"{extracted.domain}.{extracted.suffix}"
        
        if domain in cls.RED_DOMAINS:
            return LinkSafetyStatus.RED_DANGER.value
        elif domain in cls.GREEN_DOMAINS:
            return LinkSafetyStatus.GREEN_SAFE.value
        return LinkSafetyStatus.PENDING.value


# --- 2. NLP MODERATION (SPAM & TOXIC DETECTION) ---
class NLPModeration:
    TOXIC_KEYWORDS = ["lừa đảo", "chết", "ngu", "bố láo", "thằng chó"]
    FOMO_KEYWORDS = ["x10", "cháy hàng", "đáy rồi", "mua ngay kẻo lỡ", "sốt đất", "vào lướt sóng", "lời to", "bùng nổ"]

    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, float]:
        text_lower = text.lower()
        tokens = word_tokenize(text_lower)
        
        toxic_count = sum(1 for kw in cls.TOXIC_KEYWORDS if kw in text_lower)
        toxic_score = min(1.0, toxic_count * 0.5)
        
        fomo_count = sum(1 for kw in cls.FOMO_KEYWORDS if kw in text_lower)
        fomo_score = min(1.0, fomo_count * 0.4)
        
        return {
            "toxic_score": round(toxic_score, 3),
            "fomo_score": round(fomo_score, 3),
            "is_rejected": toxic_score > 0.6 or fomo_score >= 0.8
        }


# --- 3. DTS ROUTING ENGINE ---
class DTSRoutingEngine:
    @classmethod
    def calculate_dts_and_ring(cls, claim: Claim, author_rep: ReputationLedger, evidence_list: List[ClaimEvidence]) -> Tuple[float, int]:
        base_score = author_rep.global_score / 100.0  # Normalize
        
        # Topic Penalty
        penalty = 0.0
        if claim.claim_type in [ClaimType.LEGAL_ZONING.value, ClaimType.FORECAST.value]:
            penalty = -0.3
            claim.topic_sensitivity_score = 0.8
            
        # Evidence Bonus
        evidence_bonus = 0.0
        for ev in evidence_list:
            if ev.evidence_type == "image":
                if ev.metadata_json and ev.metadata_json.get("gps"):
                    evidence_bonus += 0.25
                else:
                    evidence_bonus += 0.05
            if ev.link_safety_status == LinkSafetyStatus.GREEN_SAFE.value:
                evidence_bonus += 0.15
        
        # Coalition Penalty (If flagged by Trust Graph)
        coalition_penalty = 0.0
        if claim.coalition_risk_score > 0.5:
            coalition_penalty = -0.8
            
        total_dts = max(0.0, base_score + penalty + evidence_bonus + coalition_penalty)
        
        if total_dts < 0.3:
            ring = 1
        elif total_dts < 0.6:
            ring = 2
        elif total_dts < 0.9:
            ring = 3
        else:
            ring = 4
            
        return total_dts, ring


# --- 4. TRUST GRAPH (COALITION DETECTION) ---
class TrustGraphEngine:
    @classmethod
    def detect_coalitions(cls, db: Session):
        """
        Builds graph using NetworkX to find users colluding (verifying/challenging in cliques).
        """
        G = nx.Graph()
        
        # Add edges between challengers and target claims' authors
        challenges = db.query(Challenge).all()
        for ch in challenges:
            claim = db.query(Claim).filter(Claim.id == ch.target_claim_id).first()
            if claim:
                # Add edge with weight based on action
                G.add_edge(ch.challenger_id, claim.author_id, weight=1)
                
        # Find cliques (groups of fully connected users > 2)
        cliques = [c for c in nx.find_cliques(G) if len(c) > 2]
        
        for clique in cliques:
            # Check if clique already flagged
            existing_flag = db.query(CoalitionFlag).filter(
                CoalitionFlag.involved_user_ids.contains(clique)
            ).first()
            
            if not existing_flag:
                flag = CoalitionFlag(
                    cluster_id=f"clique_{datetime.now(timezone.utc).timestamp()}",
                    involved_user_ids=clique,
                    risk_level="high",
                    action_taken="isolated_to_ring_1"
                )
                db.add(flag)
                
                # Punish associated claims
                db.query(Claim).filter(Claim.author_id.in_(clique)).update(
                    {"coalition_risk_score": 0.9, "distribution_ring": 1},
                    synchronize_session=False
                )
        db.commit()


# --- 5. CLAIM COURT SERVICE ---
class ClaimCourtService:
    @classmethod
    def process_verdicts(cls, db: Session):
        """
        Cron job logic to close sessions and calculate final >75% consensus.
        """
        open_sessions = db.query(ClaimCourtSession).filter(ClaimCourtSession.final_verdict == None).all()
        
        for session in open_sessions:
            votes = session.voting_result_json # format: {"true": 3, "false": 1, "misleading": 0}
            if not votes: continue
            
            total_votes = sum(votes.values())
            if total_votes < 3: # Need min 3 jury votes
                continue
                
            # Calculate percentages
            true_pct = votes.get(VerdictType.TRUE.value, 0) / total_votes
            false_pct = votes.get(VerdictType.FALSE.value, 0) / total_votes
            misleading_pct = votes.get(VerdictType.MISLEADING.value, 0) / total_votes
            
            final_v = VerdictType.INCONCLUSIVE.value
            if true_pct >= 0.75:
                final_v = VerdictType.TRUE.value
            elif false_pct >= 0.75:
                final_v = VerdictType.FALSE.value
            elif misleading_pct >= 0.5:
                final_v = VerdictType.MISLEADING.value
                
            session.final_verdict = final_v
            session.closed_at = datetime.now(timezone.utc)
            
            # State Transition on Claim
            claim = db.query(Claim).filter(Claim.id == session.claim_id).first()
            if claim:
                claim.status = f"resolved_{final_v}"
                # Trigger Reputation engine
                ReputationEngine.apply_verdict(db, claim, final_v)
                
        db.commit()


# --- 6. REPUTATION ENGINE ---
class ReputationEngine:
    @classmethod
    def apply_verdict(cls, db: Session, claim: Claim, final_verdict: str):
        rep = db.query(ReputationLedger).filter(ReputationLedger.user_id == claim.author_id).first()
        if not rep:
            return
            
        if final_verdict == VerdictType.TRUE.value:
            rep.global_score += 10.0
            rep.verifier_score += 5.0
            if claim.claim_type == ClaimType.FORECAST.value:
                rep.forecaster_score += 20.0
                
        elif final_verdict in [VerdictType.FALSE.value, VerdictType.MISLEADING.value]:
            rep.global_score -= 25.0  # Heavy penalty
            rep.verifier_score -= 10.0
            if claim.claim_type == ClaimType.FORECAST.value:
                rep.forecaster_score -= 50.0  # Destroy forecaster rep on fake news
                
        db.add(rep)


# --- ORCHESTRATOR: FAST SCAN MODERATION PIPELINE ---
def execute_fast_scan_pipeline(claim_id: int, db: Session):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim or claim.status != ClaimStatus.SHADOW_PENDING.value:
        return
        
    author_rep = db.query(ReputationLedger).filter(ReputationLedger.user_id == claim.author_id).first()
    if not author_rep:
        author_rep = ReputationLedger(user_id=claim.author_id)
        db.add(author_rep)
        db.flush()
        
    evidence_list = db.query(ClaimEvidence).filter(ClaimEvidence.claim_id == claim.id).all()
    
    # 1. NLP Scan
    nlp_res = NLPModeration.analyze_text(claim.content)
    
    # 2. URL Extraction & Scan
    urls_in_text = SafeLinkScanner.extract_urls(claim.content)
    has_red_link = False
    
    for url in urls_in_text:
        if SafeLinkScanner.scan_url(url) == LinkSafetyStatus.RED_DANGER.value:
            has_red_link = True
            
    for ev in evidence_list:
        if ev.evidence_type == "link":
            ev.link_safety_status = SafeLinkScanner.scan_url(ev.evidence_url)
            if ev.link_safety_status == LinkSafetyStatus.RED_DANGER.value:
                has_red_link = True
                
    # 3. Decision & State Machine
    if nlp_res["is_rejected"] or has_red_link:
        claim.status = ClaimStatus.DISPUTED.value
        claim.distribution_ring = 0
        claim.dts_score = 0.0
    else:
        dts, ring = DTSRoutingEngine.calculate_dts_and_ring(claim, author_rep, evidence_list)
        claim.dts_score = dts
        claim.distribution_ring = ring
        
        if ring >= 2:
            claim.status = ClaimStatus.EXPANDED_LIVE.value
        else:
            claim.status = ClaimStatus.LIMITED_LIVE.value
            
    db.commit()


# ═══════════════════════════════════════════════════
# AUTO-DETECT CLAIM TYPE (AI classifies, not user)
# ═══════════════════════════════════════════════════

def auto_detect_claim_type(content: str) -> str:
    """AI keyword-based claim type detection."""
    text = content.lower()
    if any(kw in text for kw in ['quy hoạch', 'pháp lý', 'sổ đỏ', 'sổ hồng', 'giấy phép', 'nghị định']):
        return ClaimType.LEGAL_ZONING.value
    if any(kw in text for kw in ['dự báo', 'sẽ tăng', 'sẽ giảm', 'xu hướng', 'triển vọng']):
        return ClaimType.FORECAST.value
    if any(kw in text for kw in ['giá chốt', 'giao dịch', 'triệu/m²', 'tỷ vnd', 'thống kê']):
        return ClaimType.DATA_FACT.value
    if any(kw in text for kw in ['khảo sát', 'thực địa', 'tận mắt', 'hiện trạng', 'tại khu vực']):
        return ClaimType.FIELD_OBSERVATION.value
    if any(kw in text for kw in ['khuyến nghị', 'nên mua', 'nên bán', 'tiềm năng']):
        return ClaimType.RECOMMENDATION.value
    return ClaimType.OPINION.value


# ═══════════════════════════════════════════════════
# COMMENT RISK LAYER
# ═══════════════════════════════════════════════════

class CommentRiskLayer:
    CLAIM_LITE_KW = ['giá chốt', 'tỷ đồng', 'triệu/m²', 'giao dịch', 'đã bán', 'đã mua',
                     'quy hoạch', 'pháp lý', 'dự báo', 'cảnh báo']

    @classmethod
    def evaluate(cls, comment: CommunityComment, db: Session):
        text = comment.content.lower()
        if any(kw in text for kw in cls.CLAIM_LITE_KW):
            comment.is_claim_lite = True
        # Auto-promote to full claim if thread has >10 comments
        count = db.query(CommunityComment).filter(CommunityComment.claim_id == comment.claim_id).count()
        if count >= 10 and comment.is_claim_lite:
            new_claim = Claim(
                author_id=comment.author_id, claim_type=auto_detect_claim_type(comment.content),
                content=f"[Auto-promoted from comment] {comment.content}",
                status=ClaimStatus.SHADOW_PENDING.value, distribution_ring=0,
            )
            db.add(new_claim); db.flush()
            comment.promoted_to_claim_id = new_claim.id


# ═══════════════════════════════════════════════════
# ABUSE DETECTION ENGINE
# ═══════════════════════════════════════════════════

class AbuseDetectionEngine:
    @classmethod
    def check_targeted_discredit(cls, challenger_id: int, target_author_id: int, db: Session):
        recent = db.query(Challenge).filter(
            Challenge.challenger_id == challenger_id,
            Challenge.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
        ).all()
        targets = set()
        for ch in recent:
            claim = db.query(Claim).filter(Claim.id == ch.target_claim_id).first()
            if claim: targets.add(claim.author_id)
        if len([t for t in targets if t == target_author_id]) >= 5:
            rep = db.query(ReputationLedger).filter(ReputationLedger.user_id == challenger_id).first()
            if rep:
                rep.global_score = max(0, rep.global_score - 50)
                rep.active_sanctions = (rep.active_sanctions or 0) + 1
                db.commit()

    @classmethod
    def check_image_duplicate(cls, evidence_url: str, db: Session) -> bool:
        url_hash = hashlib.sha256(evidence_url.encode()).hexdigest()
        existing = db.query(ClaimEvidence).filter(ClaimEvidence.evidence_url == evidence_url).count()
        return existing > 1


# ═══════════════════════════════════════════════════
# APPEAL SERVICE
# ═══════════════════════════════════════════════════

class AppealService:
    @classmethod
    def create(cls, claim: Claim, user_id: int, reason: str, db: Session) -> dict:
        appeal = AppealCase(claim_id=claim.id, user_id=user_id, appeal_reason=reason, status="open")
        db.add(appeal); db.commit(); db.refresh(appeal)
        return {"id": appeal.id, "status": appeal.status}

    @classmethod
    def accept(cls, appeal_id: int, admin_id: int, db: Session) -> dict:
        appeal = db.query(AppealCase).filter(AppealCase.id == appeal_id).first()
        if not appeal: return {"error": "Not found"}
        appeal.status = "accepted_rollback"
        appeal.resolved_at = datetime.now(timezone.utc)
        claim = db.query(Claim).filter(Claim.id == appeal.claim_id).first()
        if claim: claim.status = ClaimStatus.EXPANDED_LIVE.value
        db.commit()
        return {"id": appeal.id, "status": appeal.status}

    @classmethod
    def reject(cls, appeal_id: int, admin_id: int, db: Session) -> dict:
        appeal = db.query(AppealCase).filter(AppealCase.id == appeal_id).first()
        if not appeal: return {"error": "Not found"}
        appeal.status = "rejected"
        appeal.resolved_at = datetime.now(timezone.utc)
        db.commit()
        return {"id": appeal.id, "status": appeal.status}


# ═══════════════════════════════════════════════════
# PREDICTION BONDS
# ═══════════════════════════════════════════════════

class PredictionBondService:
    @classmethod
    def place(cls, claim_id: int, user_id: int, direction: str, stake: float, db: Session) -> dict:
        rep = db.query(ReputationLedger).filter(ReputationLedger.user_id == user_id).first()
        if not rep or rep.forecaster_score < stake:
            return {"error": "Insufficient forecaster score"}
        bond = PredictionBond(
            claim_id=claim_id, forecaster_id=user_id, staked_points=stake,
            validation_date=datetime.now(timezone.utc) + timedelta(days=90),
        )
        rep.forecaster_score -= stake
        db.add(bond); db.commit(); db.refresh(bond)
        return {"id": bond.id, "staked": bond.staked_points, "validation_date": str(bond.validation_date)}


# ═══════════════════════════════════════════════════
# AI TRAINING FIREWALL
# ═══════════════════════════════════════════════════

class AITrainingFirewall:
    @classmethod
    def get_candidates(cls, db: Session) -> list:
        candidates = db.query(AiTrainingCandidate).filter(AiTrainingCandidate.eligibility_status == True).all()
        return [{"id": c.id, "claim_id": c.claim_id, "source": c.validation_source,
                 "reason": c.training_status_reason} for c in candidates]

    @classmethod
    def evaluate_claim(cls, claim: Claim, verdict: str, db: Session):
        if verdict == VerdictType.TRUE.value:
            candidate = AiTrainingCandidate(
                claim_id=claim.id, validation_source="jury",
                eligibility_status=True, training_status_reason="Verified by jury",
            )
            db.add(candidate)
        elif verdict in [VerdictType.FALSE.value, VerdictType.MISLEADING.value]:
            existing = db.query(AiTrainingCandidate).filter(AiTrainingCandidate.claim_id == claim.id).first()
            if existing:
                existing.eligibility_status = False
                existing.training_status_reason = f"Excluded: {verdict}"
        db.commit()


# ═══════════════════════════════════════════════════
# PRIVATE KNOWLEDGE FUNNEL (Anonymous)
# ═══════════════════════════════════════════════════

class PrivateKnowledgeFunnel:
    @classmethod
    def submit(cls, content: str, area_hint: Optional[str], db: Session) -> dict:
        encrypted = hashlib.sha256(content.encode()).hexdigest()[:16] + "::" + content
        insight = PrivateInsight(content_encrypted=encrypted, area_hint=area_hint)
        db.add(insight); db.commit(); db.refresh(insight)
        return {"id": insight.id, "status": "received", "signal_type": insight.signal_type}
