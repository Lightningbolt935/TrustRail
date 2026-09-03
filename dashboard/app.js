/**
 * TrustRail — Apple Cupertino Interactive Experience
 * Precision Activity Ring, Living Mandate Matrix, 4-Beat Controller, and Audit Ledger.
 */

const STATE = {
  activeAgentId: "agent_001",
  auditFilter: "all",
  cachedLogs: [],
  previousScore: 50,
};

// DOM Cache
const el = {
  agentSelect: document.getElementById("agentSelect"),
  btnResetAgent: document.getElementById("btnResetAgent"),
  scoreValue: document.getElementById("scoreValue"),
  scoreDeltaBadge: document.getElementById("scoreDeltaBadge"),
  gaugeProgress: document.getElementById("gaugeProgress"),
  tierBadge: document.getElementById("tierBadge"),
  tierEmoji: document.getElementById("tierEmoji"),
  tierProgressBar: document.getElementById("tierProgressBar"),
  tierPromotionHint: document.getElementById("tierPromotionHint"),
  tierPrivilegeSummary: document.getElementById("tierPrivilegeSummary"),
  
  // Timeline Steps
  stepBronze: document.getElementById("stepBronze"),
  stepSilver: document.getElementById("stepSilver"),
  stepGold: document.getElementById("stepGold"),

  // Mandate
  mandatePerTxnCap: document.getElementById("mandatePerTxnCap"),
  mandateDailyCap: document.getElementById("mandateDailyCap"),
  mandateDailyRemaining: document.getElementById("mandateDailyRemaining"),
  spendBarFill: document.getElementById("spendBarFill"),
  spendPercentLabel: document.getElementById("spendPercentLabel"),
  categoryTagsContainer: document.getElementById("categoryTagsContainer"),

  // 4 Beats
  btnBeat1: document.getElementById("btnBeat1"),
  btnBeat2: document.getElementById("btnBeat2"),
  btnBeat3: document.getElementById("btnBeat3"),
  btnBeat4: document.getElementById("btnBeat4"),

  // Linear Command Bar & Terminal
  agentPromptInput: document.getElementById("agentPromptInput"),
  btnSendPrompt: document.getElementById("btnSendPrompt"),
  terminalBody: document.getElementById("terminalBody"),
  btnClearTerminal: document.getElementById("btnClearTerminal"),
  quickPromptChips: document.querySelectorAll(".chip-item"),

  // Audit Feed
  auditLogFeed: document.getElementById("auditLogFeed"),
  filterBtns: document.querySelectorAll(".seg-item"),
};

// ==========================================
// Initialization
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  refreshAll();

  // Gentle Cupertino polling for ledger updates
  setInterval(() => {
    refreshAgentStatus(false);
    refreshAuditTrail(false);
  }, 2500);
});

function setupEventListeners() {
  // Agent Selection
  el.agentSelect.addEventListener("change", (e) => {
    STATE.activeAgentId = e.target.value;
    logToTerminal("system", `Active agent switched to ${STATE.activeAgentId}. Synchronizing mandate ledger.`);
    refreshAll();
  });

  // Reset Button
  el.btnResetAgent.addEventListener("click", resetCurrentAgent);

  // 4 Demo Beats
  el.btnBeat1.addEventListener("click", () => runDemoScenario("beat1_clean"));
  el.btnBeat2.addEventListener("click", () => runDemoScenario("beat2_tierup"));
  el.btnBeat3.addEventListener("click", () => runDemoScenario("beat3_blocked"));
  el.btnBeat4.addEventListener("click", () => runDemoScenario("beat4_failure"));

  // Command input
  el.btnSendPrompt.addEventListener("click", handleSendPrompt);
  el.agentPromptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSendPrompt();
  });

  // Quick chips
  el.quickPromptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const promptText = chip.getAttribute("data-prompt");
      el.agentPromptInput.value = promptText;
      handleSendPrompt();
    });
  });

  // Terminal Clear
  el.btnClearTerminal.addEventListener("click", () => {
    el.terminalBody.innerHTML = `
      <div class="console-line line-sys">
        <span class="c-tag">[SYSTEM]</span> Console cleared. Ready for agent shopping instructions.
      </div>
    `;
  });

  // Segmented Audit Filter
  el.filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      el.filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      STATE.auditFilter = btn.getAttribute("data-filter");
      renderAuditLogs(STATE.cachedLogs);
    });
  });
}

