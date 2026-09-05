"""Layer 2 deterministic fallback — app.ml.risk_model._heuristic_risk_score."""

from app.ml.risk_model import _heuristic_risk_score, score_transaction


def _features(**overrides):
    defaults = dict(
        amount=1000, amount_ratio=0.5, merchant_age_days=365, merchant_risk_score=10,
        txn_count_last_hour=0, txn_count_last_day=1, intent_match_score=0.9,
        category_allowed=1, daily_budget_remaining_ratio=0.8,
        refund_rate=0.02, chargeback_rate=0.01, failed_payment_rate=0.03,
    )
    defaults.update(overrides)
    return defaults


def test_clean_transaction_scores_low():
    score = _heuristic_risk_score(_features())
    assert score < 30


def test_new_merchant_increases_score():
    clean = _heuristic_risk_score(_features())
    new_merchant = _heuristic_risk_score(_features(merchant_age_days=10))
    assert new_merchant > clean


def test_high_merchant_risk_increases_score():
    clean = _heuristic_risk_score(_features())
    risky = _heuristic_risk_score(_features(merchant_risk_score=90))
    assert risky > clean


def test_velocity_spike_increases_score():
    clean = _heuristic_risk_score(_features())
    spiky = _heuristic_risk_score(_features(txn_count_last_hour=10))
    assert spiky > clean


def test_low_intent_match_increases_score():
    clean = _heuristic_risk_score(_features())
    mismatched = _heuristic_risk_score(_features(intent_match_score=0.1))
    assert mismatched > clean


def test_category_not_allowed_increases_score():
    clean = _heuristic_risk_score(_features())
    disallowed = _heuristic_risk_score(_features(category_allowed=0))
    assert disallowed > clean


def test_score_never_exceeds_100():
    worst_case = _heuristic_risk_score(_features(
        amount_ratio=10, merchant_age_days=1, merchant_risk_score=100,
        txn_count_last_hour=50, intent_match_score=0.0, category_allowed=0,
    ))
    assert worst_case <= 100.0


def test_score_transaction_returns_score_and_latency():
    score, latency_ms = score_transaction(_features())
    assert 0 <= score <= 100
    assert latency_ms >= 0
