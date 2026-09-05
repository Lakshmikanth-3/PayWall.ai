"""
Shared pytest fixtures.

Forces the test suite to run fully offline and deterministic — no real LLM
(Groq/OpenAI) or Razorpay calls, regardless of what backend/.env has
configured for local dev — and gives each test its own isolated in-memory
database so tests never interfere with each other or with the local dev
sqlite file.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["GROQ_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["RAZORPAY_KEY_ID"] = ""
os.environ["RAZORPAY_KEY_SECRET"] = ""
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models
from app.main import app
from app.ml import intent_matcher

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _isolated_db():
    """Fresh schema per test, and the LLM kill-switch reset to 'available'
    (empty API keys already make match_intent fall back to keyword scoring
    regardless — this just guards against a test that flips the switch and
    forgets to flip it back)."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    intent_matcher.set_llm_disabled(False)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def agent(db_session):
    a = models.Agent(
        id="AGT-TEST", name="Test Shopping Agent", owner_id="USR-TEST",
        max_transaction=5000, daily_limit=10000,
        allowed_categories=["sports", "electronics", "food", "groceries"],
        blocked_categories=["gambling", "financial_services"],
        requires_approval_above=4900,
        last_reset_date=date.today().isoformat(),
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def suspended_agent(db_session):
    a = models.Agent(
        id="AGT-SUSPENDED", name="Suspended Agent", owner_id="USR-TEST",
        status="SUSPENDED", max_transaction=5000, daily_limit=10000,
        allowed_categories=["sports"], blocked_categories=[],
        requires_approval_above=0, last_reset_date=date.today().isoformat(),
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture
def merchant(db_session):
    m = models.Merchant(
        id="MER-TEST", name="Test Store", category="sports",
        risk_score=8, risk_level="LOW", age_days=3650,
        refund_rate=0.02, chargeback_rate=0.01, failed_payment_rate=0.03,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def risky_merchant(db_session):
    m = models.Merchant(
        id="MER-RISKY", name="Shady Store", category="electronics",
        risk_score=88, risk_level="HIGH", age_days=5,
        refund_rate=0.2, chargeback_rate=0.15, failed_payment_rate=0.18,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


@pytest.fixture
def blocked_merchant(db_session):
    m = models.Merchant(
        id="MER-BLOCKED", name="Banned Store", category="electronics",
        risk_score=95, risk_level="HIGH", age_days=2, is_blocked=True,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m