// ==========================================
// State Synchronization
// ==========================================

async function refreshAll() {
  await refreshAgentStatus(true);
  await refreshAuditTrail(true);
}

async function refreshAgentStatus(showAnimation = true) {
  try {
    const res = await fetch(`/api/agent/${STATE.activeAgentId}/status`);
    if (!res.ok) return;
    const data = await res.json();
    renderAgentStatus(data, showAnimation);
  } catch (err) {
    console.error("Status fetch error:", err);
  }
}

function renderAgentStatus(data) {
  const score = data.trust_score;
  const tier = data.tier.toLowerCase();
  const mandate = data.mandate;

  // 1. Numeric Score
  el.scoreValue.textContent = score;

  // 2. Activity Ring Fill (Circumference = 2 * PI * 66 = 415)
  const circumference = 415;
  const offset = circumference - (circumference * score) / 100;
  el.gaugeProgress.style.strokeDashoffset = offset;

  // Dynamic Ring Gradient Stroke
  if (tier === "gold") {
    el.gaugeProgress.style.stroke = "url(#ringGold)";
  } else if (tier === "silver") {
    el.gaugeProgress.style.stroke = "url(#ringSilver)";
  } else {
    el.gaugeProgress.style.stroke = "url(#ringBronze)";
  }

  // 3. Score Delta Pill
  const delta = score - STATE.previousScore;
  if (delta > 0) {
    el.scoreDeltaBadge.textContent = `+${delta}`;
    el.scoreDeltaBadge.className = "apple-badge badge-green";
  } else if (delta < 0) {
    el.scoreDeltaBadge.textContent = `${delta}`;
    el.scoreDeltaBadge.className = "apple-badge badge-red";
  } else {
    el.scoreDeltaBadge.textContent = "±0";
    el.scoreDeltaBadge.className = "apple-badge badge-neutral";
  }
  STATE.previousScore = score;

  // 4. Tier Badge & Status
  el.tierBadge.textContent = tier.toUpperCase();
  el.tierBadge.className = `tier-pill-label tier-${tier}`;

  // Update Progression Steps UI
  updateProgressionUI(tier, score);

  // 5. Mandate Display & Spend Utilization
  el.mandatePerTxnCap.textContent = `₹${mandate.per_txn_cap.toLocaleString("en-IN")}`;
  el.mandateDailyCap.textContent = `₹${mandate.daily_cap.toLocaleString("en-IN")}`;
  el.mandateDailyRemaining.textContent = `₹${mandate.daily_remaining.toLocaleString("en-IN")} remaining`;

  const spendUsed = mandate.daily_spent_today;
  const totalCap = mandate.daily_cap;
  const spendPercent = totalCap > 0 ? Math.min(100, Math.round((spendUsed / totalCap) * 100)) : 0;
  el.spendBarFill.style.width = `${spendPercent}%`;
  el.spendPercentLabel.textContent = `${spendPercent}% (₹${spendUsed.toLocaleString("en-IN")} used)`;

  // Category tags
  renderCategoryTags(mandate.allowed_categories, mandate.is_category_unrestricted);
}

function updateProgressionUI(tier, score) {
  // Clear step active states
  el.stepBronze.classList.remove("active-tier");
  el.stepSilver.classList.remove("active-tier");
  el.stepGold.classList.remove("active-tier");

  if (tier === "gold") {
    el.tierEmoji.textContent = "GOLD";
    el.stepGold.classList.add("active-tier");
    el.stepSilver.classList.add("active-tier");
    el.stepBronze.classList.add("active-tier");
    el.tierProgressBar.style.width = "100%";
    el.tierPromotionHint.innerHTML = "Authority: <strong>Gold (Maximum Authority)</strong>. All categories unlocked.";
    el.tierPrivilegeSummary.textContent = "Per-Txn Cap: ₹10,000 • Daily Cap: ₹25,000 • All Categories Unlocked (Luxury, Tech, Essentials).";
  } else if (tier === "silver") {
    el.tierEmoji.textContent = "SILVER";
    el.stepSilver.classList.add("active-tier");
    el.stepBronze.classList.add("active-tier");
    const percent = Math.min(100, Math.max(0, ((score - 40) / 30) * 100));
    el.tierProgressBar.style.width = `${percent}%`;
    const remaining = 70 - score;
    el.tierPromotionHint.innerHTML = `Need <strong>${remaining} more pts</strong> to reach Gold Tier.`;
    el.tierPrivilegeSummary.textContent = "Per-Txn Cap: ₹2,000 • Daily Cap: ₹5,000 • Essentials, Apparel, Electronics permitted.";
  } else {
    el.tierEmoji.textContent = "BRONZE";
    el.stepBronze.classList.add("active-tier");
    const percent = Math.min(100, Math.max(0, (score / 40) * 100));
    el.tierProgressBar.style.width = `${percent}%`;
    const remaining = 40 - score;
    el.tierPromotionHint.innerHTML = `Need <strong>${remaining} more pts</strong> to reach Silver Tier.`;
    el.tierPrivilegeSummary.textContent = "Per-Txn Cap: ₹500 • Daily Cap: ₹1,000 • Essentials only. Higher categories locked.";
  }
}

