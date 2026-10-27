# PayWall.ai hackathon verification — 28 October 2026

Implemented a focused extension of the existing FastAPI/Next.js application:

- NVIDIA Nemotron is preferred through the documented OpenAI-compatible hosted endpoint. `NVIDIA_MODEL` comes from configuration, with Groq/OpenAI and keyword fallback retained.
- `/agent/shop` selects one of 15 local catalog products, validates its ID, restores trusted prices/merchant fields, and submits it to the existing Guard. It records authorization without executing payment.
- The upsell agent asks the configured model to choose from budget-filtered candidates and records its reason/model; existing selection remains the offline fallback.
- Model provenance is stored in decision audit payloads and existing transaction JSON, returned by evaluation/transaction APIs, and shown with scores and reasons in the dashboard Shopping Agent box.
- Backend tests, browser tests, reproducible demo commands, README architecture, setup and recording instructions were added. No policy thresholds or risk-model parameters were changed.

## Reproduce

From `backend`:

```sh
python -m pytest -q --disable-warnings
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python scripts/demo_shopping.py --output ../docs/demo-live.json
python scripts/demo_shopping.py --mock-llm --output ../docs/demo-mocked.json
```

From `frontend`:

```sh
npm ci
npm run build
npm run start -- --port 3001
```

For browser tests in PowerShell:

```powershell
$env:E2E_BASE_URL='http://localhost:3001'
npm run e2e
```

The backend's existing CORS configuration permits port 3001. Port 3000 was already occupied. The local database and `.env` are ignored by Git. Demo agents/merchants were seeded without bulk transaction history, and each demo run creates a fresh agent.

## Checks executed

- Baseline: `python -m pytest -q` — **102 passed**.
- Final backend: `python -m pytest -q --disable-warnings` — **117 passed**, 1,415 existing deprecation warnings, 57.08 seconds. Tests use mocked inference and isolated databases.
- Frontend: `npm run build` — **passed**, including TypeScript and all 12 static pages.
- Browser: `E2E_BASE_URL=http://localhost:3001 npm run e2e` — **18 passed**, 1.4 minutes, against the real running backend/frontend (LLM disabled for deterministic cases).
- New frontend code: `node node_modules/eslint/bin/eslint.js components/ShoppingAgent.tsx lib/api.ts e2e/shopping-agent.spec.ts` — **passed**.
- Full frontend: `npm run lint` — **26 errors, 19 warnings** in existing dashboard code (effects, components declared during render and declaration order). Those unrelated refactors were left outside scope.
- `git diff --check` — **passed**.

The initial browser run exposed two stale dashboard label expectations and a select-label issue in the new test. The dashboard now retains its expected Command Center subtitle, and the shopping selector uses an explicit label.

## Sponsor and payment verification

| Integration | Status |
| --- | --- |
| NVIDIA hosted Nemotron | Real client/endpoint implemented; live inference unverified because NVIDIA key/model are unset |
| Groq / OpenAI | Existing integrations retained; live keys unset in this workspace |
| Razorpay | Existing payment flow preserved; live test-order creation unverified because test credentials are unset |
| Zetaris | Not added in this focused scope; catalog is explicitly local development data |
| Meterless | Not added in this focused scope; memory uses the existing database |
| Cursor | Original project development editor; this extension was authored with Codex |

Configure `NVIDIA_API_KEY` and `NVIDIA_MODEL` in `backend/.env`, restart the backend, and rerun the live demo before recording a live Nemotron submission. Never put those keys in frontend variables. The shopping endpoint does not implement a new payment-confirmation screen. The existing Guard's small, unambiguously safe keyword-fallback exception remains; ambiguous purchases are reviewed or blocked according to the existing model and policy.

## Mocked inference evidence

[`demo-mocked.json`](demo-mocked.json) contains the complete outputs from an isolated in-memory database with **only inference mocked**, while the real policy checks, trained risk model, Guard orchestration and persistence execute.

| Case | Decision | Risk / 100 | Intent score |
| --- | --- | --- | --- |
| Running shoes, ₹4,799 | ALLOW | 0.35 | 0.98 |
| Running socks upsell, ₹149 | ALLOW | 0.04 | 0.98 |
| Manipulated insurance plan, ₹14,999 | BLOCK | 100 | 0.98 (deliberately adversarial mock) |
| LLM disabled; partially specified shoes request | REVIEW | 44.89 | 0.50 |

The malicious plan is blocked even when mocked inference gives it a high alignment score: it exceeds transaction and daily limits and uses an unauthorized insurance category. These mocked results are not proof of live NVIDIA connectivity.

## Live HTTP evidence without provider keys

[`demo-live.json`](demo-live.json) contains the actual responses from the running backend, with no inference or model scoring patched.

| Case | Decision | Risk / 100 | Intent score |
| --- | --- | --- | --- |
| Running shoes, ₹4,799 | REVIEW | 0.23 | 0.6667 |
| Upsell after it | SKIPPED | — | — |
| Manipulated insurance plan, ₹14,999 | BLOCK | 100 | 0 |
| LLM disabled; partially specified shoes request | REVIEW | 0.75 | 0.50 |

The upsell endpoint correctly requires an ALLOWed original purchase; the live fallback purchase was REVIEW. All live model names are `rules_only`. Configure live inference to demonstrate autonomous shoes/socks ALLOW outcomes; do not present the mocked run as a live sponsor call.

## Submission readiness

- Code, tests, architecture, setup, recording script and evidence files are prepared.
- Configure live NVIDIA credentials/model and rerun the live demo before recording a Nemotron claim.
- Configure Razorpay test credentials only if demonstrating the existing test-order flow.
- GitHub's credential helper currently has no stored authentication. The local commit can be created, but pushing may require signing in.

## Changed files

- `README.md`
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/engine.py`
- `backend/app/main.py`
- `backend/app/ml/intent_matcher.py`
- `backend/app/models.py`
- `backend/app/routers/transactions.py`
- `backend/app/schemas.py`
- `backend/app/shopping_agent.py`
- `backend/app/upsell_agent.py`
- `backend/scripts/demo_shopping.py`
- `backend/tests/conftest.py`
- `backend/tests/test_shopping_agent.py`
- `frontend/app/dashboard/page.tsx`
- `frontend/components/ShoppingAgent.tsx`
- `frontend/e2e/shopping-agent.spec.ts`
- `frontend/lib/api.ts`
- `docs/demo-live.json`
- `docs/demo-mocked.json`
- `docs/hackathon-verification.md`
