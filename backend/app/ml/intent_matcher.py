"""
Intent matching — Layer 3 LLM reasoning.

Uses Groq (OpenAI-compatible API) to:
  1. Extract structured intent from a natural-language user request.
  2. Score semantic similarity between user intent and the payment being requested.
  3. Generate a human-readable decision explanation.

Falls back to keyword-based matching when the LLM is unavailable.
"""

import time
import re
import json
from typing import Tuple, Optional
from app.config import settings


def _openai_client():
    """Return a Groq client (OpenAI-compatible). Falls back to OpenAI if Groq key is absent."""
    # Prefer Groq
    if settings.GROQ_API_KEY:
        try:
            from openai import OpenAI
            return OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
        except Exception:
            pass
    # Fallback: plain OpenAI
    if settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            return OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception:
            pass
    return None


def _keyword_intent_match(user_intent: str, product: str, category: str, amount: float, max_amount: float) -> float:
    """Deterministic keyword-overlap similarity scorer (0–1)."""
    intent_words = set(re.findall(r"\w+", user_intent.lower()))
    product_words = set(re.findall(r"\w+", product.lower()))
    category_words = set(re.findall(r"\w+", category.lower()))

    combined = product_words | category_words
    overlap = len(intent_words & combined)
    total = len(intent_words | combined)

    score = overlap / total if total > 0 else 0.0

    # Penalise large amount overruns
    if max_amount > 0 and amount > max_amount * 1.2:
        score *= 0.5

    return round(min(score, 1.0), 4)


def match_intent(
    user_intent: str,
    product: str,
    category: str,
    amount: float,
    max_amount: float = 0,
) -> Tuple[float, str, float]:
    """
    Returns (similarity_score 0-1, explanation, latency_ms).
    """
    start = time.perf_counter()
    client = _openai_client()

    if client:
        try:
            prompt = f"""You are an intent verification system for AI agent payments.

User's original intent: "{user_intent}"
Agent's payment request:
  Product: {product}
  Category: {category}
  Amount: ₹{amount:,.0f}
  User's stated maximum: ₹{max_amount:,.0f}

Score how well the payment request matches the user's original intent.
Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "score": <float 0.0-1.0>,
  "reasoning": "<one sentence explaining the score>"
}}"""

            model = "llama-3.3-70b-versatile" if settings.GROQ_API_KEY else "gpt-4o-mini"
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150,
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            score = float(data["score"])
            reasoning = data.get("reasoning", "")
            latency_ms = (time.perf_counter() - start) * 1000
            return round(score, 4), reasoning, round(latency_ms, 2)

        except Exception as e:
            pass  # fall through to keyword scorer

    score = _keyword_intent_match(user_intent, product, category, amount, max_amount)
    reasoning = (
        f"Keyword-based match: {score:.2f} "
        f"(LLM unavailable — deterministic fallback)"
    )
    latency_ms = (time.perf_counter() - start) * 1000
    return score, reasoning, round(latency_ms, 2)


def generate_explanation(
    decision: str,
    policy_violations: list,
    risk_score: float,
    intent_score: float,
    user_intent: str,
    product: str,
    amount: float,
) -> str:
    """Generate a human-readable explanation of the decision."""
    client = _openai_client()

    if client:
        try:
            prompt = f"""You are an AI payment guard explaining a transaction decision.

Decision: {decision}
User Intent: "{user_intent}"
Product: "{product}"
Amount: ₹{amount:,.0f}
Intent Match Score: {intent_score:.2f}
Risk Score: {risk_score:.1f}/100
Policy Violations: {', '.join(policy_violations) if policy_violations else 'None'}

Write a clear, concise 1-2 sentence explanation of this decision for the user. Be specific."""

            model = "llama-3.3-70b-versatile" if settings.GROQ_API_KEY else "gpt-4o-mini"
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

    # Fallback explanation
    if policy_violations:
        return f"Transaction {decision.lower()}ed due to policy violations: {'; '.join(policy_violations)}."
    if risk_score > 70:
        return f"Transaction {decision.lower()}ed due to high risk score ({risk_score:.0f}/100)."
    if intent_score < 0.5:
        return f"Transaction {decision.lower()}ed due to low intent match ({intent_score:.0%})."
    return f"Transaction {decision.lower()}ed. Risk score: {risk_score:.0f}/100. Intent match: {intent_score:.0%}."
