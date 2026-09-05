"""
Layers 1+2+3 combined — app.engine.decide().

Tested as a pure function against controlled inputs so behavior doesn't
depend on the trained ML model's exact scores for hand-picked amounts.
"""

from types import SimpleNamespace

from app import schemas
from app.engine import decide


def _agent(max_transaction=5000, requires_approval_above=0):
    return SimpleNamespace(max_transaction=max_transaction, requires_approval_above=requires_approval_above)


def _merchant(risk_score=10):
    return SimpleNamespace(risk_score=risk_score)


def test_low_risk_no_violations_allows():
    decision, failed_closed = decide(
        risk_score=10, violations=[], hard_violation=False, llm_used=True,
        intent_score=0.95, amount=1000, agent=_agent(), merchant=_merchant(),
    )
    assert decision == schemas.Decision.ALLOW
    assert failed_closed is False


def test_mid_risk_reviews():
    decision, _ = decide(
        risk_score=50, violations=[], hard_violation=False, llm_used=True,
        intent_score=0.8, amount=1000, agent=_agent(), merchant=_merchant(),
    )
    assert decision == schemas.Decision.REVIEW


def test_high_risk_blocks():
    decision, _ = decide(
        risk_score=90, violations=[], hard_violation=False, llm_used=True,
        intent_score=0.2, amount=1000, agent=_agent(), merchant=_merchant(),
    )
    assert decision == schemas.Decision.BLOCK


def test_any_violation_blocks_even_at_low_risk():
    decision, _ = decide(
        risk_score=5, violations=["some policy violation"], hard_violation=False, llm_used=True,
        intent_score=0.95, amount=1000, agent=_agent(), merchant=_merchant(),
    )
    assert decision == schemas.Decision.BLOCK


def test_hard_violation_blocks_regardless_of_risk_score():
    decision, failed_closed = decide(
        risk_score=1, violations=["Agent is not active"], hard_violation=True, llm_used=True,
        intent_score=0.99, amount=1, agent=_agent(), merchant=_merchant(),
    )
    assert decision == schemas.Decision.BLOCK
    assert failed_closed is False


def test_requires_approval_above_forces_review_on_allow():
    decision, _ = decide(
        risk_score=5, violations=[], hard_violation=False, llm_used=True,
        intent_score=0.95, amount=4000, agent=_agent(requires_approval_above=3000), merchant=_merchant(),
    )
    assert decision == schemas.Decision.REVIEW


def test_requires_approval_above_does_not_affect_block_or_review():
    # The override only downgrades ALLOW -> REVIEW; it must not upgrade an
    # already-REVIEW or already-BLOCK decision into something else.
    decision, _ = decide(
        risk_score=90, violations=[], hard_violation=False, llm_used=True,
        intent_score=0.2, amount=4000, agent=_agent(requires_approval_above=3000), merchant=_merchant(),
    )
    assert decision == schemas.Decision.BLOCK


# ── Fail-closed when the LLM is unavailable (PRD Section 21) ─────────────────

def test_llm_unavailable_downgrades_ambiguous_allow_to_review():
    decision, failed_closed = decide(
        risk_score=10, violations=[], hard_violation=False, llm_used=False,
        intent_score=0.95, amount=4000,  # 80% of max_transaction — not "unambiguously safe"
        agent=_agent(max_transaction=5000), merchant=_merchant(risk_score=10),
    )
    assert decision == schemas.Decision.REVIEW
    assert failed_closed is True


def test_llm_unavailable_still_allows_when_unambiguously_safe():
    decision, failed_closed = decide(
        risk_score=5, violations=[], hard_violation=False, llm_used=False,
        intent_score=0.9, amount=500,  # 10% of max_transaction
        agent=_agent(max_transaction=5000), merchant=_merchant(risk_score=10),
    )
    assert decision == schemas.Decision.ALLOW
    assert failed_closed is False


def test_llm_unavailable_does_not_affect_block_or_review_paths():
    decision, failed_closed = decide(
        risk_score=50, violations=[], hard_violation=False, llm_used=False,
        intent_score=0.9, amount=500,
        agent=_agent(max_transaction=5000), merchant=_merchant(risk_score=10),
    )
    assert decision == schemas.Decision.REVIEW
    assert failed_closed is False  # only fires on the ALLOW path
