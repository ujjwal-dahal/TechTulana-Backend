import asyncio
import time

import pytest

from app.core.sites import get_all_sites
from app.core.config import settings
from app.tools.extractor_client import fetch_many


PRODUCTS_BY_CATEGORY = {
    "mobile": ["iPhone 15"],
    "laptop": ["MacBook Air M3"],
    "accessories": ["Logitech mouse"],
    "tv": ["Samsung Smart TV"],
    "appliance": ["Samsung washing machine"],
    "fashion": ["Nike Air Force 1"],
    "general": ["iPhone 15", "MacBook Air M3", "Logitech mouse"],
}


def get_test_queries(site: dict) -> list[str]:
    """Select three distinct product queries for a website."""
    queries = []

    for category in site["categories"]:
        candidates = PRODUCTS_BY_CATEGORY.get(category, [])

        for product in candidates:
            if product not in queries:
                queries.append(product)
                break

        if len(queries) == 3:
            break

    # If the site supports fewer than three categories,
    # fill the remaining queries with distinct general products.
    for product in PRODUCTS_BY_CATEGORY["general"]:
        if product not in queries:
            queries.append(product)

        if len(queries) == 3:
            break

    return queries[:3]


def get_product_field(product, field: str):
    """Read a field from either a Pydantic model or dictionary."""
    if isinstance(product, dict):
        return product.get(field, "-")

    return getattr(product, field, "-")


@pytest.mark.integration
def test_live_site_extraction():
    """Call the real Extractor API for every registered website."""

    if not settings.EXTRACTOR_API_URL:
        pytest.skip("EXTRACTOR_API_URL is not configured")

    sites = get_all_sites()
    rows = []

    async def run_tests():
        for site in sites:
            queries = get_test_queries(site)

            for query in queries:
                start = time.perf_counter()

                results = await fetch_many(
                    urls=[site["url"]],
                    product_name=query,
                    max_results=5,
                )

                elapsed = time.perf_counter() - start

                result = results[0]

                first_product = (
                    result.products[0] if result.products else None
                )

                rows.append({
                    "site": site["name"],
                    "key": site["key"],
                    "query": query,
                    "status": result.status,
                    "count": len(result.products),
                    "elapsed": elapsed,
                    "name": (
                        get_product_field(first_product, "name")
                        if first_product else "-"
                    ),
                    "price": (
                        get_product_field(first_product, "price")
                        if first_product else "-"
                    ),
                    "error": getattr(result, "error_message", None) or "-",
                })

    asyncio.run(run_tests())

    # Print diagnostic results.
    headers = [
        "Website", "Query", "Status", "Count",
        "Seconds", "First product", "Price", "Error",
    ]

    table_rows = [
        [
            row["site"],
            row["query"],
            row["status"],
            str(row["count"]),
            f'{row["elapsed"]:.2f}',
            str(row["name"]),
            str(row["price"]),
            str(row["error"]),
        ]
        for row in rows
    ]

    widths = [
        max(len(headers[i]), *(len(row[i]) for row in table_rows))
        for i in range(len(headers))
    ]

    print("\n\nLIVE EXTRACTOR RESULTS\n")

    print(" | ".join(
        headers[i].ljust(widths[i])
        for i in range(len(headers))
    ))
    print("-+-".join("-" * width for width in widths))

    for row in table_rows:
        print(" | ".join(
            row[i].ljust(widths[i])
            for i in range(len(headers))
        ))

    # Summarize whether each site met the 2-of-3 criterion.
    print("\nSITE RECOMMENDATIONS\n")

    for site in sites:
        site_rows = [
            row for row in rows
            if row["key"] == site["key"]
        ]

        successful = sum(
            row["status"] == "ok" and row["count"] > 0
            for row in site_rows
        )

        if site["source_type"] == "editorial":
            recommendation = (
                "Editorial source: evaluate separately; "
                "do not treat as a retailer."
            )
        elif successful >= 2:
            recommendation = "Candidate for enabled=True"
        else:
            recommendation = (
                "Keep disabled; investigate extraction failures."
            )

        print(
            f'{site["name"]}: '
            f'{successful}/{len(site_rows)} successful — '
            f'{recommendation}'
        )

    # These assertions validate the test harness, not website reliability.
    assert len(rows) == len(sites) * 3
    assert all(
        row["status"] in {"ok", "empty", "error"}
        for row in rows
    )