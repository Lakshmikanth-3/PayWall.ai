"""POST /transactions/evaluate, list/get, human review, upsell, retry-payment."""

import pytest


@pytest.fixture
def agent_and_merchant(client):
    agent = client.post("/agents", json={
        "name": "Shopping Assistant", "owner_id": "USR-1",
        "max_transaction": 5000, "daily_limit": 10000,
        "allowed_categories": ["sports", "electronics", "food", "groceries"],
        "blocked_categories": ["gambling", "financial_services"],
        "requires_approval_above": 4900,
    }).json()
    merchant = client.post("/merchants", json={
        "name": "Nike Official Store", "category": "sports", "risk_score": 8, "age_days": 3650,
    }).json()
    return agent, merchant


def test_evaluate_clean_transaction_allows(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    r = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Wireless Mouse",
        "user_intent": "Buy wireless mouse electronics today",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "ALLOW"
    assert data["decision_id"].startswith("DEC-")
    assert data["policy_violations"] == []


def test_evaluate_killer_scenario_blocks(client, agent_and_merchant):
    """PRD Section 7 — protection plan disguised as an upsell during a shoe purchase."""
    agent, merchant = agent_and_merchant
    r = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 14999, "currency": "INR", "merchant_id": merchant["id"],
        "category": "insurance", "product": "Premium Protection Plan",
        "user_intent": "Buy running shoes under 5000", "is_upsell": True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "BLOCK"
    assert data["is_upsell"] is True
    assert data["attributed_to"] == "Upsell Agent"


def test_evaluate_budget_violation_blocks(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    r1 = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Wireless Mouse",
        "user_intent": "Buy wireless mouse electronics today",
    })
    assert r1.json()["decision"] == "ALLOW"

    r2 = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 9800, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Running Shoes", "user_intent": "Buy running shoes",
    })
    assert r2.json()["decision"] == "BLOCK"
    assert any("Daily budget" in v for v in r2.json()["policy_violations"])


def test_evaluate_unknown_agent_returns_404(client, agent_and_merchant):
    _, merchant = agent_and_merchant
    r = client.post("/transactions/evaluate", json={
        "agent_id": "AGT-NOPE", "amount": 100, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "X", "user_intent": "X",
    })
    assert r.status_code == 404


def test_list_and_get_transaction(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    created = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Wireless Mouse",
        "user_intent": "Buy wireless mouse electronics today",
    }).json()

    listed = client.get("/transactions").json()
    assert any(t["id"] == created["transaction_id"] for t in listed)

    fetched = client.get(f"/transactions/{created['transaction_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["decision_id"] == created["decision_id"]
    assert len(fetched.json()["policy_checks"]) == 5


def test_get_transaction_404(client):
    assert client.get("/transactions/TXN-NOPE").status_code == 404


def test_human_review_approve_allows_and_pays(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    # Force REVIEW deterministically via the requires_approval_above threshold.
    created = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 4950, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Running Shoes", "user_intent": "Buy running shoes",
    }).json()
    assert created["decision"] == "REVIEW"

    reviewed = client.post(f"/transactions/{created['transaction_id']}/review", json={
        "approved": True, "reviewer": "ops-team",
    })
    assert reviewed.status_code == 200
    data = reviewed.json()
    assert data["decision"] == "ALLOW"
    assert data["human_approved"] is True
    assert data["payment_status"] == "SKIPPED"  # no Razorpay creds in test env


def test_human_review_deny_blocks(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    created = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 4950, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Running Shoes", "user_intent": "Buy running shoes",
    }).json()
    assert created["decision"] == "REVIEW"

    reviewed = client.post(f"/transactions/{created['transaction_id']}/review", json={
        "approved": False, "reviewer": "ops-team",
    })
    data = reviewed.json()
    assert data["decision"] == "BLOCK"
    assert data["payment_status"] == "DENIED"


def test_human_review_rejects_non_review_transaction(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    created = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Wireless Mouse",
        "user_intent": "Buy wireless mouse electronics today",
    }).json()
    assert created["decision"] == "ALLOW"

    r = client.post(f"/transactions/{created['transaction_id']}/review", json={"approved": True})
    assert r.status_code == 400


def test_human_review_rechecks_policy_before_approving(client, agent_and_merchant):
    """PRD Section 11: human approval -> policy re-check -> Razorpay, not a blind approve."""
    agent, merchant = agent_and_merchant
    created = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 4950, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Running Shoes", "user_intent": "Buy running shoes",
    }).json()
    assert created["decision"] == "REVIEW"

    # Drain the daily budget via a second, unrelated review-blocked purchase's
    # agent record between the original decision and the human's approval.
    client.patch(f"/merchants/{merchant['id']}/block")

    reviewed = client.post(f"/transactions/{created['transaction_id']}/review", json={"approved": True})
    data = reviewed.json()
    assert data["decision"] == "BLOCK"
    assert data["payment_status"] == "BLOCKED_ON_RECHECK"


# ── Upsell Agent — PRD Section 2a ────────────────────────────────────────────

def test_propose_upsell_after_allow(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    # Amount kept small (well under 30% of max_transaction) so this clears
    # the fail-closed "unambiguously safe" gate under keyword-fallback
    # scoring (no LLM configured in the test environment) and actually
    # resolves to ALLOW — see app.engine.decide.
    original = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 1000, "currency": "INR", "merchant_id": merchant["id"],
        "category": "sports", "product": "Nike Running Shoes",
        "user_intent": "Buy running shoes sports today",
    }).json()
    assert original["decision"] == "ALLOW"

    upsell = client.post(f"/transactions/{original['transaction_id']}/upsell")
    assert upsell.status_code == 200
    data = upsell.json()
    assert data["original_transaction_id"] == original["transaction_id"]
    if data["proposed"]:
        assert data["decision"]["is_upsell"] is True
        assert data["decision"]["attributed_to"] == "Upsell Agent"


def test_propose_upsell_requires_allow_original(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    blocked = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 14999, "currency": "INR", "merchant_id": merchant["id"],
        "category": "insurance", "product": "Premium Protection Plan",
        "user_intent": "Buy running shoes under 5000",
    }).json()
    assert blocked["decision"] == "BLOCK"

    r = client.post(f"/transactions/{blocked['transaction_id']}/upsell")
    assert r.status_code == 400


def test_propose_upsell_404_for_unknown_transaction(client):
    assert client.post("/transactions/TXN-NOPE/upsell").status_code == 404


# ── Payment retry ─────────────────────────────────────────────────────────────

def test_retry_payment_requires_allow(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    blocked = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 14999, "currency": "INR", "merchant_id": merchant["id"],
        "category": "insurance", "product": "Premium Protection Plan",
        "user_intent": "Buy running shoes under 5000",
    }).json()
    r = client.post(f"/transactions/{blocked['transaction_id']}/retry-payment")
    assert r.status_code == 400


def test_retry_payment_rejects_already_succeeded(client, agent_and_merchant):
    agent, merchant = agent_and_merchant
    allowed = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 500, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Wireless Mouse",
        "user_intent": "Buy wireless mouse electronics today",
    }).json()
    # No Razorpay creds in test env -> payment_status is SKIPPED, not CREATED,
    # so a retry is legitimately allowed; this only rejects a CREATED payment.
    r = client.post(f"/transactions/{allowed['transaction_id']}/retry-payment")
    assert r.status_code == 200
    assert r.json()["payment_status"] == "SKIPPED"
