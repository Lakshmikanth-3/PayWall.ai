"""
Synthetic dataset generator — PRD Section 18.

Generates ~100,000 labeled synthetic transactions across the recommended
distribution (70k normal / 10k budget violations / 5k category violations /
5k intent mismatches / 4k suspicious merchants / 3k anomalous behavior /
2k velocity-duplicate anomalies / 1k mixed attacks), then writes a
stratified 80/20 train/holdout split.

This dataset lives entirely as offline CSV files under backend/data/ — it is
NOT loaded into the live application database. It exists purely to compute
real precision/recall/F1/ROC-AUC/money-protected numbers (see
evaluate_dataset.py) against a held-out set, instead of relying on whatever
happens to be in the demo DB.

The held-out split (dataset_holdout.csv) must never be used to tune
thresholds or retrain the risk model — only to report final numbers.

Usage:
    python scripts/generate_dataset.py
"""

import csv
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SEED = 42
rng = random.Random(SEED)

TOTAL = 100_000
DISTRIBUTION = {
    "normal": 70_000,
    "budget_violation": 10_000,
    "category_violation": 5_000,
    "intent_mismatch": 5_000,
    "suspicious_merchant": 4_000,
    "anomalous_behavior": 3_000,
    "velocity_duplicate": 2_000,
    "mixed_attack": 1_000,
}
assert sum(DISTRIBUTION.values()) == TOTAL

CATEGORIES = ["food", "groceries", "sports", "electronics", "travel", "hotel",
              "office", "stationery", "fashion", "beauty", "books", "gaming"]
RESTRICTED_CATEGORIES = ["gambling", "financial_services", "insurance", "crypto"]

PRODUCTS_BY_CATEGORY = {
    "food": ["Pizza Order", "Biryani Combo", "Cafe Latte", "Grocery Snack Pack"],
    "groceries": ["Monthly Grocery Pack", "Vegetable Basket", "Rice 10kg Bag", "Dairy Combo"],
    "sports": ["Nike Running Shoes", "Yoga Mat", "Cricket Bat", "Gym Gloves"],
    "electronics": ["USB Hub", "Laptop Stand", "Wireless Mouse", "Bluetooth Speaker"],
    "travel": ["Flight Ticket", "Airport Shuttle", "Bus Pass", "Train Ticket"],
    "hotel": ["Hotel Booking", "Resort Stay", "Homestay Booking", "Hostel Bed"],
    "office": ["Office Chair", "Desk Organizer", "Printer Paper", "Whiteboard Markers"],
    "stationery": ["Notebook Pack", "Pen Set", "Sticky Notes", "Highlighters"],
    "fashion": ["Cotton T-Shirt", "Denim Jacket", "Running Shorts", "Sneakers"],
    "beauty": ["Face Wash", "Sunscreen SPF50", "Moisturizer", "Lip Balm"],
    "books": ["Fiction Novel", "Textbook", "Comic Book", "Cookbook"],
    "gaming": ["Game Controller", "Gaming Headset", "Gift Card", "Mouse Pad"],
    "gambling": ["Casino Chips Bundle", "Bet Credits"],
    "financial_services": ["Personal Loan Fee", "Investment Plan"],
    "insurance": ["Premium Protection Plan", "Extended Warranty Plan"],
    "crypto": ["Crypto Top-up", "Token Purchase"],
}

INTENT_TEMPLATES = [
    "Buy {product} under {budget}",
    "Order {product} for me",
    "I need {product}, keep it under {budget}",
    "Get me some {product}",
    "Purchase {product} today",
]

MISMATCHED_INTENTS = [
    "Buy running shoes under 5000",
    "Order a grocery pack for the week",
    "Book a flight to Delhi under 8000",
    "Get me a birthday gift under 2000",
    "I need a new phone charger",
    "Order dinner for tonight",
]


