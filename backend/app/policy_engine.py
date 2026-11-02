
from datetime import datetime, timezone


def evaluate_payment(mandate: dict, payment: dict) -> tuple[bool, str]:
    """
    Check whether a payment follows the mandate rules.
    Amounts are stored and compared in paise.
    """

    if payment["amount_minor"] > mandate["max_amount_minor"]:
        return False, "Payment exceeds the maximum allowed amount."

    if payment["amount_minor"] <= 0:
        return False, "Payment amount must be greater than zero."

    if payment["currency"].upper() != mandate["currency"].upper():
        return False, "Payment currency does not match the mandate."

    allowed_merchants = [
        merchant.strip().lower()
        for merchant in mandate["allowed_merchants"]
    ]

    if payment["merchant"].strip().lower() not in allowed_merchants:
        return False, "Merchant is not allowed by the mandate."

    try:
        expiry = datetime.fromisoformat(
            mandate["expires_at"].replace("Z", "+00:00")
        )

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

    except ValueError:
        return False, "Mandate expiry date is invalid."

    if datetime.now(timezone.utc) > expiry.astimezone(timezone.utc):
        return False, "Mandate has expired."

    if mandate["require_approval"]:
        return False, "This mandate requires user approval before payment."

    return True, "Payment is within the mandate rules."
