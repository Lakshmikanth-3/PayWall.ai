"""PRD Section 2a — app.upsell_agent.propose_upsell."""

from types import SimpleNamespace

from app.upsell_agent import propose_upsell


def _agent(daily_limit=10000, daily_spent=4799, max_transaction=5000):
    return SimpleNamespace(daily_limit=daily_limit, daily_spent=daily_spent, max_transaction=max_transaction)


def _original_txn(category="sports", merchant_id="MER-001"):
    return SimpleNamespace(category=category, merchant_id=merchant_id)


def test_proposes_largest_fitting_candidate_within_remaining_budget():
    # remaining budget = 10000 - 4799 = 5201, comfortably fits both sports
    # candidates (149, 299) — should pick the larger one.
    candidate = propose_upsell(_agent(), _original_txn("sports"))
    assert candidate is not None
    assert candidate["amount"] == 299
    assert candidate["category"] == "sports"
    assert candidate["merchant_id"] == "MER-001"


def test_picks_smaller_candidate_when_budget_is_tight():
    # remaining budget = 10000 - 9900 = 100 — only the ₹149 item... actually
    # doesn't fit either; nothing should be proposed.
    candidate = propose_upsell(_agent(daily_spent=9900), _original_txn("sports"))
    assert candidate is None


def test_fits_within_narrow_but_sufficient_budget():
    # remaining budget = 10000 - 9800 = 200 — only the ₹149 socks fit, not the ₹299 bottle.
    candidate = propose_upsell(_agent(daily_spent=9800), _original_txn("sports"))
    assert candidate is not None
    assert candidate["amount"] == 149


def test_never_exceeds_agent_max_transaction():
    candidate = propose_upsell(
        _agent(daily_limit=100000, daily_spent=0, max_transaction=100), _original_txn("sports"),
    )
    # both sports candidates (149, 299) exceed max_transaction=100
    assert candidate is None


def test_no_catalog_entry_for_unknown_category_returns_none():
    candidate = propose_upsell(_agent(), _original_txn("insurance"))
    assert candidate is None


def test_no_remaining_budget_returns_none():
    candidate = propose_upsell(_agent(daily_spent=10000), _original_txn("sports"))
    assert candidate is None
