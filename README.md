# TrustRail — Adaptive Permission Layer for AI Shopping Agents
**Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce**

> **One-Liner:** TrustRail is an adaptive permission layer for AI shopping agents: instead of a fixed spend cap, an agent earns trust through clean transactions, and its spending authority expands or contracts automatically based on a transparent, deterministic score.

[![Build & Tests](https://img.shields.io/badge/pytest-18%20passed-10b981.svg)](tests/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-0c8ce9.svg)](backend/)
[![Evaluation Track](https://img.shields.io/badge/Track-01%3A%20AI%20Growth%20%26%20Agentic%20Commerce-f59e0b.svg)](https://razorpay.com)

---

## 1. The Core Thesis: Beyond Static Bounded Checkout

Static bounded checkout (fixed ₹1,000 cap, rigid category allowlist) is the minimum bar for agentic commerce. However, static limits introduce a fundamental tension:
- **Too restrictive:** An agent cannot purchase genuine bundles or higher-ticket items even after dozens of flawless transactions.
- **Too permissive:** A newly spawned agent with zero history is granted dangerous authority.

**TrustRail reframes Razorpay's own core competency (risk-adjusted creditworthiness & underwriting) and applies it to an entirely new counterparty type: autonomous AI buyer agents.**

The spending mandate becomes a **living object**:
1. Every clean transaction earns trust and incrementally expands limits.
2. Every overreach or anomaly is gated pre-payment and penalizes the score.
3. Every single decision is explainable from the append-only audit log alone.

---

## 2. System Architecture

```
                    ┌─────────────────────────┐
                    │   AI Buyer Agent        │  (LLM + tool-calling:
                    │  "buy a blue tee        │   list_products,
                    │   under ₹1000"          │   get_product,
                    │                         │   attempt_purchase)
                    └───────────┬─────────────┘
                                │ tool calls
                                ▼
                    ┌─────────────────────────┐
                    │     Catalog Service     │  GET /catalog, /catalog/:id
                    └───────────┬─────────────┘
                                │ product chosen
                                ▼
                    ┌─────────────────────────┐
                    │      Mandate Gate       │  ◄── 100% DETERMINISTIC (NO LLM)
                    │  (checks tier limits,   │      Enforces: per-txn cap,
                    │   category, daily cap)  │      daily cap, category allowlist
                    └───────────┬─────────────┘
                     allow │        │ block
                           ▼        ▼
                ┌──────────────┐  ┌─────────────────────────┐
                │ Razorpay Test│  │ Append-Only Audit Log   │
                │ Orders API / │  │ Explainable Rule Reason │
                │ Simulator    │  │ (Score -15 / -25)       │
                └──────┬───────┘  └─────────────────────────┘
                       │ success / failure
                       ▼
                ┌─────────────────────────┐
                │   Trust Score Engine    │  ◄── 100% DETERMINISTIC (NO LLM)
                │  (updates score + tier) │      Clamped [0, 100]
                └───────────┬─────────────┘
                            ▼
                ┌─────────────────────────┐
                │  Interactive Dashboard  │  (Live Score Gauge, Mandate Matrix,
                │   & Audit Log Feed      │   4-Beat Pitch Demo Controller)
                └─────────────────────────┘
```

---

## 3. How TrustRail Satisfies the Track 01 Evaluation Criteria

| Requirement | How TrustRail Satisfies It |
|---|---|
| **Every money action explainable** | Every gate decision (allow/block/error) logs the exact rule that fired: current tier, per-txn limit, daily spend budget, requested amount, category, and human-readable explanation. |
| **Bounded & Gated** | Hard tier-based spend caps + category allowlists are enforced deterministically before any Razorpay API call is made. The agent never communicates with Razorpay directly. |
| **Audit Trail** | Full append-only event log (in-memory + `audit_trail.jsonl`): timestamped, queryable, with `score_before`, `score_after`, `tier_before`, `tier_after`, and rule reasons. |
| **One Failure Handled Gracefully** | Simulated Razorpay payment gateway socket timeout (HTTP 504) executes 1 retry after 200ms delay → clean abort with logged reason and **zero trust penalty** applied. |
| **AI Judgment (Razorpay's Explicit Criterion)** | The trust engine and mandate gate are **100% deterministic rule-based code — zero LLM in the scoring or enforcement path**. The LLM is used only where it adds genuine value: interpreting natural language shopping tasks and invoking tools. Razorpay explicitly penalizes forcing AI where deterministic rules suffice. |
| **Problem Taste** | Solves the real friction in agentic commerce (counterparty trust & dynamic underwriting) rather than building an imported chatbot gimmick. |
| **Failure Recovery Narrative** | Documented and engineered failure recovery distinguishing system faults from agent misbehavior (detailed below). |

---

## 4. The Failure Recovery Story

Razorpay's evaluation explicitly looks for a documented failure-recovery narrative:

### What Broke:
During integration testing of external payment gateways, network instability or upstream socket timeouts (HTTP 504 Gateway Timeout) can cause the Orders API call to drop mid-flight. In our test suite, this is deterministically triggered on SKUs ending in `.13` (e.g., `prod_fail_timeout` at ₹499.13) or with the `simulate_failure=True` flag.

### How the System Responded:
1. When the initial order call fails with a socket timeout, the `RazorpayClient` wrapper catches the exception and initiates **exactly one retry** after a 200ms backoff.
2. If the second attempt also fails, TrustRail cleanly aborts the transaction without hanging or charging funds.
3. The Mandate Gate logs an audit event:
   ```json
   {
     "event_type": "system_failure",
     "decision": "error",
     "reason": "Payment provider timed out after 1 retry — transaction aborted, no charge made",
     "score_before": 50,
     "score_after": 50,
     "trust_penalty": 0
   }
   ```
4. **CRITICAL DESIGN POINT — ZERO TRUST PENALTY:** The agent's trust score remains completely intact (`score_delta: 0`).

### Why This Design Choice (AI Judgment):
Distinguishing **"agent violated its mandate"** (penalized) from **"payment infrastructure failed"** (not penalized) is central to sound financial engineering:
- If an agent attempts to buy a ₹8,999 luxury watch on a ₹2,000 cap, it has intentionally violated its mandate → **-15 penalty**.
- If the payment provider drops a TCP connection, the agent did nothing wrong → **0 penalty**.
A naive system that conflates transaction failure with agent misbehavior would unfairly degrade an agent's creditworthiness due to upstream third-party downtime.

---

## 5. Trust Engine & Mandate Specification

### 5.1 Deterministic Tiers & Living Mandates

| Tier | Score Range | Per-Txn Cap | Daily Cap | Permitted Categories |
|---|---|---|---|---|
| **Bronze** | 0–39 | ₹500 | ₹1,000 | `["essentials"]` |
| **Silver** (Default) | 40–69 | ₹2,000 | ₹5,000 | `["essentials", "apparel", "electronics"]` |
| **Gold** | 70–100 | ₹10,000 | ₹25,000 | All categories (`["*"]`) |

New agents start at score **50** (Silver midpoint) for instant demoability.

### 5.2 Deterministic Score Adjustments

| Event | Score Delta | System Rationale |
|---|---|---|
| **Clean Transaction Completed** | **+8** | Incentivizes continuous compliant behavior |
| **Attempted Mandate Overreach** | **-15** | Penalizes overreach attempts before money moves |
| **Anomaly Flag (3+ blocks in 60s)** | **-25** | Rule-based abuse detection for rogue agents |
| **System Failure (Gateway Timeout)** | **0** | Zero penalty; distinguishes system fault from agent fault |

Score is clamped strictly to `[0, 100]`. Authority tier is recomputed immediately upon score change.

---

## 6. Project Structure

```
RazorPay/
├── README.md                          # Architecture, evaluation criteria, failure recovery
├── backend/
│   ├── main.py                        # FastAPI entrypoint, CORS, static mounting
│   ├── config.py                      # Tiers, score deltas, Razorpay settings
│   ├── catalog/
│   │   ├── models.py                  # Product schema
│   │   ├── seed_data.py               # Seed catalog (essentials, apparel, electronics, luxury)
│   │   └── service.py                 # Product querying and filtering
│   ├── trust_engine/
│   │   ├── models.py                  # Agent, MandateView, Transaction
│   │   └── engine.py                  # Pure deterministic scoring, clamping, anomaly detection
│   ├── razorpay_client/
│   │   └── client.py                  # Razorpay Orders API client + 1-retry failure recovery
│   ├── gate/
│   │   └── mandate_gate.py            # Pre-payment enforcement (per-txn, category, daily cap)
│   ├── audit/
│   │   └── logger.py                  # Append-only audit logger & query aggregations
│   └── api/
│       └── routes.py                  # /catalog, /agent/:id/*, /audit, /demo/*
├── agent/
│   ├── tools.py                       # 3 function tools: list_products, get_product, attempt_purchase
│   └── agent_runner.py                # AI Buyer Agent shopping loop and honest reporting
├── dashboard/
│   ├── index.html                     # Modern glassmorphic web dashboard
│   ├── style.css                      # Custom dark mode design system (Razorpay blue palette)
│   └── app.js                         # SVG circular gauge, live audit feed, 4-beat controller
├── tests/
│   ├── test_trust_engine.py           # Unit tests: tiers, clamping, anomaly triggers
│   ├── test_mandate_gate.py           # Unit tests: per-txn caps, categories, daily budgets
│   ├── test_failure_recovery.py       # Unit tests: timeout, 1-retry, zero penalty abort
│   └── test_agent_runner.py           # Unit tests: agent tool calling and honest explanations
└── demo/
    └── pitch_script.md                # 4-beat 45-second pitch video script
```

---

## 7. Quickstart & Local Setup

### Prerequisites
- Python 3.10+
- `fastapi`, `uvicorn`, `httpx`, `pytest`, `pydantic` (all standard)

### 1. Run the Automated Test Suite
```bash
python -m pytest tests/ -v
```
*Output: All 18 tests passing covering scoring, clamping, gating, anomaly detection, failure recovery, and agent tool execution.*

### 2. Start the TrustRail Server & Web Dashboard
```bash
python -m backend.main
```
The server will start on `http://localhost:8000`.

### 3. Open the Dashboard in your Browser
Navigate to **`http://localhost:8000/`** to interact with the real-time dashboard:
- Watch the **Circular Trust Score Gauge** and **Live Mandate Matrix**.
- Trigger the **4 Demo Beats** with 1 click.
- Test the **Autonomous AI Buyer Agent Terminal** with custom natural language prompts.
- Inspect the **Append-Only Audit Trail**.
- Compare mandates across tiers in the **Multi-Agent Comparison Matrix**.

### 4. Razorpay Test-Mode Credentials (Optional)
TrustRail includes a built-in sandbox simulator for immediate offline demoing. To test against live Razorpay test-mode API:
```bash
export RAZORPAY_KEY_ID="rzp_test_YourKeyId"
export RAZORPAY_KEY_SECRET="YourKeySecret"
python -m backend.main
```

---

## 8. API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/catalog` | List catalog products (optional `?category=` and `?max_price=`) |
| `GET` | `/catalog/{id}` | Retrieve individual product specifications |
| `POST` | `/agent/{id}/purchase` | Attempt purchase through Mandate Gate → Razorpay → Trust Engine |
| `GET` | `/agent/{id}/status` | Get current trust score, authority tier, and live mandate limits |
| `POST` | `/agent/{id}/run-task` | Execute autonomous AI agent shopping loop for a user task prompt |
| `POST` | `/agent/{id}/reset` | Reset agent state to baseline score 50 (Silver) |
| `GET` | `/audit` | Query append-only audit trail (optional `?agent_id=` and `?limit=`) |
| `GET` | `/audit/{id}/summary` | Retrieve score progression history for charting |
| `POST` | `/demo/scenario/{beat}` | One-click demo beat triggers (`beat1_clean`, `beat2_tierup`, etc.) |
| `GET` | `/agents/comparison` | Live comparative status across Bronze, Silver, and Gold agents |

---

## 9. Track 01 Pitch Video Script

Refer to [`demo/pitch_script.md`](demo/pitch_script.md) for the verbatim 4-beat, 45-second script matching Razorpay's judging rubric.
