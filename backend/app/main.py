
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from .schemas import MandateCreate, PaymentCheck
from .database import db_session, initialize_database
from .signatures import create_signature, verify_signature
from .policy_engine import evaluate_payment


app = FastAPI(
    title="MANDATE API",
    description="AI Payment Security and Authorization Platform",
    version="1.1.0"
)


def to_minor_units(amount: float) -> int:
    """Convert rupees into paise safely."""
    return int(
        (Decimal(str(amount)) * 100).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def to_major_units(amount_minor: int) -> float:
    """Convert paise into rupees for API responses."""
    return float(Decimal(amount_minor) / 100)


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {
        "message": "Welcome to MANDATE API",
        "status": "running"
    }


@app.post("/mandates")
def create_mandate(request: MandateCreate):
    mandate_id = str(uuid.uuid4())
    max_amount_minor = to_minor_units(request.max_amount)

    if max_amount_minor <= 0:
        raise HTTPException(status_code=422, detail="Amount is too small.")

    mandate_data = {
        "purpose": request.purpose,
        "max_amount_minor": max_amount_minor,
        "currency": request.currency.upper(),
        "allowed_merchants": request.allowed_merchants,
        "expires_at": request.expires_at,
        "require_approval": request.require_approval
    }

    signature = create_signature(mandate_data)
    created_at = datetime.now(timezone.utc).isoformat()

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO mandates (
                id, purpose, max_amount_minor, currency,
                allowed_merchants, expires_at,
                require_approval, signature, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mandate_id,
                request.purpose,
                max_amount_minor,
                request.currency.upper(),
                json.dumps(request.allowed_merchants),
                request.expires_at,
                int(request.require_approval),
                signature,
                created_at
            )
        )

    return {
        "message": "Mandate created successfully",
        "mandate_id": mandate_id,
        "signature": signature,
        "mandate": {
            **mandate_data,
            "max_amount": to_major_units(max_amount_minor)
        }
    }


@app.get("/mandates")
def get_mandates():
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM mandates ORDER BY created_at DESC"
        ).fetchall()

    mandates = []

    for row in rows:
        mandates.append({
            "id": row["id"],
            "purpose": row["purpose"],
            "max_amount": to_major_units(row["max_amount_minor"]),
            "currency": row["currency"],
            "allowed_merchants": json.loads(row["allowed_merchants"]),
            "expires_at": row["expires_at"],
            "require_approval": bool(row["require_approval"]),
            "created_at": row["created_at"]
        })

    return {"mandates": mandates}


@app.post("/payments/check")
def check_payment(request: PaymentCheck):
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM mandates WHERE id = ?",
            (request.mandate_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Mandate not found"
            )

        mandate_data = {
            "purpose": row["purpose"],
            "max_amount_minor": row["max_amount_minor"],
            "currency": row["currency"],
            "allowed_merchants": json.loads(row["allowed_merchants"]),
            "expires_at": row["expires_at"],
            "require_approval": bool(row["require_approval"])
        }

        signature_valid = verify_signature(
            mandate_data,
            row["signature"]
        )

        amount_minor = to_minor_units(request.amount)

        payment_data = {
            "amount_minor": amount_minor,
            "currency": request.currency.upper(),
            "merchant": request.merchant
        }

        if signature_valid:
            approved, reason = evaluate_payment(
                mandate_data,
                payment_data
            )
        else:
            approved = False
            reason = "Mandate signature verification failed."

        if approved:
            decision = "allow"
        elif "requires user approval" in reason.lower():
            decision = "needs_approval"
        else:
            decision = "deny"

        decision_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO decisions (
                id, mandate_id, amount_minor, currency,
                merchant, decision, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                request.mandate_id,
                amount_minor,
                request.currency.upper(),
                request.merchant,
                decision,
                reason,
                created_at
            )
        )

    return {
        "decision_id": decision_id,
        "mandate_id": request.mandate_id,
        "decision": {
            "allow": "APPROVED",
            "deny": "BLOCKED",
            "needs_approval": "NEEDS_APPROVAL"
        }[decision],
        "reason": reason
    }


@app.get("/transactions")
def get_transactions():
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY created_at DESC"
        ).fetchall()

    transactions = []

    for row in rows:
        transactions.append({
            "id": row["id"],
            "mandate_id": row["mandate_id"],
            "amount": to_major_units(row["amount_minor"]),
            "currency": row["currency"],
            "merchant": row["merchant"],
            "decision": {
                "allow": "APPROVED",
                "deny": "BLOCKED",
                "needs_approval": "NEEDS_APPROVAL"
            }[row["decision"]],
            "reason": row["reason"],
            "created_at": row["created_at"]
        })

    return {"transactions": transactions}
