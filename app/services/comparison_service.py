
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.schemas.comparison import (
    ComparisonGroup,
    ComparisonResult,
    Offer,
    SiteStatus,
)
from app.schemas.llm_response import ParsedQuery
from app.schemas.product import EachWebsiteResult
from app.schemas.product_validator import ValidatedProduct


MARKETPLACE_DOMAINS = {
    "daraz.com.np",
    "hamrobazar.com",
}


def get_site_key(value: str) -> str:
    """Normalize a website URL or domain into its hostname."""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or value).lower().removeprefix("www.")


def get_source_type(site_key: str) -> str:
    """Classify known marketplaces; treat other sites as retailers."""
    if any(
        site_key == domain or site_key.endswith(f".{domain}")
        for domain in MARKETPLACE_DOMAINS
    ):
        return "marketplace"
    return "retailer"


def has_unknown_variant(variant_key: str) -> bool:
    """Detect missing variant dimensions represented by '?'."""
    return any(part.strip() == "?" for part in variant_key.split("|"))


def make_variant_label(item: ValidatedProduct) -> str:
    """Build a readable label from explicitly extracted specifications."""
    parts = [
        item.ram,
        item.storage,
        item.screen_size,
    ]
    label = " / ".join(part for part in parts if part)

    if not label or has_unknown_variant(item.variant_key):
        return "Unspecified variant"

    return label


def _known_specs(item: ValidatedProduct) -> dict[str, str]:
    specs = {
        name: value
        for name, value in {
            "ram": item.ram,
            "storage": item.storage,
            "screen_size": item.screen_size,
            "chip": item.chip,
        }.items()
        if value
    }

    # Older callers only supplied variant_key. Keep that format compatible.
    if item.identity_key is None:
        parts = item.variant_key.split("|")
        for index, name in enumerate(("ram", "storage", "screen_size")):
            if index < len(parts) and parts[index] != "?":
                specs[name] = parts[index]

    return specs


def _items_are_compatible(
    first: ValidatedProduct,
    second: ValidatedProduct,
) -> bool:
    """Allow missing specs, but never hide a confirmed conflict."""
    if (
        first.identity_key
        and second.identity_key
        and first.identity_key != second.identity_key
    ):
        return False

    first_specs = _known_specs(first)
    second_specs = _known_specs(second)

    return all(
        first_specs.get(name) is None
        or second_specs.get(name) is None
        or first_specs[name] == second_specs[name]
        for name in set(first_specs) | set(second_specs)
    )


def _group_variant_key(items: list[ValidatedProduct]) -> str:
    """Build a stable key from the specifications known by this group."""
    known = {}
    for item in items:
        for name, value in _known_specs(item).items():
            known.setdefault(name, value)

    return "|".join([
        known.get("ram", "?"),
        known.get("storage", "?"),
        known.get("screen_size", "?"),
    ])


