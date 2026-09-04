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
    # Revenue growth layer (PRD Section 2a) — set by POST /transactions/{id}/upsell
    # or by a caller demonstrating a manipulative upsell attempt. An upsell gets
    # NO special treatment in the Guard pipeline; these fields are audit metadata
    # only, attached after the same evaluate() decision is made.
    is_upsell: bool = False
    upsell_of_transaction_id: Optional[str] = None


class PolicyCheck(BaseModel):
    check: str
    passed: bool
    detail: str


class DecisionResponse(BaseModel):
    transaction_id: str
    decision_id: str
    decision: Decision
    risk_score: float
    intent_match_score: float
    policy_violations: List[str]
    policy_checks: List[PolicyCheck]
    reason: str
    confidence: float
    requires_human_review: bool
    decision_latency_ms: float
    is_upsell: bool = False
    attributed_to: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    decision_id: Optional[str]
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
    policy_checks: Optional[List[PolicyCheck]]
    reason: Optional[str]
    requires_human_review: bool
    human_approved: Optional[bool]
    payment_status: str
    razorpay_order_id: Optional[str]
    created_at: Optional[datetime]
    decision_latency_ms: Optional[float]
    is_upsell: bool = False
    upsell_of_transaction_id: Optional[str] = None
    attributed_to: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Upsell / Revenue Growth Layer — PRD Section 2a ───────────────────────────

class UpsellProposalResponse(BaseModel):
    proposed: bool
    reason: str
    original_transaction_id: str
    decision: Optional[DecisionResponse] = None


class RevenueImpactResponse(BaseModel):
    upsells_proposed: int
    upsells_allowed: int
    upsells_blocked: int
    upsells_review: int
    incremental_gmv: float
    upsell_acceptance_rate: float
    manipulative_exposure_blocked: float


class HumanReviewRequest(BaseModel):
    approved: bool
    reviewer: str = "ops-team"


# ─── Policy Simulator ─────────────────────────────────────────────────────────

class PolicySimulationRequest(BaseModel):
    max_transaction: Optional[float] = None
    daily_limit: Optional[float] = None
    allowed_categories: Optional[List[str]] = None
    blocked_categories: Optional[List[str]] = None
    requires_approval_above: Optional[float] = None


class PolicyView(BaseModel):
    max_transaction: float
    daily_limit: float
    allowed_categories: List[str]
    blocked_categories: List[str]
    requires_approval_above: float


class DecisionCounts(BaseModel):
    ALLOW: int = 0
    REVIEW: int = 0
    BLOCK: int = 0


class FlippedTransaction(BaseModel):
    transaction_id: str
    amount: float
    category: str
    product: str
    merchant_name: Optional[str]
    risk_score: Optional[float]
    before: str
    after: str


class PolicySimulationResponse(BaseModel):
    agent_id: str
    transactions_analyzed: int
    current_policy: PolicyView
    proposed_policy: PolicyView
    before: DecisionCounts
    after: DecisionCounts
    now_allowed_count: int
    now_allowed_gmv: float
    additional_risky_exposure: float
    now_blocked_count: int
    now_blocked_gmv: float
    flipped_transactions: List[FlippedTransaction]


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
    # Detection
    precision: float
    recall: float
    f1: float
    roc_auc: float
    # False-positive cost
    false_positive_rate: float
    false_positive_gmv: float
    legitimate_transactions_blocked: int
    # Money protected
    total_gmv: float
    risky_gmv: float
    risky_gmv_blocked: float
    protection_rate: float
    # Human review
    review_rate: float
    approval_rate: float
    denial_rate: float
    # Latency — total
    avg_decision_latency_ms: float
    p50_latency: float
    p95_latency: float
    # Latency — per layer
    avg_policy_latency_ms: float
    avg_ml_latency_ms: float
    avg_llm_latency_ms: float
