from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from app import models, schemas
from app.database import get_db
from app.engine import evaluate
from app import payments

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/evaluate", response_model=schemas.DecisionResponse)
def evaluate_transaction(
    payload: schemas.TransactionEvaluateRequest,
    db: Session = Depends(get_db),
):
    try:
        result = evaluate(payload, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")


@router.get("", response_model=list[schemas.TransactionResponse])
def list_transactions(
    skip: int = 0,
    limit: int = 50,
    decision: Optional[str] = None,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)
    if decision:
        q = q.filter(models.Transaction.decision == decision.upper())
    if agent_id:
        q = q.filter(models.Transaction.agent_id == agent_id)
    return q.order_by(models.Transaction.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{txn_id}", response_model=schemas.TransactionResponse)
def get_transaction(txn_id: str, db: Session = Depends(get_db)):
    t = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return t


@router.post("/{txn_id}/review", response_model=schemas.TransactionResponse)
def human_review(
    txn_id: str,
    payload: schemas.HumanReviewRequest,
    db: Session = Depends(get_db),
):
    t = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if t.decision != "REVIEW":
        raise HTTPException(status_code=400, detail="Transaction is not in REVIEW state")

    t.human_approved = payload.approved
    t.human_reviewed_at = datetime.utcnow()
    t.human_reviewer = payload.reviewer

    if payload.approved:
        t.decision = "ALLOW"
        # Update agent daily spend
        agent = db.query(models.Agent).filter(models.Agent.id == t.agent_id).first()
        if agent:
            agent.daily_spent = (agent.daily_spent or 0) + t.amount

        order_id, payment_status = payments.create_order(
            amount_inr=t.amount,
            currency=t.currency,
            receipt=t.id,
            notes={"agent_id": t.agent_id, "merchant_id": t.merchant_id, "product": t.product, "human_approved": True},
        )
        t.razorpay_order_id = order_id
        t.payment_status = payment_status
        db.add(models.AuditLog(
            id=f"AUD-{__import__('uuid').uuid4().hex[:8].upper()}",
            transaction_id=txn_id,
            event_type="PAYMENT_EXECUTION",
            payload={"razorpay_order_id": order_id, "payment_status": payment_status},
        ))
    else:
        t.decision = "BLOCK"
        t.payment_status = "DENIED"

    # Audit
    audit = models.AuditLog(
        id=f"AUD-{__import__('uuid').uuid4().hex[:8].upper()}",
        transaction_id=txn_id,
        event_type="HUMAN_REVIEW",
        payload={"approved": payload.approved, "reviewer": payload.reviewer},
    )
    db.add(audit)
    db.commit()
    db.refresh(t)
    return t
