"""
Razorpay Test-Mode Client & Failure Recovery Simulator
Integrates with Razorpay Orders API or sandbox simulator,
with engineered failure detection and 1-retry graceful recovery.
"""
import os
import time
import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel
import httpx
from backend.config import FAILURE_TRIGGER_DECIMAL, FAILURE_TRIGGER_KEYWORD


class RazorpayOrderResult(BaseModel):
    success: bool
    order_id: Optional[str] = None
    amount_inr: float
    currency: str = "INR"
    error: Optional[str] = None
    retried: bool = False
    retry_count: int = 0
    simulated: bool = False


class RazorpayClient:
    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "")
        self.has_credentials = bool(self.key_id and self.key_secret)

    def _should_trigger_simulated_failure(
        self,
        amount: float,
        product_id: Optional[str] = None,
        simulate_failure: bool = False,
    ) -> bool:
        """
        Check if deliberate failure condition is met:
        1. Explicit flag `simulate_failure`
        2. Amount ending in .13 (e.g. ₹499.13)
        3. Product ID containing `fail_timeout`
        """
        if simulate_failure:
            return True
        if product_id and FAILURE_TRIGGER_KEYWORD in product_id:
            return True
        # Check decimal portion for .13
        decimal_part = round(amount - int(amount), 2)
        if abs(decimal_part - FAILURE_TRIGGER_DECIMAL) < 0.001:
            return True
        return False

    def create_order(
        self,
        amount_inr: float,
        product_id: str,
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
        simulate_failure: bool = False,
        retry_delay_seconds: float = 0.2,
    ) -> RazorpayOrderResult:
        """
        Execute Razorpay order creation with 1-retry graceful recovery.
        Never penalizes the agent for gateway timeouts or network drops.
        """
        is_deliberate_failure = self._should_trigger_simulated_failure(
            amount=amount_inr,
            product_id=product_id,
            simulate_failure=simulate_failure,
        )

        receipt = receipt or f"rcpt_{uuid.uuid4().hex[:8]}"
        amount_paise = int(round(amount_inr * 100))

        # Attempt 1
        success, order_id, error = self._call_provider(amount_paise, receipt, notes, is_deliberate_failure)
        if success:
            return RazorpayOrderResult(
                success=True,
                order_id=order_id,
                amount_inr=amount_inr,
                simulated=not self.has_credentials,
            )

        # Failure occurred -> Execute exactly 1 retry after delay
        time.sleep(retry_delay_seconds)
        retry_success, retry_order_id, retry_error = self._call_provider(
            amount_paise, receipt, notes, is_deliberate_failure
        )

        if retry_success:
            return RazorpayOrderResult(
                success=True,
                order_id=retry_order_id,
                amount_inr=amount_inr,
                retried=True,
                retry_count=1,
                simulated=not self.has_credentials,
            )

        # Retry failed -> Clean abort with explainable system failure
        clean_error = "Payment provider timed out after 1 retry — transaction aborted, no charge made"
        return RazorpayOrderResult(
            success=False,
            amount_inr=amount_inr,
            error=clean_error,
            retried=True,
            retry_count=1,
            simulated=True,
        )

    def _call_provider(
        self,
        amount_paise: int,
        receipt: str,
        notes: Optional[Dict[str, Any]],
        force_fail: bool,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Underlying provider invocation or realistic simulation."""
        if force_fail:
            return False, None, "GATEWAY_TIMEOUT: Razorpay payment gateway socket timeout (504)"

        if self.has_credentials:
            try:
                with httpx.Client(timeout=4.0) as client:
                    resp = client.post(
                        "https://api.razorpay.com/v1/orders",
                        auth=(self.key_id, self.key_secret),
                        json={
                            "amount": amount_paise,
                            "currency": "INR",
                            "receipt": receipt,
                            "notes": notes or {},
                        },
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        return True, data.get("id"), None
                    else:
                        return False, None, f"Razorpay API Error ({resp.status_code}): {resp.text}"
            except Exception as exc:
                return False, None, f"Network exception: {str(exc)}"

        # Simulated sandbox order creation
        simulated_order_id = f"order_sim_{uuid.uuid4().hex[:10]}"
        return True, simulated_order_id, None


# Global singleton client
razorpay_client = RazorpayClient()
