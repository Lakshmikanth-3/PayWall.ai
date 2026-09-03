from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, Enum
from sqlalchemy.sql import func
import enum
from app.database import Base


class DecisionEnum(str, enum.Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class AgentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class MerchantRisk(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=False, index=True)
    status = Column(String, default=AgentStatus.ACTIVE)
    payment_enabled = Column(Boolean, default=True)
    max_transaction = Column(Float, nullable=False)
    daily_limit = Column(Float, nullable=False)
    allowed_categories = Column(JSON, default=list)
    blocked_categories = Column(JSON, default=list)
    requires_approval_above = Column(Float, default=0)
    daily_spent = Column(Float, default=0.0)
    last_reset_date = Column(String, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    risk_score = Column(Float, default=20.0)
    risk_level = Column(String, default=MerchantRisk.LOW)
    age_days = Column(Integer, default=365)
    transaction_volume = Column(Integer, default=1000)
    refund_rate = Column(Float, default=0.02)
    chargeback_rate = Column(Float, default=0.01)
    failed_payment_rate = Column(Float, default=0.03)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    merchant_id = Column(String, nullable=False)
    merchant_name = Column(String)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    category = Column(String, nullable=False)
    product = Column(String, nullable=False)
    user_intent = Column(Text, nullable=False)

    # Decision results
    decision = Column(String, nullable=False)
    risk_score = Column(Float)
    intent_match_score = Column(Float)
    policy_violations = Column(JSON, default=list)
    reason = Column(Text)
    decision_detail = Column(JSON, default=dict)

    # Human review
    requires_human_review = Column(Boolean, default=False)
    human_approved = Column(Boolean, nullable=True)
    human_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    human_reviewer = Column(String, nullable=True)

    # Razorpay
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    payment_status = Column(String, default="PENDING")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decision_latency_ms = Column(Float, default=0)
    policy_latency_ms = Column(Float, default=0)
    ml_latency_ms = Column(Float, default=0)
    llm_latency_ms = Column(Float, default=0)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, index=True)
    transaction_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
