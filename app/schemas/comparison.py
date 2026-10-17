
from typing import Literal

from pydantic import BaseModel, Field


class Offer(BaseModel):
    site_name: str
    site_key: str
    tier: Literal["retailer", "marketplace"]
    source_type: Literal["retailer", "marketplace"]

    product_name: str
    url: str
    image: str | None = None

    price: float = Field(gt=0)
    regular_price: float | None = Field(default=None, gt=0)
    in_stock: bool | None = None

    verified: bool = False
    specs_verified: bool = False
    flags: list[str] = Field(default_factory=list)


class ComparisonGroup(BaseModel):
    variant_key: str
    label: str
    offers: list[Offer] = Field(default_factory=list)

    best_offer: Offer | None = None

    price_min: float | None = None
    price_max: float | None = None
    spread_amount: float | None = None
    spread_percent: float | None = None

    is_comparable: bool = False


class SiteStatus(BaseModel):
    name: str
    status: Literal["ok", "empty", "error"]
    found_count: int = 0
    elapsed_seconds: float | None = None
    message: str


class ComparisonResult(BaseModel):
    query: str
    groups: list[ComparisonGroup] = Field(default_factory=list)
    site_status: list[SiteStatus] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    generated_at: str
