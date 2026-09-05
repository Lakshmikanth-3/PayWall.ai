"""PRD Section 26 — Policy Simulator (app/simulator.py, POST /agents/{id}/simulate-policy)."""

from datetime import datetime

import pytest

from app import models


@pytest.fixture
def agent_with_history(client):
    agent = client.post("/agents", json={
        "name": "Shopping Assistant", "max_transaction": 2000, "daily_limit": 4000,
        "allowed_categories": ["sports"], "blocked_categories": [],
        "requires_approval_above": 0,
    }).json()
    merchant = client.post("/merchants", json={
        "name": "Nike", "category": "sports", "risk_score": 8, "age_days": 3650,
    }).json()

    # This exceeds the CURRENT 2000 max_transaction -> BLOCK today.
    client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 2500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Running Shoes", "user_intent": "Buy running shoes",
    })
    return agent, merchant


def test_simulate_raising_max_transaction_flips_block_to_allow(client, db_session):
    agent = client.post("/agents", json={
        "name": "Shopping Assistant", "max_transaction": 2000, "daily_limit": 4000,
        "allowed_categories": ["sports"], "blocked_categories": [],
        "requires_approval_above": 0,
    }).json()
    merchant = client.post("/merchants", json={
        "name": "Nike", "category": "sports", "risk_score": 8, "age_days": 3650,
    }).json()
    # simulator.py reuses each transaction's already-stored risk_score
    # as-is (a documented simplification — see its module docstring), so
    # this inserts one directly with a controlled low risk_score: the point
    # under test is the POLICY-dependent re-evaluation (amount vs.
    # max_transaction), not the ML model's exact output for hand-picked
    # amounts, which test_engine_evaluate.py already covers via mocking.
    txn = models.Transaction(
        id="TXN-SIM01", decision_id="DEC-SIM01", agent_id=agent["id"], user_id="USR-1",
        merchant_id=merchant["id"], merchant_name=merchant["name"], amount=2500, currency="INR",
        category="sports", product="Running Shoes", user_intent="Buy running shoes",
        decision="BLOCK", risk_score=5.0, intent_match_score=0.9,
        policy_violations=["Amount ₹2,500 exceeds max transaction ₹2,000"],
        requires_human_review=False, created_at=datetime.utcnow(),
    )
    db_session.add(txn)
    db_session.commit()

    r = client.post(f"/agents/{agent['id']}/simulate-policy", json={"max_transaction": 5000})
    assert r.status_code == 200
    data = r.json()
    assert data["transactions_analyzed"] == 1
    assert data["before"]["BLOCK"] == 1
    assert data["after"]["ALLOW"] == 1
    assert data["now_allowed_count"] == 1
    assert data["now_allowed_gmv"] == 2500.0
    assert data["flipped_transactions"][0] == {
        "transaction_id": "TXN-SIM01", "amount": 2500.0, "category": "sports",
        "product": "Running Shoes", "merchant_name": merchant["name"], "risk_score": 5.0,
        "before": "BLOCK", "after": "ALLOW",
    }


def test_simulate_with_no_changes_is_a_no_op(client, agent_with_history):
    agent, _ = agent_with_history
    r = client.post(f"/agents/{agent['id']}/simulate-policy", json={})
    data = r.json()
    assert data["now_allowed_count"] == 0
    assert data["now_blocked_count"] == 0
    assert data["before"] == data["after"]


def test_simulate_unknown_agent_404(client):
    r = client.post("/agents/AGT-NOPE/simulate-policy", json={"max_transaction": 5000})
    assert r.status_code == 404


def test_simulate_blocking_a_category_flips_allow_to_block(client, agent_with_history):
    agent, merchant = agent_with_history
    client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Socks", "user_intent": "Buy socks",
    })
    r = client.post(f"/agents/{agent['id']}/simulate-policy", json={"blocked_categories": ["sports"]})
    data = r.json()
    assert data["now_blocked_count"] >= 1
