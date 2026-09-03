"""
Unit Tests for Failure Recovery
Tests the Track 01 requirement:
Simulated Razorpay failure (timeout / insufficient test funds) -> 1 retry -> clean abort with logged reason,
and ZERO trust penalty (system failure != agent misbehavior).
"""
import pytest
from backend.gate.mandate_gate import MandateGate
from backend.trust_engine.engine import TrustEngine
from backend.audit.logger import AuditLogger
from backend.razorpay_client.client import RazorpayClient


@pytest.fixture
def gate():
    g = MandateGate()
    g.trust_engine = TrustEngine()
    g.audit_logger = AuditLogger()
    g.audit_logger.clear()
    return g


def test_simulated_gateway_timeout_retry_and_abort(gate):
    agent = gate.trust_engine.get_or_create_agent("agent_failure_demo", starting_score=50)
    score_before = agent.trust_score

    # Attempt purchasing product engineered to trigger simulated timeout (prod_fail_timeout)
    res = gate.evaluate_and_execute_purchase(
        agent_id="agent_failure_demo",
        product_id="prod_fail_timeout",
        simulate_failure=True,
    )

    # 1. Verification of clean abort outcome
    assert not res.allowed
    assert res.is_system_error is True
    assert res.decision == "error"
    assert "Payment provider timed out after 1 retry" in res.reason

    # 2. Verification of 1 retry execution
    assert res.retried is True
    assert res.retry_count == 1

    # 3. CRITICAL EVALUATION CRITERIA: ZERO TRUST PENALTY
    assert res.score_before == score_before
    assert res.score_after == score_before
    assert res.score_delta == 0
    assert agent.trust_score == score_before
    assert agent.total_system_errors == 1

    # 4. Audit Log Verification: Must be recorded as system_failure
    logs = gate.audit_logger.get_entries(agent_id="agent_failure_demo")
    assert len(logs) == 1
    log = logs[0]
    assert log.event_type == "system_failure"
    assert log.decision == "error"
    assert log.score_before == score_before
    assert log.score_after == score_before
    assert log.metadata.get("trust_penalty") == 0


def test_failure_trigger_by_price_decimal(gate):
    """Verify that any item ending in .13 automatically triggers deliberate timeout."""
    agent = gate.trust_engine.get_or_create_agent("agent_decimal_trigger", starting_score=50)

    # prod_fail_timeout has price 499.13
    res = gate.evaluate_and_execute_purchase(
        agent_id="agent_decimal_trigger",
        product_id="prod_fail_timeout",
    )

    assert not res.allowed
    assert res.is_system_error is True
    assert res.retried is True
    assert agent.trust_score == 50  # ZERO penalty!
