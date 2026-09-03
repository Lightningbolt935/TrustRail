"""
Mandate Gate Enforcement Point
Deterministically intercepts agent intents before any Razorpay interaction.
"""
import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.trust_engine.engine import trust_engine
from backend.trust_engine.models import Agent, MandateView
from backend.catalog.service import catalog_service
from backend.catalog.models import Product
from backend.razorpay_client.client import razorpay_client, RazorpayOrderResult
from backend.audit.logger import audit_logger, AuditLogEntry


class GateDecisionResult(BaseModel):
    allowed: bool
    is_system_error: bool = False
    decision: str  # "allowed" | "blocked" | "error"
    reason: str
    product_id: str
    product_name: str
    amount: float
    category: str
    score_before: int
    score_after: int
    score_delta: int
    tier_before: str
    tier_after: str
    razorpay_order_id: Optional[str] = None
    txn_id: Optional[str] = None
    retried: bool = False
    retry_count: int = 0
    mandate: Optional[MandateView] = None


class MandateGate:
    """Enforces deterministic constraints and executes gated Razorpay transactions."""

    def __init__(self):
        self.trust_engine = trust_engine
        self.catalog_service = catalog_service
        self.razorpay_client = razorpay_client
        self.audit_logger = audit_logger

    def evaluate_and_execute_purchase(
        self,
        agent_id: str,
        product_id: str,
        simulate_failure: bool = False,
    ) -> GateDecisionResult:
        agent = self.trust_engine.get_or_create_agent(agent_id)
        product = self.catalog_service.get_product(product_id)

        if not product:
            return GateDecisionResult(
                allowed=False,
                decision="blocked",
                reason=f"Product with ID '{product_id}' not found in catalog",
                product_id=product_id,
                product_name="Unknown",
                amount=0.0,
                category="unknown",
                score_before=agent.trust_score,
                score_after=agent.trust_score,
                score_delta=0,
                tier_before=agent.tier.value,
                tier_after=agent.tier.value,
                mandate=agent.get_mandate_view(),
            )

        score_before = agent.trust_score
        tier_before = agent.tier.value
        mandate_rule = agent.get_mandate_rule()
        txn_id = f"txn_{uuid.uuid4().hex[:8]}"

        # Check 1: Category Allowlist Check
        is_all_categories = "*" in mandate_rule.allowed_categories
        is_cat_allowed = is_all_categories or (product.category.lower() in [c.lower() for c in mandate_rule.allowed_categories])

        if not is_cat_allowed:
            new_score, new_tier, delta, is_anomaly = self.trust_engine.record_violation(agent)
            reason = (
                f"Category '{product.category}' is NOT permitted under {tier_before.upper()} mandate. "
                f"Allowed categories: {mandate_rule.allowed_categories}"
            )
            if is_anomaly:
                reason += " [ANOMALY DETECTED: 3+ rapid violations triggered maximum penalty -25]"

            self.audit_logger.log_event(
                AuditLogEntry(
                    agent_id=agent.agent_id,
                    event_type="gate_decision",
                    decision="blocked",
                    reason=reason,
                    score_before=score_before,
                    score_after=new_score,
                    tier_before=tier_before,
                    tier_after=new_tier.value,
                    txn_id=txn_id,
                    metadata={
                        "product_id": product.id,
                        "amount": product.price,
                        "category": product.category,
                        "violation_type": "category_restriction",
                    },
                )
            )

            return GateDecisionResult(
                allowed=False,
                decision="blocked",
                reason=reason,
                product_id=product.id,
                product_name=product.name,
                amount=product.price,
                category=product.category,
                score_before=score_before,
                score_after=new_score,
                score_delta=delta,
                tier_before=tier_before,
                tier_after=new_tier.value,
                txn_id=txn_id,
                mandate=agent.get_mandate_view(),
            )

        # Check 2: Per-Transaction Spend Cap
        if product.price > mandate_rule.per_txn_cap:
            new_score, new_tier, delta, is_anomaly = self.trust_engine.record_violation(agent)
            reason = (
                f"Requested ₹{product.price:.2f} exceeds {tier_before.upper()} "
                f"per-transaction spend cap of ₹{mandate_rule.per_txn_cap:.2f}"
            )
            if is_anomaly:
                reason += " [ANOMALY DETECTED: 3+ rapid violations triggered maximum penalty -25]"

            self.audit_logger.log_event(
                AuditLogEntry(
                    agent_id=agent.agent_id,
                    event_type="gate_decision",
                    decision="blocked",
                    reason=reason,
                    score_before=score_before,
                    score_after=new_score,
                    tier_before=tier_before,
                    tier_after=new_tier.value,
                    txn_id=txn_id,
                    metadata={
                        "product_id": product.id,
                        "amount": product.price,
                        "category": product.category,
                        "cap": mandate_rule.per_txn_cap,
                        "violation_type": "per_txn_cap_exceeded",
                    },
                )
            )

            return GateDecisionResult(
                allowed=False,
                decision="blocked",
                reason=reason,
                product_id=product.id,
                product_name=product.name,
                amount=product.price,
                category=product.category,
                score_before=score_before,
                score_after=new_score,
                score_delta=delta,
                tier_before=tier_before,
                tier_after=new_tier.value,
                txn_id=txn_id,
                mandate=agent.get_mandate_view(),
            )

        # Check 3: Daily Spend Cap
        daily_spent = agent.get_daily_spent_today()
        if daily_spent + product.price > mandate_rule.daily_cap:
            new_score, new_tier, delta, is_anomaly = self.trust_engine.record_violation(agent)
            remaining = max(0.0, mandate_rule.daily_cap - daily_spent)
            reason = (
                f"Requested ₹{product.price:.2f} exceeds remaining daily cap of ₹{remaining:.2f} "
                f"(₹{daily_spent:.2f} spent today out of ₹{mandate_rule.daily_cap:.2f} daily limit)"
            )
            if is_anomaly:
                reason += " [ANOMALY DETECTED: 3+ rapid violations triggered maximum penalty -25]"

            self.audit_logger.log_event(
                AuditLogEntry(
                    agent_id=agent.agent_id,
                    event_type="gate_decision",
                    decision="blocked",
                    reason=reason,
                    score_before=score_before,
                    score_after=new_score,
                    tier_before=tier_before,
                    tier_after=new_tier.value,
                    txn_id=txn_id,
                    metadata={
                        "product_id": product.id,
                        "amount": product.price,
                        "category": product.category,
                        "daily_cap": mandate_rule.daily_cap,
                        "daily_spent": daily_spent,
                        "violation_type": "daily_cap_exceeded",
                    },
                )
            )

            return GateDecisionResult(
                allowed=False,
                decision="blocked",
                reason=reason,
                product_id=product.id,
                product_name=product.name,
                amount=product.price,
                category=product.category,
                score_before=score_before,
                score_after=new_score,
                score_delta=delta,
                tier_before=tier_before,
                tier_after=new_tier.value,
                txn_id=txn_id,
                mandate=agent.get_mandate_view(),
            )

        # All Gate Checks PASSED! Now invoke Razorpay test integration
        order_result: RazorpayOrderResult = self.razorpay_client.create_order(
            amount_inr=product.price,
            product_id=product.id,
            receipt=txn_id,
            notes={
                "agent_id": agent.agent_id,
                "tier": tier_before,
                "product_name": product.name,
            },
            simulate_failure=simulate_failure,
        )

        # Handle System Error / Gateway Timeout
        if not order_result.success:
            self.trust_engine.record_system_failure(agent)
            reason = order_result.error or "Payment provider error — aborted cleanly"

            # Log system failure (Score unchanged, 0 penalty!)
            self.audit_logger.log_event(
                AuditLogEntry(
                    agent_id=agent.agent_id,
                    event_type="system_failure",
                    decision="error",
                    reason=reason,
                    score_before=score_before,
                    score_after=score_before,
                    tier_before=tier_before,
                    tier_after=tier_before,
                    txn_id=txn_id,
                    metadata={
                        "product_id": product.id,
                        "amount": product.price,
                        "retries_attempted": order_result.retry_count,
                        "trust_penalty": 0,
                    },
                )
            )

            return GateDecisionResult(
                allowed=False,
                is_system_error=True,
                decision="error",
                reason=reason,
                product_id=product.id,
                product_name=product.name,
                amount=product.price,
                category=product.category,
                score_before=score_before,
                score_after=score_before,
                score_delta=0,
                tier_before=tier_before,
                tier_after=tier_before,
                txn_id=txn_id,
                retried=order_result.retried,
                retry_count=order_result.retry_count,
                mandate=agent.get_mandate_view(),
            )

        # Payment Provider Succeeded -> Record Spend & Reward Agent Trust
        agent.record_spend(product.price)
        new_score, new_tier, delta = self.trust_engine.record_clean_transaction(agent)
        reason = (
            f"Transaction approved: ₹{product.price:.2f} in '{product.category}' "
            f"strictly within {tier_before.upper()} mandate (Order ID: {order_result.order_id})"
        )

        self.audit_logger.log_event(
            AuditLogEntry(
                agent_id=agent.agent_id,
                event_type="gate_decision",
                decision="allowed",
                reason=reason,
                score_before=score_before,
                score_after=new_score,
                tier_before=tier_before,
                tier_after=new_tier.value,
                txn_id=txn_id,
                metadata={
                    "product_id": product.id,
                    "amount": product.price,
                    "category": product.category,
                    "razorpay_order_id": order_result.order_id,
                    "retried": order_result.retried,
                },
            )
        )

        return GateDecisionResult(
            allowed=True,
            decision="allowed",
            reason=reason,
            product_id=product.id,
            product_name=product.name,
            amount=product.price,
            category=product.category,
            score_before=score_before,
            score_after=new_score,
            score_delta=delta,
            tier_before=tier_before,
            tier_after=new_tier.value,
            razorpay_order_id=order_result.order_id,
            txn_id=txn_id,
            retried=order_result.retried,
            retry_count=order_result.retry_count,
            mandate=agent.get_mandate_view(),
        )


# Global singleton gate
mandate_gate = MandateGate()
