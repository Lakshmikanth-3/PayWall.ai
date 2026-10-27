"""Local demo catalog → agent proposal → existing Guard, with no direct payments."""

import re
import math
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app import engine, models, schemas
from app.database import get_db
from app.ml.intent_matcher import choose_catalog_item, keyword_intent_match

router = APIRouter(prefix="/agent", tags=["shopping agent"])

# Illustrative local prices, linked to the existing seeded merchant IDs.
# These are development data, not live merchant inventory.
CATALOG = {
    "running-shoes": {"product": "Running Shoes", "category": "sports", "amount": 4799, "merchant_id": "MER-001"},
    "road-shoes": {"product": "Lightweight Road Running Shoes", "category": "sports", "amount": 3999, "merchant_id": "MER-008"},
    "running-socks": {"product": "Running Socks", "category": "sports", "amount": 149, "merchant_id": "MER-001"},
    "water-bottle": {"product": "Sports Water Bottle", "category": "sports", "amount": 299, "merchant_id": "MER-008"},
    "headphones": {"product": "Wireless Headphones", "category": "electronics", "amount": 2499, "merchant_id": "MER-002"},
    "charger": {"product": "Phone Charger", "category": "electronics", "amount": 799, "merchant_id": "MER-002"},
    "laptop-bag": {"product": "Waterproof Laptop Bag", "category": "electronics", "amount": 1799, "merchant_id": "MER-009"},
    "mouse": {"product": "Wireless Mouse", "category": "electronics", "amount": 599, "merchant_id": "MER-009"},
    "keyboard": {"product": "USB Keyboard", "category": "electronics", "amount": 999, "merchant_id": "MER-002"},
    "groceries": {"product": "Weekly Grocery Pack", "category": "groceries", "amount": 899, "merchant_id": "MER-003"},
    "fruit": {"product": "Fresh Fruit Basket", "category": "groceries", "amount": 499, "merchant_id": "MER-003"},
    "rice": {"product": "Rice Bag", "category": "groceries", "amount": 699, "merchant_id": "MER-003"},
    "pizza": {"product": "Vegetable Pizza", "category": "food", "amount": 349, "merchant_id": "MER-005"},
    "lunch": {"product": "Lunch Bowl", "category": "food", "amount": 249, "merchant_id": "MER-005"},
    "flight": {"product": "Domestic Flight Ticket", "category": "travel", "amount": 7999, "merchant_id": "MER-004"},
}


class ShopRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=100)
    user_intent: str = Field(min_length=3, max_length=2000, pattern=r"\S")


class ShopResponse(BaseModel):
    intent: str
    agent_proposal: dict
    agent_reasoning: str
    model: str
    guard_model: str
    decision: schemas.Decision
    risk_score: float
    intent_score: float
    reasons: list[str]
    transaction_id: str


def propose_purchase(intent: str, candidates: list):
    result = choose_catalog_item(intent, candidates, "Choose the closest match to the user's purchase request and budget.")
    if result:
        return result
    best = max(candidates, key=lambda c: keyword_intent_match(intent, c["product"], c["category"], c["amount"], 0))
    return dict(best), "Keyword match from the local development catalog; Guard verification required.", "rules_only"


@router.post("/shop", response_model=ShopResponse)
def shop(payload: ShopRequest, db: Session = Depends(get_db)):
    agent = db.get(models.Agent, payload.agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    # Parse explicit numeric budget deterministically; the model cannot raise it.
    budget_match = re.search(r"(?:under|below|up to|budget(?: of)?)\s*(?:₹|rs\.?|inr)?\s*([+-]?[\d,]+(?:\.\d+)?)", payload.user_intent, re.I)
    try:
        budget = float(budget_match.group(1).replace(",", "")) if budget_match else agent.max_transaction
    except ValueError:
        raise HTTPException(422, "Purchase budget must be a positive finite amount")
    if not math.isfinite(budget) or budget <= 0:
        raise HTTPException(422, "Purchase budget must be a positive finite amount")
    candidates = [
        {"product_id": pid, **item, "currency": "INR"}
        for pid, item in CATALOG.items()
        if item["amount"] <= budget and db.get(models.Merchant, item["merchant_id"]) is not None
    ]
    if not candidates:
        raise HTTPException(422, "No local catalog product fits this budget and the available merchants. Seed the demo database first.")
    proposed, reasoning, model = propose_purchase(payload.user_intent, candidates)
    # Rehydrate all financial fields from server data, even if a model invents them.
    trusted = next((c for c in candidates if c["product_id"] == proposed.get("product_id")), None)
    if trusted is None:
        raise HTTPException(422, "Agent selected a product outside the eligible catalog")
    result = engine.evaluate(schemas.TransactionEvaluateRequest(
        agent_id=payload.agent_id, user_intent=payload.user_intent,
        **{k: trusted[k] for k in ("product", "category", "amount", "merchant_id", "currency")},
    ), db, execute_payment=False)
    # Shopping is a proposal/authorization demo; explicit payment confirmation stays
    # outside this new endpoint. No Razorpay call is made by /agent/shop.
    db.add(models.AuditLog(
        id=f"AUD-{uuid.uuid4().hex[:8].upper()}", transaction_id=result.transaction_id,
        event_type="SHOPPING_PROPOSAL", payload={
            "model": model, "product_id": trusted["product_id"],
            "reasoning": reasoning, "catalog_source": "local_demo",
        },
    ))
    db.commit()
    return ShopResponse(
        intent=payload.user_intent, agent_proposal=trusted, agent_reasoning=reasoning,
        model=model, guard_model=result.model, decision=result.decision,
        risk_score=result.risk_score, intent_score=result.intent_match_score,
        reasons=[*result.policy_violations, result.reason], transaction_id=result.transaction_id,
    )
