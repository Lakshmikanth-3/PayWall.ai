"""
Razorpay test-mode payment execution.

Per PRD Section 21/22: authorization (the Guard's decision) and payment
execution are separate steps. This module is only ever invoked AFTER the
Guard has already returned ALLOW (or REVIEW + human_approved). It never
makes an authorization decision itself.
"""

import logging
from typing import Optional, Tuple
from app.config import settings

logger = logging.getLogger(__name__)


def _client():
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        return None
    try:
        import razorpay
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except Exception:
        logger.exception("Failed to construct Razorpay client")
        return None


def create_order(amount_inr: float, currency: str, receipt: str, notes: dict) -> Tuple[Optional[str], str]:
    """
    Creates a Razorpay test-mode order for an already-authorized transaction.

    Returns (razorpay_order_id, payment_status). payment_status is one of:
      CREATED  — order created successfully, awaiting checkout/capture
      FAILED   — Razorpay API unreachable or rejected the request
      SKIPPED  — no Razorpay credentials configured (dev without keys)
    """
    client = _client()
    if client is None:
        return None, "SKIPPED"

    try:
        order = client.order.create({
            # Razorpay amounts are in the smallest currency unit (paise for INR)
            "amount": int(round(amount_inr * 100)),
            "currency": currency,
            "receipt": receipt,
            "notes": {k: str(v) for k, v in notes.items()},
        })
        return order["id"], "CREATED"
    except Exception:
        logger.exception("Razorpay order creation failed for receipt=%s", receipt)
        return None, "FAILED"
