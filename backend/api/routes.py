"""
FastAPI Routes for TrustRail API
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field

from backend.catalog.service import catalog_service
from backend.catalog.models import Product
from backend.trust_engine.engine import trust_engine
from backend.trust_engine.models import Agent, MandateView
from backend.gate.mandate_gate import mandate_gate, GateDecisionResult
from backend.audit.logger import audit_logger, AuditLogEntry
from backend.config import DEFAULT_STARTING_SCORE

router = APIRouter()


class PurchaseRequest(BaseModel):
    product_id: str
    simulate_failure: bool = False


class AgentResetRequest(BaseModel):
    score: Optional[int] = DEFAULT_STARTING_SCORE


# ==========================================
# Catalog Endpoints
# ==========================================

@router.get("/catalog", response_model=List[Product], tags=["Catalog"])
def list_products(
    category: Optional[str] = Query(None, description="Filter products by category"),
    max_price: Optional[float] = Query(None, description="Filter products by max price in INR"),
):
    """Agent-readable product catalog with optional category and budget filtering."""
    return catalog_service.list_products(category=category, max_price=max_price)


@router.get("/catalog/{product_id}", response_model=Product, tags=["Catalog"])
def get_product(product_id: str = Path(..., description="Product ID to look up")):
    """Get single product details by ID."""
    product = catalog_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product


# ==========================================
# Agent & Gate Endpoints
# ==========================================

@router.post("/agent/{agent_id}/purchase", response_model=GateDecisionResult, tags=["Agent Gating"])
def attempt_purchase(
    agent_id: str = Path(..., description="Agent identifier"),
    request: PurchaseRequest = ...,
):
    """
    Attempt purchase for an agent.
    Strictly intercepted by Mandate Gate before any Razorpay execution.
    """
    result = mandate_gate.evaluate_and_execute_purchase(
        agent_id=agent_id,
        product_id=request.product_id,
        simulate_failure=request.simulate_failure,
    )
    return result


@router.get("/agent/{agent_id}/status", tags=["Agent"])
def get_agent_status(agent_id: str = Path(..., description="Agent identifier")):
    """Get live agent score, tier, and currently active mandate limits."""
    agent = trust_engine.get_or_create_agent(agent_id)
    mandate = agent.get_mandate_view()
    return {
        "agent_id": agent.agent_id,
        "trust_score": agent.trust_score,
        "tier": agent.tier.value,
        "created_at": agent.created_at,
        "stats": {
            "total_clean_txns": agent.total_clean_txns,
            "total_violations": agent.total_violations,
            "total_system_errors": agent.total_system_errors,
        },
        "mandate": mandate,
    }


@router.post("/agent/{agent_id}/reset", tags=["Agent"])
def reset_agent(
    agent_id: str = Path(..., description="Agent identifier"),
    body: AgentResetRequest = ...,
):
    """Reset agent score and state to baseline for demo repeatability."""
    agent = trust_engine.reset_agent(agent_id, score=body.score or DEFAULT_STARTING_SCORE)
    return {
        "message": f"Agent '{agent_id}' reset successfully",
        "trust_score": agent.trust_score,
        "tier": agent.tier.value,
    }


# ==========================================
# Audit Trail Endpoints
# ==========================================

@router.get("/audit", response_model=List[AuditLogEntry], tags=["Audit Trail"])
def get_audit_trail(
    agent_id: Optional[str] = Query(None, description="Filter log entries by agent_id"),
    limit: int = Query(100, ge=1, le=500, description="Max entries to return"),
):
    """Full append-only audit trail, newest first."""
    return audit_logger.get_entries(agent_id=agent_id, limit=limit)


@router.get("/audit/{agent_id}/summary", tags=["Audit Trail"])
def get_agent_audit_summary(agent_id: str = Path(..., description="Agent identifier")):
    """Summary metrics and historical score progression for dashboard visualization."""
    agent = trust_engine.get_or_create_agent(agent_id)
    history = audit_logger.get_agent_score_history(agent_id)
    return {
        "agent_id": agent_id,
        "trust_score": agent.trust_score,
        "tier": agent.tier.value,
        "total_clean_txns": agent.total_clean_txns,
        "total_violations": agent.total_violations,
        "total_system_errors": agent.total_system_errors,
        "score_history": history,
    }


# ==========================================
# Multi-Agent Comparison (Stretch Feature)
# ==========================================

@router.get("/agents/comparison", tags=["Demo & Comparison"])
def compare_agents():
    """Returns status and mandate comparison of sample Bronze, Silver, and Gold agents."""
    bronze_agent = trust_engine.get_or_create_agent("agent_bronze", starting_score=25)
    silver_agent = trust_engine.get_or_create_agent("agent_silver", starting_score=55)
    gold_agent = trust_engine.get_or_create_agent("agent_gold", starting_score=85)

    return {
        "agents": [
            {
                "agent_id": bronze_agent.agent_id,
                "label": "Cautious Rookie Agent",
                "score": bronze_agent.trust_score,
                "tier": bronze_agent.tier.value,
                "mandate": bronze_agent.get_mandate_view(),
            },
            {
                "agent_id": silver_agent.agent_id,
                "label": "Standard Operational Agent",
                "score": silver_agent.trust_score,
                "tier": silver_agent.tier.value,
                "mandate": silver_agent.get_mandate_view(),
            },
            {
                "agent_id": gold_agent.agent_id,
                "label": "High-Trust Power Buyer Agent",
                "score": gold_agent.trust_score,
                "tier": gold_agent.tier.value,
                "mandate": gold_agent.get_mandate_view(),
            },
        ]
    }


# ==========================================
# Agentic Task & Demo Scenarios
# ==========================================

class TaskRequest(BaseModel):
    task: str


@router.post("/agent/{agent_id}/run-task", tags=["Agent Gating"])
def run_agent_task(
    agent_id: str = Path(..., description="Agent identifier"),
    body: TaskRequest = ...,
):
    """
    Run natural language shopping task through the autonomous AI Buyer Agent.
    Executes tool-calling sequence: list_products -> get_product -> attempt_purchase.
    """
    from agent.agent_runner import AgentRunner
    runner = AgentRunner(agent_id=agent_id)
    return runner.run_task(body.task)


@router.post("/demo/scenario/{scenario_name}", tags=["Demo & Comparison"])
def run_demo_scenario(
    scenario_name: str = Path(..., description="Scenario: beat1_clean | beat2_tierup | beat3_blocked | beat4_failure"),
    agent_id: str = Query("agent_001", description="Target agent"),
):
    """
    Execute one of the 4 scripted demo beats with 1 click:
    - beat1_clean: Clean transaction (+8 score)
    - beat2_tierup: Clean transactions pushing score >= 70 into Gold tier
    - beat3_blocked: Overreach attempt exceeding tier mandate (-15 penalty, explainable reason)
    - beat4_failure: Simulated gateway timeout -> 1 retry -> clean abort -> 0 penalty!
    """
    if scenario_name == "beat1_clean":
        # Buy Blue Cotton T-Shirt (₹799 in apparel, permitted under Silver)
        result = mandate_gate.evaluate_and_execute_purchase(
            agent_id=agent_id,
            product_id="prod_app_001",
        )
        return {
            "beat": 1,
            "title": "Clean Transaction within Mandate",
            "description": "Agent purchases ₹799 t-shirt within Silver cap. Gate allows and awards +8 trust score.",
            "result": result,
        }

    elif scenario_name == "beat2_tierup":
        # Run clean transactions to push score into Gold (>=70)
        results = []
        agent = trust_engine.get_or_create_agent(agent_id)
        while agent.trust_score < 70:
            res = mandate_gate.evaluate_and_execute_purchase(
                agent_id=agent_id,
                product_id="prod_ess_001",  # ₹249 notebook
            )
            results.append(res)
        return {
            "beat": 2,
            "title": "Tier Promotion to Gold",
            "description": f"Earned clean track record! Score reached {agent.trust_score}. Tier promoted to GOLD, unlocking luxury items and ₹10,000 cap.",
            "results": results,
            "current_tier": agent.tier.value,
            "current_score": agent.trust_score,
        }

    elif scenario_name == "beat3_blocked":
        # Ensure agent is Silver or Bronze, then attempt luxury smartwatch (₹8999)
        agent = trust_engine.get_or_create_agent(agent_id)
        if agent.trust_score >= 70:
            agent.trust_score = 50
            agent.tier = trust_engine.get_tier(50)
        result = mandate_gate.evaluate_and_execute_purchase(
            agent_id=agent_id,
            product_id="prod_lux_001",  # ₹8999 smartwatch (luxury)
        )
        return {
            "beat": 3,
            "title": "Blocked Overreach Attempt",
            "description": "Agent attempted ₹8999 luxury purchase exceeding Silver mandate. Gate blocked with transparent rule violation and -15 penalty.",
            "result": result,
        }

    elif scenario_name == "beat4_failure":
        # Buy item engineered to trigger simulated gateway timeout
        result = mandate_gate.evaluate_and_execute_purchase(
            agent_id=agent_id,
            product_id="prod_fail_timeout",
            simulate_failure=True,
        )
        return {
            "beat": 4,
            "title": "Payment Provider Timeout & Graceful Recovery",
            "description": "Gateway timed out. Mandate Gate executed 1 retry, cleanly aborted, and applied ZERO trust penalty (system failure != agent fault).",
            "result": result,
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario_name}'")

