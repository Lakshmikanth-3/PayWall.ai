"""Layer 1 — deterministic hard policy rules (app.engine._run_policy_checks)."""

from app import schemas
from app.engine import _run_policy_checks


def _req(**overrides):
    defaults = dict(
        agent_id="AGT-TEST", amount=1000, currency="INR", merchant_id="MER-TEST",
        category="sports", product="Running Shoes", user_intent="Buy running shoes",
    )
    defaults.update(overrides)
    return schemas.TransactionEvaluateRequest(**defaults)


def test_all_checks_pass_for_clean_transaction(agent, merchant):
    checks, violations = _run_policy_checks(agent, merchant, _req(amount=1000, category="sports"))
    assert violations == []
    assert all(c.passed for c in checks)
    assert len(checks) == 5


def test_suspended_agent_violates(suspended_agent, merchant):
    checks, violations = _run_policy_checks(suspended_agent, merchant, _req(amount=1000, category="sports"))
    assert any("not active" in v for v in violations)
    assert not next(c for c in checks if c.check == "Agent authenticated & active").passed


def test_blocked_merchant_violates(agent, blocked_merchant):
    checks, violations = _run_policy_checks(agent, blocked_merchant, _req(amount=1000, merchant_id="MER-BLOCKED", category="electronics"))
    assert any("blocked" in v.lower() for v in violations)


def test_amount_over_max_transaction_violates(agent, merchant):
    checks, violations = _run_policy_checks(agent, merchant, _req(amount=6000, category="sports"))
    assert any("exceeds max transaction" in v for v in violations)


def test_amount_over_daily_budget_violates(agent, merchant):
    agent.daily_spent = 9500
    checks, violations = _run_policy_checks(agent, merchant, _req(amount=1000, category="sports"))
    assert any("Daily budget exceeded" in v for v in violations)


def test_blocked_category_violates(agent, merchant):
    checks, violations = _run_policy_checks(agent, merchant, _req(amount=500, category="gambling"))
    assert any("not authorized" in v for v in violations)


def test_category_outside_allowed_list_violates(agent, merchant):
    # "insurance" is neither in allowed_categories nor blocked_categories —
    # PRD's own "protection plan" killer scenario: an unlisted category is
    # still not authorized, not silently permitted.
    checks, violations = _run_policy_checks(agent, merchant, _req(amount=500, category="insurance"))
    assert any("not authorized" in v for v in violations)


def test_category_check_is_case_insensitive(agent, merchant):
    checks, violations = _run_policy_checks(agent, merchant, _req(amount=500, category="SPORTS"))
    assert violations == []


def test_agent_with_empty_allowed_list_permits_any_non_blocked_category(db_session, merchant):
    from datetime import date
    from app import models
    a = models.Agent(
        id="AGT-OPEN", name="Open Agent", owner_id="USR-TEST",
        max_transaction=5000, daily_limit=10000,
        allowed_categories=[], blocked_categories=["gambling"],
        requires_approval_above=0, last_reset_date=date.today().isoformat(),
    )
    db_session.add(a)
    db_session.commit()
    checks, violations = _run_policy_checks(a, merchant, _req(amount=500, category="anything"))
    assert violations == []
