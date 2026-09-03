/**
 * TrustRail Interactive Dashboard Logic
 * Real-time gauge updates, 4-beat demo controller, agent runner, and explainable audit feed.
 */

const STATE = {
  activeAgentId: "agent_001",
  auditFilter: "all",
  cachedLogs: [],
  previousScore: 50,
};

// DOM Elements
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
  mandatePerTxnCap: document.getElementById("mandatePerTxnCap"),
  mandateDailyCap: document.getElementById("mandateDailyCap"),
  mandateDailyRemaining: document.getElementById("mandateDailyRemaining"),
  categoryTagsContainer: document.getElementById("categoryTagsContainer"),
  
  // Beats
  btnBeat1: document.getElementById("btnBeat1"),
  btnBeat2: document.getElementById("btnBeat2"),
  btnBeat3: document.getElementById("btnBeat3"),
  btnBeat4: document.getElementById("btnBeat4"),

  // Terminal & Prompt
  agentPromptInput: document.getElementById("agentPromptInput"),
  btnSendPrompt: document.getElementById("btnSendPrompt"),
  terminalBody: document.getElementById("terminalBody"),
  btnClearTerminal: document.getElementById("btnClearTerminal"),
  quickPromptChips: document.querySelectorAll(".chip-btn"),

  // Audit Feed
  auditLogFeed: document.getElementById("auditLogFeed"),
  filterBtns: document.querySelectorAll(".filter-btn"),
};

// ==========================================
// Initialization
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  refreshAll();
  // Poll periodically for live changes
  setInterval(() => {
    refreshAgentStatus(false);
    refreshAuditTrail(false);
  }, 3000);
});

function setupEventListeners() {
  // Agent selection
  el.agentSelect.addEventListener("change", (e) => {
    STATE.activeAgentId = e.target.value;
    logToTerminal("system", `Switched active agent to: ${STATE.activeAgentId}`);
    refreshAll();
  });

  // Reset button
  el.btnResetAgent.addEventListener("click", resetCurrentAgent);

  // 4 Beats
  el.btnBeat1.addEventListener("click", () => runDemoScenario("beat1_clean"));
  el.btnBeat2.addEventListener("click", () => runDemoScenario("beat2_tierup"));
  el.btnBeat3.addEventListener("click", () => runDemoScenario("beat3_blocked"));
  el.btnBeat4.addEventListener("click", () => runDemoScenario("beat4_failure"));

  // Task Runner
  el.btnSendPrompt.addEventListener("click", handleSendPrompt);
  el.agentPromptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleSendPrompt();
  });

  el.quickPromptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const promptText = chip.getAttribute("data-prompt");
      el.agentPromptInput.value = promptText;
      handleSendPrompt();
    });
  });

  el.btnClearTerminal.addEventListener("click", () => {
    el.terminalBody.innerHTML = `
      <div class="terminal-line system-line">
        <span class="t-time">[SYS]</span> Terminal cleared. Ready for agent shopping instructions.
      </div>
    `;
  });

  // Audit Filter
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
// API Interaction & State Updates
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
    console.error("Failed to fetch agent status:", err);
  }
}

