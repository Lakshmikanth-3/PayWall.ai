"""POST/GET /agents and /merchants."""


def test_create_agent(client):
    r = client.post("/agents", json={
        "name": "Shopping Assistant", "owner_id": "USR-1",
        "max_transaction": 5000, "daily_limit": 10000,
        "allowed_categories": ["sports"], "blocked_categories": ["gambling"],
        "requires_approval_above": 3000,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["id"].startswith("AGT-")
    assert data["status"] == "ACTIVE"
    assert data["daily_spent"] == 0


def test_create_agent_rejects_non_positive_limits(client):
    r = client.post("/agents", json={
        "name": "Bad Agent", "max_transaction": 0, "daily_limit": 10000,
    })
    assert r.status_code == 422


def test_list_agents(client):
    client.post("/agents", json={"name": "A1", "max_transaction": 1000, "daily_limit": 2000})
    client.post("/agents", json={"name": "A2", "max_transaction": 1000, "daily_limit": 2000})
    r = client.get("/agents")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_agent_404(client):
    r = client.get("/agents/AGT-NOPE")
    assert r.status_code == 404


def test_suspend_and_activate_agent(client):
    created = client.post("/agents", json={"name": "A1", "max_transaction": 1000, "daily_limit": 2000}).json()
    agent_id = created["id"]

    r = client.patch(f"/agents/{agent_id}/suspend")
    assert r.status_code == 200
    assert client.get(f"/agents/{agent_id}").json()["status"] == "SUSPENDED"

    r = client.patch(f"/agents/{agent_id}/activate")
    assert r.status_code == 200
    assert client.get(f"/agents/{agent_id}").json()["status"] == "ACTIVE"


def test_reset_daily_spend(client, db_session):
    from app import models
    created = client.post("/agents", json={"name": "A1", "max_transaction": 1000, "daily_limit": 2000}).json()
    agent = db_session.query(models.Agent).filter(models.Agent.id == created["id"]).first()
    agent.daily_spent = 1500
    db_session.commit()

    r = client.patch(f"/agents/{created['id']}/reset-daily-spend")
    assert r.status_code == 200
    assert r.json()["daily_spent"] == 0

    assert client.get(f"/agents/{created['id']}").json()["daily_spent"] == 0


def test_reset_daily_spend_404(client):
    assert client.patch("/agents/AGT-NOPE/reset-daily-spend").status_code == 404


def test_create_merchant(client):
    r = client.post("/merchants", json={
        "name": "Nike", "category": "sports", "risk_score": 8, "age_days": 3650,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["id"].startswith("MER-")
    assert data["risk_level"] == "LOW"


def test_merchant_risk_level_bucketing(client):
    low = client.post("/merchants", json={"name": "A", "category": "x", "risk_score": 20}).json()
    medium = client.post("/merchants", json={"name": "B", "category": "x", "risk_score": 50}).json()
    high = client.post("/merchants", json={"name": "C", "category": "x", "risk_score": 90}).json()
    assert low["risk_level"] == "LOW"
    assert medium["risk_level"] == "MEDIUM"
    assert high["risk_level"] == "HIGH"


def test_block_merchant(client):
    created = client.post("/merchants", json={"name": "A", "category": "x", "risk_score": 20}).json()
    r = client.patch(f"/merchants/{created['id']}/block")
    assert r.status_code == 200
    assert client.get(f"/merchants/{created['id']}").json()["is_blocked"] is True


def test_delete_agent_removes_it_and_its_transactions(client):
    agent = client.post("/agents", json={
        "name": "Throwaway Agent", "max_transaction": 1000, "daily_limit": 2000,
        "allowed_categories": ["electronics"],
    }).json()
    merchant = client.post("/merchants", json={"name": "M", "category": "electronics", "risk_score": 8}).json()
    txn = client.post("/transactions/evaluate", json={
        "agent_id": agent["id"], "amount": 100, "currency": "INR", "merchant_id": merchant["id"],
        "category": "electronics", "product": "Cable", "user_intent": "Buy cable electronics today",
    }).json()

    r = client.delete(f"/agents/{agent['id']}")
    assert r.status_code == 200
    assert r.json()["transactions_removed"] == 1

    assert client.get(f"/agents/{agent['id']}").status_code == 404
    assert client.get(f"/transactions/{txn['transaction_id']}").status_code == 404


def test_delete_agent_404(client):
    assert client.delete("/agents/AGT-NOPE").status_code == 404


def test_delete_merchant(client):
    created = client.post("/merchants", json={"name": "Throwaway Merchant", "category": "x", "risk_score": 20}).json()
    r = client.delete(f"/merchants/{created['id']}")
    assert r.status_code == 200
    assert client.get(f"/merchants/{created['id']}").status_code == 404


def test_delete_merchant_404(client):
    assert client.delete("/merchants/MER-NOPE").status_code == 404
