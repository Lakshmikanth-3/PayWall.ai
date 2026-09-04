"""
Demo fixture validation — PRD Section 19 "Scenario-level targets".

Runs the exact three demo fixtures (Section 2a / Section 7 / Section 27
demo script) through the live decision engine and checks them against the
PRD's target ranges:

  normal-plus-upsell (shoes)          risk < 20   intent >= 0.90   ALLOW
  normal-plus-upsell (socks upsell)   risk < 20   intent >= 0.85   ALLOW
  manipulated-upsell (protection plan) risk > 70   intent < 0.20   BLOCK

Per Section 19: "If your model doesn't land in these ranges on the seeded
fixtures, fix the fixtures or the thresholds before the demo — don't
discover this live." Run this after scripts/seed_db.py and before demoing.

Requires AGT-001 / MER-001 to exist (created by scripts/seed_db.py).

Usage:
    python scripts/validate_fixtures.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

from app.database import SessionLocal
from app import models, schemas
from app.engine import evaluate

AGENT_ID = "AGT-001"
MERCHANT_ID = "MER-001"


def _reset_agent(db):
    agent = db.query(models.Agent).filter(models.Agent.id == AGENT_ID).first()
    if not agent:
        print(f"[ERROR] Agent {AGENT_ID} not found. Run scripts/seed_db.py first.")
        sys.exit(1)
    agent.daily_spent = 0.0
    agent.last_reset_date = date.today().isoformat()
    db.commit()
    return agent


def _check(label, decision, risk_score, intent_score, risk_ok, intent_ok, expected_decision):
    decision_ok = decision == expected_decision
    all_ok = risk_ok and intent_ok and decision_ok
    status = "PASS" if all_ok else "FAIL"
    print(f"\n[{status}] {label}")
    print(f"  decision={decision} (expected {expected_decision}) {'OK' if decision_ok else 'MISMATCH'}")
    print(f"  risk_score={risk_score:.1f} {'OK' if risk_ok else 'OUT OF RANGE'}")
    print(f"  intent_match={intent_score:.3f} {'OK' if intent_ok else 'OUT OF RANGE'}")
    return all_ok


def _cleanup(db, txn_id):
    # Validation runs are dry runs, not real demo history — delete what they
    # wrote so repeated runs stay idempotent instead of accumulating fake
    # same-agent velocity that would skew the NEXT run's risk score.
    db.query(models.AuditLog).filter(models.AuditLog.transaction_id == txn_id).delete()
    db.query(models.Transaction).filter(models.Transaction.id == txn_id).delete()
    db.commit()


def main():
    db = SessionLocal()
    all_passed = True
    created_txn_ids = []

    # ── Fixture 1: normal-plus-upsell (shoes) ─────────────────────────────────
    _reset_agent(db)
    shoes_req = schemas.TransactionEvaluateRequest(
        agent_id=AGENT_ID, amount=4799, currency="INR", merchant_id=MERCHANT_ID,
        category="sports", product="Nike Running Shoes",
        user_intent="Buy running shoes under 5000",
    )
    shoes_result = evaluate(shoes_req, db, execute_payment=False)
    created_txn_ids.append(shoes_result.transaction_id)
    all_passed &= _check(
        "normal-plus-upsell (shoes)",
        shoes_result.decision.value, shoes_result.risk_score, shoes_result.intent_match_score,
        risk_ok=shoes_result.risk_score < 20, intent_ok=shoes_result.intent_match_score >= 0.90,
        expected_decision="ALLOW",
    )

    # ── Fixture 2: normal-plus-upsell (socks upsell) ──────────────────────────
    socks_req = schemas.TransactionEvaluateRequest(
        agent_id=AGENT_ID, amount=149, currency="INR", merchant_id=MERCHANT_ID,
        category="sports", product="Moisture-wicking Running Socks",
        user_intent="Buy running shoes under 5000",
        is_upsell=True, upsell_of_transaction_id=shoes_result.transaction_id,
    )
    socks_result = evaluate(socks_req, db, execute_payment=False)
    created_txn_ids.append(socks_result.transaction_id)
    all_passed &= _check(
        "normal-plus-upsell (socks upsell)",
        socks_result.decision.value, socks_result.risk_score, socks_result.intent_match_score,
        risk_ok=socks_result.risk_score < 20, intent_ok=socks_result.intent_match_score >= 0.85,
        expected_decision="ALLOW",
    )

    # ── Fixture 3: manipulated-upsell (protection plan) — the killer scenario ─
    _reset_agent(db)
    plan_req = schemas.TransactionEvaluateRequest(
        agent_id=AGENT_ID, amount=14999, currency="INR", merchant_id=MERCHANT_ID,
        category="insurance", product="Premium Protection Plan",
        user_intent="Buy running shoes under 5000",
        is_upsell=True,
    )
    plan_result = evaluate(plan_req, db, execute_payment=False)
    created_txn_ids.append(plan_result.transaction_id)
    all_passed &= _check(
        "manipulated-upsell (protection plan)",
        plan_result.decision.value, plan_result.risk_score, plan_result.intent_match_score,
        risk_ok=plan_result.risk_score > 70, intent_ok=plan_result.intent_match_score < 0.20,
        expected_decision="BLOCK",
    )

    for txn_id in created_txn_ids:
        _cleanup(db, txn_id)
    db.close()
    print(f"\n{'='*50}")
    print("ALL FIXTURES PASSED" if all_passed else "SOME FIXTURES FAILED — fix before demoing")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
