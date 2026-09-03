"""
Trust Engine Data Models
Defines Agent, Tier, Mandate, and Transaction representations.
"""
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.config import Tier, MandateRule, TIER_MANDATES, DEFAULT_STARTING_SCORE


class MandateView(BaseModel):
    tier: Tier
    per_txn_cap: float
    daily_cap: float
    daily_spent_today: float
    daily_remaining: float
    allowed_categories: List[str]
    is_category_unrestricted: bool


class Agent(BaseModel):
    agent_id: str
    trust_score: int = Field(default=DEFAULT_STARTING_SCORE, ge=0, le=100)
    tier: Tier = Tier.SILVER
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_clean_txns: int = 0
    total_violations: int = 0
    total_system_errors: int = 0
    daily_spent: float = 0.0
    last_spend_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    recent_blocked_timestamps: List[float] = Field(default_factory=list)

    def get_mandate_rule(self) -> MandateRule:
        return TIER_MANDATES[self.tier]

    def get_mandate_view(self) -> MandateView:
        rule = self.get_mandate_rule()
        daily_spent = self.get_daily_spent_today()
        remaining = max(0.0, rule.daily_cap - daily_spent)
        is_unrestricted = "*" in rule.allowed_categories
        return MandateView(
            tier=self.tier,
            per_txn_cap=rule.per_txn_cap,
            daily_cap=rule.daily_cap,
            daily_spent_today=daily_spent,
            daily_remaining=remaining,
            allowed_categories=rule.allowed_categories,
            is_category_unrestricted=is_unrestricted,
        )

    def get_daily_spent_today(self) -> float:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.last_spend_date != today:
            return 0.0
        return self.daily_spent

    def record_spend(self, amount: float):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.last_spend_date != today:
            self.daily_spent = amount
            self.last_spend_date = today
        else:
            self.daily_spent += amount


class Transaction(BaseModel):
    txn_id: str
    agent_id: str
    product_id: str
    product_name: str
    amount: float
    category: str
    status: str  # "completed" | "blocked" | "failed_system_error"
    razorpay_order_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str
