import re
from typing import Any

from app.core.validation_config import (
    ACCESSORY_KEYWORDS,
    PRICE_FLOORS,
    VARIANT_WORDS,
)
from app.schemas.product import EachWebsiteResult, Product


def tokenize(text: str) -> list[str]:
    """Normalize product text into comparable tokens."""
    text = text.lower().replace("+", " plus ")

    # M3 -> M 3, S24 -> S 24
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)

    return re.findall(r"[a-z0-9]+", text)


def normalize_name(name: str) -> str:
    """Return a normalized product name."""
    return " ".join(tokenize(name))


def contains_keyword(
    tokens: list[str],
    keyword: str,
) -> bool:
    """Match a keyword as complete tokens, not substrings."""
    keyword_tokens = tokenize(keyword)

    if not keyword_tokens:
        return False

    size = len(keyword_tokens)

    return any(
        tokens[index:index + size] == keyword_tokens
        for index in range(len(tokens) - size + 1)
    )


def get_rejection_reason(
    product: Product,
    product_name: str,
    category: str,
) -> str | None:
    """Apply deterministic validation rules."""

    title_tokens = tokenize(product.name)
    query_tokens = set(tokenize(product_name))
    normalized_category = category.lower().strip()

    # Rule 1: Reject clearly identified accessories.
    if normalized_category != "accessories":
        for keyword in ACCESSORY_KEYWORDS:
            if contains_keyword(title_tokens, keyword):
                return "accessory"

    # Rule 2: Reject suspiciously low prices.
    price_floor = PRICE_FLOORS.get(normalized_category)

    if price_floor is not None and product.price < price_floor:
        return "price_floor"

    # Rule 3: Reject a variant explicitly present in the title
    # but absent from the user's query.
    title_token_set = set(title_tokens)

    extra_variants = (
        title_token_set & VARIANT_WORDS
    ) - query_tokens

    if extra_variants:
        return "variant_word"

    return None


def validate_rules(
    site_results: list[EachWebsiteResult],
    product_name: str,
    category: str,
) -> tuple[list[Product], list[dict[str, Any]]]:
    """
    Layer 1: Deduplicate within each website.
    Layer 2: Apply deterministic validation rules.
    """

    accepted: list[Product] = []
    rejected: list[dict[str, Any]] = []

    seen_urls: set[tuple[str, str]] = set()
    seen_name_prices: set[tuple[str, str, float]] = set()

    for site_result in site_results:
        site = site_result.website.strip().lower()

        for product in site_result.products:
            normalized_url = str(product.url).rstrip("/").lower()
            normalized_name = normalize_name(product.name)

            url_key = (site, normalized_url)
            name_price_key = (
                site,
                normalized_name,
                product.price,
            )

            # Layer 1: Same URL or same normalized name + price
            # on the same website means duplicate.
            if (
                url_key in seen_urls
                or name_price_key in seen_name_prices
            ):
                rejected.append({
                    "site": site_result.website,
                    "name": product.name,
                    "price": product.price,
                    "reason_code": "duplicate",
                })
                continue

            seen_urls.add(url_key)
            seen_name_prices.add(name_price_key)

            # Layer 2: Price, accessory and variant checks.
            reason = get_rejection_reason(
                product=product,
                product_name=product_name,
                category=category,
            )

            if reason:
                rejected.append({
                    "site": site_result.website,
                    "name": product.name,
                    "price": product.price,
                    "reason_code": reason,
                })
                continue

            accepted.append(product)

    return accepted, rejected