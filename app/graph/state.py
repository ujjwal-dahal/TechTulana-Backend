from typing import Any, TypedDict
import time


from app.schemas.llm_response import ParsedQuery
from app.schemas.product import EachWebsiteResult
from app.schemas.product_validator import ValidatedProduct
from app.schemas.comparison import ComparisonResult

class GraphState(TypedDict, total=False):
    # User ko original query.
    user_query: str

    # Agent 1 bata parse bhayeko query.
    parsed: ParsedQuery

    # Selected websites.
    sites: list[dict]

    # Website extraction results.
    site_results: list[EachWebsiteResult]

    # Products that passed validation.
    valid_products: list[ValidatedProduct]

    # Products rejected during validation.
    rejected: list[dict[str, Any]]

    # Message shown to the user.
    message: str
    
    comparison: ComparisonResult | None
    
    attempt: int
    started_at: float
    errors: list[str]
    retry_messages: list[str]