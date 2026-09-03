# Agent Commerce Guard — Product Requirements Document

**Project:** Agent Commerce Guard  
**Razorpay AI Buildathon Track:** 01 — AI Growth & Agentic Commerce  
**Tagline:** The trust layer that lets AI agents spend money safely.

---

## 1. Product Overview

### Problem

AI agents are moving from simply recommending products to actually purchasing them for users.

This creates a new payment problem:

> How does a payment system know that an AI agent's requested transaction is actually what the user authorized?

An agent may:
- exceed the user's spending limit
- purchase an unintended product
- purchase an unauthorized category
- transact with a suspicious merchant
- repeat a transaction
- behave differently from its historical behavior
- encounter malicious or irrelevant instructions during the shopping process

Traditional payment fraud detection mainly asks:

> Is this transaction fraudulent?

Agent Commerce Guard asks:

> Is this transaction authorized, consistent with the user's intent, within policy, and safe to execute?

---

## 2. Product Vision

Build a real-time AI decision layer between an AI agent and Razorpay payment APIs.

```text
User
  |
  | "Buy running shoes under ₹5,000"
  v
AI Shopping Agent
  |
  | Payment Request
  v
+-----------------------------+
|    AGENT COMMERCE GUARD     |
|                             |
|  Identity                   |
|  Intent                     |
|  Policy                     |
|  Merchant Risk              |
|  Transaction Risk           |
|  Behavioral Anomaly         |
+--------------+--------------+
               |
        +------+-------+
        v      v       v
      ALLOW  REVIEW   BLOCK
        |      |       |
        +------+-------+
               v
          Razorpay API
               |
               v
            Payment
```

---

## 3. Goals

### G1 — Verify agent authorization
Determine whether the agent is authorized to perform the requested action.

### G2 — Verify user intent
Compare the requested payment with what the user actually asked the agent to do.

### G3 — Enforce spending policies
Ensure agents cannot exceed:
- transaction limits
- daily limits
- category limits
- merchant restrictions
- frequency restrictions

### G4 — Detect risky transactions
Identify unusual or suspicious transactions using ML/risk signals.

### G5 — Make bounded decisions
Every transaction must result in:
- ALLOW
- REVIEW
- BLOCK

### G6 — Explain every decision
The system must tell the merchant/user why it made the decision.

### G7 — Maintain an audit trail
Every money-related decision must be recorded.

### G8 — Demonstrate measurable performance
Evaluate the system on a held-out test dataset.

---

## 4. Non-Goals

The MVP will not attempt to build:
- a complete payment gateway
- a general-purpose fraud platform
- a full e-commerce marketplace
- a fully autonomous unrestricted purchasing agent
- a replacement for Razorpay's payment infrastructure
- an LLM that makes every decision

The product is specifically the trust/decision layer for agentic transactions.

---

## 5. Target Users

### Primary — Merchant
The merchant wants to safely accept purchases initiated by AI agents.

### Secondary — Consumer
The consumer gives an AI agent permission to purchase things and needs confidence that the agent cannot exceed that permission.

### Third — Risk/Operations Team
They investigate:
- blocked transactions
- suspicious agents
- unusual merchants
- policy violations

---

## 6. Core User Journey

### Step 1 — User creates an agent policy

Example:

```json
{
  "agent": "Shopping Assistant",
  "daily_budget": 10000,
  "max_transaction": 5000,
  "allowed_categories": ["food", "groceries", "sports"],
  "blocked_categories": ["gambling", "financial_services"],
  "approval_above": 3000
}
```

### Step 2 — Agent receives user intent

User:

> Buy me running shoes under ₹5,000.

The system converts this into structured intent:

```json
{
  "category": "sports",
  "product_type": "running_shoes",
  "maximum_amount": 5000,
  "currency": "INR"
}
```

### Step 3 — Agent searches for a product

Example:

```text
Product: Nike Running Shoes
Price: ₹4,799
Category: Sports
Merchant: ABC Sports
Merchant Risk: Low
```

### Step 4 — Agent Commerce Guard evaluates

The Guard evaluates:
- identity
- authorization
- user intent
- policy
- budget
- merchant trust
- transaction risk
- behavioral anomaly

### Step 5 — Decision

Example:

```text
Transaction: ₹4,799
Intent: Running shoes
Policy: Maximum ₹5,000
Merchant: Low risk
Daily spend: ₹2,100 / ₹10,000

Result: ALLOW
```

Payment proceeds through Razorpay test mode.

---

## 7. Killer Scenario — Intent Manipulation

User:

> Buy me running shoes under ₹5,000.

During checkout, an additional offer appears:

```text
Premium Protection Plan
₹14,999
```

