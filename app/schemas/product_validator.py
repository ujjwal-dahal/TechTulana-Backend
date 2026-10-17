from pydantic import BaseModel, Field

from app.schemas.product import Product

class ProductVerdict(BaseModel):
    """LLM ko euta product sambandhi decision."""

    id: int = Field(
        ...,
        description="ID of the product being validated.",
    )

    is_match: bool = Field(
        ...,
        description="Whether the product matches the requested model.",
    )

    reason: str = Field(
        ...,
        description="Short explanation for the decision.",
    )

    ram: str | None = Field(
        default=None,
        description="RAM capacity, only when explicitly available.",
    )

    storage: str | None = Field(
        default=None,
        description="Storage capacity, only when explicitly available.",
    )

    screen_size: str | None = Field(
        default=None,
        description="Display size, only when explicitly available.",
    )

    chip: str | None = Field(
        default=None,
        description="Processor chip or generation, only when explicitly available.",
    )


class BatchVerdict(BaseModel):
    """Structured response containing multiple product decisions."""

    verdicts: list[ProductVerdict] = Field(
        default_factory=list,
        description="Validation decisions for submitted products.",
    )


class ValidatedProduct(BaseModel):
    """Product with its validation status and extracted variants."""

    product: Product
    verified: bool = False
    variant_key: str
    ram: str | None = None
    storage: str | None = None
    screen_size: str | None = None
    chip: str | None = None
    identity_key: str | None = None
    specs_verified: bool = False