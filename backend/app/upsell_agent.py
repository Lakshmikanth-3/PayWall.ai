"""
Upsell Agent — PRD Section 2a "Revenue Growth Layer".

Proposes ONE relevant, budget-aware add-on based on a just-completed purchase
and the agent's remaining daily budget — the same kind of suggestion a good
in-store salesperson makes. The proposal itself carries no special authority:
routers/transactions.py runs it through the exact same app.engine.evaluate()
pipeline as any other transaction (identity, intent match, policy, risk).

This module only decides WHAT to propose (product + price) and whether a fit
exists at all. It never decides ALLOW/REVIEW/BLOCK — that's the Guard's job.
"""

from typing import Optional
from app import models

# Complementary add-ons per category, ordered cheapest-first so the agent
# proposes the smallest fitting item rather than maxing out the remaining
# budget. Prices are illustrative, in the same spirit as the PRD's own
# "Moisture-wicking running socks, ₹149" example for a running-shoes purchase.
UPSELL_CATALOG = {
    "sports": [
        {"product": "Moisture-wicking Running Socks", "amount": 149},
        {"product": "Sports Water Bottle", "amount": 299},
    ],
    "electronics": [
        {"product": "USB-C Charging Cable", "amount": 199},
        {"product": "Screen Protector", "amount": 249},
    ],
    "groceries": [
        {"product": "Reusable Grocery Bag", "amount": 99},
        {"product": "Kitchen Roll 2-Pack", "amount": 179},
    ],
    "food": [
        {"product": "Add a Dessert", "amount": 129},
        {"product": "Add a Beverage", "amount": 89},
    ],
    "travel": [
        {"product": "Travel Neck Pillow", "amount": 349},
    ],
    "hotel": [
        {"product": "Late Checkout Add-on", "amount": 499},
    ],
    "office": [
        {"product": "Desk Organizer", "amount": 249},
    ],
    "stationery": [
        {"product": "Highlighter 5-Pack", "amount": 149},
    ],
    "fashion": [
        {"product": "Cotton Socks 3-Pack", "amount": 179},
    ],
    "beauty": [
        {"product": "Travel-size Sunscreen", "amount": 159},
    ],
    "books": [
        {"product": "Bookmark Set", "amount": 99},
    ],
    "gaming": [
        {"product": "Mouse Pad", "amount": 199},
    ],
}


def propose_upsell(agent: models.Agent, original_txn: models.Transaction) -> Optional[dict]:
    """
    Returns a candidate {product, category, amount, merchant_id} for the
    given already-ALLOWed transaction, or None if nothing fits.

    A candidate only qualifies if it fits within BOTH the agent's remaining
    daily budget and its per-transaction max — i.e. the Upsell Agent never
    proposes something the Guard would obviously reject on budget grounds
    alone. It can still fail intent/risk checks (that's the Guard's job, not
    this module's).
    """
    candidates = UPSELL_CATALOG.get(original_txn.category.lower(), [])
    if not candidates:
        return None

    remaining_budget = max(0.0, (agent.daily_limit or 0) - (agent.daily_spent or 0))

    fitting = [
        c for c in candidates
        if c["amount"] <= remaining_budget and c["amount"] <= (agent.max_transaction or 0)
    ]
    if not fitting:
        return None

    # Prefer the largest item that still fits comfortably within budget —
    # more incremental revenue without exceeding what the user authorized.
    best = max(fitting, key=lambda c: c["amount"])
    return {
        "product": best["product"],
        "category": original_txn.category,
        "amount": best["amount"],
        "merchant_id": original_txn.merchant_id,
    }
