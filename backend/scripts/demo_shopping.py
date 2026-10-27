"""Run actual HTTP demos, or explicitly mocked inference with the real Guard.

Live: python scripts/demo_shopping.py
Offline: python scripts/demo_shopping.py --mock-llm
The offline run uses an isolated in-memory DB and never contacts payment APIs.
"""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(post):
    agent = post("/agents", {
        "name": "Hackathon demo shopper", "max_transaction": 5000, "daily_limit": 10000,
        "allowed_categories": ["sports", "electronics", "food", "groceries"],
        "blocked_categories": ["gambling", "financial_services"], "requires_approval_above": 4900,
    })
    intent = "Buy running shoes under 5000"
    shopping = post("/agent/shop", {"agent_id": agent["id"], "user_intent": intent})
    if shopping["decision"] == "ALLOW":
        upsell = post(f"/transactions/{shopping['transaction_id']}/upsell", None)
    else:
        upsell = {"skipped": "Original purchase was not ALLOW; live inference may be unconfigured or unavailable."}
    manipulation = post("/transactions/evaluate", {
        "agent_id": agent["id"], "merchant_id": "MER-001", "amount": 14999,
        "category": "insurance", "product": "Premium Protection Plan", "user_intent": intent,
        "is_upsell": True, "upsell_of_transaction_id": shopping["transaction_id"],
    })
    post("/dashboard/llm-toggle?disabled=true", None)
    try:
        ambiguous = post("/agent/shop", {
            "agent_id": agent["id"], "user_intent": "Buy shoes or running shoes under 5000",
        })
    finally:
        post("/dashboard/llm-toggle?disabled=false", None)
    return {"shopping": shopping, "upsell": upsell, "manipulated_protection_plan": manipulation, "llm_off_ambiguous": ambiguous}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", help="Save the complete JSON evidence to this file")
    args = parser.parse_args()
    if not args.mock_llm:
        def post(path, body):
            req = Request(args.base_url + path, data=json.dumps(body).encode() if body is not None else b"", headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=120) as response:
                return json.load(response)
        result = {"mode": "live_http", **run(post)}
    else:
        # Set before importing app settings: no production database or payment keys.
        for key in ("NVIDIA_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"):
            os.environ[key] = ""
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import Base, get_db
        from app.seed import _seed_agents_and_merchants
        from app.ml import intent_matcher

        db_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(db_engine)
        session = sessionmaker(bind=db_engine)
        with session() as db:
            _seed_agents_and_merchants(db)
        def get_demo_db():
            with session() as db:
                yield db
        client = Mock()
        client.base_url = "https://integrate.api.nvidia.com/v1"
        def complete(**kwargs):
            if kwargs["messages"][0]["content"].startswith("You are an AI payment guard explaining"):
                content = "Mock explanation: Guard policy blocks the unauthorized insurance category and over-budget amount."
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
            elif kwargs["messages"][0]["role"] == "system":
                catalog = json.loads(kwargs["messages"][1]["content"])["catalog"]
                selected = next((c for c in catalog if "socks" in c["product"].lower()), catalog[0]) if "complementary" in kwargs["messages"][0]["content"] else next(c for c in catalog if c["product_id"] == "running-shoes")
                data = {"product_id": selected["product_id"], "reasoning": "Relevant catalog item within the available budget (mock inference)."}
            else:
                data = {"score": 0.98, "reasoning": "Mock inference: consistent with running purchase."}
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(data)))])
        client.chat.completions.create.side_effect = complete
        with ExitStack() as stack:
            stack.enter_context(patch.object(intent_matcher.settings, "NVIDIA_MODEL", "mock-nemotron"))
            stack.enter_context(patch.object(intent_matcher, "_openai_client", lambda: None if intent_matcher.is_llm_disabled() else client))
            app.dependency_overrides[get_db] = get_demo_db
            try:
                with TestClient(app) as http:
                    def post(path, body):
                        response = http.post(path, json=body)
                        response.raise_for_status()
                        return response.json()
                    result = {"mode": "mock_inference_real_guard_isolated_db", **run(post)}
            finally:
                app.dependency_overrides.pop(get_db, None)
                db_engine.dispose()
    output = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(json.dumps({"mode": result["mode"], "shopping": result["shopping"]["decision"],
                          "upsell": result["upsell"].get("decision", {}).get("decision", "SKIPPED"),
                          "protection_plan": result["manipulated_protection_plan"]["decision"],
                          "llm_off": result["llm_off_ambiguous"]["decision"], "output": args.output}))
    else:
        print(output)


if __name__ == "__main__":
    main()