function renderCategoryTags(allowedCategories, isUnrestricted) {
  const allKnownCategories = ["essentials", "apparel", "electronics", "luxury"];
  el.categoryTagsContainer.innerHTML = "";

  allKnownCategories.forEach((cat) => {
    const isAllowed = isUnrestricted || allowedCategories.includes(cat);
    const span = document.createElement("span");
    span.className = `apple-cat-pill ${isAllowed ? "pill-on" : "pill-off"}`;
    span.textContent = isAllowed ? `✓ ${cat}` : `✕ ${cat} (locked)`;
    el.categoryTagsContainer.appendChild(span);
  });
}

// ==========================================
// Audit Stream Feed
// ==========================================

async function refreshAuditTrail() {
  try {
    const res = await fetch(`/api/audit?agent_id=${STATE.activeAgentId}&limit=50`);
    if (!res.ok) return;
    const logs = await res.json();
    STATE.cachedLogs = logs;
    renderAuditLogs(logs);
  } catch (err) {
    console.error("Audit fetch error:", err);
  }
}

function renderAuditLogs(logs) {
  let filtered = logs;
  if (STATE.auditFilter !== "all") {
    filtered = logs.filter((l) => l.decision.toLowerCase() === STATE.auditFilter.toLowerCase());
  }

  if (filtered.length === 0) {
    el.auditLogFeed.innerHTML = `<div class="audit-empty-state">No ledger events recorded under this filter.</div>`;
    return;
  }

  el.auditLogFeed.innerHTML = "";
  filtered.forEach((entry) => {
    const card = document.createElement("div");
    const dec = entry.decision.toLowerCase();
    card.className = `audit-item edge-${dec}`;

    const dateStr = new Date(entry.timestamp).toLocaleTimeString();
    const scoreDiff = entry.score_after - entry.score_before;
    const diffDisplay = scoreDiff > 0 ? `+${scoreDiff}` : scoreDiff === 0 ? "±0" : `${scoreDiff}`;

    card.innerHTML = `
      <div class="audit-top-row">
        <span class="audit-badge ${dec}">${entry.decision}</span>
        <span class="audit-time">${dateStr} • ${entry.txn_id || "GATE-BLOCK"}</span>
      </div>
      <div class="audit-reason-text">
        ${entry.reason}
      </div>
      <div class="audit-footer-row">
        <span>Score: ${entry.score_before} → <strong>${entry.score_after}</strong> (${diffDisplay})</span>
        <span>Tier: ${entry.tier_before.toUpperCase()} → <strong>${entry.tier_after.toUpperCase()}</strong></span>
      </div>
    `;
    el.auditLogFeed.appendChild(card);
  });
}

// ==========================================
// 4 Demo Beats Execution
// ==========================================

async function runDemoScenario(scenarioName) {
  try {
    logToTerminal("system", `Triggering demo sequence: [${scenarioName}]`);
    const res = await fetch(`/api/demo/scenario/${scenarioName}?agent_id=${STATE.activeAgentId}`, {
      method: "POST",
    });
    const data = await res.json();

    if (data.beat === 1) {
      logToTerminal("allowed", `[BEAT 1 APPROVED] ${data.description}`);
      logToTerminal("detail", `Order ID: ${data.result.razorpay_order_id} • Score: ${data.result.score_before} → ${data.result.score_after} (+${data.result.score_delta})`);
    } else if (data.beat === 2) {
      logToTerminal("allowed", `[BEAT 2 TIER-UP] ${data.description}`);
      logToTerminal("detail", `Promoted to ${data.current_tier.toUpperCase()} with Score ${data.current_score}. Mandate expanded.`);
    } else if (data.beat === 3) {
      logToTerminal("blocked", `[BEAT 3 BLOCKED] ${data.description}`);
      logToTerminal("detail", `Rule: "${data.result.reason}" • Score: ${data.result.score_before} → ${data.result.score_after} (${data.result.score_delta})`);
    } else if (data.beat === 4) {
      logToTerminal("error", `[BEAT 4 RESILIENCE] ${data.description}`);
      logToTerminal("detail", `1 retry executed → Clean abort. Trust score UNCHANGED at ${data.result.score_after} (0 penalty).`);
    }

    await refreshAll();
  } catch (err) {
    logToTerminal("error", `Demo beat failed: ${err.message}`);
  }
}

