from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


# ─── Agent Schemas ────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    owner_id: str = "USR-001"
    max_transaction: float = Field(gt=0)
    daily_limit: float = Field(gt=0)
    allowed_categories: List[str] = []
    blocked_categories: List[str] = []
    requires_approval_above: float = 0


class AgentResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    status: str
    payment_enabled: bool
    max_transaction: float
    daily_limit: float
    allowed_categories: List[str]
    blocked_categories: List[str]
    requires_approval_above: float
    daily_spent: float
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Merchant Schemas ─────────────────────────────────────────────────────────

class MerchantCreate(BaseModel):
    name: str
    category: str
    risk_score: float = 20.0
    age_days: int = 365
    refund_rate: float = 0.02
    chargeback_rate: float = 0.01
    failed_payment_rate: float = 0.03


class MerchantResponse(BaseModel):
    id: str
    name: str
    category: str
    risk_score: float
    risk_level: str
    age_days: int
    refund_rate: float
    chargeback_rate: float
    is_blocked: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Transaction Schemas ──────────────────────────────────────────────────────

class TransactionEvaluateRequest(BaseModel):
    agent_id: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    merchant_id: str
    category: str
    product: str
    user_intent: str


class PolicyCheck(BaseModel):
    check: str
    passed: bool
    detail: str


class DecisionResponse(BaseModel):
    transaction_id: str
    decision: Decision
    risk_score: float
    intent_match_score: float
    policy_violations: List[str]
    policy_checks: List[PolicyCheck]
    reason: str
    confidence: float
    requires_human_review: bool
    decision_latency_ms: float


class TransactionResponse(BaseModel):
    id: str
    agent_id: str
    user_id: str
    merchant_id: str
    merchant_name: Optional[str]
    amount: float
    currency: str
    category: str
    product: str
    user_intent: str
    decision: str
    risk_score: Optional[float]
    intent_match_score: Optional[float]
    policy_violations: Optional[List[str]]
    reason: Optional[str]
    requires_human_review: bool
    human_approved: Optional[bool]
    payment_status: str
    razorpay_order_id: Optional[str]
    created_at: Optional[datetime]
    decision_latency_ms: Optional[float]

    class Config:
        from_attributes = True


class HumanReviewRequest(BaseModel):
    approved: bool
    reviewer: str = "ops-team"


# ─── Stats Schemas ────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_evaluated: int
    total_allowed: int
    total_reviewed: int
    total_blocked: int
    money_protected: float
    total_gmv: float
    risky_gmv_blocked: float
    false_positive_rate: float
    avg_risk_score: float
    p50_latency: float
    p95_latency: float


class MetricsResponse(BaseModel):
    precision: float
    recall: float
    f1: float
    roc_auc: float
    false_positive_rate: float
    false_positive_gmv: float
    risky_gmv: float
    risky_gmv_blocked: float
    protection_rate: float
    review_rate: float
    avg_decision_latency_ms: float
    p50_latency: float
    p95_latency: float