The agent attempts to pay ₹14,999.

Agent Commerce Guard compares:

```text
USER INTENT:
Running shoes under ₹5,000

PAYMENT:
Premium protection plan ₹14,999
```

Result:

```text
BLOCKED

Reasons:
1. Amount exceeds user's ₹5,000 limit
2. Product does not match user's requested intent
3. Protection plan was not requested
4. Agent authorization does not cover this purchase

Risk: HIGH
Confidence: 97.4%
```

The payment never executes.

---

## 8. Additional Scenarios

### Scenario A — Normal purchase

User asks for running shoes under ₹5,000.

Agent requests ₹4,799 from a low-risk merchant.

Result: ALLOW.

### Scenario B — Budget violation

Daily budget is ₹10,000.

Agent has already spent ₹7,500 and requests another ₹4,000.

Result:

```text
BLOCK
Reason: Daily agent budget exceeded.
```

### Scenario C — Human approval

Transaction is ₹4,500 and the user's policy requires approval above ₹3,000.

Result:

```text
REVIEW
```

Human can approve or deny.

### Scenario D — Suspicious merchant

Transaction is within the amount limit, but merchant is newly created, has elevated risk signals, and the price is abnormally low.

Result:

```text
REVIEW or BLOCK
```

### Scenario E — LLM failure

If the LLM is unavailable:
- never guess
- run deterministic policy checks
- allow only when the transaction is unambiguously safe
- otherwise move to REVIEW

---

## 9. Decision Engine

The decision engine uses three layers.

### Layer 1 — Hard Policy Rules

Deterministic checks for:
- maximum transaction
- daily budget
- category authorization
- merchant restrictions
- frequency limits
- approval thresholds

Example:

```text
amount > maximum_transaction
        |
        v
      BLOCK
```

### Layer 2 — Risk Model

ML model outputs:

```text
risk_score = 0..100
```

Potential features:
- transaction amount
- merchant age
- merchant risk
- transaction velocity
- agent history
- user spending pattern
- amount deviation
- category deviation
- time anomaly
- merchant frequency

### Layer 3 — LLM Reasoning

Use an LLM for:
- natural-language intent extraction
- semantic matching
- ambiguous policy interpretation
- human-readable explanations

Do not use the LLM for deterministic rules that can be enforced reliably in code.

---

## 10. Decision Logic

```text
                 Transaction
                      |
                      v
             Identity Valid?
                /          \
              NO            YES
              |              |
            BLOCK            v
                        Hard Policy
                           |
                   +-------+-------+
                   |               |
                Violation         Pass
                   |               |
                 BLOCK             v
                             Risk + Intent
                                  |
                        +---------+---------+
                        v         v         v
                      LOW      MEDIUM      HIGH
                        |         |          |
                      ALLOW     REVIEW      BLOCK
```

Initial thresholds:

| Risk Score | Decision |
|---:|---|
| 0–30 | ALLOW |
| 31–70 | REVIEW |
| 71–100 | BLOCK |

Thresholds must be configurable.

---

## 11. Human Approval Flow

For REVIEW:

```text
Approval Required

Transaction:
₹4,500

Merchant:
XYZ Store

Reason:
Merchant risk is elevated.

User policy:
Approval required above ₹3,000.

[Approve]
[Deny]
```

If approved:

```text
Human approval
      |
      v
Policy re-check
      |
      v
Razorpay payment
```

---

## 12. Agent Identity

Every agent gets:

```text
Agent ID
Agent name
Owner/User ID
Authorization scope
Created timestamp
Status
```

Example:

```text
Agent ID: AGT-92831
Name: Shopping Assistant
Owner: USR-1292
Status: ACTIVE
Payment permission: YES
Daily limit: ₹10,000
```

---

## 13. Agent Authorization

Example:

```json
{
  "payment_enabled": true,
  "max_transaction": 5000,
  "daily_limit": 10000,
  "allowed_categories": [
    "food",
    "groceries",
    "sports"
  ],
  "requires_approval_above": 3000
}
```

The agent never receives unrestricted authority to move money.

---

## 14. Merchant Risk

Merchant risk score:

```text
0–30     LOW
31–70    MEDIUM
71–100   HIGH
```

Signals may include:
- merchant age
- transaction volume
- refund rate
- chargeback rate
- failed payment rate
- customer complaints
- price anomaly
- historical agent behavior

For the buildathon, these can be synthetic.

---

## 15. Intent Matching

The system compares:

```text
User intent
     |
     v
Agent action
     |
     v
Payment
```

Example:

```text
User:
Buy running shoes under ₹5,000.

Payment:
Running shoes ₹4,799

Intent similarity:
0.96

Result:
PASS
```