def make_agents(n=60):
    agents = []
    for i in range(n):
        max_txn = rng.choice([1000, 2000, 3000, 5000, 8000, 10000, 20000, 30000])
        daily_limit = max_txn * rng.choice([2, 3, 4, 5])
        allowed = rng.sample(CATEGORIES, k=rng.randint(3, 6))
        blocked = rng.sample(RESTRICTED_CATEGORIES, k=rng.randint(1, len(RESTRICTED_CATEGORIES)))
        agents.append({
            "id": f"SYN-AGT-{i:04d}",
            "max_transaction": max_txn,
            "daily_limit": daily_limit,
            "allowed_categories": allowed,
            "blocked_categories": blocked,
            "requires_approval_above": round(max_txn * 0.6),
            "status": "ACTIVE",
            "payment_enabled": True,
        })
    return agents


def make_merchants(n=250):
    merchants = []
    for i in range(n):
        tier = rng.choices(["low", "medium", "high"], weights=[0.75, 0.15, 0.10])[0]
        if tier == "low":
            risk_score = rng.uniform(0, 30)
            age_days = rng.randint(180, 6000)
            refund, chargeback, failed = rng.uniform(0, 0.03), rng.uniform(0, 0.01), rng.uniform(0, 0.02)
        elif tier == "medium":
            risk_score = rng.uniform(31, 70)
            age_days = rng.randint(30, 200)
            refund, chargeback, failed = rng.uniform(0.03, 0.1), rng.uniform(0.01, 0.05), rng.uniform(0.02, 0.08)
        else:
            risk_score = rng.uniform(71, 100)
            age_days = rng.randint(1, 45)
            refund, chargeback, failed = rng.uniform(0.1, 0.3), rng.uniform(0.05, 0.2), rng.uniform(0.08, 0.25)
        merchants.append({
            "id": f"SYN-MER-{i:04d}",
            "risk_score": round(risk_score, 1),
            "age_days": age_days,
            "refund_rate": round(refund, 4),
            "chargeback_rate": round(chargeback, 4),
            "failed_payment_rate": round(failed, 4),
            "is_blocked": False,
            "tier": tier,
        })
    return merchants


AGENTS = make_agents()
MERCHANTS = make_merchants()
LOW_RISK_MERCHANTS = [m for m in MERCHANTS if m["tier"] == "low"]
HIGH_RISK_MERCHANTS = [m for m in MERCHANTS if m["tier"] == "high"]

BASE_TIME = datetime(2026, 8, 1)


def random_timestamp():
    return BASE_TIME + timedelta(
        days=rng.randint(0, 30), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
    )


def make_intent(product, budget, matching=True):
    if matching:
        template = rng.choice(INTENT_TEMPLATES)
        return template.format(product=product.lower(), budget=int(budget))
    return rng.choice(MISMATCHED_INTENTS)


def row(scenario_type, is_risky, agent, merchant, amount, category, product,
        user_intent, daily_spent_before, txn_hour=0, txn_day=1, merchant_blocked=False):
    return {
        "transaction_id": f"SYN-{scenario_type[:4].upper()}-{rng.randint(0, 10**9):09d}",
        "scenario_type": scenario_type,
        "is_risky": int(is_risky),
        "agent_id": agent["id"],
        "agent_max_transaction": agent["max_transaction"],
        "agent_daily_limit": agent["daily_limit"],
        "agent_daily_spent_before": round(daily_spent_before, 2),
        "agent_allowed_categories": "|".join(agent["allowed_categories"]),
        "agent_blocked_categories": "|".join(agent["blocked_categories"]),
        "agent_requires_approval_above": agent["requires_approval_above"],
        "agent_status": agent["status"],
        "agent_payment_enabled": agent["payment_enabled"],
        "merchant_id": merchant["id"],
        "merchant_risk_score": merchant["risk_score"],
        "merchant_age_days": merchant["age_days"],
        "merchant_refund_rate": merchant["refund_rate"],
        "merchant_chargeback_rate": merchant["chargeback_rate"],
        "merchant_failed_payment_rate": merchant["failed_payment_rate"],
        "merchant_is_blocked": merchant_blocked,
        "amount": round(amount, 2),
        "currency": "INR",
        "category": category,
        "product": product,
        "user_intent": user_intent,
        "txn_count_last_hour": txn_hour,
        "txn_count_last_day": txn_day,
        "created_at": random_timestamp().isoformat(),
    }


