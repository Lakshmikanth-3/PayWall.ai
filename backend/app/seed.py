"""
Demo data seeding — agents, merchants, transaction history, and upsell
history. Runs directly against whatever database the calling process is
connected to.

Used two ways:
  - scripts/seed_db.py (CLI, local dev — connects to the local sqlite file)
  - POST /admin/seed (backend/app/routers/admin.py — lets a deployed
    instance without shell/filesystem access, e.g. Render's free tier,
    seed its own database over HTTP instead of needing a direct DB
    connection from outside)

Idempotent: each stage skips if its data already exists, so calling this
repeatedly (e.g. re-triggering the admin endpoint) is safe.
"""

import random
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from app import models

AGENTS = [
    {
        "id": "AGT-001",
        "name": "Shopping Assistant",
        "owner_id": "USR-001",
        "max_transaction": 5000,
        "daily_limit": 10000,
        "allowed_categories": ["food", "groceries", "sports", "electronics"],
        "blocked_categories": ["gambling", "financial_services"],
        # PRD Section 19 pins the canonical ₹4,799 running-shoes fixture to
        # ALLOW; Section 6's own worked example pairs the SAME ₹4,799
        # purchase with a 3,000 approval threshold while also calling it
        # ALLOW — those two can't both be literally true under the
        # requires_approval_above hard-override rule this engine implements
        # (see app.engine.decide). Resolved in favor of the numeric Section
        # 19 target: threshold set just above the canonical fixture amount.
        # The "Human Review Required" demo scenario (MER-010, ₹3,500) still
        # exercises REVIEW through the risk-score path via that merchant's
        # medium risk tier, independent of this threshold.
        "requires_approval_above": 4900,
    },
    {
        "id": "AGT-002",
        "name": "Travel Booker",
        "owner_id": "USR-002",
        "max_transaction": 20000,
        "daily_limit": 50000,
        "allowed_categories": ["travel", "hotel", "food"],
        "blocked_categories": ["gambling"],
        "requires_approval_above": 10000,
    },
    {
        "id": "AGT-003",
        "name": "Office Supply Agent",
        "owner_id": "USR-003",
        "max_transaction": 2000,
        "daily_limit": 5000,
        "allowed_categories": ["office", "electronics", "stationery"],
        "blocked_categories": [],
        "requires_approval_above": 1500,
    },
]

MERCHANTS = [
    {"id": "MER-001", "name": "Nike Official Store", "category": "sports", "risk_score": 8, "age_days": 3650},
    {"id": "MER-002", "name": "Amazon India", "category": "electronics", "risk_score": 5, "age_days": 5000},
    {"id": "MER-003", "name": "BigBasket", "category": "groceries", "risk_score": 10, "age_days": 2000},
    {"id": "MER-004", "name": "MakeMyTrip", "category": "travel", "risk_score": 12, "age_days": 4000},
    {"id": "MER-005", "name": "Zomato", "category": "food", "risk_score": 7, "age_days": 3000},
    {"id": "MER-006", "name": "QuickShop24", "category": "electronics", "risk_score": 65, "age_days": 15, "refund_rate": 0.12},
    {"id": "MER-007", "name": "ShadyDeals.in", "category": "electronics", "risk_score": 88, "age_days": 5, "chargeback_rate": 0.15},
    {"id": "MER-008", "name": "Decathlon", "category": "sports", "risk_score": 9, "age_days": 2500},
    {"id": "MER-009", "name": "Flipkart", "category": "electronics", "risk_score": 6, "age_days": 5500},
    {"id": "MER-010", "name": "SwiftGrocers", "category": "groceries", "risk_score": 35, "age_days": 90},
]