function renderAgentStatus(data, animate = true) {
  const score = data.trust_score;
  const tier = data.tier.toLowerCase();
  const mandate = data.mandate;

  // Render Numeric Score & Gauge Fill
  el.scoreValue.textContent = score;

  // 314 is circumference of r=50 circle (2 * PI * 50)
  const offset = 314 - (314 * score) / 100;
  el.gaugeProgress.style.strokeDashoffset = offset;

  // Gauge Color by Tier
  if (tier === "gold") {
    el.gaugeProgress.style.stroke = "var(--tier-gold)";
  } else if (tier === "silver") {
    el.gaugeProgress.style.stroke = "var(--rzp-blue)";
  } else {
    el.gaugeProgress.style.stroke = "var(--tier-bronze)";
  }

  // Delta Badge
  const delta = score - STATE.previousScore;
  if (delta > 0) {
    el.scoreDeltaBadge.textContent = `+${delta}`;
    el.scoreDeltaBadge.className = "delta-badge delta-positive";
  } else if (delta < 0) {
    el.scoreDeltaBadge.textContent = `${delta}`;
    el.scoreDeltaBadge.className = "delta-badge delta-negative";
  } else {
    el.scoreDeltaBadge.textContent = "±0";
    el.scoreDeltaBadge.className = "delta-badge delta-neutral";
  }
  STATE.previousScore = score;

  // Tier Status Pill & Emoji
  el.tierBadge.textContent = tier.toUpperCase();
  el.tierBadge.className = `tier-pill tier-${tier}`;

  if (tier === "gold") {
    el.tierEmoji.textContent = "🥇";
    el.tierProgressBar.style.width = "100%";
    el.tierPromotionHint.innerHTML = "Authority: <strong>Gold (Maximum Authority)</strong>. All categories unlocked.";
  } else if (tier === "silver") {
    el.tierEmoji.textContent = "🥈";
    const percent = Math.min(100, Math.max(0, ((score - 40) / 30) * 100));
    el.tierProgressBar.style.width = `${percent}%`;
    const remaining = 70 - score;
    el.tierPromotionHint.innerHTML = `Need <strong>${remaining} more pts</strong> to reach Gold Tier.`;
  } else {
    el.tierEmoji.textContent = "🥉";
    const percent = Math.min(100, Math.max(0, (score / 40) * 100));
    el.tierProgressBar.style.width = `${percent}%`;
    const remaining = 40 - score;
    el.tierPromotionHint.innerHTML = `Need <strong>${remaining} more pts</strong> to reach Silver Tier.`;
  }

  // Mandate Limits
  el.mandatePerTxnCap.textContent = `₹${mandate.per_txn_cap.toLocaleString("en-IN")}`;
  el.mandateDailyCap.textContent = `₹${mandate.daily_cap.toLocaleString("en-IN")}`;
  el.mandateDailyRemaining.textContent = `₹${mandate.daily_remaining.toLocaleString("en-IN")} remaining today`;

  // Category tags
  renderCategoryTags(mandate.allowed_categories, mandate.is_category_unrestricted);
}

function renderCategoryTags(allowedCategories, isUnrestricted) {
  const allKnownCategories = ["essentials", "apparel", "electronics", "luxury"];
  el.categoryTagsContainer.innerHTML = "";

  allKnownCategories.forEach((cat) => {
    const isAllowed = isUnrestricted || allowedCategories.includes(cat);
    const span = document.createElement("span");
    span.className = `cat-tag ${isAllowed ? "active" : "disabled"}`;
    span.textContent = isAllowed ? `✓ ${cat}` : `✕ ${cat} (locked)`;
    el.categoryTagsContainer.appendChild(span);
  });
}

async function refreshAuditTrail(showEmpty = false) {
  try {
    const res = await fetch(`/api/audit?agent_id=${STATE.activeAgentId}&limit=50`);
    if (!res.ok) return;
    const logs = await res.json();
    STATE.cachedLogs = logs;
    renderAuditLogs(logs);
  } catch (err) {
    console.error("Failed to fetch audit logs:", err);
  }
}

function renderAuditLogs(logs) {
  let filtered = logs;
  if (STATE.auditFilter !== "all") {
    filtered = logs.filter((l) => l.decision.toLowerCase() === STATE.auditFilter.toLowerCase());
  }

  if (filtered.length === 0) {
    el.auditLogFeed.innerHTML = `<div class="empty-state">No audit events match current filter.</div>`;
    return;
  }

  el.auditLogFeed.innerHTML = "";
  filtered.forEach((entry) => {
    const card = document.createElement("div");
    const dec = entry.decision.toLowerCase();
    card.className = `audit-entry-card border-${dec}`;

    const dateStr = new Date(entry.timestamp).toLocaleTimeString();
    const scoreDiff = entry.score_after - entry.score_before;
    const diffDisplay = scoreDiff > 0 ? `+${scoreDiff}` : scoreDiff === 0 ? "±0" : `${scoreDiff}`;

    card.innerHTML = `
      <div class="entry-top-row">
        <span class="entry-badge entry-${dec}">${entry.decision}</span>
        <span class="entry-time">${dateStr} • ${entry.txn_id || "GATE-BLOCK"}</span>
      </div>
      <div class="entry-reason">
        ${entry.reason}
      </div>
      <div class="entry-meta-row">
        <span>Score: ${entry.score_before} → <strong>${entry.score_after}</strong> (${diffDisplay})</span>
        <span>Tier: ${entry.tier_before.toUpperCase()} → <strong>${entry.tier_after.toUpperCase()}</strong></span>
      </div>
    `;
    el.auditLogFeed.appendChild(card);
  });
}

