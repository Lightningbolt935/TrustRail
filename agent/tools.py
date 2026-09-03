"""
AI Buyer Agent Tools Specification and Implementation
Exposes exactly three tools for shopping agents:
1. list_products
2. get_product
3. attempt_purchase
"""
from typing import Optional, Dict, Any, List
from backend.catalog.service import catalog_service
from backend.gate.mandate_gate import mandate_gate

# Function calling schema for LLM integrations
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List available products in the catalog with optional category and max_price filtering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category: 'essentials', 'apparel', 'electronics', 'luxury'",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in INR",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Retrieve comprehensive details for a specific product ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Unique product identifier (e.g., 'prod_app_001')",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "attempt_purchase",
            "description": (
                "Attempt to purchase a product through the Mandate Gate. "
                "Returns structured outcome: allowed, blocked, or error with explainable reason."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Unique product identifier to purchase",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
]


class AgentTools:
    """Tool execution layer for AI Buyer Agents."""

    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id

    def list_products(
        self,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """List products available in the store."""
        products = catalog_service.list_products(category=category, max_price=max_price)
        return [p.model_dump() for p in products]

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by ID."""
        prod = catalog_service.get_product(product_id)
        return prod.model_dump() if prod else None

    def attempt_purchase(
        self,
        product_id: str,
        simulate_failure: bool = False,
    ) -> Dict[str, Any]:
        """
        Attempt purchase through Mandate Gate.
        The agent never touches Razorpay directly and never modifies trust score internals.
        """
        decision = mandate_gate.evaluate_and_execute_purchase(
            agent_id=self.agent_id,
            product_id=product_id,
            simulate_failure=simulate_failure,
        )
        return {
            "allowed": decision.allowed,
            "decision": decision.decision,
            "reason": decision.reason,
            "product_id": decision.product_id,
            "product_name": decision.product_name,
            "amount": decision.amount,
            "category": decision.category,
            "razorpay_order_id": decision.razorpay_order_id,
            "is_system_error": decision.is_system_error,
        }
