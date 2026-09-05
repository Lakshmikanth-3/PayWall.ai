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
