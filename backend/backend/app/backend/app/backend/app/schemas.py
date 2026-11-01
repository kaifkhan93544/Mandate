from pydantic import BaseModel, Field
from typing import List


class MandateCreate(BaseModel):
    purpose: str = Field(min_length=3, max_length=200)
    max_amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    allowed_merchants: List[str] = Field(default_factory=list)
    expires_at: str
    require_approval: bool = False


class PaymentCheck(BaseModel):
    mandate_id: str
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    merchant: str = Field(min_length=1, max_length=200)
