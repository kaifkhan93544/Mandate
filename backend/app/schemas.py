from pydantic import BaseModel, Field
from typing import List


class MandateCreate(BaseModel):
    purpose: str
    max_amount: float = Field(gt=0)
    currency: str = "INR"
    allowed_merchants: List[str]
    expires_at: str
    require_approval: bool = True


class PaymentCheck(BaseModel):
    mandate_id: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    merchant: str
