"""
Risk scoring model — XGBoost-based ML layer (Layer 2).

When a trained model is not available on disk, falls back to a
deterministic heuristic scorer so the API never crashes.
"""

import os
import time
import numpy as np
from typing import Tuple, Optional

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "risk_model.json")


def _load_model():
    try:
        import xgboost as xgb
        if os.path.exists(MODEL_PATH):
            model = xgb.XGBClassifier()
            model.load_model(MODEL_PATH)
            return model
    except Exception:
        pass
    return None


_model = _load_model()


def _heuristic_risk_score(features: dict) -> float:
    """
    Deterministic fallback risk scorer when the ML model is unavailable.
    Returns a risk score 0–100.
    """
    score = 0.0

    # Amount deviation from category average
    amount_ratio = features.get("amount_ratio", 1.0)
    if amount_ratio > 3:
        score += 30
    elif amount_ratio > 2:
        score += 15
    elif amount_ratio > 1.5:
        score += 8

    # Merchant signals
    merchant_age = features.get("merchant_age_days", 365)
    if merchant_age < 30:
        score += 20
    elif merchant_age < 90:
        score += 10

    merchant_risk = features.get("merchant_risk_score", 20)
    score += merchant_risk * 0.25

    # Velocity
    txn_count_hour = features.get("txn_count_last_hour", 0)
    if txn_count_hour > 5:
        score += 15
    elif txn_count_hour > 2:
        score += 7

    # Intent mismatch
    intent_match = features.get("intent_match_score", 1.0)
    if intent_match < 0.3:
        score += 30
    elif intent_match < 0.6:
        score += 15
    elif intent_match < 0.8:
        score += 5

    # Category deviation
    category_allowed = features.get("category_allowed", 1)
    if not category_allowed:
        score += 20

    return min(score, 100.0)


def score_transaction(features: dict) -> Tuple[float, float]:
    """
    Returns (risk_score 0-100, latency_ms).
    """
    start = time.perf_counter()

    if _model is not None:
        try:
            feature_vector = _build_feature_vector(features)
            prob = _model.predict_proba([feature_vector])[0][1]
            risk_score = prob * 100.0
        except Exception:
            risk_score = _heuristic_risk_score(features)
    else:
        risk_score = _heuristic_risk_score(features)

    latency_ms = (time.perf_counter() - start) * 1000
    return round(risk_score, 2), round(latency_ms, 2)


def _build_feature_vector(features: dict) -> list:
    return [
        features.get("amount", 0),
        features.get("amount_ratio", 1.0),
        features.get("merchant_age_days", 365),
        features.get("merchant_risk_score", 20),
        features.get("txn_count_last_hour", 0),
        features.get("txn_count_last_day", 0),
        features.get("intent_match_score", 1.0),
        features.get("category_allowed", 1),
        features.get("daily_budget_remaining_ratio", 1.0),
        features.get("refund_rate", 0.02),
        features.get("chargeback_rate", 0.01),
        features.get("failed_payment_rate", 0.03),
    ]