def build_comparison(
    parsed: ParsedQuery,
    valid_products: list[ValidatedProduct],
    site_results: list[EachWebsiteResult],
) -> ComparisonResult:
    """
    Group products by variant and rank offers deterministically.

    Spread is calculated using in-stock offers only. Offers with
    in_stock=None are treated as potentially available, consistent
    with the best-offer eligibility rule.
    """
    grouped: list[list[ValidatedProduct]] = []

    for item in valid_products:
        matching_group = next(
            (
                group for group in grouped
                if any(_items_are_compatible(item, existing) for existing in group)
            ),
            None,
        )
        if matching_group is None:
            grouped.append([item])
        else:
            matching_group.append(item)

    comparison_groups: list[ComparisonGroup] = []
    warnings: list[str] = []

    # Count validated offers per site for site_status.
    found_by_site: dict[str, int] = defaultdict(int)
    for item in valid_products:
        found_by_site[get_site_key(item.product.website)] += 1

    for items in grouped:
        variant_key = _group_variant_key(items)
        unknown_variant = has_unknown_variant(variant_key)

        # Keep only the cheapest offer from each site for this variant.
        cheapest_by_site: dict[str, ValidatedProduct] = {}

        for item in items:
            site_key = get_site_key(item.product.website)
            previous = cheapest_by_site.get(site_key)

            if previous is None or item.product.price < previous.product.price:
                cheapest_by_site[site_key] = item

        offers: list[Offer] = []

        for site_key, item in cheapest_by_site.items():
            source_type = get_source_type(site_key)
            product = item.product

            offers.append(
                Offer(
                    site_name=product.website,
                    site_key=site_key,
                    tier=source_type,
                    source_type=source_type,
                    product_name=product.name,
                    url=str(product.url),
                    image=str(product.image) if product.image else None,
                    price=product.price,
                    regular_price=product.regular_price,
                    in_stock=product.in_stock,
                    verified=item.verified,
                    specs_verified=item.specs_verified,
                    flags=[],
                )
            )

        # Flag unusually low prices; retain the offer in the results.
        if len(offers) >= 3:
            median_price = statistics.median(
                offer.price for offer in offers
            )
            for offer in offers:
                if offer.price < median_price * 0.5:
                    offer.flags.append("price_outlier")

        # Display offers from cheapest to most expensive.
        offers.sort(key=lambda offer: (offer.price, offer.site_key))

        # None means stock status is unknown, not explicitly out of stock.
        eligible = [
            offer for offer in offers
            if offer.in_stock is not False
        ]

        best_offer = eligible[0] if eligible else None

        # Spread excludes offers explicitly marked out of stock.
        if eligible:
            prices = [offer.price for offer in eligible]
            price_min = min(prices)
            price_max = max(prices)
            spread_amount = price_max - price_min
            spread_percent = (
                spread_amount / price_min * 100
                if price_min > 0
                else None
            )
        else:
            price_min = None
            price_max = None
            spread_amount = None
            spread_percent = None

        # Unknown specifications must never be presented as comparable.
        is_comparable = (
            not unknown_variant
            and len({offer.site_key for offer in offers}) >= 2
        )

        group = ComparisonGroup(
            variant_key=variant_key,
            label=make_variant_label(items[0]),
            offers=offers,
            best_offer=best_offer,
            price_min=price_min,
            price_max=price_max,
            spread_amount=spread_amount,
            spread_percent=spread_percent,
            is_comparable=is_comparable,
        )
        comparison_groups.append(group)

        if unknown_variant:
            warnings.append(
                "Spec thaha nabhayeko variant chha; "
                "price compare garnu aghi specifications verify garnus."
            )

        if best_offer is None:
            warnings.append(
                f"{group.label}: sabai offers out of stock chhan."
            )
        else:
            if best_offer.source_type == "marketplace":
                warnings.append(
                    "Marketplace seller, verify before buying."
                )

            if not best_offer.verified:
                warnings.append(
                    "Best offer ko exact model/specifications verify bhayeko chhaina."
                )

        if spread_percent is not None and spread_percent > 40:
            warnings.append(
                f"{group.label}: price farak dherai chha; "
                "product same ho ki verify garnus."
            )

    # Comparable groups first, then fully specified groups, then
    # groups with more distinct sites. Lower price breaks remaining ties.
    comparison_groups.sort(
        key=lambda group: (
            not group.is_comparable,
            has_unknown_variant(group.variant_key),
            -len({offer.site_key for offer in group.offers}),
            group.best_offer.price if group.best_offer else float("inf"),
            group.variant_key,
        )
    )

    # Explain every website's result without exposing technical errors.
    site_status: list[SiteStatus] = []

    for result in site_results:
        site_key = get_site_key(result.website)
        found_count = found_by_site.get(site_key, 0)

        if result.status == "error":
            message = "Site did not respond"
        elif result.status == "empty":
            message = "Product not found"
        elif found_count > 0:
            message = f"{found_count} offers found"
        else:
            message = "Only accessories/other models found"

        site_status.append(
            SiteStatus(
                name=result.website,
                status=result.status,
                found_count=found_count,
                elapsed_seconds=result.elapsed_seconds,
                message=message,
            )
        )

    # Only advertise a cross-site cheapest price for a comparable group.
    comparable_groups = [
        group for group in comparison_groups
        if group.is_comparable and group.best_offer is not None
    ]

    site_count = len({
        get_site_key(item.product.website)
        for item in valid_products
    })

    if comparable_groups:
        main_group = comparable_groups[0]
        best = main_group.best_offer
        summary = (
            f"{len(comparison_groups)} variants, {site_count} sites ma "
            f"offers bhetiye. {main_group.label} ko sabai bhanda sasto: "
            f"{best.site_name} ma Rs. {best.price:,.2f}."
        )
    elif valid_products:
        summary = (
            f"{len(comparison_groups)} variants, {site_count} sites ma "
            "offers bhetiye, tara same variant ko reliable cross-site "
            "comparison garna milena."
        )
        warnings.append(
            "Compare garna kam se kam 2 sites ma same variant chahincha."
        )
    else:
        summary = (
            "Kunai website ma valid matching product bhetiyena."
        )

    # Deduplicate repeated warnings while preserving their order.
    warnings = list(dict.fromkeys(warnings))

    return ComparisonResult(
        query=parsed.product_name,
        groups=comparison_groups,
        site_status=site_status,
        warnings=warnings,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
