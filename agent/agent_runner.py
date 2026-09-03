"""
AI Buyer Agent Runner
Implements autonomous agent execution with function/tool calling.
Follows strict system instructions:
- Use tools to find and purchase matching products
- If blocked, explain reason to user in plain language
- Never attempt to game the mandate or retry with altered amounts
"""
import os
import re
from typing import Dict, Any, List
from agent.tools import AgentTools, TOOLS_SCHEMA


SYSTEM_PROMPT = (
    "You are an autonomous AI shopping agent. You've been given a task by a user. "
    "Use the tools to find a matching product in the catalog and attempt to purchase it. "
    "If a purchase is blocked by the Mandate Gate, read the reason and explain it to the user "
    "in plain language — do not retry with a different amount to work around a limit. "
    "You do not have direct access to payment gateways."
)


class AgentRunner:
    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id
        self.tools = AgentTools(agent_id=agent_id)

    def run_task(self, user_prompt: str) -> Dict[str, Any]:
        """
        Execute an agentic shopping loop for the given user task.
        Emits step-by-step trace showing tool calls and reasoning.
        """
        steps: List[Dict[str, Any]] = []

        # Step 1: Agent analyzes user intent and queries catalog
        extracted_category, max_price = self._parse_intent(user_prompt)

        steps.append({
            "step": 1,
            "action": "call_tool",
            "tool": "list_products",
            "arguments": {"category": extracted_category, "max_price": max_price},
            "thought": f"Searching catalog for items matching user request: '{user_prompt}'",
        })

        products = self.tools.list_products(category=extracted_category, max_price=max_price)
        steps.append({
            "step": 2,
            "action": "tool_result",
            "tool": "list_products",
            "result_summary": f"Found {len(products)} products matching criteria.",
            "candidates": [p["id"] + f" ({p['name']} - ₹{p['price']})" for p in products[:4]],
        })

        if not products:
            final_response = (
                f"I searched the catalog for '{user_prompt}', but found no products matching "
                f"category '{extracted_category}' or budget ₹{max_price}."
            )
            return {
                "agent_id": self.agent_id,
                "user_prompt": user_prompt,
                "steps": steps,
                "outcome": "no_match",
                "final_response": final_response,
            }

        # Step 2: Agent selects the best match
        chosen_product = self._select_best_product(products, user_prompt)

        steps.append({
            "step": 3,
            "action": "call_tool",
            "tool": "get_product",
            "arguments": {"product_id": chosen_product["id"]},
            "thought": f"Selected '{chosen_product['name']}' (₹{chosen_product['price']}). Inspecting details before checkout.",
        })

        product_details = self.tools.get_product(chosen_product["id"])

        # Step 3: Agent calls attempt_purchase through Mandate Gate
        steps.append({
            "step": 4,
            "action": "call_tool",
            "tool": "attempt_purchase",
            "arguments": {"product_id": chosen_product["id"]},
            "thought": f"Submitting purchase request for '{chosen_product['name']}' (₹{chosen_product['price']}) to Mandate Gate.",
        })

        gate_outcome = self.tools.attempt_purchase(chosen_product["id"])

        steps.append({
            "step": 5,
            "action": "tool_result",
            "tool": "attempt_purchase",
            "gate_decision": gate_outcome["decision"],
            "reason": gate_outcome["reason"],
            "razorpay_order_id": gate_outcome.get("razorpay_order_id"),
        })

        # Step 4: Formulate honest user-facing response based on gate outcome
        if gate_outcome["allowed"]:
            final_response = (
                f"Success! I purchased '{chosen_product['name']}' for ₹{chosen_product['price']:.2f}. "
                f"Razorpay Order ID: {gate_outcome.get('razorpay_order_id')}. "
                "The transaction was verified and approved by the Mandate Gate."
            )
        elif gate_outcome.get("is_system_error"):
            final_response = (
                f"Order for '{chosen_product['name']}' could not be completed due to a payment provider error: "
                f"\"{gate_outcome['reason']}\". The transaction was safely aborted without charge or trust penalty."
            )
        else:
            final_response = (
                f"I could not complete the purchase for '{chosen_product['name']}'. "
                f"The Mandate Gate blocked this transaction: {gate_outcome['reason']}. "
                "In accordance with shopping agent guidelines, I will not attempt to bypass these limits."
            )

        return {
            "agent_id": self.agent_id,
            "user_prompt": user_prompt,
            "steps": steps,
            "gate_outcome": gate_outcome,
            "final_response": final_response,
        }

    def _parse_intent(self, prompt: str) -> tuple[str | None, float | None]:
        """Extract category and budget hints from prompt."""
        p_lower = prompt.lower()

        # Category extraction
        category = None
        if any(w in p_lower for w in ["tee", "t-shirt", "shirt", "shoe", "denim", "jacket", "apparel", "clothing"]):
            category = "apparel"
        elif any(w in p_lower for w in ["mouse", "keyboard", "headphone", "electronic", "cable", "gadget"]):
            category = "electronics"
        elif any(w in p_lower for w in ["watch", "smartwatch", "bag", "leather", "luxury"]):
            category = "luxury"
        elif any(w in p_lower for w in ["tea", "notebook", "pen", "essential"]):
            category = "essentials"

        # Price extraction (e.g. "under 1000", "under ₹2000", "< 500")
        max_price = None
        match = re.search(r'(?:under|below|less than|<)\s*₹?\s*(\d+(?:\.\d+)?)', p_lower)
        if match:
            max_price = float(match.group(1))

        return category, max_price

    def _select_best_product(self, products: List[Dict[str, Any]], prompt: str) -> Dict[str, Any]:
        """Rank products by textual relevance to prompt."""
        p_lower = prompt.lower()
        # Look for failure simulation trigger
        if "fail" in p_lower or "timeout" in p_lower:
            for p in products:
                if "fail_timeout" in p["id"]:
                    return p

        # Keyword match scoring
        best_prod = products[0]
        max_overlap = -1
        for p in products:
            name_words = set(p["name"].lower().split())
            prompt_words = set(re.findall(r'\b\w+\b', p_lower))
            overlap = len(name_words.intersection(prompt_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_prod = p

        return best_prod
