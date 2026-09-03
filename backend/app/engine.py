"""
Decision Engine — the core of Agent Commerce Guard.

Three-layer architecture:
  Layer 1: Hard policy rules (deterministic)
  Layer 2: ML risk model (XGBoost / heuristic)
  Layer 3: LLM intent matching (OpenAI / keyword fallback)
"""

import time
import uuid
from datetime import date, datetime
from typing import List, Tuple
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.ml.risk_model import score_transaction
from app.ml.intent_matcher import match_intent, generate_explanation


def _reset_daily_spend_if_needed(agent: models.Agent, db: Session):
    today = date.today().isoformat()
    if agent.last_reset_date != today:
        agent.daily_spent = 0.0
        agent.last_reset_date = today
        db.commit()


def _run_policy_checks(
    agent: models.Agent,
    merchant: models.Merchant,
    req: schemas.TransactionEvaluateRequest,
) -> Tuple[List[schemas.PolicyCheck], List[str]]:
    """
    Layer 1: Deterministic hard policy rules.
    Returns (check_list, violations).
    """
    checks = []
    violations = []

    # ── 1. Agent authenticated & active ──────────────────────────────────────
    is_active = agent.status == "ACTIVE" and agent.payment_enabled
    checks.append(schemas.PolicyCheck(
        check="Agent authenticated & active",
        passed=is_active,
        detail=f"Agent status: {agent.status}, Payment enabled: {agent.payment_enabled}"
    ))
    if not is_active:
        violations.append("Agent is not active or payment is disabled")

    # ── 2. Merchant not blocked ───────────────────────────────────────────────
    merchant_ok = not merchant.is_blocked
    checks.append(schemas.PolicyCheck(
        check="Merchant not blocked",
        passed=merchant_ok,
        detail=f"Merchant blocked: {merchant.is_blocked}"
    ))
    if not merchant_ok:
        violations.append("Merchant is blocked")

    # ── 3. Maximum transaction limit ─────────────────────────────────────────
    within_max = req.amount <= agent.max_transaction
    checks.append(schemas.PolicyCheck(
        check="Within maximum transaction limit",
        passed=within_max,
        detail=f"₹{req.amount:,.0f} vs limit ₹{agent.max_transaction:,.0f}"
    ))
    if not within_max:
        violations.append(f"Amount ₹{req.amount:,.0f} exceeds max transaction ₹{agent.max_transaction:,.0f}")

    # ── 4. Daily budget check ────────────────────────────────────────────────
    remaining = agent.daily_limit - agent.daily_spent
    within_daily = req.amount <= remaining
    checks.append(schemas.PolicyCheck(
        check="Within daily budget",
        passed=within_daily,
        detail=f"Daily spent: ₹{agent.daily_spent:,.0f} / ₹{agent.daily_limit:,.0f}. Remaining: ₹{remaining:,.0f}"
    ))
    if not within_daily:
        violations.append(f"Daily budget exceeded — spent ₹{agent.daily_spent:,.0f}, limit ₹{agent.daily_limit:,.0f}")

    # ── 5. Category allowed ──────────────────────────────────────────────────
    allowed_cats = [c.lower() for c in agent.allowed_categories]
    blocked_cats = [c.lower() for c in agent.blocked_categories]
    req_cat = req.category.lower()

    cat_allowed = (not allowed_cats or req_cat in allowed_cats) and req_cat not in blocked_cats
    checks.append(schemas.PolicyCheck(
        check="Category authorized",
        passed=cat_allowed,
        detail=f"Category: {req.category}. Allowed: {agent.allowed_categories}. Blocked: {agent.blocked_categories}"
    ))
    if not cat_allowed:
        violations.append(f"Category '{req.category}' is not authorized for this agent")

    return checks, violations


