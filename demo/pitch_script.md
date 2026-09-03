# TrustRail — 45-Second Pitch & Demo Script
**Razorpay AI Buildathon 2026 • Track 01: AI Growth & Agentic Commerce**

> This script is designed for a fast, punchy 45–60 second pitch video demonstrating the 4 core beats directly on the TrustRail interactive dashboard.

---

## 🎯 The Hook (0:00 – 0:10)
> *"Today, AI shopping agents are either trapped under rigid spend caps or given dangerous unrestricted wallets. Static caps break the moment an agent needs to handle a slightly larger cart.*  
>  
> *Meet **TrustRail**: an adaptive permission layer for AI shopping agents. Instead of a static ceiling, the mandate is a living object — an agent earns trust through clean transactions, expanding its authority automatically based on a transparent, deterministic score."*

---

## 🎬 Beat 1: Clean Transaction & Earned Trust (+8) (0:10 – 0:20)
**Action on Screen:**  
Click **`▶ Run Beat 1 (Clean Txn)`** on the Dashboard.
- The agent purchases a Blue Cotton Crewneck T-Shirt (₹799 in `apparel`).
- **Gate Check:** Within the Silver mandate (per-txn cap ₹2,000, category allowed).
- **Result:** Approved. Razorpay test order generated.
- **Score Update:** Trust score increments from **50 → 58 (+8 pts)**.

> **Voiceover / Caption:**  
> *"Our agent starts at score 50 in Silver tier. When it completes a clean purchase within its mandate, the Gate approves the transaction and rewards +8 trust points. Good behavior is explicitly incentivized."*

---

## 🎬 Beat 2: Autonomous Tier Expansion to Gold (0:20 – 0:32)
**Action on Screen:**  
Click **`▶ Run Beat 2 (Promote to Gold)`**.
- A sequence of clean transactions pushes the score across the threshold (>= 70).
- **Authority Tier Badge** turns **GOLD 🥇** with dynamic visual illumination.
- **Mandate Matrix visibly expands:**
  - Single-txn cap leaps from **₹2,000 → ₹10,000**
  - Daily spend cap expands from **₹5,000 → ₹25,000**
  - `luxury` category automatically unlocks.

> **Voiceover / Caption:**  
> *"As the agent demonstrates reliable behavior and crosses 70 points, it automatically promotes to Gold. Notice the mandate expand in real-time: the cap jumps to ₹10,000 and higher-risk categories like luxury unlock without human intervention."*

---

## 🎬 Beat 3: Blocked Overreach & Explainable Gating (0:32 – 0:42)
**Action on Screen:**  
Click **`▶ Run Beat 3 (Blocked Overreach)`**.
- While at Silver, the agent attempts to buy a Titanium Smartwatch Pro (₹8,999 in `luxury`).
- **Mandate Gate intercepts pre-Razorpay:** The request is blocked before any payment gateway call can occur.
- **Score Update:** Penalized by **-15 points** (or -25 if repeated anomaly).
- **Audit Feed:** Shows exact firing rule: `Category 'luxury' is NOT permitted under SILVER mandate.`

> **Voiceover / Caption:**  
> *"What if an agent tries to overreach? Here, it attempts to buy an unauthorized luxury item. The Mandate Gate halts it cold before Razorpay is ever touched. The overreach is logged, the reason is fully explainable, and the agent takes a -15 score penalty."*

---

## 🎬 Beat 4: Failure Recovery & AI Judgment (0:42 – 0:55)
**Action on Screen:**  
Click **`▶ Run Beat 4 (Gateway Failure)`**.
- The agent orders a test SKU triggering a simulated Razorpay gateway timeout.
- **System Behavior:** The wrapper executes exactly 1 retry → safely aborts with no charge made.
- **Score Outcome:** Trust score is **completely untouched (0 penalty applied)**.

> **Voiceover / Caption:**  
> *"Now for resilience: when Razorpay experiences a gateway timeout, TrustRail retries once and aborts cleanly. Crucially: trust score penalty is ZERO. Why? Because infrastructure failure is NOT agent misbehavior. A naive system would unfairly penalize the agent's reputation."*

---

## 🏁 The Closer (0:55 – 1:00)
> *"Notice one critical design choice: **Zero LLMs in the scoring or gating path.** The LLM is used strictly for shopping intent and tool calls, while risk enforcement is 100% deterministic code. That is agentic commerce you can trust. That is **TrustRail**."*
