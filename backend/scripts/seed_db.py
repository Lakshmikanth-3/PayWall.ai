"""
Seed script — creates demo agents, merchants and runs ~200 test
transactions to populate the dashboard with realistic data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import random
from datetime import date

from app.database import SessionLocal, engine
from app import models

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ── Seed agents ──────────────────────────────────────────────────────────────
AGENTS = [
    {
        "id": "AGT-001",
        "name": "Shopping Assistant",
        "owner_id": "USR-001",
        "max_transaction": 5000,
        "daily_limit": 10000,
        "allowed_categories": ["food", "groceries", "sports", "electronics"],
        "blocked_categories": ["gambling", "financial_services"],
        "requires_approval_above": 3000,
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

for a in AGENTS:
    if not db.query(models.Agent).filter(models.Agent.id == a["id"]).first():
        db.add(models.Agent(
            id=a["id"],
            name=a["name"],
            owner_id=a["owner_id"],
            max_transaction=a["max_transaction"],
            daily_limit=a["daily_limit"],
            allowed_categories=a["allowed_categories"],
            blocked_categories=a["blocked_categories"],
            requires_approval_above=a["requires_approval_above"],
            last_reset_date=date.today().isoformat(),
        ))

# ── Seed merchants ────────────────────────────────────────────────────────────
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

for m in MERCHANTS:
    if not db.query(models.Merchant).filter(models.Merchant.id == m["id"]).first():
        risk = m.get("risk_score", 20)
        db.add(models.Merchant(
            id=m["id"],
            name=m["name"],
            category=m["category"],
            risk_score=risk,
            risk_level="LOW" if risk <= 30 else ("MEDIUM" if risk <= 70 else "HIGH"),
            age_days=m.get("age_days", 365),
            refund_rate=m.get("refund_rate", 0.02),
            chargeback_rate=m.get("chargeback_rate", 0.01),
            failed_payment_rate=m.get("failed_payment_rate", 0.03),
        ))

db.commit()
print("[OK] Seeded agents and merchants successfully.")
print(f"   Agents: {len(AGENTS)}")
print(f"   Merchants: {len(MERCHANTS)}")
db.close()
