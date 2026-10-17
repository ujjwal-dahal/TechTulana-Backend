import logging

from langgraph.graph import END
import asyncio
import time
from urllib.parse import urlparse


from app.core.retry_config import (
    MAX_RETRIES,
    TOTAL_BUDGET_SECONDS,
    PER_SITE_TIMEOUT,
    RETRY_DELAY_SECONDS,
)

from app.agents.query_parser_Agent1 import parse_query, select_sites
from app.schemas.llm_response import ParsedQuery
from app.schemas.product import EachWebsiteResult
from app.schemas.product_validator import ValidatedProduct
from app.services.product_validator import validate_rules
from app.services.llm_product_validator import validate_products_with_llm
from app.tools.extractor_client import fetch_many
from app.graph.state import GraphState
from app.core.logging_config import setup_logging
from app.services.comparison_service import build_comparison


setup_logging()
logger = logging.getLogger(__name__)


def parse_node(state: GraphState) -> dict:
    """Parse the user's query and initialize retry state."""

    started_at = state.get("started_at", time.monotonic())

    try:
        parsed = parse_query(state.get("user_query", ""))

        if not parsed.is_valid_query:
            return {
                "parsed": parsed,
                "message": parsed.reason,
                "attempt": 0,
                "started_at": started_at,
                "errors": [],
                "retry_messages": [],
            }

        return {
            "parsed": parsed,
            "message": "",
            "attempt": 0,
            "started_at": started_at,
            "errors": [],
            "retry_messages": [],
        }

    except Exception:
        logger.exception("Query parsing failed")
        return {
            "message": "Could not understand your product query. Please try again.",
            "errors": ["Query parsing failed"],
            "attempt": 0,
            "started_at": started_at,
            "retry_messages": [],
        }



def _site_key(value: str) -> str:
    """Normalize a URL or hostname for matching site results."""

    parsed = urlparse(
        value if "://" in value else f"https://{value}"
    )
    return (parsed.hostname or value).lower().removeprefix("www.")


def select_sites_node(state: GraphState) -> dict:
    """Select supported websites for the requested category."""

    parsed: ParsedQuery = state["parsed"]
    sites = select_sites(parsed)

    if not sites:
        return {
            "sites": [],
            "message": (
                "Yo product category ko lagi aile "
                "supported website available chhaina."
            ),
        }

    return {
        "sites": sites,
        "message": "",
    }


async def extract_node(state: GraphState) -> dict:
    """Fetch products from selected websites concurrently."""

    parsed = state.get("parsed")
    sites = state.get("sites", [])

    if parsed is None:
        return {
            "site_results": [],
            "errors": state.get("errors", []) + [
                "Extraction skipped because query parsing failed"
            ],
        }

    urls = [site["url"] for site in sites]

    try:
        results = await fetch_many(
            urls,
            product_name=parsed.product_name,
            max_results=8,
        )
        return {"site_results": results}

    except Exception:
        logger.exception("Website extraction failed")

        failed_results = [
            EachWebsiteResult(
                website=_site_key(url),
                status="error",
                products=[],
                error_message="Extraction failed",
                retryable=False,
            )
            for url in urls
        ]

        return {
            "site_results": failed_results,
            "errors": state.get("errors", []) + [
                "Website extraction failed unexpectedly"
            ],
        }

def route_after_extract(state: GraphState) -> str:
    """Retry only retryable site failures within the time budget."""

    if state.get("attempt", 0) >= MAX_RETRIES:
        return "validate"

    site_results = state.get("site_results", [])

    if not any(result.retryable for result in site_results):
        return "validate"

    started_at = state.get("started_at")

    if started_at is None:
        return "validate"

    elapsed = time.monotonic() - started_at
    remaining = TOTAL_BUDGET_SECONDS - elapsed

    if remaining < PER_SITE_TIMEOUT:
        return "validate"

    return "retry_extract"