Incorrect action:

```text
Payment:
Premium protection plan ₹14,999

Intent similarity:
0.12

Result:
BLOCK
```

---

## 16. Audit Trail

Every transaction receives a complete decision record.

Example:

```text
Transaction ID: TXN-928371
Agent: AGT-192
User: USR-82
Amount: ₹14,999

User Intent:
Running shoes under ₹5,000

Requested Item:
Premium protection plan

Policy Checks:
✓ Agent authenticated
✗ Maximum amount
✗ Intent match
✗ Category authorization

Risk Score: 91
Decision: BLOCK

Reason:
Transaction violates user authorization.

Timestamp:
2026-09-03 10:14:32

Decision ID:
DEC-918273
```

---

## 17. Dashboard

### A. Overview

```text
Transactions evaluated: 100,000
Allowed: 91,420
Reviewed: 5,230
Blocked: 3,350
Money protected: ₹8.2L
```

### B. Live Decisions

```text
TXN-19283
₹2,300
ALLOW

TXN-19284
₹8,900
BLOCK

TXN-19285
₹3,800
REVIEW
```

### C. Risk Analytics

Display:
- high-risk agents
- high-risk merchants
- policy violations
- intent mismatches
- risky transaction value

### D. Audit Explorer

Search by:
- Transaction ID
- Agent ID
- Merchant
- Decision
- Risk score

---

## 18. Dataset

Create a synthetic dataset containing at least 100,000 transactions.

Recommended distribution:

```text
70,000 normal
10,000 budget violations
5,000 category violations
5,000 intent mismatches
4,000 suspicious merchants
3,000 anomalous agent behavior
2,000 duplicate/velocity anomalies
1,000 mixed attacks
```

Keep the final test set completely held out.

Do not tune the model against the final test set.

---

## 19. Evaluation Metrics

### Detection

Report:
- Precision
- Recall
- F1
- ROC-AUC

### False-positive cost

Measure:
- false-positive rate
- number of legitimate transactions blocked
- legitimate GMV blocked
- economic cost of false positives

### Money Protected

Report:

```text
Total transactions
Total GMV
Risky GMV
Risky GMV blocked
Percentage of risky GMV protected
```

### Human Review

Report:
- review rate
- approval rate
- denial rate

### Latency

Measure:
- policy evaluation latency
- ML inference latency
- LLM inference latency
- total decision latency
- P50
- P95

Target:

```text
P50 < 200ms
P95 < 500ms
```

If LLM latency is high, use deterministic rules first and invoke the LLM only for ambiguous cases.

---

## 20. Money-Safety Architecture

Core principle:

> The AI agent never gets unrestricted authority to move money.

The architecture is:

```text
Agent
  |
  v
Payment Request
  |
  v
Agent Commerce Guard
  |
  +--> Identity
  +--> Intent
  +--> Policy
  +--> Risk
  +--> Merchant
  +--> Audit
  |
  v
ALLOW / REVIEW / BLOCK
  |
  v
Razorpay
```

The AI proposes.

The Guard authorizes.

---

## 21. Failure Handling

### Failure: AI service unavailable

```text
Agent requests payment
        |
        v
LLM unavailable
        |
        v
Do NOT guess
        |
        v
Run deterministic policies
        |
        +--> Clearly safe -> ALLOW
        |
        +--> Ambiguous -> REVIEW
```

Never approve an unsafe transaction simply because the AI service is unavailable.

### Failure: Razorpay payment fails

Record:

```text
Decision: ALLOW
Payment: FAILED
Money movement: NONE
Failure reason: Payment failure
```

Authorization and payment execution must remain separate.

---

## 22. API Design

### Create Agent

```http
POST /agents
```

Example:

```json
{
  "name": "Shopping Assistant",
  "daily_limit": 10000,
  "max_transaction": 5000,
  "allowed_categories": [
    "food",
    "groceries",
    "sports"
  ]
}
```

### Evaluate Transaction

```http
POST /transactions/evaluate
```

Example:

```json
{
  "agent_id": "AGT-123",
  "amount": 4799,
  "currency": "INR",
  "merchant_id": "MER-821",
  "category": "sports",
  "product": "running shoes",
  "user_intent": "Buy running shoes under 5000"
}
```

Response:

```json
{
  "decision": "ALLOW",
  "risk_score": 12,
  "intent_match": 0.97,
  "policy_violations": [],
  "reason": "Transaction matches user intent and agent policy."
}
```

### Payment Execution

Only execute when:

```text
decision == ALLOW
```

or:

```text
decision == REVIEW
AND human_approved == true
```

Then:

```text
Agent Commerce Guard
        |
        v
Razorpay Test API
        |
        v
Payment
```

