"""
TrustRail System Configuration & Constants
Defines tier limits, scoring rules, and Razorpay test mode settings.
"""
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class Tier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


@dataclass(frozen=True)
class MandateRule:
    tier: Tier
    min_score: int
    max_score: int
    per_txn_cap: float       # INR
    daily_cap: float         # INR
    allowed_categories: List[str]  # ["*"] means all categories


# Tier Mandates defined deterministically
TIER_MANDATES: Dict[Tier, MandateRule] = {
    Tier.BRONZE: MandateRule(
        tier=Tier.BRONZE,
        min_score=0,
        max_score=39,
        per_txn_cap=500.0,
        daily_cap=1000.0,
        allowed_categories=["essentials"],
    ),
    Tier.SILVER: MandateRule(
        tier=Tier.SILVER,
        min_score=40,
        max_score=69,
        per_txn_cap=2000.0,
        daily_cap=5000.0,
        allowed_categories=["essentials", "apparel", "electronics"],
    ),
    Tier.GOLD: MandateRule(
        tier=Tier.GOLD,
        min_score=70,
        max_score=100,
        per_txn_cap=10000.0,
        daily_cap=25000.0,
        allowed_categories=["*"],  # All categories permitted
    ),
}

# Score Adjustments
SCORE_DELTA_CLEAN_TXN = +8
SCORE_DELTA_BLOCKED_VIOLATION = -15
SCORE_DELTA_ANOMALY = -25
SCORE_DELTA_SYSTEM_FAILURE = 0

SCORE_MIN = 0
SCORE_MAX = 100
DEFAULT_STARTING_SCORE = 50  # Silver midpoint for instant demoability

# Anomaly detection window (e.g., 3+ blocked attempts in 60s)
ANOMALY_WINDOW_SECONDS = 60
ANOMALY_THRESHOLD_BLOCKS = 3

# Deliberate failure trigger marker (e.g. price ending in .13 or prod_id containing fail)
FAILURE_TRIGGER_DECIMAL = 0.13
FAILURE_TRIGGER_KEYWORD = "fail_timeout"
