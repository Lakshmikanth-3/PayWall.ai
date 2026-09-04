import json
import os
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.ml import intent_matcher

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

EVAL_REPORT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "eval_report.json"
)


@router.get("/holdout-metrics")
def get_holdout_metrics():
    """
    Metrics computed offline against the 20,000-row held-out synthetic
    dataset (backend/scripts/evaluate_dataset.py) — independent of whatever
    is currently in the live demo database. See PRD Section 18-19.
    """
    if not os.path.exists(EVAL_REPORT_PATH):
        raise HTTPException(
            status_code=404,
            detail="No held-out evaluation report found. Run scripts/generate_dataset.py "
                   "then scripts/evaluate_dataset.py to produce one.",
        )
    with open(EVAL_REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/llm-toggle")
def toggle_llm(disabled: bool):
    """Demo control: force the LLM (Layer 3) unavailable to show fail-closed behavior."""
    intent_matcher.set_llm_disabled(disabled)
    return {"llm_disabled": intent_matcher.is_llm_disabled()}


@router.get("/llm-status")
def llm_status():
    return {"llm_disabled": intent_matcher.is_llm_disabled()}


@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(models.Transaction.id)).scalar() or 0
    allowed = db.query(func.count(models.Transaction.id)).filter(models.Transaction.decision == "ALLOW").scalar() or 0
    reviewed = db.query(func.count(models.Transaction.id)).filter(models.Transaction.decision == "REVIEW").scalar() or 0
    blocked = db.query(func.count(models.Transaction.id)).filter(models.Transaction.decision == "BLOCK").scalar() or 0

    # Money protected = amount of blocked transactions
    blocked_txns = db.query(models.Transaction).filter(models.Transaction.decision == "BLOCK").all()
    money_protected = sum(t.amount for t in blocked_txns)

    all_txns = db.query(models.Transaction).all()
    total_gmv = sum(t.amount for t in all_txns)
    risky_txns = [t for t in all_txns if (t.risk_score or 0) > 50]
    risky_gmv_blocked = sum(t.amount for t in risky_txns if t.decision == "BLOCK")

    # Latency percentiles
    latencies = [t.decision_latency_ms for t in all_txns if t.decision_latency_ms]
    p50 = float(np.percentile(latencies, 50)) if latencies else 0
    p95 = float(np.percentile(latencies, 95)) if latencies else 0

    avg_risk = float(np.mean([t.risk_score for t in all_txns if t.risk_score])) if all_txns else 0

    # FP rate: legit txns wrongly blocked (risk < 30 but blocked)
    fp = [t for t in blocked_txns if (t.risk_score or 100) < 30]
    fp_rate = len(fp) / total if total else 0

    return schemas.DashboardStats(
        total_evaluated=total,
        total_allowed=allowed,
        total_reviewed=reviewed,
        total_blocked=blocked,
        money_protected=money_protected,
        total_gmv=total_gmv,
        risky_gmv_blocked=risky_gmv_blocked,
        false_positive_rate=round(fp_rate, 4),
        avg_risk_score=round(avg_risk, 2),
        p50_latency=round(p50, 2),
        p95_latency=round(p95, 2),
    )


