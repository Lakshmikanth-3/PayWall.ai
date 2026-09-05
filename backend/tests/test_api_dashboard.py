"""GET /dashboard/* — stats, metrics, revenue-impact, live, audit."""

import pytest


@pytest.fixture
def seeded(client):
    agent = client.post("/agents", json={
        "name": "Shopping Assistant", "max_transaction": 5000, "daily_limit": 10000,
        "allowed_categories": ["sports", "electronics"], "blocked_categories": ["gambling"],
        "requires_approval_above": 4900,
    }).json()
    merchant = client.post("/merchants", json={
        "name": "Nike", "category": "sports", "risk_score": 8, "age_days": 3650,
    }).json()

    allowed = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Wireless Mouse",
        "user_intent": "Buy wireless mouse electronics today",
    }).json()
    blocked = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 14999, "currency": "INR", "merchant_id": merchant["id"],
        "category": "insurance", "product": "Premium Protection Plan",
        "user_intent": "Buy running shoes under 5000", "is_upsell": True,
    }).json()
    return agent, merchant, allowed, blocked


def test_stats_reflects_seeded_transactions(client, seeded):
    r = client.get("/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_evaluated"] == 2
    assert data["total_allowed"] == 1
    assert data["total_blocked"] == 1


def test_stats_empty_state(client):
    r = client.get("/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_evaluated"] == 0


def test_metrics_empty_state_does_not_crash(client):
    r = client.get("/dashboard/metrics")
    assert r.status_code == 200
    assert r.json()["precision"] == 0


def test_metrics_with_data(client, seeded):
    r = client.get("/dashboard/metrics")
    assert r.status_code == 200
    data = r.json()
    assert 0 <= data["precision"] <= 1
    assert 0 <= data["recall"] <= 1


def test_revenue_impact_tracks_upsell_transactions(client, seeded):
    r = client.get("/dashboard/revenue-impact")
    assert r.status_code == 200
    data = r.json()
    assert data["upsells_proposed"] == 1
    assert data["upsells_blocked"] == 1
    assert data["upsells_allowed"] == 0
    assert data["manipulative_exposure_blocked"] == 14999.0


def test_revenue_impact_empty_state(client):
    r = client.get("/dashboard/revenue-impact")
    data = r.json()
    assert data["upsells_proposed"] == 0
    assert data["upsell_acceptance_rate"] == 0.0


def test_live_feed_returns_recent_transactions(client, seeded):
    r = client.get("/dashboard/live?limit=10")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_audit_search_by_decision(client, seeded):
    r = client.get("/dashboard/audit?decision=BLOCK")
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert results[0]["decision"] == "BLOCK"


def test_audit_search_by_txn_id(client, seeded):
    _, _, allowed, _ = seeded
    r = client.get(f"/dashboard/audit?txn_id={allowed['transaction_id']}")
    assert len(r.json()) == 1


def test_llm_toggle_and_status(client):
    r = client.post("/dashboard/llm-toggle", params={"disabled": True})
    assert r.status_code == 200
    assert r.json()["llm_disabled"] is True

    status = client.get("/dashboard/llm-status")
    assert status.json()["llm_disabled"] is True

    client.post("/dashboard/llm-toggle", params={"disabled": False})
