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

# Bacheko time yo bhanda kam bhayo bhane site skip garne (seconds)
MIN_SITE_TIME = 15.0


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


def _base_url() -> str:
    return (settings.EXTRACTOR_API_URL or "").rstrip("/")


def _auth_headers() -> dict[str, str]:
    """API key header (only if configured)."""
    if settings.EXTRACTOR_API_KEY:
        return {"X-API-Key": settings.EXTRACTOR_API_KEY}
    return {}


# Render free instance sutdai huna sakcha, tesaile pahile uthaune
async def wake_extractor() -> None:
    """Ping /health once so a sleeping extractor starts before real requests."""
    base = _base_url()
    if not base:
        return

    started_at = time.perf_counter()

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(40.0, connect=10.0)
        ) as client:
            response = await client.get(f"{base}/health", headers=_auth_headers())

        logger.info(
            "Extractor wake-up status=%s elapsed=%.2fs",
            response.status_code,
            time.perf_counter() - started_at,
        )
    except httpx.HTTPError as exc:
        # Wake-up fail bhaye pani real request try garne
        logger.warning(
            "Extractor wake-up failed error=%s elapsed=%.2fs",
            type(exc).__name__,
            time.perf_counter() - started_at,
        )


# Extractor API bata products fetch garne
async def fetch_website(
    website_url: str,
    product_name: str,
    max_results: int = 5,
    read_timeout: float | None = None,
) -> EachWebsiteResult:
    """Fetch and validate products from one website."""

    website_name = get_website_name(website_url)
    started_at = time.perf_counter()

    if not website_name:
        return error_result(
            website="unknown",
            error_message="Invalid website URL",
        )

    base_url = _base_url()

    if not base_url:
        logger.error("EXTRACTOR_API_URL is not configured")
        return error_result(
            website=website_name,
            error_message="EXTRACTOR_API_URL is not configured",
        )

    endpoint = f"{base_url}/extract"

    # Bacheko budget bhanda badhi parkhane haina
    read_seconds = (
        min(PER_SITE_TIMEOUT, read_timeout) if read_timeout else PER_SITE_TIMEOUT
    )

    timeout = httpx.Timeout(
        read_seconds,
        connect=10.0,
        read=read_seconds,
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
                headers=_auth_headers(),
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

            if response.status_code in (401, 403):
                return error_result(
                    website=website_name,
                    error_message="Extractor rejected the API key",
                )

            if response.status_code == 503:
                return error_result(
                    website=website_name,
                    error_message="Extractor is busy",
                    retryable=True,
                )

            # Body user-facing message ma nahalne (log ma matra)
            return error_result(
                website=website_name,
                error_message=f"Extractor returned HTTP {response.status_code}",
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

    # Connect timeout: extractor samma pugna sakena (URL galat / down)
    except httpx.ConnectTimeout as exc:
        logger.error(
            "Extractor connect timeout site=%s elapsed=%.2fs type=%s",
            website_name,
            time.perf_counter() - started_at,
            type(exc).__name__,
        )
        return error_result(
            website=website_name,
            error_message="Could not reach extractor (connect timeout)",
            retryable=True,
        )

    # Read/write/pool timeout: pugyo tara response aayena (slow / hang)
    except httpx.TimeoutException as exc:
        logger.error(
            "Extractor timeout site=%s elapsed=%.2fs type=%s",
            website_name,
            time.perf_counter() - started_at,
            type(exc).__name__,
        )
        return error_result(
            website=website_name,
            error_message="Extractor did not respond in time",
            retryable=True,
        )

    except httpx.ConnectError as exc:
        logger.error(
            "Extractor connection failure site=%s elapsed=%.2fs error=%s",
            website_name,
            time.perf_counter() - started_at,
            str(exc),
        )
        return error_result(
            website=website_name,
            error_message="Could not connect to extractor API",
            retryable=True,
        )

    except httpx.RequestError as exc:
        logger.exception(
            "Extractor request error site=%s type=%s",
            website_name,
            type(exc).__name__,
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


# Multiple websites fetch garne (default: ek-ek garera)
async def fetch_many(
    urls: list[str],
    product_name: str,
    max_results: int = 5,
    deadline: float | None = None,
) -> list[EachWebsiteResult]:
    """
    Fetch products from multiple websites.

    deadline: time.monotonic() based timestamp. Time sakkiyo bhane bacheko
    site skip hunchha ra aile samma ko result return hunchha.
    """

    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_EXTRACTS)

    await wake_extractor()

    async def limited_fetch(url: str) -> EachWebsiteResult:
        async with semaphore:
            start_time = time.perf_counter()

            read_timeout = None

            # Semaphore pachi check garne (aghi ko site le time khayo hola)
            if deadline is not None:
                remaining = deadline - time.monotonic()

                if remaining < MIN_SITE_TIME:
                    logger.warning(
                        "Site skipped (time budget) url=%s remaining=%.1fs",
                        url,
                        remaining,
                    )
                    skipped = error_result(
                        website=get_website_name(url) or "unknown",
                        error_message="Skipped: time budget exhausted",
                    )
                    skipped.elapsed_seconds = 0.0
                    return skipped

                read_timeout = remaining

            try:
                result = await fetch_website(
                    website_url=url,
                    product_name=product_name,
                    max_results=max_results,
                    read_timeout=read_timeout,
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

    tasks = [limited_fetch(url) for url in urls]

    return await asyncio.gather(*tasks)