async def retry_extract_node(state: GraphState) -> dict:
    """Retry only failed sites marked as retryable."""

    parsed = state.get("parsed")
    site_results = state.get("site_results", [])
    sites = state.get("sites", [])

    if parsed is None:
        return {
            "attempt": state.get("attempt", 0) + 1,
            "errors": state.get("errors", []) + [
                "Retry skipped because parsed query is missing"
            ],
        }

    retryable_keys = {
        _site_key(result.website)
        for result in site_results
        if result.retryable
    }

    retry_sites = [
        site for site in sites
        if _site_key(site["url"]) in retryable_keys
    ]

    # Defensive guard: retry नगर्ने भए पनि loop रोक्न attempt बढाऊ।
    next_attempt = state.get("attempt", 0) + 1

    if not retry_sites:
        return {"attempt": next_attempt}

    await asyncio.sleep(RETRY_DELAY_SECONDS)

    # Sleep पछि पनि time budget जाँच।
    started_at = state.get("started_at")
    if started_at is None:
        return {
            "attempt": next_attempt,
            "errors": state.get("errors", []) + [
                "Retry skipped because start time is missing"
            ],
        }

    remaining = TOTAL_BUDGET_SECONDS - (
        time.monotonic() - started_at
    )

    if remaining < PER_SITE_TIMEOUT:
        return {"attempt": next_attempt}

    retry_urls = [site["url"] for site in retry_sites]

    try:
        new_results = await fetch_many(
            retry_urls,
            product_name=parsed.product_name,
            max_results=8,
        )
    except Exception:
        logger.exception("Retry extraction failed")
        new_results = [
            EachWebsiteResult(
                website=_site_key(url),
                status="error",
                products=[],
                error_message="Retry failed",
                retryable=False,
            )
            for url in retry_urls
        ]

    # Existing results लाई site key अनुसार राखेर नयाँ result ले replace गर।
    merged = {
        _site_key(result.website): result
        for result in site_results
    }

    retry_messages = list(state.get("retry_messages", []))

    for result in new_results:
        key = _site_key(result.website)
        previous = merged.get(key)

        merged[key] = result

        if (
            previous is not None
            and previous.status == "error"
            and result.status == "ok"
        ):
            retry_messages.append(
                f"{result.website} le pahile response diyena, "
                "feri try garera paiyo."
            )

    return {
        "site_results": list(merged.values()),
        "attempt": next_attempt,
        "retry_messages": retry_messages,
    }
    
    
def validate_node(state: GraphState) -> dict:
    """Run deduplication, code rules and LLM validation."""

    parsed: ParsedQuery = state["parsed"]
    site_results = state.get("site_results", [])

    # Layer 1 + Layer 2.
    rule_passed, rejected_by_rules = validate_rules(
        site_results=site_results,
        product_name=parsed.product_name,
        category=str(parsed.category),
    )

    # LLM call nagarne if code rules le sabai products reject gare.
    if not rule_passed:
        return {
            "valid_products": [],
            "rejected": rejected_by_rules,
            "message": "Kunai website ma yo product bhetiyena.",
        }

    # Layer 3.
    valid_products, rejected_by_llm = validate_products_with_llm(
        product_name=parsed.product_name,
        products=rule_passed,
    )

    all_rejected = rejected_by_rules + rejected_by_llm

    message = ""
    if not valid_products:
        message = "Kunai website ma yo product bhetiyena."

    logger.info(
        "Validation completed: accepted=%s rejected=%s",
        len(valid_products),
        len(all_rejected),
    )

    return {
        "valid_products": valid_products,
        "rejected": all_rejected,
        "message": message,
    }


def route_after_parse(state: GraphState) -> str:
    parsed = state.get("parsed")

    if parsed is None or not parsed.is_valid_query:
        return END

    return "select_sites"


def route_after_select(state: GraphState) -> str:
    """Stop if no supported websites were selected."""

    if not state.get("sites"):
        return END

    return "extract"


def route_after_validate(state: GraphState) -> str:
    """End the graph after validation."""

    return END



def compare_node(state: GraphState) -> dict:
    """Build the final structured product comparison."""
    parsed = state.get("parsed")

    if parsed is None:
        return {
            "comparison": None,
            "message": "Product query parse bhayena.",
        }

    comparison = build_comparison(
        parsed=parsed,
        valid_products=state.get("valid_products", []),
        site_results=state.get("site_results", []),
    )

    logger.info(
        "Comparison completed: groups=%s sites=%s warnings=%s",
        len(comparison.groups),
        len(comparison.site_status),
        len(comparison.warnings),
    )
    
    for retry_message in state.get("retry_messages", []):
        comparison.warnings.append(retry_message)

    return {"comparison": comparison}