def gen_normal(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(LOW_RISK_MERCHANTS)
        category = rng.choice(agent["allowed_categories"])
        product = rng.choice(PRODUCTS_BY_CATEGORY[category])
        amount = agent["max_transaction"] * rng.uniform(0.1, 0.85)
        daily_spent = rng.uniform(0, agent["daily_limit"] - amount - agent["max_transaction"] * 0.1)
        daily_spent = max(0, daily_spent)
        intent = make_intent(product, agent["max_transaction"], matching=True)
        rows.append(row("normal", False, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(0, 2), txn_day=rng.randint(1, 8)))
    return rows


def gen_budget_violation(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(LOW_RISK_MERCHANTS)
        category = rng.choice(agent["allowed_categories"])
        product = rng.choice(PRODUCTS_BY_CATEGORY[category])
        amount = agent["max_transaction"] * rng.uniform(0.2, 0.7)
        # daily_spent_before is deliberately close to the limit so this push exceeds it
        daily_spent = agent["daily_limit"] - amount * rng.uniform(0.1, 0.6)
        intent = make_intent(product, agent["max_transaction"], matching=True)
        rows.append(row("budget_violation", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(0, 3), txn_day=rng.randint(2, 10)))
    return rows


def gen_category_violation(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(LOW_RISK_MERCHANTS)
        category = rng.choice(agent["blocked_categories"] or RESTRICTED_CATEGORIES)
        product = rng.choice(PRODUCTS_BY_CATEGORY.get(category, ["Restricted Item"]))
        amount = agent["max_transaction"] * rng.uniform(0.1, 0.6)
        daily_spent = rng.uniform(0, agent["daily_limit"] * 0.3)
        intent = make_intent(product, agent["max_transaction"], matching=True)
        rows.append(row("category_violation", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(0, 2), txn_day=rng.randint(1, 5)))
    return rows


def gen_intent_mismatch(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(LOW_RISK_MERCHANTS)
        category = rng.choice(agent["allowed_categories"] + RESTRICTED_CATEGORIES[:1])
        product = rng.choice(PRODUCTS_BY_CATEGORY[category])
        amount = agent["max_transaction"] * rng.uniform(0.5, 1.0)
        daily_spent = rng.uniform(0, agent["daily_limit"] * 0.3)
        intent = make_intent(product, agent["max_transaction"], matching=False)
        rows.append(row("intent_mismatch", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(0, 2), txn_day=rng.randint(1, 5)))
    return rows


def gen_suspicious_merchant(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(HIGH_RISK_MERCHANTS)
        category = rng.choice(agent["allowed_categories"])
        product = rng.choice(PRODUCTS_BY_CATEGORY[category])
        amount = agent["max_transaction"] * rng.uniform(0.1, 0.7)
        daily_spent = rng.uniform(0, agent["daily_limit"] * 0.3)
        intent = make_intent(product, agent["max_transaction"], matching=True)
        rows.append(row("suspicious_merchant", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(0, 2), txn_day=rng.randint(1, 5)))
    return rows


def gen_anomalous_behavior(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(LOW_RISK_MERCHANTS + [m for m in MERCHANTS if m["tier"] == "medium"])
        category = rng.choice(agent["allowed_categories"])
        product = rng.choice(PRODUCTS_BY_CATEGORY[category])
        # amount right at the edge of the limit — a sharp deviation from typical spend
        amount = agent["max_transaction"] * rng.uniform(0.9, 1.0)
        daily_spent = rng.uniform(0, agent["daily_limit"] * 0.2)
        intent = make_intent(product, agent["max_transaction"], matching=True)
        rows.append(row("anomalous_behavior", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(0, 1), txn_day=rng.randint(1, 3)))
    return rows


def gen_velocity_duplicate(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(LOW_RISK_MERCHANTS)
        category = rng.choice(agent["allowed_categories"])
        product = rng.choice(PRODUCTS_BY_CATEGORY[category])
        amount = agent["max_transaction"] * rng.uniform(0.1, 0.5)
        daily_spent = rng.uniform(0, agent["daily_limit"] * 0.3)
        intent = make_intent(product, agent["max_transaction"], matching=True)
        rows.append(row("velocity_duplicate", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(6, 15), txn_day=rng.randint(15, 40)))
    return rows


def gen_mixed_attack(count):
    rows = []
    for _ in range(count):
        agent = rng.choice(AGENTS)
        merchant = rng.choice(HIGH_RISK_MERCHANTS)
        category = rng.choice(agent["blocked_categories"] or RESTRICTED_CATEGORIES)
        product = rng.choice(PRODUCTS_BY_CATEGORY.get(category, ["Restricted Item"]))
        amount = agent["max_transaction"] * rng.uniform(0.9, 2.5)
        daily_spent = agent["daily_limit"] * rng.uniform(0.5, 0.95)
        intent = make_intent(product, agent["max_transaction"], matching=False)
        rows.append(row("mixed_attack", True, agent, merchant, amount, category, product,
                         intent, daily_spent, txn_hour=rng.randint(4, 12), txn_day=rng.randint(10, 30)))
    return rows


GENERATORS = {
    "normal": gen_normal,
    "budget_violation": gen_budget_violation,
    "category_violation": gen_category_violation,
    "intent_mismatch": gen_intent_mismatch,
    "suspicious_merchant": gen_suspicious_merchant,
    "anomalous_behavior": gen_anomalous_behavior,
    "velocity_duplicate": gen_velocity_duplicate,
    "mixed_attack": gen_mixed_attack,
}

FIELDNAMES = [
    "transaction_id", "scenario_type", "is_risky",
    "agent_id", "agent_max_transaction", "agent_daily_limit", "agent_daily_spent_before",
    "agent_allowed_categories", "agent_blocked_categories", "agent_requires_approval_above",
    "agent_status", "agent_payment_enabled",
    "merchant_id", "merchant_risk_score", "merchant_age_days", "merchant_refund_rate",
    "merchant_chargeback_rate", "merchant_failed_payment_rate", "merchant_is_blocked",
    "amount", "currency", "category", "product", "user_intent",
    "txn_count_last_hour", "txn_count_last_day", "created_at",
]


def main():
    all_rows = []
    train_rows = []
    holdout_rows = []

    for scenario_type, count in DISTRIBUTION.items():
        rows = GENERATORS[scenario_type](count)
        rng.shuffle(rows)
        split_idx = int(len(rows) * 0.8)
        train_rows.extend(rows[:split_idx])
        holdout_rows.extend(rows[split_idx:])
        all_rows.extend(rows)
        print(f"  {scenario_type:22s} {count:>6d} rows  (train={split_idx}, holdout={len(rows) - split_idx})")

    rng.shuffle(all_rows)
    rng.shuffle(train_rows)
    rng.shuffle(holdout_rows)

    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(os.path.join(DATA_DIR, "dataset_full.csv"), all_rows)
    write_csv(os.path.join(DATA_DIR, "dataset_train.csv"), train_rows)
    write_csv(os.path.join(DATA_DIR, "dataset_holdout.csv"), holdout_rows)

    print(f"\n[OK] Generated {len(all_rows)} synthetic transactions (seed={SEED})")
    print(f"     Train:   {len(train_rows)} -> backend/data/dataset_train.csv")
    print(f"     Holdout: {len(holdout_rows)} -> backend/data/dataset_holdout.csv (never tune against this)")


if __name__ == "__main__":
    main()