def evaluate(
    req: schemas.TransactionEvaluateRequest,
    db: Session,
) -> schemas.DecisionResponse:
    total_start = time.perf_counter()

    # ── Load agent ────────────────────────────────────────────────────────────
    agent = db.query(models.Agent).filter(models.Agent.id == req.agent_id).first()
    if not agent:
        raise ValueError(f"Agent {req.agent_id} not found")

    _reset_daily_spend_if_needed(agent, db)

    # ── Load merchant ─────────────────────────────────────────────────────────
    merchant = db.query(models.Merchant).filter(models.Merchant.id == req.merchant_id).first()
    if not merchant:
        raise ValueError(f"Merchant {req.merchant_id} not found")

    # ── Layer 1: Policy checks ────────────────────────────────────────────────
    policy_start = time.perf_counter()
    policy_checks, violations = _run_policy_checks(agent, merchant, req)
    policy_latency_ms = (time.perf_counter() - policy_start) * 1000

    # Immediate block on hard violations
    if violations and any(v for v in violations if "Agent" in v or "Merchant" in v or "Daily" in v):
        decision = schemas.Decision.BLOCK
        risk_score = 95.0
        intent_score = 0.5
        reasoning = "; ".join(violations)
        ml_latency_ms = 0
        llm_latency_ms = 0
    else:
        # ── Layer 2: ML risk scoring ──────────────────────────────────────────
        # Count recent transactions for velocity
        recent_hour = db.query(models.Transaction).filter(
            models.Transaction.agent_id == req.agent_id,
            models.Transaction.created_at >= datetime.utcnow().replace(minute=0, second=0)
        ).count()
        recent_day = db.query(models.Transaction).filter(
            models.Transaction.agent_id == req.agent_id,
        ).count()

        daily_remaining_ratio = max(0, (agent.daily_limit - agent.daily_spent) / agent.daily_limit)

        # Intent match (Layer 3) needed for ML features
        intent_score, reasoning, llm_latency_ms = match_intent(
            user_intent=req.user_intent,
            product=req.product,
            category=req.category,
            amount=req.amount,
            max_amount=agent.max_transaction,
        )

        ml_features = {
            "amount": req.amount,
            "amount_ratio": req.amount / (agent.max_transaction or 1),
            "merchant_age_days": merchant.age_days,
            "merchant_risk_score": merchant.risk_score,
            "txn_count_last_hour": recent_hour,
            "txn_count_last_day": recent_day,
            "intent_match_score": intent_score,
            "category_allowed": 1 if not violations else 0,
            "daily_budget_remaining_ratio": daily_remaining_ratio,
            "refund_rate": merchant.refund_rate,
            "chargeback_rate": merchant.chargeback_rate,
            "failed_payment_rate": merchant.failed_payment_rate,
        }
        risk_score, ml_latency_ms = score_transaction(ml_features)

        # ── Combine policy violations into risk ───────────────────────────────
        if violations:
            risk_score = min(risk_score + 30, 100.0)

        # ── Final decision ────────────────────────────────────────────────────
        if risk_score <= settings.ALLOW_THRESHOLD and not violations:
            decision = schemas.Decision.ALLOW
        elif risk_score >= settings.REVIEW_THRESHOLD or violations:
            decision = schemas.Decision.BLOCK
        else:
            decision = schemas.Decision.REVIEW

        # Human approval threshold override
        if (decision == schemas.Decision.ALLOW and
                agent.requires_approval_above > 0 and
                req.amount >= agent.requires_approval_above):
            decision = schemas.Decision.REVIEW

    # ── LLM explanation (if not already set) ─────────────────────────────────
    if decision in (schemas.Decision.BLOCK, schemas.Decision.REVIEW):
        explanation = generate_explanation(
            decision=decision.value,
            policy_violations=violations,
            risk_score=risk_score,
            intent_score=intent_score if 'intent_score' in dir() else 0.5,
            user_intent=req.user_intent,
            product=req.product,
            amount=req.amount,
        )
    else:
        explanation = f"Transaction matches user intent and agent policy. Risk score: {risk_score:.0f}/100."

    total_latency_ms = (time.perf_counter() - total_start) * 1000
    txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"

    # ── Persist transaction ───────────────────────────────────────────────────
    txn = models.Transaction(
        id=txn_id,
        agent_id=req.agent_id,
        user_id=agent.owner_id,
        merchant_id=req.merchant_id,
        merchant_name=merchant.name,
        amount=req.amount,
        currency=req.currency,
        category=req.category,
        product=req.product,
        user_intent=req.user_intent,
        decision=decision.value,
        risk_score=risk_score,
        intent_match_score=intent_score if 'intent_score' in locals() else 0.5,
        policy_violations=violations,
        reason=explanation,
        requires_human_review=(decision == schemas.Decision.REVIEW),
        decision_latency_ms=total_latency_ms,
        policy_latency_ms=round(policy_latency_ms, 2),
        ml_latency_ms=ml_latency_ms if 'ml_latency_ms' in locals() else 0,
        llm_latency_ms=llm_latency_ms if 'llm_latency_ms' in locals() else 0,
    )
    db.add(txn)

    # Update daily spend if ALLOW
    if decision == schemas.Decision.ALLOW:
        agent.daily_spent = (agent.daily_spent or 0) + req.amount
        db.add(agent)

    # Audit log
    audit = models.AuditLog(
        id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
        transaction_id=txn_id,
        event_type="DECISION",
        payload={
            "decision": decision.value,
            "risk_score": risk_score,
            "violations": violations,
        },
    )
    db.add(audit)
    db.commit()

    confidence = abs(risk_score - 50) / 50 + 0.5
    confidence = min(round(confidence, 3), 1.0)

    return schemas.DecisionResponse(
        transaction_id=txn_id,
        decision=decision,
        risk_score=round(risk_score, 2),
        intent_match_score=round(intent_score if 'intent_score' in locals() else 0.5, 4),
        policy_violations=violations,
        policy_checks=policy_checks,
        reason=explanation,
        confidence=confidence,
        requires_human_review=(decision == schemas.Decision.REVIEW),
        decision_latency_ms=round(total_latency_ms, 2),
    )
