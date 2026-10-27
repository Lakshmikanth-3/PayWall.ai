"""Real Guard orchestration with only hosted inference mocked."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app import models, shopping_agent
from app.ml import intent_matcher
from app.seed import _seed_agents_and_merchants


def llm(monkeypatch, *, product_id="running-shoes", down=False):
    client = Mock()
    client.base_url = "https://integrate.api.nvidia.com/v1"
    monkeypatch.setattr(intent_matcher.settings, "NVIDIA_MODEL", "test-nemotron")
    def complete(**kwargs):
        if down:
            raise TimeoutError("hosted inference unavailable")
        if kwargs["messages"][0]["role"] == "system":
            data = {"product_id": product_id, "reasoning": "Running shoes fit the stated budget."}
        else:
            data = {"score": 0.98, "reasoning": "Matches requested running shoes."}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])
    client.chat.completions.create.side_effect = complete
    monkeypatch.setattr(intent_matcher, "_openai_client", lambda: client)
    return client


def test_shop_matching_proposal_allowed_and_audited(client, db_session, monkeypatch):
    _seed_agents_and_merchants(db_session)
    llm(monkeypatch)
    response = client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy running shoes under 5000"})
    assert response.status_code == 200
    result = response.json()
    assert result["decision"] == "ALLOW"
    assert result["agent_proposal"]["amount"] == 4799
    assert result["model"] == result["guard_model"] == "test-nemotron"
    audit = db_session.query(models.AuditLog).filter_by(transaction_id=result["transaction_id"], event_type="DECISION").one()
    assert audit.payload["model"] == "test-nemotron"
    assert client.get(f"/transactions/{result['transaction_id']}").json()["model"] == "test-nemotron"
    txn = db_session.get(models.Transaction, result["transaction_id"])
    assert txn.razorpay_order_id is None  # authorization does not charge


def test_manipulated_insurance_proposal_blocked(client, db_session, monkeypatch):
    _seed_agents_and_merchants(db_session)
    llm(monkeypatch)
    response = client.post("/transactions/evaluate", json={
        "agent_id": "AGT-001", "user_intent": "Buy running shoes under 5000",
        "product": "Premium Protection Plan", "category": "insurance", "amount": 14999,
        "merchant_id": "MER-001", "is_upsell": True,
    })
    assert response.status_code == 200
    assert response.json()["decision"] == "BLOCK"
    assert "not authorized" in " ".join(response.json()["policy_violations"])


def test_shop_llm_down_rules_only_no_crash(client, db_session, monkeypatch):
    _seed_agents_and_merchants(db_session)
    llm(monkeypatch, down=True)
    result = client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy running shoes under 5000"}).json()
    assert result["model"] == result["guard_model"] == "rules_only"
    assert result["decision"] == "REVIEW"


@pytest.mark.parametrize("product_id", ["invented-product", "flight"])
def test_fabricated_or_over_budget_llm_selection_falls_back(client, db_session, monkeypatch, product_id):
    _seed_agents_and_merchants(db_session)
    llm(monkeypatch, product_id=product_id)
    result = client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy running shoes under 5000"}).json()
    assert result["model"] == "rules_only"
    assert result["agent_proposal"]["product_id"] == "running-shoes"
    assert result["agent_proposal"]["amount"] <= 5000


def test_shop_server_catalog_overrides_model_price(client, db_session, monkeypatch):
    _seed_agents_and_merchants(db_session)
    llm(monkeypatch)
    monkeypatch.setattr(shopping_agent, "propose_purchase", lambda *_: (
        {"product_id": "running-shoes", "amount": 1, "merchant_id": "attacker"}, "Tampered price", "mock",
    ))
    result = client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy running shoes under 5000"}).json()
    assert result["agent_proposal"]["amount"] == 4799
    assert result["agent_proposal"]["merchant_id"] == "MER-001"


def test_toggle_disables_shopping_and_ambiguous_intent_reviews(client, db_session):
    _seed_agents_and_merchants(db_session)
    assert client.post("/dashboard/llm-toggle?disabled=true").json()["llm_disabled"]
    result = client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy shoes or running shoes under 5000"}).json()
    assert result["model"] == "rules_only"
    assert result["decision"] == "REVIEW"


def test_shop_no_budget_fit_and_unknown_agent(client, db_session):
    _seed_agents_and_merchants(db_session)
    assert client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy shoes under 1"}).status_code == 422
    assert client.post("/agent/shop", json={"agent_id": "missing", "user_intent": "Buy shoes"}).status_code == 404
    for budget in ("-5000", "0", ",,,"):
        assert client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": f"Buy shoes under {budget}"}).status_code == 422


def test_nvidia_outage_uses_groq_and_records_actual_model(monkeypatch):
    nvidia = llm(monkeypatch, down=True)
    groq = Mock()
    groq.base_url = "https://api.groq.com/openai/v1"
    groq.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"score":0.95,"reasoning":"Shoes match"}'))])
    monkeypatch.setattr(intent_matcher.settings, "GROQ_API_KEY", "test-groq")
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: groq)
    result = intent_matcher.match_intent("Buy shoes", "Running Shoes", "sports", 4799, 5000)
    assert result[3] is True
    assert result.model == intent_matcher.GROQ_MODEL
    nvidia.chat.completions.create.assert_called_once()


def test_upsell_llm_selects_socks_and_audits_model(client, db_session, monkeypatch):
    _seed_agents_and_merchants(db_session)
    llm_client = llm(monkeypatch)
    original_complete = llm_client.chat.completions.create.side_effect
    def complete(**kwargs):
        if kwargs["messages"][0]["role"] == "system" and "complementary" in kwargs["messages"][0]["content"]:
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"product_id":"0","reasoning":"Running socks complement the shoes."}'))])
        return original_complete(**kwargs)
    llm_client.chat.completions.create.side_effect = complete
    primary = client.post("/agent/shop", json={"agent_id": "AGT-001", "user_intent": "Buy running shoes under 5000"}).json()
    result = client.post(f"/transactions/{primary['transaction_id']}/upsell").json()
    assert result["decision"]["decision"] == "ALLOW"
    assert result["model"] == "test-nemotron"
    assert "socks" in result["reason"].lower()
    audit = db_session.query(models.AuditLog).filter_by(transaction_id=result["decision"]["transaction_id"], event_type="UPSELL_PROPOSAL").one()
    assert audit.payload["model"] == "test-nemotron"


def test_nvidia_preferred_and_model_matches_client(monkeypatch):
    monkeypatch.setattr(intent_matcher.settings, "NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(intent_matcher.settings, "NVIDIA_MODEL", "test-nemotron")
    monkeypatch.setattr(intent_matcher.settings, "GROQ_API_KEY", "test-groq")
    client = intent_matcher._openai_client()
    assert str(client.base_url) == "https://integrate.api.nvidia.com/v1/"
    assert intent_matcher._model_for(client) == "test-nemotron"
    assert client.max_retries == 0


@pytest.mark.parametrize("score", [-1, 2, float("nan"), float("inf")])
def test_invalid_intent_scores_fail_closed(monkeypatch, score):
    client = llm(monkeypatch)
    client.chat.completions.create.side_effect = None
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"score": score})))])
    result = intent_matcher.match_intent("Buy shoes", "Running Shoes", "sports", 4799, 5000)
    assert not result[3]
    assert result.model == "rules_only"
