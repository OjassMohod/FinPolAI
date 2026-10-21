from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Assessment = Literal["PASS", "FLAGGED", "NEEDS INFORMATION", "REVIEW REQUIRED"]


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sender_name: str | None = Field(None, max_length=80)
    recipient_name: str | None = Field(None, max_length=80)
    sender_country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    recipient_country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    amount: Decimal | None = Field(None, gt=0, max_digits=15, decimal_places=2)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    purpose: str | None = Field(None, max_length=80)
    sender_kyc: bool | None = Field(None, strict=True)
    recipient_verified: bool | None = Field(None, strict=True)
    documents: (
        list[Literal["invoice", "source_of_funds", "scholarship_letter", "enrollment_letter"]]
        | None
    ) = None
    customer_type: Literal["individual", "business"] | None = None

    @field_validator("sender_name", "recipient_name", "purpose", mode="before")
    @classmethod
    def empty_is_unknown(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=1200)
    top_k: int = Field(5, ge=1, le=10)


class VerificationReport(BaseModel):
    id: str
    transaction_id: str
    timestamp: str
    transaction: dict
    assessment: Assessment
    execution_mode: Literal["Agent Mode", "Workflow Mode"]
    mode_reason: str
    summary: str
    rule_results: list[dict]
    evidence: list[dict]
    documents_searched: list[str]
    missing_information: list[str]
    next_steps: list[str]
    trace: list[dict]
    policy_versions: list[dict]
    retrieval_mode: str
    ai_explanation: dict | None = None
