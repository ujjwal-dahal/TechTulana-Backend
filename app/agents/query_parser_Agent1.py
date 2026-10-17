
# Agent 1: Query Understanding Node

import logging

from app.services.llm_service import llm_1
from app.schemas.llm_response import ParsedQuery
from app.agents.prompts import QUERY_PARSER_PROMPT
from app.core.logging_config import setup_logging
from app.core.sites import CATEGORIES, get_sites_by_category


# Logging setup
setup_logging()
logger = logging.getLogger(__name__)


def _fallback_query(reason: str) -> ParsedQuery:
    # LLM/API fail bhaye pani predictable schema return gara.
    return ParsedQuery(
        is_valid_query=False,
        reason=reason,
        product_name="",
        brand=None,
        category="other",
    )


def parse_query(user_query: str) -> ParsedQuery:
    # Empty input lai LLM call nagari nai reject gara.
    if not user_query or not user_query.strip():
        return _fallback_query("Please enter a product name.")

    try:
        # Project ma configure gareko LLM instance use gara.
        llm = llm_1

        # Model bata plain text haina, ParsedQuery object maga.
        structured_llm = llm.with_structured_output(
            ParsedQuery,
            method="json_schema",
            strict=True,
        )

        result = structured_llm.invoke(
            [
                ("system", QUERY_PARSER_PROMPT),
                ("human", user_query.strip()),
            ]
        )

        # Pydantic le schema check garchha; yaha extra sanity checks pani gara.
        if not isinstance(result, ParsedQuery):
            logger.error(
                "Unexpected structured output type: %s",
                type(result),
            )
            return _fallback_query(
                "Unable to understand the product query."
            )

        # Valid query ma product name khali hunu hudaina.
        if result.is_valid_query and not result.product_name.strip():
            return _fallback_query(
                "Please provide a specific product name."
            )

        # Category lowercase ra supported list bhitra chha ki check gara.
        normalized_category = result.category.strip().lower()

        if normalized_category not in CATEGORIES:
            logger.warning(
                "Unsupported category returned by LLM: %s",
                result.category,
            )
            return _fallback_query(
                "Unable to identify the product category."
            )

        # LLM le category uppercase ma diyeko case normalize gara.
        result.category = normalized_category

        # "other" category lai valid product search ko lagi accept nagara.
        if result.is_valid_query and normalized_category == "other":
            return _fallback_query(
                "The product category is not supported yet."
            )

        return result

    except Exception:
        # API key, rate limit, network, model/schema error le app crash nahos.
        logger.exception("Query parsing failed")
        return _fallback_query("Service temporarily unavailable.")


def select_sites(parsed: ParsedQuery) -> list[dict]:
    # Invalid query ho bhane website search nagara.
    if not parsed.is_valid_query:
        return []

    # Unsupported category wa configuration error aaye crash nahos.
    try:
        # Site selection Python code le garchha, LLM le URL banaudaina.
        sites = get_sites_by_category(parsed.category)

        if not sites:
            logger.info(
                "No enabled websites support category: %s",
                parsed.category,
            )

        return sites

    except ValueError:
        logger.exception(
            "Site selection failed for category: %s",
            parsed.category,
        )
        return []
