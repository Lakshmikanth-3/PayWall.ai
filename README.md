# Agent Commerce Guard 🛡️

> **Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**  
> The trust layer that lets AI agents spend money safely.

---

## Overview

Agent Commerce Guard is a real-time AI decision engine that sits between an AI shopping agent and Razorpay's payment APIs. Every payment request is verified across three layers before a rupee moves:

```
AI Agent → Payment Request → Agent Commerce Guard → ALLOW / REVIEW / BLOCK → Razorpay
```

### Three-Layer Decision Engine

| Layer | Technology | Purpose |
|-------|-----------|---------|
| 1 — Hard Policy | Deterministic rules | Amount limits, budgets, categories |
| 2 — ML Risk Model | XGBoost / heuristic | Risk score 0–100 |
| 3 — LLM Intent | GPT-4o-mini / keyword | Semantic intent matching |

---

## Quick Start

### Backend (FastAPI)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt

# Seed demo data (agents + merchants)
.\venv\Scripts\python scripts/seed_db.py

# Start API (http://localhost:8000)
.\venv\Scripts\uvicorn app.main:app --reload
```

### Frontend (Next.js)

```powershell
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
DATABASE_URL=sqlite:///./agent_guard.db   # default (SQLite)
OPENAI_API_KEY=sk-...                     # optional — enables LLM intent matching
RAZORPAY_KEY_ID=rzp_test_...              # optional — for payment execution
RAZORPAY_KEY_SECRET=...
```

> **The system works without an OpenAI key** — it falls back to keyword-based intent matching.

---

## API Reference

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/agents` | Register an AI agent with policy |
| `GET` | `/agents` | List all agents |
| `POST` | `/merchants` | Register a merchant |
| `POST` | `/transactions/evaluate` | **Evaluate a payment request** |
| `POST` | `/transactions/{id}/review` | Human approve/deny |
| `GET` | `/dashboard/stats` | Aggregate statistics |
| `GET` | `/dashboard/metrics` | ML evaluation metrics |
| `GET` | `/dashboard/live` | Latest transactions |
| `GET` | `/dashboard/audit` | Searchable audit trail |

Full interactive docs at: **http://localhost:8000/docs**

---

## Demo Scenarios

### ✅ Normal Purchase — ALLOW
```json
{
  "agent_id": "AGT-001",
  "merchant_id": "MER-001",
  "amount": 4799,
  "category": "sports",
  "product": "Nike Running Shoes",
  "user_intent": "Buy running shoes under 5000"
}
```
**Result**: `ALLOW` · Risk: 12 · Intent: 96%

---

### 🚨 Intent Manipulation — BLOCK
```json
{
  "agent_id": "AGT-001",
  "merchant_id": "MER-001",
  "amount": 14999,
  "category": "insurance",
  "product": "Premium Protection Plan",
  "user_intent": "Buy running shoes under 5000"
}
```
**Result**: `BLOCK` · Risk: 95 · Violations: 3

---

### ⚠️ Suspicious Merchant — REVIEW/BLOCK
```json
{
  "agent_id": "AGT-001",
  "merchant_id": "MER-007",
  "amount": 2000,
  "category": "electronics",
  "product": "USB Hub",
  "user_intent": "Buy a USB hub"
}
```
**Result**: `BLOCK` · Merchant risk: HIGH (88/100)

---

## Pre-seeded Data

### Agents
| ID | Name | Max Txn | Daily Limit |
|----|------|---------|------------|
| AGT-001 | Shopping Assistant | ₹5,000 | ₹10,000 |
| AGT-002 | Travel Booker | ₹20,000 | ₹50,000 |
| AGT-003 | Office Supply Agent | ₹2,000 | ₹5,000 |

### Merchants
| ID | Name | Risk |
|----|------|------|
| MER-001 | Nike Official Store | LOW (8) |
| MER-002 | Amazon India | LOW (5) |
| MER-006 | QuickShop24 | MEDIUM (65) |
| MER-007 | ShadyDeals.in | HIGH (88) |

---

## Tech Stack

- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS
- **Backend**: Python + FastAPI + SQLite (dev) / PostgreSQL (prod)  
- **ML**: XGBoost + heuristic fallback
- **AI**: OpenAI GPT-4o-mini + keyword fallback
- **Charts**: Recharts

---

## Decision Thresholds

| Risk Score | Decision |
|-----------|---------|
| 0–30 | ALLOW |
| 31–70 | REVIEW |
| 71–100 | BLOCK |

Configurable via `ALLOW_THRESHOLD` and `REVIEW_THRESHOLD` env vars.