def _seed_agents_and_merchants(db: Session) -> None:
    for a in AGENTS:
        if not db.query(models.Agent).filter(models.Agent.id == a["id"]).first():
            db.add(models.Agent(
                id=a["id"], name=a["name"], owner_id=a["owner_id"],
                max_transaction=a["max_transaction"], daily_limit=a["daily_limit"],
                allowed_categories=a["allowed_categories"], blocked_categories=a["blocked_categories"],
                requires_approval_above=a["requires_approval_above"],
                last_reset_date=date.today().isoformat(),
            ))

    for m in MERCHANTS:
        if not db.query(models.Merchant).filter(models.Merchant.id == m["id"]).first():
            risk = m.get("risk_score", 20)
            db.add(models.Merchant(
                id=m["id"], name=m["name"], category=m["category"], risk_score=risk,
                risk_level="LOW" if risk <= 30 else ("MEDIUM" if risk <= 70 else "HIGH"),
                age_days=m.get("age_days", 365),
                refund_rate=m.get("refund_rate", 0.02),
                chargeback_rate=m.get("chargeback_rate", 0.01),
                failed_payment_rate=m.get("failed_payment_rate", 0.03),
            ))
    db.commit()


def _seed_transaction_history(db: Session) -> int:
    if db.query(models.Transaction).first():
        return -1  # already present

    from app import schemas
    from app.engine import evaluate

    PRODUCTS = {
        "food": "Pizza Order", "groceries": "Monthly Grocery Pack", "sports": "Running Shoes",
        "electronics": "Wireless Mouse", "travel": "Flight Ticket", "hotel": "Hotel Booking",
        "office": "Office Chair", "stationery": "Notebook Pack", "gambling": "Casino Chips",
        "financial_services": "Investment Plan",
    }
    LOW_RISK_MERCHANT_IDS = ["MER-001", "MER-002", "MER-003", "MER-004", "MER-005", "MER-008", "MER-009"]
    RISKY_MERCHANT_IDS = ["MER-006", "MER-007", "MER-010"]

    random.seed(7)
    count = 0
    BATCH_SIZE = 8  # one simulated calendar day per BATCH_SIZE transactions
    for a in AGENTS:
        agent_categories = a["allowed_categories"]
        agent_row = db.query(models.Agent).filter(models.Agent.id == a["id"]).first()
        day_index = -1
        for i in range(35):
            if i % BATCH_SIZE == 0:
                # simulate the start of a new business day: reset the running
                # daily spend AND backdate created_at so the Policy Simulator's
                # per-day budget replay (grouped by calendar date) matches how
                # this history was generated, instead of every transaction
                # landing on "today" and looking like one massive spend spike
                agent_row.daily_spent = 0.0
                db.commit()
                day_index += 1
            # +2 day floor so even the most recent simulated batch stays
            # outside the live engine's recent_hour/recent_day velocity
            # windows (app.engine.evaluate) — otherwise a fixture evaluated
            # shortly after seeding would see inflated same-agent velocity
            # from this backfilled history and get misread as anomalous.
            sim_day = datetime.utcnow() - timedelta(days=2 + (35 // BATCH_SIZE - day_index) * 2)
            roll = random.random()
            if roll < 0.75:
                category = random.choice(agent_categories)
                product = PRODUCTS.get(category, "General Item")
                amount = round(a["max_transaction"] * random.uniform(0.1, 0.85), 2)
                merchant_id = random.choice(LOW_RISK_MERCHANT_IDS)
                intent = f"Buy {product.lower()} under {int(a['max_transaction'])}"
            elif roll < 0.85:
                category = random.choice(agent_categories)
                product = PRODUCTS.get(category, "General Item")
                amount = round(a["max_transaction"] * random.uniform(0.9, 1.4), 2)
                merchant_id = random.choice(LOW_RISK_MERCHANT_IDS)
                intent = f"Buy {product.lower()}"
            elif roll < 0.93:
                category = random.choice(a["blocked_categories"] or ["gambling"])
                product = PRODUCTS.get(category, "Restricted Item")
                amount = round(a["max_transaction"] * random.uniform(0.1, 0.6), 2)
                merchant_id = random.choice(LOW_RISK_MERCHANT_IDS)
                intent = "Buy groceries for the week"
            else:
                category = random.choice(agent_categories)
                product = PRODUCTS.get(category, "General Item")
                amount = round(a["max_transaction"] * random.uniform(0.1, 0.5), 2)
                merchant_id = random.choice(RISKY_MERCHANT_IDS)
                intent = f"Buy {product.lower()}"

            req = schemas.TransactionEvaluateRequest(
                agent_id=a["id"], amount=amount, currency="INR", merchant_id=merchant_id,
                category=category, product=product, user_intent=intent,
            )
            try:
                result = evaluate(req, db, execute_payment=False)
                txn = db.query(models.Transaction).filter(models.Transaction.id == result.transaction_id).first()
                txn.created_at = sim_day + timedelta(minutes=(i % BATCH_SIZE) * 17, hours=random.randint(0, 6))
                db.commit()
                count += 1
            except Exception:
                pass
    return count


def _seed_upsell_history(db: Session) -> int:
    if db.query(models.Transaction).filter(models.Transaction.is_upsell == True).first():  # noqa: E712
        return -1  # already present

    from app import schemas
    from app.engine import evaluate
    from app.upsell_agent import propose_upsell

    def _backdate(txn_id, days_ago, minute_offset):
        t = db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()
        t.created_at = datetime.utcnow() - timedelta(days=days_ago) + timedelta(minutes=minute_offset)
        db.commit()

    upsell_count = 0
    agent_row = db.query(models.Agent).filter(models.Agent.id == "AGT-001").first()
    agent_row.daily_spent = 0.0
    db.commit()

    for i in range(6):
        original_amount = round(4000 * random.uniform(0.5, 0.97), 2)
        original_req = schemas.TransactionEvaluateRequest(
            agent_id="AGT-001", amount=original_amount, currency="INR", merchant_id="MER-001",
            category="sports", product="Nike Running Shoes",
            user_intent="Buy running shoes under 5000",
        )
        try:
            original_result = evaluate(original_req, db, execute_payment=False)
        except Exception:
            continue
        _backdate(original_result.transaction_id, days_ago=3, minute_offset=i * 5)
        if original_result.decision.value != "ALLOW":
            continue

        original_txn = db.query(models.Transaction).filter(models.Transaction.id == original_result.transaction_id).first()
        candidate = propose_upsell(agent_row, original_txn)
        if not candidate:
            continue
        upsell_req = schemas.TransactionEvaluateRequest(
            agent_id="AGT-001", amount=candidate["amount"], currency="INR", merchant_id=candidate["merchant_id"],
            category=candidate["category"], product=candidate["product"],
            user_intent=original_txn.user_intent,
            is_upsell=True, upsell_of_transaction_id=original_txn.id,
        )
        try:
            upsell_result = evaluate(upsell_req, db, execute_payment=False)
            _backdate(upsell_result.transaction_id, days_ago=3, minute_offset=i * 5 + 2)
            upsell_count += 1
        except Exception:
            pass

    for i in range(2):
        manipulated_req = schemas.TransactionEvaluateRequest(
            agent_id="AGT-001", amount=14999, currency="INR", merchant_id="MER-001",
            category="insurance", product="Premium Protection Plan",
            user_intent="Buy running shoes under 5000",
            is_upsell=True,
        )
        try:
            manipulated_result = evaluate(manipulated_req, db, execute_payment=False)
            _backdate(manipulated_result.transaction_id, days_ago=3, minute_offset=30 + i * 5)
            upsell_count += 1
        except Exception:
            pass

    return upsell_count


def run_seed(db: Session) -> dict:
    _seed_agents_and_merchants(db)
    txn_count = _seed_transaction_history(db)
    upsell_count = _seed_upsell_history(db)
    return {
        "agents": len(AGENTS),
        "merchants": len(MERCHANTS),
        "transactions_seeded": txn_count if txn_count >= 0 else "already present",
        "upsell_transactions_seeded": upsell_count if upsell_count >= 0 else "already present",
    }
