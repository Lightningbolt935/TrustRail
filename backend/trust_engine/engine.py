"""
Deterministic Trust Score Engine
100% rule-based and transparent. Zero LLM in the scoring path.
"""
import time
from typing import Tuple, Dict, Optional
from backend.config import (
    Tier,
    SCORE_MIN,
    SCORE_MAX,
    SCORE_DELTA_CLEAN_TXN,
    SCORE_DELTA_BLOCKED_VIOLATION,
    SCORE_DELTA_ANOMALY,
    SCORE_DELTA_SYSTEM_FAILURE,
    ANOMALY_WINDOW_SECONDS,
    ANOMALY_THRESHOLD_BLOCKS,
    DEFAULT_STARTING_SCORE,
)
from backend.trust_engine.models import Agent


class TrustEngine:
    """Pure deterministic trust engine managing agent scores, tiers, and anomaly detection."""

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def get_tier(self, score: int) -> Tier:
        """Deterministically map numeric score [0-100] to Tier."""
        clamped = self.clamp_score(score)
        if clamped <= 39:
            return Tier.BRONZE
        elif clamped <= 69:
            return Tier.SILVER
        else:
            return Tier.GOLD

    def clamp_score(self, score: int) -> int:
        """Clamp score strictly between SCORE_MIN and SCORE_MAX."""
        return max(SCORE_MIN, min(SCORE_MAX, int(score)))

    def get_or_create_agent(self, agent_id: str, starting_score: int = DEFAULT_STARTING_SCORE) -> Agent:
        """Retrieve existing agent or register new agent at starting score."""
        if agent_id not in self._agents:
            clamped_score = self.clamp_score(starting_score)
            tier = self.get_tier(clamped_score)
            self._agents[agent_id] = Agent(
                agent_id=agent_id,
                trust_score=clamped_score,
                tier=tier,
            )
        return self._agents[agent_id]

    def reset_agent(self, agent_id: str, score: int = DEFAULT_STARTING_SCORE) -> Agent:
        """Reset agent to clean baseline state for demo and tests."""
        clamped_score = self.clamp_score(score)
        tier = self.get_tier(clamped_score)
        self._agents[agent_id] = Agent(
            agent_id=agent_id,
            trust_score=clamped_score,
            tier=tier,
        )
        return self._agents[agent_id]

    def record_clean_transaction(self, agent: Agent) -> Tuple[int, Tier, int]:
        """
        Clean transaction completed within mandate.
        Reward: +8 score. Recompute tier. Clamped [0, 100].
        """
        score_before = agent.trust_score
        new_score = self.clamp_score(score_before + SCORE_DELTA_CLEAN_TXN)
        new_tier = self.get_tier(new_score)

        agent.trust_score = new_score
        agent.tier = new_tier
        agent.total_clean_txns += 1

        delta = new_score - score_before
        return new_score, new_tier, delta

    def record_violation(self, agent: Agent, now: Optional[float] = None) -> Tuple[int, Tier, int, bool]:
        """
        Attempted transaction exceeding mandate (blocked).
        Standard penalty: -15 score.
        Anomaly penalty (3+ blocked attempts in 60s): -25 score.
        Clamped [0, 100]. Recompute tier.
        """
        if now is None:
            now = time.time()

        # Prune older blocked attempt timestamps
        cutoff = now - ANOMALY_WINDOW_SECONDS
        agent.recent_blocked_timestamps = [
            ts for ts in agent.recent_blocked_timestamps if ts > cutoff
        ]
        agent.recent_blocked_timestamps.append(now)

        is_anomaly = len(agent.recent_blocked_timestamps) >= ANOMALY_THRESHOLD_BLOCKS
        penalty = SCORE_DELTA_ANOMALY if is_anomaly else SCORE_DELTA_BLOCKED_VIOLATION

        score_before = agent.trust_score
        new_score = self.clamp_score(score_before + penalty)
        new_tier = self.get_tier(new_score)

        agent.trust_score = new_score
        agent.tier = new_tier
        agent.total_violations += 1

        delta = new_score - score_before
        return new_score, new_tier, delta, is_anomaly

    def record_system_failure(self, agent: Agent) -> Tuple[int, Tier, int]:
        """
        Payment provider failure (timeout, network drop).
        Explicitly ZERO trust penalty. System failure != agent misbehavior.
        """
        agent.total_system_errors += 1
        return agent.trust_score, agent.tier, SCORE_DELTA_SYSTEM_FAILURE


# Global singleton engine
trust_engine = TrustEngine()
