import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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
            false_positive_rate=0, false_positive_gmv=0,
            risky_gmv=0, risky_gmv_blocked=0, protection_rate=0,
            review_rate=0, avg_decision_latency_ms=0, p50_latency=0, p95_latency=0,
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

    review_rate = sum(1 for t in all_txns if t.decision == "REVIEW") / total

    latencies = [t.decision_latency_ms for t in all_txns if t.decision_latency_ms]
    p50 = float(np.percentile(latencies, 50)) if latencies else 0
    p95 = float(np.percentile(latencies, 95)) if latencies else 0
    avg_latency = float(np.mean(latencies)) if latencies else 0

    return schemas.MetricsResponse(
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        roc_auc=round(roc_auc, 4),
        false_positive_rate=round(fpr, 4),
        false_positive_gmv=round(fp_gmv, 2),
        risky_gmv=round(risky_gmv, 2),
        risky_gmv_blocked=round(risky_gmv_blocked, 2),
        protection_rate=round(risky_gmv_blocked / risky_gmv if risky_gmv else 0, 4),
        review_rate=round(review_rate, 4),
        avg_decision_latency_ms=round(avg_latency, 2),
        p50_latency=round(p50, 2),
        p95_latency=round(p95, 2),
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
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns
    ]


@router.get("/audit")
def get_audit_trail(
    txn_id: str = None,
    agent_id: str = None,
    decision: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)
    if txn_id:
        q = q.filter(models.Transaction.id.ilike(f"%{txn_id}%"))
    if agent_id:
        q = q.filter(models.Transaction.agent_id == agent_id)
    if decision:
        q = q.filter(models.Transaction.decision == decision.upper())
    return q.order_by(models.Transaction.created_at.desc()).offset(skip).limit(limit).all()
