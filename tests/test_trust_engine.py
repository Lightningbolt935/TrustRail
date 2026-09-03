"""
Unit Tests for TrustEngine
Tests pure deterministic scoring, tier transitions, clamping, and anomaly detection.
"""
import time
import pytest
from backend.config import Tier
from backend.trust_engine.engine import TrustEngine
from backend.trust_engine.models import Agent


@pytest.fixture
def engine():
    return TrustEngine()


def test_tier_mapping(engine):
    assert engine.get_tier(0) == Tier.BRONZE
    assert engine.get_tier(39) == Tier.BRONZE
    assert engine.get_tier(40) == Tier.SILVER
    assert engine.get_tier(50) == Tier.SILVER
    assert engine.get_tier(69) == Tier.SILVER
    assert engine.get_tier(70) == Tier.GOLD
    assert engine.get_tier(100) == Tier.GOLD


def test_clamping_boundaries(engine):
    assert engine.clamp_score(-10) == 0
    assert engine.clamp_score(0) == 0
    assert engine.clamp_score(50) == 50
    assert engine.clamp_score(100) == 100
    assert engine.clamp_score(125) == 100


def test_clean_transaction_reward(engine):
    agent = engine.get_or_create_agent("test_agent_1", starting_score=50)
    assert agent.tier == Tier.SILVER

    new_score, new_tier, delta = engine.record_clean_transaction(agent)
    assert new_score == 58
    assert new_tier == Tier.SILVER
    assert delta == 8
    assert agent.total_clean_txns == 1

    # Run clean transactions to push across tier boundary into Gold (>=70)
    new_score, new_tier, delta = engine.record_clean_transaction(agent)  # 58 + 8 = 66 (Silver)
    assert new_score == 66
    assert new_tier == Tier.SILVER

    new_score, new_tier, delta = engine.record_clean_transaction(agent)  # 66 + 8 = 74 (Gold!)
    assert new_score == 74
    assert new_tier == Tier.GOLD
    assert agent.tier == Tier.GOLD


def test_score_upper_clamp_at_100(engine):
    agent = engine.get_or_create_agent("test_agent_max", starting_score=96)
    new_score, new_tier, delta = engine.record_clean_transaction(agent)
    assert new_score == 100
    assert delta == 4  # Clamped to 100

    new_score, new_tier, delta = engine.record_clean_transaction(agent)
    assert new_score == 100
    assert delta == 0


def test_standard_violation_penalty(engine):
    agent = engine.get_or_create_agent("test_agent_viol", starting_score=50)
    now = time.time()
    new_score, new_tier, delta, is_anomaly = engine.record_violation(agent, now=now)

    assert new_score == 35
    assert new_tier == Tier.BRONZE  # Demoted from Silver to Bronze!
    assert delta == -15
    assert not is_anomaly
    assert agent.total_violations == 1


def test_score_lower_clamp_at_0(engine):
    agent = engine.get_or_create_agent("test_agent_min", starting_score=10)
    now = time.time()
    new_score, new_tier, delta, is_anomaly = engine.record_violation(agent, now=now)
    assert new_score == 0
    assert delta == -10
    assert new_tier == Tier.BRONZE


def test_anomaly_detection_penalty(engine):
    """3+ rapid violations within 60s trigger -25 anomaly penalty."""
    agent = engine.get_or_create_agent("test_agent_anomaly", starting_score=80)
    now = time.time()

    # Violation 1 (Standard -15)
    s1, _, d1, a1 = engine.record_violation(agent, now=now)
    assert s1 == 65
    assert d1 == -15
    assert not a1

    # Violation 2 (Standard -15)
    s2, _, d2, a2 = engine.record_violation(agent, now=now + 2)
    assert s2 == 50
    assert d2 == -15
    assert not a2

    # Violation 3 within 60s window (Anomaly flag fires! Penalty is -25!)
    s3, _, d3, a3 = engine.record_violation(agent, now=now + 5)
    assert s3 == 25  # 50 - 25 = 25!
    assert d3 == -25
    assert a3 is True
    assert agent.tier == Tier.BRONZE


def test_system_failure_no_penalty(engine):
    """Payment system timeouts must apply 0 trust penalty to agent."""
    agent = engine.get_or_create_agent("test_agent_sys", starting_score=50)
    score, tier, delta = engine.record_system_failure(agent)

    assert score == 50
    assert tier == Tier.SILVER
    assert delta == 0
    assert agent.total_system_errors == 1
    assert agent.trust_score == 50
