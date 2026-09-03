"""
Held-out evaluation — PRD Section 19.

Runs the SAME decision-engine code paths used in production (Layer 1 hard
policy checks + Layer 2 risk scoring, from app.engine / app.ml.risk_model)
against backend/data/dataset_holdout.csv and reports precision/recall/F1/
ROC-AUC, false-positive cost, money protected, review rate, and latency.

Layer 3 (semantic intent matching) uses the deterministic keyword scorer
rather than live LLM calls — batch-scoring 20,000 transactions through a
hosted LLM is neither how a real deployment would run offline evaluation
nor within the point of holding out a fixed test set (the LLM path is
exercised per-transaction in the live API instead, see /transactions/evaluate).

The holdout set must never be used to tune ALLOW_THRESHOLD/REVIEW_THRESHOLD —
if you're adjusting thresholds based on these numbers, use dataset_train.csv.

Usage:
    python scripts/evaluate_dataset.py
"""

import csv
import json
import os
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from app.config import settings
from app import schemas
from app.engine import _run_policy_checks
from app.ml.risk_model import score_transaction
from app.ml.intent_matcher import keyword_intent_match

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HOLDOUT_PATH = os.path.join(DATA_DIR, "dataset_holdout.csv")
REPORT_PATH = os.path.join(DATA_DIR, "eval_report.json")


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def evaluate_row(r):
    agent = SimpleNamespace(
        status=r["agent_status"],
        payment_enabled=r["agent_payment_enabled"] == "True",
        max_transaction=float(r["agent_max_transaction"]),
        daily_limit=float(r["agent_daily_limit"]),
        daily_spent=float(r["agent_daily_spent_before"]),
        allowed_categories=r["agent_allowed_categories"].split("|") if r["agent_allowed_categories"] else [],
        blocked_categories=r["agent_blocked_categories"].split("|") if r["agent_blocked_categories"] else [],
        requires_approval_above=float(r["agent_requires_approval_above"]),
    )
    merchant = SimpleNamespace(
        is_blocked=r["merchant_is_blocked"] == "True",
        age_days=int(float(r["merchant_age_days"])),
        risk_score=float(r["merchant_risk_score"]),
        refund_rate=float(r["merchant_refund_rate"]),
        chargeback_rate=float(r["merchant_chargeback_rate"]),
        failed_payment_rate=float(r["merchant_failed_payment_rate"]),
    )
    req = schemas.TransactionEvaluateRequest(
        agent_id=r["agent_id"], amount=float(r["amount"]), currency=r["currency"],
        merchant_id=r["merchant_id"], category=r["category"], product=r["product"],
        user_intent=r["user_intent"],
    )

    start = time.perf_counter()

    policy_checks, violations = _run_policy_checks(agent, merchant, req)

    if violations and any(v for v in violations if "Agent" in v or "Merchant" in v or "Daily" in v):
        decision = "BLOCK"
        risk_score = 95.0
        intent_score = 0.5
    else:
        intent_score = keyword_intent_match(
            r["user_intent"], r["product"], r["category"], req.amount, agent.max_transaction
        )
        daily_remaining_ratio = max(0, (agent.daily_limit - agent.daily_spent) / agent.daily_limit) if agent.daily_limit else 0
        features = {
            "amount": req.amount,
            "amount_ratio": req.amount / (agent.max_transaction or 1),
            "merchant_age_days": merchant.age_days,
            "merchant_risk_score": merchant.risk_score,
            "txn_count_last_hour": int(float(r["txn_count_last_hour"])),
            "txn_count_last_day": int(float(r["txn_count_last_day"])),
            "intent_match_score": intent_score,
            "category_allowed": 1 if not violations else 0,
            "daily_budget_remaining_ratio": daily_remaining_ratio,
            "refund_rate": merchant.refund_rate,
            "chargeback_rate": merchant.chargeback_rate,
            "failed_payment_rate": merchant.failed_payment_rate,
        }
        risk_score, _ = score_transaction(features)
        if violations:
            risk_score = min(risk_score + 30, 100.0)

        if risk_score <= settings.ALLOW_THRESHOLD and not violations:
            decision = "ALLOW"
        elif risk_score >= settings.REVIEW_THRESHOLD or violations:
            decision = "BLOCK"
        else:
            decision = "REVIEW"

        if (decision == "ALLOW" and agent.requires_approval_above > 0
                and req.amount >= agent.requires_approval_above):
            decision = "REVIEW"

    latency_ms = (time.perf_counter() - start) * 1000
    return decision, risk_score, intent_score, latency_ms


