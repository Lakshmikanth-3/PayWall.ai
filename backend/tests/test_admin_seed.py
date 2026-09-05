"""POST /admin/seed — protected, idempotent remote seeding for deployments
without shell/filesystem access (see app/seed.py, app/routers/admin.py)."""

from app.config import settings


def test_seed_rejects_missing_key(client):
    r = client.post("/admin/seed")
    assert r.status_code == 403


def test_seed_rejects_wrong_key(client):
    r = client.post("/admin/seed", headers={"X-Admin-Key": "wrong-key"})
    assert r.status_code == 403


def test_seed_succeeds_with_correct_key(client):
    r = client.post("/admin/seed", headers={"X-Admin-Key": settings.SECRET_KEY})
    assert r.status_code == 200
    data = r.json()
    assert data["agents"] == 3
    assert data["merchants"] == 10

    agents = client.get("/agents").json()
    assert any(a["id"] == "AGT-001" for a in agents)


def test_seed_is_idempotent(client):
    headers = {"X-Admin-Key": settings.SECRET_KEY}
    first = client.post("/admin/seed", headers=headers).json()
    second = client.post("/admin/seed", headers=headers).json()

    assert first["transactions_seeded"] != "already present"
    assert second["transactions_seeded"] == "already present"
    assert second["upsell_transactions_seeded"] == "already present"

    # Re-running must not duplicate agents/merchants.
    assert len(client.get("/agents").json()) == 3
    assert len(client.get("/merchants").json()) == 10


def test_seed_force_wipes_transactions_and_reseeds_fully(client):
    """
    force=true is the fix for a partial run — e.g. a slow free-tier instance
    scoring 100+ transactions outlasting an HTTP client's timeout, leaving a
    partial history that a plain retry won't top up since "any transaction
    exists" is what the idempotency check looks for.
    """
    headers = {"X-Admin-Key": settings.SECRET_KEY}
    client.post("/admin/seed", headers=headers)
    before = len(client.get("/transactions?limit=1000").json())
    assert before > 0

    forced = client.post("/admin/seed", headers=headers, params={"force": "true"}).json()
    assert forced["transactions_seeded"] != "already present"
    assert forced["upsell_transactions_seeded"] != "already present"

    # force=true must not touch agents/merchants, only transactions/audit logs.
    assert len(client.get("/agents").json()) == 3
    assert len(client.get("/merchants").json()) == 10
    after = len(client.get("/transactions?limit=1000").json())
    assert after == before  # deterministic history generation (fixed random.seed)


def test_seed_force_resets_agent_daily_spent(client):
    headers = {"X-Admin-Key": settings.SECRET_KEY}
    client.post("/admin/seed", headers=headers)
    client.post("/admin/seed", headers=headers, params={"force": "true"})
    for agent in client.get("/agents").json():
        assert agent["daily_spent"] >= 0
