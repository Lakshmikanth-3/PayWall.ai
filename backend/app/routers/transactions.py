from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from app import models, schemas
from app.database import get_db
from app.engine import evaluate, _run_policy_checks, _reset_daily_spend_if_needed
from app import payments
from app.upsell_agent import propose_upsell

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
        # PRD Section 11: "Human approval -> Policy re-check -> Razorpay payment".
        # Policy may have changed (or the agent's daily budget may have been
        # consumed by other transactions) between the original decision and
        # this approval, so re-run Layer 1 against current state before
        # allowing money to move.
        agent = db.query(models.Agent).filter(models.Agent.id == t.agent_id).first()
        merchant = db.query(models.Merchant).filter(models.Merchant.id == t.merchant_id).first()
        if not agent or not merchant:
            raise HTTPException(status_code=404, detail="Agent or merchant no longer exists")

        _reset_daily_spend_if_needed(agent, db)
        recheck_req = schemas.TransactionEvaluateRequest(
            agent_id=t.agent_id, amount=t.amount, currency=t.currency,
            merchant_id=t.merchant_id, category=t.category, product=t.product,
            user_intent=t.user_intent or "",
        )
        _, recheck_violations = _run_policy_checks(agent, merchant, recheck_req)

        if recheck_violations:
            t.decision = "BLOCK"
            t.payment_status = "BLOCKED_ON_RECHECK"
            t.reason = "Policy re-check failed after human approval: " + "; ".join(recheck_violations)
            db.add(models.AuditLog(
                id=f"AUD-{__import__('uuid').uuid4().hex[:8].upper()}",
                transaction_id=txn_id,
                event_type="POLICY_RECHECK_FAILED",
                payload={"violations": recheck_violations},
            ))
        else:
            t.decision = "ALLOW"
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


@router.post("/{txn_id}/upsell", response_model=schemas.UpsellProposalResponse)
def propose_upsell_for_transaction(txn_id: str, db: Session = Depends(get_db)):
    """
    PRD Section 2a — Upsell Agent. Given a just-ALLOWed purchase, proposes one
    budget-aware complementary add-on and evaluates it through the exact same
    Guard pipeline as any other agent-initiated payment (identity, intent
    match against the ORIGINAL user intent, policy, risk). The Upsell Agent
    has no special authority: a legitimate upsell is allowed, a manipulative
    one is blocked, by the same code path either way.
    """
    original = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if original.decision != "ALLOW":
        raise HTTPException(status_code=400, detail="Upsells can only be proposed after an ALLOWed purchase")

    agent = db.query(models.Agent).filter(models.Agent.id == original.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    candidate = propose_upsell(agent, original)
    if not candidate:
        return schemas.UpsellProposalResponse(
            proposed=False,
            reason="No complementary add-on fits the agent's remaining budget.",
            original_transaction_id=txn_id,
        )

    upsell_req = schemas.TransactionEvaluateRequest(
        agent_id=original.agent_id,
        amount=candidate["amount"],
        currency=original.currency,
        merchant_id=candidate["merchant_id"],
        category=candidate["category"],
        product=candidate["product"],
        # Intent match is checked against the SAME original user intent — this
        # is what makes a relevant upsell score well and a manipulative one
        # (e.g. an unrelated ₹14,999 "protection plan") score badly.
        user_intent=original.user_intent,
        is_upsell=True,
        upsell_of_transaction_id=txn_id,
    )
    decision_result = evaluate(upsell_req, db)

    return schemas.UpsellProposalResponse(
        proposed=True,
        reason=f"Proposed {candidate['product']} (₹{candidate['amount']:,.0f}) as a complementary add-on.",
        original_transaction_id=txn_id,
        decision=decision_result,
    )


@router.post("/{txn_id}/retry-payment", response_model=schemas.TransactionResponse)
def retry_payment(txn_id: str, db: Session = Depends(get_db)):
    """
    PRD Section 21 — authorization and payment execution are separate. If the
    Guard already ALLOWed a transaction but the Razorpay call failed (network
    blip, transient API error), retry only the payment step. Never re-runs
    authorization — a stale ALLOW is not re-litigated here.
    """
    t = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if t.decision != "ALLOW":
        raise HTTPException(status_code=400, detail="Only ALLOWed transactions can retry payment")
    if t.payment_status == "CREATED":
        raise HTTPException(status_code=400, detail="Payment already succeeded")

    order_id, payment_status = payments.create_order(
        amount_inr=t.amount,
        currency=t.currency,
        receipt=t.id,
        notes={"agent_id": t.agent_id, "merchant_id": t.merchant_id, "product": t.product, "retry": True},
    )
    t.razorpay_order_id = order_id
    t.payment_status = payment_status
    db.add(models.AuditLog(
        id=f"AUD-{__import__('uuid').uuid4().hex[:8].upper()}",
        transaction_id=txn_id,
        event_type="PAYMENT_RETRY",
        payload={"razorpay_order_id": order_id, "payment_status": payment_status},
    ))
    db.commit()
    db.refresh(t)
    return t
