from datetime import datetime, timezone


def evaluate_payment(mandate: dict, payment: dict) -> tuple[bool, str]:
    # Check payment amount
    if payment["amount"] > mandate["max_amount"]:
        return False, "Payment exceeds the allowed spending limit."

    # Check currency
    if payment["currency"].upper() != mandate["currency"].upper():
        return False, "Payment currency does not match the mandate."

    # Check allowed merchant
    allowed_merchants = mandate.get("allowed_merchants", [])

    if allowed_merchants:
        if payment["merchant"].lower() not in [
            merchant.lower() for merchant in allowed_merchants
        ]:
            return False, "Merchant is not approved by the user."

    # Check mandate expiry
    expiry = datetime.fromisoformat(
        mandate["expires_at"].replace("Z", "+00:00")
    )

    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expiry:
        return False, "Mandate has expired."

    # Check whether human approval is required
    if mandate["require_approval"]:
        return False, "Human approval is required before payment."

    return True, "Payment approved by mandate policy."
