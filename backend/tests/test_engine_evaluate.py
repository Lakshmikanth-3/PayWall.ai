"""
Full evaluate() orchestration — request -> decision -> persistence -> response.

Layer 2 (ML) and Layer 3 (LLM) are monkeypatched to return controlled
values so these tests exercise the real orchestration/persistence code
without depending on the trained model's exact scores for hand-picked
amounts (that's what test_decide.py and test_risk_model.py are for).
"""

import pytest

from app import schemas, models
import app.engine as engine


def _req(**overrides):
    defaults = dict(
        agent_id="AGT-TEST", amount=1000, currency="INR", merchant_id="MER-TEST",
        category="sports", product="Running Shoes", user_intent="Buy running shoes",
    )
    defaults.update(overrides)
    return schemas.TransactionEvaluateRequest(**defaults)


@pytest.fixture
def mock_layer_2_3(monkeypatch):
    """Returns a setter: mock_layer_2_3(risk_score, intent_score, llm_used)."""
    def _set(risk_score=10.0, intent_score=0.95, llm_used=True):
        monkeypatch.setattr(engine, "score_transaction", lambda features: (risk_score, 1.0))
        monkeypatch.setattr(
            engine, "match_intent",
            lambda **kwargs: (intent_score, "mocked", 1.0, llm_used),
        )
    return _set


def test_evaluate_allows_clean_transaction(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=10, intent_score=0.95, llm_used=True)
    result = engine.evaluate(_req(amount=1000, category="sports"), db_session, execute_payment=False)

    assert result.decision == schemas.Decision.ALLOW
    assert result.risk_score == 10
    assert result.policy_violations == []
    assert result.decision_id.startswith("DEC-")
    assert result.transaction_id.startswith("TXN-")

    txn = db_session.query(models.Transaction).filter(models.Transaction.id == result.transaction_id).first()
    assert txn is not None
    assert txn.decision == "ALLOW"
    assert txn.decision_id == result.decision_id
    assert len(txn.policy_checks) == 5


def test_evaluate_updates_agent_daily_spent_on_allow(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=5, intent_score=0.95, llm_used=True)
    engine.evaluate(_req(amount=1200, category="sports"), db_session, execute_payment=False)
    db_session.refresh(agent)
    assert agent.daily_spent == 1200


def test_evaluate_does_not_update_daily_spent_on_block(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=95, intent_score=0.1, llm_used=True)
    engine.evaluate(_req(amount=1200, category="sports"), db_session, execute_payment=False)
    db_session.refresh(agent)
    assert agent.daily_spent == 0


def test_evaluate_blocks_the_killer_scenario(db_session, agent, merchant, mock_layer_2_3):
    """PRD Section 7 — protection plan disguised as an upsell during a shoe purchase."""
    mock_layer_2_3(risk_score=10, intent_score=0.95, llm_used=True)  # irrelevant — hard violation short-circuits
    result = engine.evaluate(
        _req(amount=14999, category="insurance", product="Premium Protection Plan",
             user_intent="Buy running shoes under 5000", is_upsell=True),
        db_session, execute_payment=False,
    )
    assert result.decision == schemas.Decision.BLOCK
    assert any("not authorized" in v for v in result.policy_violations)
    assert result.is_upsell is True
    assert result.attributed_to == "Upsell Agent"


def test_evaluate_review_for_mid_risk(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=50, intent_score=0.8, llm_used=True)
    result = engine.evaluate(_req(amount=1000, category="sports"), db_session, execute_payment=False)
    assert result.decision == schemas.Decision.REVIEW
    assert result.requires_human_review is True


def test_evaluate_fails_closed_when_llm_unavailable(db_session, agent, merchant, mock_layer_2_3):
    # Ambiguous ALLOW (not unambiguously safe — amount is 80% of max_transaction)
    # with the LLM down must degrade to REVIEW, never silently ALLOW.
    mock_layer_2_3(risk_score=10, intent_score=0.95, llm_used=False)
    result = engine.evaluate(_req(amount=4000, category="sports"), db_session, execute_payment=False)
    assert result.decision == schemas.Decision.REVIEW
    assert "unavailable" in result.reason.lower()


def test_evaluate_allows_unambiguously_safe_even_with_llm_down(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=5, intent_score=0.9, llm_used=False)
    result = engine.evaluate(_req(amount=500, category="sports"), db_session, execute_payment=False)
    assert result.decision == schemas.Decision.ALLOW


def test_evaluate_requires_approval_above_downgrades_to_review(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=5, intent_score=0.95, llm_used=True)
    result = engine.evaluate(_req(amount=4950, category="sports"), db_session, execute_payment=False)
    assert result.decision == schemas.Decision.REVIEW


def test_evaluate_skips_payment_when_execute_payment_false(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=5, intent_score=0.95, llm_used=True)
    result = engine.evaluate(_req(amount=1000, category="sports"), db_session, execute_payment=False)
    txn = db_session.query(models.Transaction).filter(models.Transaction.id == result.transaction_id).first()
    assert txn.razorpay_order_id is None
    assert txn.payment_status == "PENDING"


def test_evaluate_runs_payment_and_stays_skipped_without_razorpay_credentials(db_session, agent, merchant, mock_layer_2_3):
    # conftest.py clears RAZORPAY_KEY_ID/SECRET for the whole suite —
    # authorization and payment execution must stay separate: ALLOW still
    # stands even though no real order gets created.
    mock_layer_2_3(risk_score=5, intent_score=0.95, llm_used=True)
    result = engine.evaluate(_req(amount=1000, category="sports"), db_session, execute_payment=True)
    assert result.decision == schemas.Decision.ALLOW
    txn = db_session.query(models.Transaction).filter(models.Transaction.id == result.transaction_id).first()
    assert txn.payment_status == "SKIPPED"
    assert txn.razorpay_order_id is None


def test_evaluate_raises_for_unknown_agent(db_session, merchant):
    with pytest.raises(ValueError):
        engine.evaluate(_req(agent_id="AGT-NOPE"), db_session, execute_payment=False)


def test_evaluate_raises_for_unknown_merchant(db_session, agent):
    with pytest.raises(ValueError):
        engine.evaluate(_req(merchant_id="MER-NOPE"), db_session, execute_payment=False)


def test_evaluate_records_audit_log(db_session, agent, merchant, mock_layer_2_3):
    mock_layer_2_3(risk_score=5, intent_score=0.95, llm_used=True)
    result = engine.evaluate(_req(amount=1000, category="sports"), db_session, execute_payment=False)
    audits = db_session.query(models.AuditLog).filter(models.AuditLog.transaction_id == result.transaction_id).all()
    assert any(a.event_type == "DECISION" for a in audits)
