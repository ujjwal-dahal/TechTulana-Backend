
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParsedQuery(BaseModel):
  
    # Extra fields aaye reject gara, defined schema matra accept gara.
    
    model_config = ConfigDict(extra="forbid")

    is_valid_query: bool = Field(
        description=(
            "True if the query identifies a specific product; "
            "False for gibberish or vague shopping requests."
        )
    )

    reason: str = Field(
        description=(
            "Short explanation in simple English. "
            "For invalid queries, explain why the query is invalid."
        )
    )

    product_name: str = Field(
        description=(
            "Clean product name. Remove shopping words like price, buy, "
            "best and Nepal. Preserve model numbers, sizes and storage."
        )
    )

    brand: str | None = Field(
        description="Recognized product brand, or null if unknown."
    )

    category: Literal[
        "mobile",
        "laptop",
        "tv",
        "accessories",
        "other",
    ] = Field(
        description=(
            "Product category in lowercase. Use other if the category "
            "cannot be identified or is outside supported categories."
        )
    )
