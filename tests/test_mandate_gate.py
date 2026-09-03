"""
Unit Tests for MandateGate
Tests deterministic enforcement: category allowlists, per-txn caps, daily caps, and audit trail.
"""
import pytest
from backend.gate.mandate_gate import MandateGate
from backend.trust_engine.engine import TrustEngine
from backend.audit.logger import AuditLogger
from backend.catalog.service import CatalogService
from backend.razorpay_client.client import RazorpayClient
from backend.config import Tier


@pytest.fixture
def clean_gate():
    gate = MandateGate()
    gate.trust_engine = TrustEngine()
    gate.audit_logger = AuditLogger()
    gate.audit_logger.clear()
    return gate


def test_category_allowlist_enforcement(clean_gate):
    # Setup agent at Bronze (Score 30) -> only 'essentials' permitted
    agent = clean_gate.trust_engine.get_or_create_agent("agent_bronze", starting_score=30)
    assert agent.tier == Tier.BRONZE

    # Try buying Apparel (prod_app_001, ₹799)
    res = clean_gate.evaluate_and_execute_purchase("agent_bronze", "prod_app_001")
    assert not res.allowed
    assert res.decision == "blocked"
    assert "Category 'apparel' is NOT permitted" in res.reason
    assert res.score_before == 30
    assert res.score_after == 15  # -15 penalty
    assert res.tier_after == "bronze"


def test_per_txn_cap_enforcement(clean_gate):
    # Setup agent at Silver (Score 50) -> cap ₹2000, apparel permitted
    agent = clean_gate.trust_engine.get_or_create_agent("agent_silver", starting_score=50)
    assert agent.tier == Tier.SILVER

    # Buy denim jacket (prod_app_003, ₹2499 -> exceeds ₹2000 per-txn cap!)
    res = clean_gate.evaluate_and_execute_purchase("agent_silver", "prod_app_003")
    assert not res.allowed
    assert res.decision == "blocked"
    assert "exceeds SILVER per-transaction spend cap of ₹2000.00" in res.reason
    assert res.score_after == 35
    assert res.tier_after == "bronze"  # Demoted!


def test_clean_transaction_approval(clean_gate):
    # Silver agent buying blue tee (prod_app_001, ₹799 -> within ₹2000 cap, apparel allowed)
    agent = clean_gate.trust_engine.get_or_create_agent("agent_silver_ok", starting_score=50)

    res = clean_gate.evaluate_and_execute_purchase("agent_silver_ok", "prod_app_001")
    assert res.allowed
    assert res.decision == "allowed"
    assert res.score_after == 58
    assert res.score_delta == 8
    assert res.razorpay_order_id is not None
    assert agent.daily_spent == 799.0


def test_daily_spend_cap_enforcement(clean_gate):
    # Silver agent daily cap is ₹5000. Start at 42 so 42 + 8 + 8 = 58 (still Silver)
    agent = clean_gate.trust_engine.get_or_create_agent("agent_daily", starting_score=42)

    # Make 2 purchases of running shoes (₹1899 each -> ₹3798 spent)
    res1 = clean_gate.evaluate_and_execute_purchase("agent_daily", "prod_app_002")
    assert res1.allowed

    res2 = clean_gate.evaluate_and_execute_purchase("agent_daily", "prod_app_002")
    assert res2.allowed
    assert agent.get_daily_spent_today() == 3798.0

    # Attempt third purchase of running shoes: 3798 + 1899 = 5697 > 5000!
    res3 = clean_gate.evaluate_and_execute_purchase("agent_daily", "prod_app_002")
    assert not res3.allowed
    assert "exceeds remaining daily cap" in res3.reason
    assert res3.score_delta == -15


def test_gold_unrestricted_access(clean_gate):
    # Gold agent (score 85) -> cap ₹10,000, all categories permitted
    agent = clean_gate.trust_engine.get_or_create_agent("agent_gold", starting_score=85)
    assert agent.tier == Tier.GOLD

    # Buy luxury titanium smartwatch (prod_lux_001, ₹8999)
    res = clean_gate.evaluate_and_execute_purchase("agent_gold", "prod_lux_001")
    assert res.allowed
    assert res.decision == "allowed"
    assert res.category == "luxury"
    assert res.score_after == 93
