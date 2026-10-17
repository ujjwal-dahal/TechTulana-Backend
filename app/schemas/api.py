from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.comparison import ComparisonResult


class CompareRequest(BaseModel):
    query: str = Field(
        min_length=2,
        max_length=100,
        description="Product name or comparison query.",
    )

    @field_validator("query", mode="before")
    @classmethod
    def strip_query(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value


class CompareResponse(BaseModel):
    status: Literal[
        "ok",
        "invalid_query",
        "unsupported_category",
        "no_results",
        "timeout",
        "busy",
        "error",
    ]

    message: str
    comparison: ComparisonResult | None = None
    elapsed_seconds: float = Field(ge=0)