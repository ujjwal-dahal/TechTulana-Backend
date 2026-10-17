
import asyncio
import logging
import time
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.retry_config import PER_SITE_TIMEOUT
from app.schemas.product import (
    RawExtractedProduct,
    to_product,
    EachWebsiteResult,
)
from app.services.product_validation import validate_product_match


# Logger setup
setup_logging()
logger = logging.getLogger(__name__)


# Website URL bata domain name extract garne
def get_website_name(url: str) -> str:
    """Extract the hostname from a website URL."""
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname

    if not hostname:
        return ""

    return hostname.lower().removeprefix("www.")


# Error result same format ma return garne
def error_result(
    website: str,
    error_message: str,
    retryable: bool = False,
) -> EachWebsiteResult:
    return EachWebsiteResult(
        website=website,
        status="error",
        products=[],
        error_message=error_message,
        retryable=retryable,
    )


# Extractor API bata products fetch garne
async def fetch_website(
    website_url: str,
    product_name: str,
    max_results: int = 5,
) -> EachWebsiteResult:
    """Fetch and validate products from one website."""

    website_name = get_website_name(website_url)
    started_at = time.perf_counter()

    if not website_name:
        return error_result(
            website="unknown",
            error_message="Invalid website URL",
        )

    if not settings.EXTRACTOR_API_URL:
        logger.error("EXTRACTOR_API_URL is not configured")
        return error_result(
            website=website_name,
            error_message="EXTRACTOR_API_URL is not configured",
        )

    endpoint = f"{settings.EXTRACTOR_API_URL.rstrip('/')}/extract"

    timeout = httpx.Timeout(
        60.0,
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=10.0,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                endpoint,
                json={
                    "website_url": website_url,
                    "product_name": product_name,
                    "max_results": max_results,
                },
            )

        elapsed = time.perf_counter() - started_at

        logger.info(
            "Extractor response site=%s status=%s elapsed=%.2fs",
            website_name,
            response.status_code,
            elapsed,
        )

        # HTTP errors handle garne
        if not response.is_success:
            body = response.text[:1000]

            logger.error(
                "Extractor HTTP error site=%s status=%s body=%s",
                website_name,
                response.status_code,
                body,
            )

            return error_result(
                website=website_name,
                error_message=(
                    f"Extractor returned HTTP {response.status_code}: "
                    f"{body[:300]}"
                ),
                retryable=response.status_code == 429
                or response.status_code >= 500,
            )

        # JSON response parse garne
        try:
            payload = response.json()
        except ValueError:
            logger.error(
                "Invalid JSON from extractor site=%s body=%s",
                website_name,
                response.text[:500],
            )
            return error_result(
                website=website_name,
                error_message="Extractor returned invalid JSON",
                retryable=True,
            )

        if not isinstance(payload, dict):
            return error_result(
                website=website_name,
                error_message="Invalid extractor response format",
            )

        raw_products = payload.get("products", [])

        if not isinstance(raw_products, list):
            return error_result(
                website=website_name,
                error_message="Invalid extractor response: products must be a list",
            )

        if not raw_products:
            logger.info(
                "No raw products found site=%s query=%s",
                website_name,
                product_name,
            )
            return EachWebsiteResult(
                website=website_name,
                status="empty",
                products=[],
            )

        products = []

        for item in raw_products:
            if not isinstance(item, dict):
                logger.warning(
                    "Skipping non-dictionary product site=%s",
                    website_name,
                )
                continue

            try:
                raw = RawExtractedProduct(**item)

                is_match, reason = validate_product_match(
                    product_name=product_name,
                    extracted_name=raw.name,
                )

                if not is_match:
                    logger.info(
                        "Product skipped site=%s name=%s reason=%s",
                        website_name,
                        raw.name,
                        reason,
                    )
                    continue

                product = to_product(raw, website_name)

                if product is not None:
                    products.append(product)

            except ValidationError as exc:
                logger.warning(
                    "Invalid product data site=%s error=%s",
                    website_name,
                    str(exc)[:300],
                )

        logger.info(
            "Product processing complete site=%s raw=%d matched=%d",
            website_name,
            len(raw_products),
            len(products),
        )

        return EachWebsiteResult(
            website=website_name,
            status="ok" if products else "empty",
            products=products,
        )

    except httpx.TimeoutException as exc:
        elapsed = time.perf_counter() - started_at

        logger.error(
            "Extractor timeout site=%s elapsed=%.2fs error=%s",
            website_name,
            elapsed,
            str(exc),
        )

        return error_result(
            website=website_name,
            error_message="Extractor request timed out",
            retryable=True,
        )

    except httpx.ConnectError as exc:
        elapsed = time.perf_counter() - started_at

        logger.error(
            "Extractor connection failure site=%s elapsed=%.2fs error=%s",
            website_name,
            elapsed,
            str(exc),
        )

        return error_result(
            website=website_name,
            error_message="Could not connect to extractor API",
            retryable=True,
        )

    except httpx.RequestError as exc:
        logger.exception(
            "Extractor request error site=%s",
            website_name,
        )

        return error_result(
            website=website_name,
            error_message=f"Extractor request failed: {type(exc).__name__}",
            retryable=True,
        )

    except Exception as exc:
        logger.exception(
            "Unexpected extractor error site=%s",
            website_name,
        )

        return error_result(
            website=website_name,
            error_message=f"Unexpected error: {type(exc).__name__}",
        )


# Multiple websites concurrently fetch garne
async def fetch_many(
    urls: list[str],
    product_name: str,
    max_results: int = 5,
) -> list[EachWebsiteResult]:
    """Fetch products from multiple websites concurrently."""

    semaphore = asyncio.Semaphore(3)

    async def limited_fetch(url: str) -> EachWebsiteResult:
        async with semaphore:
            start_time = time.perf_counter()

            try:
                result = await fetch_website(
                    website_url=url,
                    product_name=product_name,
                    max_results=max_results,
                )

            except Exception:
                logger.exception(
                    "Unexpected failure in limited_fetch url=%s",
                    url,
                )
                result = error_result(
                    website=get_website_name(url) or "unknown",
                    error_message="Unexpected website fetch failure",
                )

            elapsed = round(time.perf_counter() - start_time, 2)
            result.elapsed_seconds = elapsed

            if elapsed >= PER_SITE_TIMEOUT * 0.8:
                logger.warning(
                    "Slow extractor site=%s status=%s elapsed=%.2fs",
                    result.website,
                    result.status,
                    elapsed,
                )

            return result

    tasks = [
        limited_fetch(url)
        for url in urls
    ]

    return await asyncio.gather(*tasks)
