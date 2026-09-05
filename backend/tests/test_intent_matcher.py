"""Layer 3 fallback — app.ml.intent_matcher (keyword scoring + LLM unavailable path)."""

from app.ml.intent_matcher import keyword_intent_match, match_intent


def test_exact_product_and_category_match_scores_high():
    score = keyword_intent_match(
        "Buy wireless mouse electronics today", "Wireless Mouse", "electronics", 500, 2000,
    )
    assert score >= 0.9


def test_unrelated_product_scores_low():
    score = keyword_intent_match(
        "Buy running shoes under 5000", "Premium Protection Plan", "insurance", 14999, 5000,
    )
    assert score < 0.2


def test_stopwords_do_not_dilute_the_score():
    # "buy"/"under"/numbers used to count toward the denominator, dragging
    # down an otherwise-exact product match — see app/ml/intent_matcher.py.
    # Ceiling here is 2/3 (running, shoes match; "sports" is an extra
    # category word never mentioned in the intent text) — still much
    # higher than if "buy"/"under"/"5000" were still diluting the ratio.
    score = keyword_intent_match(
        "Buy running shoes under 5000", "Running Shoes", "sports", 4799, 5000,
    )
    assert score >= 0.6


def test_large_amount_overrun_penalizes_score():
    base = keyword_intent_match("Buy running shoes", "Running Shoes", "sports", 4000, 5000)
    overrun = keyword_intent_match("Buy running shoes", "Running Shoes", "sports", 7000, 5000)
    assert overrun < base


def test_empty_intent_scores_zero():
    score = keyword_intent_match("", "Running Shoes", "sports", 100, 5000)
    assert score == 0.0


def test_match_intent_falls_back_to_keyword_when_no_api_key_configured():
    # conftest.py sets GROQ_API_KEY / OPENAI_API_KEY to "" for the whole
    # suite, so this always exercises the fail-closed fallback path.
    score, reasoning, latency_ms, llm_used = match_intent(
        user_intent="Buy running shoes under 5000", product="Running Shoes",
        category="sports", amount=4799, max_amount=5000,
    )
    assert llm_used is False
    assert score >= 0.6
    assert "fallback" in reasoning.lower() or "keyword" in reasoning.lower()
    assert latency_ms >= 0


def test_match_intent_is_upsell_aware_prompt_selection_does_not_break_fallback():
    # is_upsell only changes which LLM prompt would be used; with no LLM
    # configured it should still safely fall back to the keyword scorer.
    score, _, _, llm_used = match_intent(
        user_intent="Buy running shoes under 5000", product="Moisture-wicking Running Socks",
        category="sports", amount=149, max_amount=5000, is_upsell=True,
    )
    assert llm_used is False
    assert 0.0 <= score <= 1.0