// ==========================================
// Demo Beats Execution
// ==========================================

async function runDemoScenario(scenarioName) {
  try {
    logToTerminal("system", `Executing Demo Scenario: [${scenarioName}]...`);
    const res = await fetch(`/api/demo/scenario/${scenarioName}?agent_id=${STATE.activeAgentId}`, {
      method: "POST",
    });
    const data = await res.json();

    if (data.beat === 1) {
      logToTerminal("allowed", `[BEAT 1 PASS] ${data.description}`);
      logToTerminal("detail", `Order ID: ${data.result.razorpay_order_id} | Score: ${data.result.score_before} -> ${data.result.score_after} (+${data.result.score_delta})`);
    } else if (data.beat === 2) {
      logToTerminal("allowed", `[BEAT 2 TIER-UP] ${data.description}`);
      logToTerminal("detail", `Agent promoted to: ${data.current_tier.toUpperCase()} with Score: ${data.current_score}!`);
    } else if (data.beat === 3) {
      logToTerminal("blocked", `[BEAT 3 BLOCKED] ${data.description}`);
      logToTerminal("detail", `Gate Rule: "${data.result.reason}" | Score: ${data.result.score_before} -> ${data.result.score_after} (${data.result.score_delta})`);
    } else if (data.beat === 4) {
      logToTerminal("error", `[BEAT 4 FAILURE RECOVERY] ${data.description}`);
      logToTerminal("detail", `Result: 1 retry executed -> Clean abort -> Trust Score UNCHANGED (0 penalty applied!)`);
    }

    await refreshAll();
  } catch (err) {
    logToTerminal("error", `Failed to execute beat: ${err.message}`);
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
    console.error("Reset failed:", err);
  }
}

// ==========================================
// AI Buyer Agent Shopping Loop
// ==========================================

async function handleSendPrompt() {
  const prompt = el.agentPromptInput.value.trim();
  if (!prompt) return;
  el.agentPromptInput.value = "";

  logToTerminal("user", `User Prompt: "${prompt}"`);
  logToTerminal("system", `AI Buyer Agent analyzing intent and initiating tool calling...`);

  try {
    const res = await fetch(`/api/agent/${STATE.activeAgentId}/run-task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: prompt }),
    });
    const data = await res.json();

    // Render step-by-step tool traces
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

    // Render Agent's customer-facing final reply
    logToTerminal("agent-reply", `💬 Agent: ${data.final_response}`);
    await refreshAll();
  } catch (err) {
    logToTerminal("error", `Agent execution error: ${err.message}`);
  }
}

function logToTerminal(type, text) {
  const line = document.createElement("div");
  const time = new Date().toLocaleTimeString();

  if (type === "user") {
    line.className = "terminal-line user-line";
    line.innerHTML = `<span class="t-prompt">👤</span> ${escapeHtml(text)}`;
  } else if (type === "system") {
    line.className = "terminal-line system-line";
    line.innerHTML = `<span class="t-time">[${time}]</span> ${escapeHtml(text)}`;
  } else if (type === "tool") {
    line.className = "terminal-line tool-call-line";
    line.innerHTML = `<span class="t-prompt">🔧</span> ${escapeHtml(text)}`;
  } else if (type === "allowed") {
    line.className = "terminal-line gate-allowed-line";
    line.innerHTML = `<span class="t-prompt">✅</span> ${escapeHtml(text)}`;
  } else if (type === "blocked") {
    line.className = "terminal-line gate-blocked-line";
    line.innerHTML = `<span class="t-prompt">🛡️</span> ${escapeHtml(text)}`;
  } else if (type === "error") {
    line.className = "terminal-line gate-error-line";
    line.innerHTML = `<span class="t-prompt">⚠️</span> ${escapeHtml(text)}`;
  } else if (type === "agent-reply") {
    line.className = "terminal-line agent-reply-line";
    line.innerHTML = `${escapeHtml(text)}`;
  } else {
    line.className = "terminal-line hint-line";
    line.innerHTML = `<span class="t-prompt">↳</span> ${escapeHtml(text)}`;
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