@router.get("/metrics", response_model=schemas.MetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    all_txns = db.query(models.Transaction).all()
    if not all_txns:
        return schemas.MetricsResponse(
            precision=0, recall=0, f1=0, roc_auc=0,
            false_positive_rate=0, false_positive_gmv=0, legitimate_transactions_blocked=0,
            total_gmv=0, risky_gmv=0, risky_gmv_blocked=0, protection_rate=0,
            review_rate=0, approval_rate=0, denial_rate=0,
            avg_decision_latency_ms=0, p50_latency=0, p95_latency=0,
            avg_policy_latency_ms=0, avg_ml_latency_ms=0, avg_llm_latency_ms=0,
        )

    total = len(all_txns)
    # Label: risky if risk_score > 50
    y_true = [1 if (t.risk_score or 0) > 50 else 0 for t in all_txns]
    y_pred = [1 if t.decision in ("BLOCK", "REVIEW") else 0 for t in all_txns]

    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)
    tn = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

    # ROC-AUC approximation
    try:
        from sklearn.metrics import roc_auc_score
        scores = [(t.risk_score or 50) / 100 for t in all_txns]
        roc_auc = float(roc_auc_score(y_true, scores)) if len(set(y_true)) > 1 else 0.5
    except Exception:
        roc_auc = 0.5

    blocked_txns = [t for t in all_txns if t.decision == "BLOCK"]
    risky_txns = [t for t in all_txns if (t.risk_score or 0) > 50]
    risky_gmv = sum(t.amount for t in risky_txns)
    risky_gmv_blocked = sum(t.amount for t in risky_txns if t.decision == "BLOCK")
    fp_gmv = sum(t.amount for t in all_txns if (t.risk_score or 100) < 30 and t.decision == "BLOCK")
    fp_txns_blocked = sum(1 for t in all_txns if (t.risk_score or 100) < 30 and t.decision == "BLOCK")
    total_gmv = sum(t.amount for t in all_txns)

    review_rate = sum(1 for t in all_txns if t.decision == "REVIEW") / total

    reviewed_txns = [t for t in all_txns if t.decision == "REVIEW" and t.human_approved is not None]
    approval_rate = (
        sum(1 for t in reviewed_txns if t.human_approved) / len(reviewed_txns) if reviewed_txns else 0
    )
    denial_rate = (
        sum(1 for t in reviewed_txns if not t.human_approved) / len(reviewed_txns) if reviewed_txns else 0
    )

    latencies = [t.decision_latency_ms for t in all_txns if t.decision_latency_ms]
    p50 = float(np.percentile(latencies, 50)) if latencies else 0
    p95 = float(np.percentile(latencies, 95)) if latencies else 0
    avg_latency = float(np.mean(latencies)) if latencies else 0

    policy_latencies = [t.policy_latency_ms for t in all_txns if t.policy_latency_ms]
    ml_latencies = [t.ml_latency_ms for t in all_txns if t.ml_latency_ms]
    llm_latencies = [t.llm_latency_ms for t in all_txns if t.llm_latency_ms]

    return schemas.MetricsResponse(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        roc_auc=round(roc_auc, 4),
        false_positive_rate=round(fpr, 4),
        false_positive_gmv=round(fp_gmv, 2),
        legitimate_transactions_blocked=fp_txns_blocked,
        total_gmv=round(total_gmv, 2),
        risky_gmv=round(risky_gmv, 2),
        risky_gmv_blocked=round(risky_gmv_blocked, 2),
        protection_rate=round(risky_gmv_blocked / risky_gmv if risky_gmv else 0, 4),
        review_rate=round(review_rate, 4),
        approval_rate=round(approval_rate, 4),
        denial_rate=round(denial_rate, 4),
        avg_decision_latency_ms=round(avg_latency, 2),
        p50_latency=round(p50, 2),
        p95_latency=round(p95, 2),
        avg_policy_latency_ms=round(float(np.mean(policy_latencies)), 2) if policy_latencies else 0,
        avg_ml_latency_ms=round(float(np.mean(ml_latencies)), 2) if ml_latencies else 0,
        avg_llm_latency_ms=round(float(np.mean(llm_latencies)), 2) if llm_latencies else 0,
    )


@router.get("/revenue-impact", response_model=schemas.RevenueImpactResponse)
def get_revenue_impact(db: Session = Depends(get_db)):
    """
    PRD Section 17.A — Merchant Revenue Impact panel. Every row here is an
    is_upsell=True transaction that went through the exact same Guard
    pipeline as any other payment (see app.upsell_agent / POST
    /transactions/{id}/upsell). This is the evidence that Agent Commerce
    Guard grows revenue, not just blocks it: real incremental GMV from
    allowed upsells, next to the exposure prevented from manipulative ones.
    """
    upsells = db.query(models.Transaction).filter(models.Transaction.is_upsell == True).all()  # noqa: E712
    proposed = len(upsells)
    allowed = [t for t in upsells if t.decision == "ALLOW"]
    blocked = [t for t in upsells if t.decision == "BLOCK"]
    review = [t for t in upsells if t.decision == "REVIEW"]

    incremental_gmv = sum(t.amount for t in allowed)
    manipulative_exposure_blocked = sum(t.amount for t in blocked)
    acceptance_rate = len(allowed) / proposed if proposed else 0.0

    return schemas.RevenueImpactResponse(
        upsells_proposed=proposed,
        upsells_allowed=len(allowed),
        upsells_blocked=len(blocked),
        upsells_review=len(review),
        incremental_gmv=round(incremental_gmv, 2),
        upsell_acceptance_rate=round(acceptance_rate, 4),
        manipulative_exposure_blocked=round(manipulative_exposure_blocked, 2),
    )


@router.get("/live")
def get_live_transactions(limit: int = 10, db: Session = Depends(get_db)):
    txns = db.query(models.Transaction).order_by(
        models.Transaction.created_at.desc()
    ).limit(limit).all()
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "decision": t.decision,
            "risk_score": t.risk_score,
            "merchant_name": t.merchant_name,
            "product": t.product,
            "user_intent": t.user_intent,
            "category": t.category,
            "agent_id": t.agent_id,
            "requires_human_review": t.requires_human_review,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]


@router.get("/audit")
def get_audit_trail(
    txn_id: str = None,
    agent_id: str = None,
    merchant: str = None,
    decision: str = None,
    min_risk: float = None,
    max_risk: float = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)
    if txn_id:
        q = q.filter(models.Transaction.id.ilike(f"%{txn_id}%"))
    if agent_id:
        q = q.filter(models.Transaction.agent_id == agent_id)
    if merchant:
        q = q.filter(models.Transaction.merchant_name.ilike(f"%{merchant}%"))
    if decision:
        q = q.filter(models.Transaction.decision == decision.upper())
    if min_risk is not None:
        q = q.filter(models.Transaction.risk_score >= min_risk)
    if max_risk is not None:
        q = q.filter(models.Transaction.risk_score <= max_risk)
    return q.order_by(models.Transaction.created_at.desc()).offset(skip).limit(limit).all()
