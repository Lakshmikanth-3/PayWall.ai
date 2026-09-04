"""
Train the Layer-2 risk model — PRD Section 9 / 23 (XGBoost).

Fits an XGBClassifier on backend/data/dataset_train.csv using the exact
feature set risk_model._build_feature_vector expects, and saves it to
backend/app/ml/risk_model.json where risk_model._load_model() picks it up
automatically. Never touches dataset_holdout.csv — that stays reserved for
scripts/evaluate_dataset.py's final, untuned report.

Usage:
    python scripts/train_model.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import xgboost as xgb

from app.ml.intent_matcher import keyword_intent_match

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRAIN_PATH = os.path.join(DATA_DIR, "dataset_train.csv")
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "ml", "risk_model.json")


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_to_features(r):
    max_transaction = float(r["agent_max_transaction"])
    daily_limit = float(r["agent_daily_limit"])
    daily_spent = float(r["agent_daily_spent_before"])
    allowed = r["agent_allowed_categories"].split("|") if r["agent_allowed_categories"] else []
    blocked = r["agent_blocked_categories"].split("|") if r["agent_blocked_categories"] else []
    category = r["category"].lower()
    category_allowed = (not allowed or category in [c.lower() for c in allowed]) and category not in [c.lower() for c in blocked]

    amount = float(r["amount"])
    intent_score = keyword_intent_match(r["user_intent"], r["product"], r["category"], amount, max_transaction)
    daily_remaining_ratio = max(0.0, (daily_limit - daily_spent) / daily_limit) if daily_limit else 0.0

    return [
        amount,
        amount / (max_transaction or 1),
        int(float(r["merchant_age_days"])),
        float(r["merchant_risk_score"]),
        int(float(r["txn_count_last_hour"])),
        int(float(r["txn_count_last_day"])),
        intent_score,
        1 if category_allowed else 0,
        daily_remaining_ratio,
        float(r["merchant_refund_rate"]),
        float(r["merchant_chargeback_rate"]),
        float(r["merchant_failed_payment_rate"]),
    ]


def main():
    if not os.path.exists(TRAIN_PATH):
        print(f"[ERROR] {TRAIN_PATH} not found. Run scripts/generate_dataset.py first.")
        sys.exit(1)

    rows = load_rows(TRAIN_PATH)
    print(f"Loading {len(rows)} training rows from {TRAIN_PATH} ...")

    X = np.array([row_to_features(r) for r in rows], dtype=float)
    y = np.array([int(r["is_risky"]) for r in rows], dtype=int)

    print(f"Feature matrix: {X.shape}, positive rate: {y.mean():.4f}")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)

    model.save_model(MODEL_PATH)
    print(f"[OK] Model saved to {MODEL_PATH}")

    train_preds = model.predict_proba(X)[:, 1]
    from sklearn.metrics import roc_auc_score
    print(f"Train ROC-AUC (in-sample, informational only): {roc_auc_score(y, train_preds):.4f}")


if __name__ == "__main__":
    main()
