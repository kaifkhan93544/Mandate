import json
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from .schemas import MandateCreate, PaymentCheck
from .database import get_connection, initialize_database
from .signatures import create_signature, verify_signature
from .policy_engine import evaluate_payment


app = FastAPI(
    title="MANDATE API",
    description="AI Payment Security and Authorization Platform",
    version="1.0.0"
)


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {
        "message": "Welcome to MANDATE API",
        "status": "running"
    }


# 1. CREATE A PAYMENT MANDATE

@app.post("/mandates")
def create_mandate(request: MandateCreate):

    mandate_id = str(uuid.uuid4())

    mandate_data = {
        "purpose": request.purpose,
        "max_amount": request.max_amount,
        "currency": request.currency,
        "allowed_merchants": request.allowed_merchants,
        "expires_at": request.expires_at,
        "require_approval": request.require_approval
    }

    signature = create_signature(mandate_data)

    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO mandates (
                id, purpose, max_amount, currency,
                allowed_merchants, expires_at,
                require_approval, signature, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mandate_id,
                request.purpose,
                request.max_amount,
                request.currency,
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
        "mandate": mandate_data
    }


# 2. GET ALL MANDATES

@app.get("/mandates")
def get_mandates():

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM mandates ORDER BY created_at DESC"
        ).fetchall()

    mandates = []

    for row in rows:
        mandates.append({
            "id": row["id"],
            "purpose": row["purpose"],
            "max_amount": row["max_amount"],
            "currency": row["currency"],
            "allowed_merchants": json.loads(row["allowed_merchants"]),
            "expires_at": row["expires_at"],
            "require_approval": bool(row["require_approval"]),
            "created_at": row["created_at"]
        })

    return {"mandates": mandates}


# 3. CHECK A PAYMENT

@app.post("/payments/check")
def check_payment(request: PaymentCheck):

    with get_connection() as conn:
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
        "max_amount": float(row["max_amount"]),
        "currency": row["currency"],
        "allowed_merchants": json.loads(row["allowed_merchants"]),
        "expires_at": row["expires_at"],
        "require_approval": bool(row["require_approval"])
    }

    payment_data = {
        "amount": request.amount,
        "currency": request.currency,
        "merchant": request.merchant
    }

    # Verify the mandate signature before trusting its rules.

    signature_valid = verify_signature(
        mandate_data,
        row["signature"]
    )

    if signature_valid:
        approved, reason = evaluate_payment(
            mandate_data,
            payment_data
        )
    else:
        approved = False
        reason = "Mandate signature verification failed."

    decision = "APPROVED" if approved else "BLOCKED"

    decision_id = str(uuid.uuid4())

    created_at = datetime.now(timezone.utc).isoformat()

    # Save the decision in the transaction ledger.

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO decisions (
                id, mandate_id, amount, currency,
                merchant, decision, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                request.mandate_id,
                request.amount,
                request.currency,
                request.merchant,
                decision,
                reason,
                created_at
            )
        )

    return {
        "decision_id": decision_id,
        "mandate_id": request.mandate_id,
        "decision": decision,
        "reason": reason
    }


# 4. GET TRANSACTION HISTORY

@app.get("/transactions")
def get_transactions():

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY created_at DESC"
        ).fetchall()

    transactions = []

    for row in rows:
        transactions.append({
            "id": row["id"],
            "mandate_id": row["mandate_id"],
            "amount": row["amount"],
            "currency": row["currency"],
            "merchant": row["merchant"],
            "decision": row["decision"],
            "reason": row["reason"],
            "created_at": row["created_at"]
        })

    return {"transactions": transactions}