---

## 23. Tech Stack

### Frontend
- Next.js
- TypeScript
- Tailwind CSS

### Backend
- Python
- FastAPI

### Database
- PostgreSQL

### ML
- Python
- scikit-learn
- XGBoost or LightGBM

### AI
LLM for:
- intent extraction
- semantic matching
- explanations
- ambiguous policy reasoning

### Payments
- Razorpay Test Mode APIs

### Authentication
- JWT
- Agent ID
- User ID

### Deployment
- Frontend: Vercel
- Backend: Render / Railway / AWS
- Database: PostgreSQL

---

## 24. MVP Scope

### Must-have

- Agent creation
- User policies
- Agent authorization
- Transaction evaluation
- Intent extraction
- Risk model
- ALLOW / REVIEW / BLOCK
- Razorpay test-mode payment
- Audit trail
- Dashboard
- Synthetic dataset
- Evaluation metrics
- One graceful failure scenario

---

## 25. Phase 2

- Merchant reputation model
- Behavioral anomaly detection
- Agent spending history
- Human approval UI
- Multiple agents
- Agent revocation
- Policy simulator
- Real-time alerts

---

## 26. Killer Feature — Policy Simulator

Allow users to change policies and immediately see the impact.

Example:

```text
Daily limit:
₹10,000 -> ₹20,000
```

System shows:

```text
Previously blocked: 1,293
Now allowed: +832
Additional risky exposure: ₹1.7L
```

This demonstrates the economic tradeoff between automation and risk.

---

## 27. Demo Plan — 5 Minutes

### 0:00–0:30 — Problem

Show:

```text
User -> AI Agent -> Payment
```

Explain:

> A payment request from an AI agent can look valid even when it does not match what the user authorized.

### 0:30–1:00 — Solution

Show:

```text
Agent -> Agent Commerce Guard -> Razorpay
```

### 1:00–2:00 — Normal Transaction

User:

> Buy running shoes under ₹5,000.

Agent requests ₹4,799.

Guard:

```text
ALLOW
```

Payment succeeds.

### 2:00–3:00 — Manipulated Transaction

Agent attempts:

```text
₹14,999 premium protection plan
```

Guard:

```text
BLOCK
```

Show the exact reasons.

### 3:00–3:45 — Human Review

Show an ambiguous transaction.

```text
₹4,200
Intent match: 82%
Merchant risk: Medium

REVIEW
```

Human approves.

### 3:45–4:30 — Metrics

Show actual results from the held-out dataset:

```text
Transactions evaluated: XX

Precision: XX%
Recall: XX%
F1: XX%

False-positive cost: ₹XX

Risky GMV: ₹XX
Protected: ₹XX

P95 latency: XX ms
```

### 4:30–5:00 — Failure Recovery

Disable LLM.

Show:

```text
AI reasoning unavailable

Unsafe autonomous approval prevented.

Transaction moved to REVIEW.
```

Finish with:

> The agent can recommend an action, but it never gets unrestricted authority to move money.

---

## 28. Product Principles

### Principle 1 — Bounded autonomy
Agents can act only within explicitly defined permissions.

### Principle 2 — AI where AI helps
Use LLMs for intent and ambiguity, not simple deterministic rules.

### Principle 3 — Fail closed for ambiguity
When authorization cannot be established, require review instead of guessing.

### Principle 4 — Explainability
Every decision must have human-readable reasons.

### Principle 5 — Auditability
Every money-related action must be traceable.

### Principle 6 — Economic measurement
Optimize both safety and legitimate transaction approval.

---

## 29. Competitive Differentiation

Do not position this as another fraud detector.

Traditional system:

```text
Transaction
    |
    v
Fraud Score
    |
    v
Approve / Block
```

Agent Commerce Guard:

```text
User Intent
     +
Agent Identity
     +
Authorization
     +
Policy
     +
Merchant Risk
     +
Behavior
     +
Transaction Risk
     |
     v
ALLOW / REVIEW / BLOCK
     |
     v
Explain + Audit
```

The product focuses on the new authorization problem created by autonomous AI commerce.

---

## 30. Final Pitch

### One-line pitch

> Agent Commerce Guard is the authorization and safety layer between AI agents and Razorpay that ensures autonomous payments stay within the user's intent, policy and risk limits.

### Core principle

> Let AI agents transact. Don't let them transact beyond what the user authorized.

### Winning narrative

The next generation of commerce will not always be human clicking "Pay." AI agents will increasingly discover products, choose merchants and initiate transactions.

The missing infrastructure is trust.

Agent Commerce Guard provides that trust layer through:

**Intent + Authorization + Policy + Risk + Human Approval + Auditability.**
