"""
Policy Simulator — PRD Section 26 ("killer feature").

Replays an agent's actual historical transactions against a proposed policy
change and reports how the ALLOW/REVIEW/BLOCK mix would shift, without
touching the live policy or re-calling the LLM. This shows the economic
tradeoff between loosening automation and taking on more risk.

Method / known simplification: the ML risk_score for each historical
transaction is reused as-is (recomputing it would require re-deriving the
exact feature snapshot from that point in time, e.g. merchant risk at that
moment). Only the policy-dependent inputs are re-evaluated for the proposed
policy: max_transaction, category allow/block lists, requires_approval_above,
and daily_limit (replayed as a real running total per calendar day across
the agent's transaction history, in chronological order).
"""

from collections import defaultdict
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings


def _category_allowed(category: str, allowed: list, blocked: list) -> bool:
    category = category.lower()
    allowed_l = [c.lower() for c in allowed]
    blocked_l = [c.lower() for c in blocked]
    return (not allowed_l or category in allowed_l) and category not in blocked_l


def _simulate_decision(amount, category, risk_score, policy, cumulative_spent_before) -> str:
    hard_violation = False
    if amount > policy["max_transaction"]:
        hard_violation = True
    if not _category_allowed(category, policy["allowed_categories"], policy["blocked_categories"]):
        hard_violation = True
    if amount > max(0, policy["daily_limit"] - cumulative_spent_before):
        hard_violation = True

    if hard_violation:
        return "BLOCK"

    risk_score = risk_score if risk_score is not None else 50.0
    if risk_score <= settings.ALLOW_THRESHOLD:
        decision = "ALLOW"
    elif risk_score >= settings.REVIEW_THRESHOLD:
        decision = "BLOCK"
    else:
        decision = "REVIEW"

    if (decision == "ALLOW" and policy["requires_approval_above"] > 0
            and amount >= policy["requires_approval_above"]):
        decision = "REVIEW"

    return decision


def simulate_policy(
    agent: models.Agent,
    proposal: schemas.PolicySimulationRequest,
    db: Session,
) -> schemas.PolicySimulationResponse:
    current_policy = {
        "max_transaction": agent.max_transaction,
        "daily_limit": agent.daily_limit,
        "allowed_categories": agent.allowed_categories or [],
        "blocked_categories": agent.blocked_categories or [],
        "requires_approval_above": agent.requires_approval_above or 0,
    }
    proposed_policy = dict(current_policy)
    for field in ("max_transaction", "daily_limit", "allowed_categories",
                  "blocked_categories", "requires_approval_above"):
        value = getattr(proposal, field)
        if value is not None:
            proposed_policy[field] = value

    txns = (
        db.query(models.Transaction)
        .filter(models.Transaction.agent_id == agent.id)
        .order_by(models.Transaction.created_at.asc())
        .all()
    )

    # Replay cumulative daily spend under the PROPOSED policy, grouped by
    # calendar day, so daily_limit changes are re-simulated accurately.
    daily_spent = defaultdict(float)

    before_counts = {"ALLOW": 0, "REVIEW": 0, "BLOCK": 0}
    after_counts = {"ALLOW": 0, "REVIEW": 0, "BLOCK": 0}
    now_allowed_count = 0
    now_allowed_gmv = 0.0
    additional_risky_exposure = 0.0
    now_blocked_count = 0
    now_blocked_gmv = 0.0
    flipped = []

    for t in txns:
        before_decision = t.decision
        before_counts[before_decision] = before_counts.get(before_decision, 0) + 1

        day_key = (t.created_at.date().isoformat() if t.created_at else "unknown")
        cumulative_before = daily_spent[day_key]

        after_decision = _simulate_decision(
            t.amount, t.category, t.risk_score, proposed_policy, cumulative_before
        )
        after_counts[after_decision] = after_counts.get(after_decision, 0) + 1

        if after_decision == "ALLOW":
            daily_spent[day_key] = cumulative_before + t.amount

        if after_decision != before_decision:
            if after_decision == "ALLOW" and before_decision != "ALLOW":
                now_allowed_count += 1
                now_allowed_gmv += t.amount
                if (t.risk_score or 0) > 50:
                    additional_risky_exposure += t.amount
            if after_decision == "BLOCK" and before_decision != "BLOCK":
                now_blocked_count += 1
                now_blocked_gmv += t.amount

            if len(flipped) < 25:
                flipped.append(schemas.FlippedTransaction(
                    transaction_id=t.id,
                    amount=t.amount,
                    category=t.category,
                    product=t.product,
                    merchant_name=t.merchant_name,
                    risk_score=t.risk_score,
                    before=before_decision,
                    after=after_decision,
                ))

    return schemas.PolicySimulationResponse(
        agent_id=agent.id,
        transactions_analyzed=len(txns),
        current_policy=schemas.PolicyView(**current_policy),
        proposed_policy=schemas.PolicyView(**proposed_policy),
        before=schemas.DecisionCounts(**before_counts),
        after=schemas.DecisionCounts(**after_counts),
        now_allowed_count=now_allowed_count,
        now_allowed_gmv=round(now_allowed_gmv, 2),
        additional_risky_exposure=round(additional_risky_exposure, 2),
        now_blocked_count=now_blocked_count,
        now_blocked_gmv=round(now_blocked_gmv, 2),
        flipped_transactions=flipped,
    )