def main():
    if not os.path.exists(HOLDOUT_PATH):
        print(f"[ERROR] {HOLDOUT_PATH} not found. Run scripts/generate_dataset.py first.")
        sys.exit(1)

    rows = load_rows(HOLDOUT_PATH)
    n = len(rows)
    print(f"Evaluating {n} held-out transactions from {HOLDOUT_PATH} ...")

    y_true, y_pred_blocked, risk_scores, decisions, amounts, latencies, scenario_types = [], [], [], [], [], [], []

    for r in rows:
        decision, risk_score, intent_score, latency_ms = evaluate_row(r)
        y_true.append(int(r["is_risky"]))
        y_pred_blocked.append(1 if decision in ("BLOCK", "REVIEW") else 0)
        risk_scores.append(risk_score)
        decisions.append(decision)
        amounts.append(float(r["amount"]))
        latencies.append(latency_ms)
        scenario_types.append(r["scenario_type"])

    y_true = np.array(y_true)
    y_pred = np.array(y_pred_blocked)
    risk_scores = np.array(risk_scores)
    amounts = np.array(amounts)
    decisions = np.array(decisions)
    scenario_types = np.array(scenario_types)

    scenario_breakdown = {}
    for scenario in sorted(set(scenario_types.tolist())):
        mask = scenario_types == scenario
        scenario_breakdown[scenario] = {
            "count": int(mask.sum()),
            "allow_rate": round(float(np.mean(decisions[mask] == "ALLOW")), 4),
            "review_rate": round(float(np.mean(decisions[mask] == "REVIEW")), 4),
            "block_rate": round(float(np.mean(decisions[mask] == "BLOCK")), 4),
        }

    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    try:
        from sklearn.metrics import roc_auc_score
        roc_auc = float(roc_auc_score(y_true, risk_scores / 100.0))
    except Exception:
        roc_auc = None

    total_gmv = float(amounts.sum())
    risky_gmv = float(amounts[y_true == 1].sum())
    risky_gmv_blocked = float(amounts[(y_true == 1) & (decisions == "BLOCK")].sum())
    legit_gmv_blocked = float(amounts[(y_true == 0) & (decisions == "BLOCK")].sum())
    fp_legit_txns_blocked = int(np.sum((y_true == 0) & (decisions == "BLOCK")))

    review_rate = float(np.mean(decisions == "REVIEW"))
    allow_rate = float(np.mean(decisions == "ALLOW"))
    block_rate = float(np.mean(decisions == "BLOCK"))

    report = {
        "dataset": {
            "holdout_size": n,
            "seed": 42,
            "note": "Layer 3 uses deterministic keyword matching, not live LLM calls (see script docstring).",
        },
        "detection": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        },
        "false_positive_cost": {
            "false_positive_rate": round(fpr, 4),
            "legitimate_transactions_blocked": fp_legit_txns_blocked,
            "legitimate_gmv_blocked": round(legit_gmv_blocked, 2),
        },
        "money_protected": {
            "total_transactions": n,
            "total_gmv": round(total_gmv, 2),
            "risky_gmv": round(risky_gmv, 2),
            "risky_gmv_blocked": round(risky_gmv_blocked, 2),
            "pct_risky_gmv_protected": round(risky_gmv_blocked / risky_gmv, 4) if risky_gmv else 0.0,
        },
        "decisions": {
            "allow_rate": round(allow_rate, 4),
            "review_rate": round(review_rate, 4),
            "block_rate": round(block_rate, 4),
        },
        "scenario_breakdown": scenario_breakdown,
        "latency_ms": {
            "note": "Policy + ML layers only (no LLM network call in batch mode).",
            "p50": round(float(np.percentile(latencies, 50)), 3),
            "p95": round(float(np.percentile(latencies, 95)), 3),
            "avg": round(float(np.mean(latencies)), 3),
        },
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\n[OK] Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