async function resetCurrentAgent() {
  try {
    const res = await fetch(`/api/agent/${STATE.activeAgentId}/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: 50 }),
    });
    const data = await res.json();
    logToTerminal("system", `Agent ${STATE.activeAgentId} reset to baseline score 50 (Silver Tier).`);
    await refreshAll();
  } catch (err) {
    console.error("Reset error:", err);
  }
}

// ==========================================
// Autonomous Agent Runner
// ==========================================

async function handleSendPrompt() {
  const prompt = el.agentPromptInput.value.trim();
  if (!prompt) return;
  el.agentPromptInput.value = "";

  logToTerminal("user", `User Prompt: "${prompt}"`);
  logToTerminal("system", `Agent initiating autonomous tool-calling loop...`);

  try {
    const res = await fetch(`/api/agent/${STATE.activeAgentId}/run-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: prompt }),
    });
    const data = await res.json();

    if (data.steps) {
      data.steps.forEach((st) => {
        if (st.action === "call_tool") {
          logToTerminal("tool", `[Tool Call] ${st.tool}(${JSON.stringify(st.arguments)}) — ${st.thought}`);
        } else if (st.action === "tool_result") {
          if (st.tool === "attempt_purchase") {
            const dec = st.gate_decision;
            if (dec === "allowed") {
              logToTerminal("allowed", `[Mandate Gate PASS] ${st.reason} (Order: ${st.razorpay_order_id})`);
            } else if (dec === "blocked") {
              logToTerminal("blocked", `[Mandate Gate BLOCKED] ${st.reason}`);
            } else {
              logToTerminal("error", `[Payment Provider ERROR] ${st.reason}`);
            }
          } else {
            logToTerminal("detail", `[Tool Result] ${st.result_summary || JSON.stringify(st.candidates || {})}`);
          }
        }
      });
    }

    logToTerminal("reply", `💬 Agent: ${data.final_response}`);
    await refreshAll();
  } catch (err) {
    logToTerminal("error", `Agent loop error: ${err.message}`);
  }
}

function logToTerminal(type, text) {
  const line = document.createElement("div");
  const time = new Date().toLocaleTimeString();

  if (type === "user") {
    line.className = "console-line line-user";
    line.innerHTML = `<span class="c-prompt">👤 User:</span> ${escapeHtml(text)}`;
  } else if (type === "system") {
    line.className = "console-line line-sys";
    line.innerHTML = `<span class="c-tag">[${time}]</span> ${escapeHtml(text)}`;
  } else if (type === "tool") {
    line.className = "console-line line-tool";
    line.innerHTML = `<span class="c-prompt">⚡</span> ${escapeHtml(text)}`;
  } else if (type === "allowed") {
    line.className = "console-line line-allowed";
    line.innerHTML = `<span class="c-prompt">✓</span> ${escapeHtml(text)}`;
  } else if (type === "blocked") {
    line.className = "console-line line-blocked";
    line.innerHTML = `<span class="c-prompt">⊘</span> ${escapeHtml(text)}`;
  } else if (type === "error") {
    line.className = "console-line line-error";
    line.innerHTML = `<span class="c-prompt">⚠</span> ${escapeHtml(text)}`;
  } else if (type === "reply") {
    line.className = "console-line line-reply";
    line.innerHTML = `${escapeHtml(text)}`;
  } else {
    line.className = "console-line line-hint";
    line.innerHTML = `<span class="c-prompt">↳</span> ${escapeHtml(text)}`;
  }

  el.terminalBody.appendChild(line);
  el.terminalBody.scrollTop = el.terminalBody.scrollHeight;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
