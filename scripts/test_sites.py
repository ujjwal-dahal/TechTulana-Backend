
# scripts/test_sites.py

import asyncio
import time

from app.core.sites import get_all_sites

# आफ्नो project मा fetch_website रहेको वास्तविक module path राख्नु।
from app.tools.extractor_client import fetch_many


# प्रत्येक category का लागि test गर्न मिल्ने products।
PRODUCTS_BY_CATEGORY = {
    "mobile": [
        "iPhone 15",
        "Samsung Galaxy S24",
        "Redmi Note 13",
    ],
    "laptop": [
        "MacBook Pro",
        "Dell Inspiron laptop",
        "Lenovo IdeaPad laptop",
    ],
    "accessories": [
        "Logitech mouse",
        "Logitech keyboard",
        "Anker charger",
    ],
    "tv": [
        "Samsung Smart TV",
        "LG Smart TV",
        "Sony Bravia TV",
    ],
    "appliance": [
        "Samsung refrigerator",
        "LG washing machine",
        "Philips air fryer",
    ],
    "fashion": [
        "Nike running shoes",
        "Adidas t-shirt",
        "Levi's jeans",
    ],
    "general": [
        "iPhone 15",
        "Samsung Galaxy S24",
        "Logitech mouse",
    ],
}


def get_test_queries(site: dict) -> list[str]:
    """Select three products supported by this website's categories."""

    categories = site["categories"]
    queries = []

    for category in categories:
        category_products = PRODUCTS_BY_CATEGORY.get(category, [])

        for product in category_products:
            if product not in queries:
                queries.append(product)

            if len(queries) == 3:
                return queries

    # Fallback when the site has fewer than three category-specific products.
    for product in PRODUCTS_BY_CATEGORY["general"]:
        if product not in queries:
            queries.append(product)

        if len(queries) == 3:
            break

    return queries


def get_first_product(products: list) -> str:
    """Format the first extracted product's name and price."""

    if not products:
        return "-"

    product = products[0]

    name = getattr(product, "name", None)
    price = getattr(product, "price", None)

    # Support dictionary-shaped results as well.
    if isinstance(product, dict):
        name = product.get("name", name)
        price = product.get("price", price)

    return f"{name or 'Unknown'} | {price if price is not None else 'N/A'}"


async def test_one_site(site: dict) -> list[dict]:
    """Test one website sequentially with three queries."""

    results = []
    queries = get_test_queries(site)

    for query in queries:
        start_time = time.perf_counter()

        try:
            # fetch_many uses the existing Semaphore(3).
            # Only one website is tested at a time in this script.
            website_results = await fetch_many(
                urls=[site["url"]],
                product_name=query,
                max_results=5,
            )

            elapsed = time.perf_counter() - start_time
            result = website_results[0]

            products = result.products or []

            results.append({
                "site": site["key"],
                "query": query,
                "status": result.status,
                "count": len(products),
                "time": f"{elapsed:.1f}s",
                "first_product": get_first_product(products),
                "error": getattr(result, "error_message", None),
            })

        except Exception as error:
            elapsed = time.perf_counter() - start_time

            results.append({
                "site": site["key"],
                "query": query,
                "status": "error",
                "count": 0,
                "time": f"{elapsed:.1f}s",
                "first_product": "-",
                "error": str(error),
            })

    return results


def print_results(results: list[dict]) -> None:
    """Print a readable results table."""

    columns = [
        ("site", "site"),
        ("query", "query"),
        ("status", "status"),
        ("count", "count"),
        ("time", "time"),
        ("first_product", "first_product"),
    ]

    widths = {
        key: max(
            len(title),
            *(len(str(row[key])) for row in results),
        )
        for key, title in columns
    }

    header = "  ".join(
        title.ljust(widths[key])
        for key, title in columns
    )

    print("\n" + header)
    print("-" * len(header))

    for row in results:
        print(
            "  ".join(
                str(row[key]).ljust(widths[key])
                for key, _ in columns
            )
        )


def print_recommendations(
    sites: list[dict],
    results: list[dict],
) -> None:
    """Recommend enabled status using the 2-of-3 rule."""

    print("\nSite recommendations")
    print("-" * 60)

    for site in sites:
        site_results = [
            row for row in results
            if row["site"] == site["key"]
        ]

        successful = sum(
            row["status"] == "ok"
            and row["count"] > 0
            for row in site_results
        )

        recommended = successful >= 2

        print(
            f"{site['key']}: "
            f"{successful}/3 successful -> "
            f"enabled={recommended}"
        )

        if not recommended:
            failed_reasons = [
                f"{row['query']}: "
                f"{row['error'] or row['status']}"
                for row in site_results
                if row["status"] != "ok" or row["count"] == 0
            ]

            reason = "; ".join(failed_reasons) or "Insufficient results"

            print(f"  # Keep disabled: {reason}")

        elif site.get("source_type") == "editorial":
            print(
                "  # Extraction works, but this is an editorial "
                "source, not a retailer for price comparison."
            )


async def main() -> None:
    sites = get_all_sites()
    all_results = []

    for site in sites:
        print(f"\nTesting {site['name']}...")

        # Finish all three queries for this site before moving on.
        site_results = await test_one_site(site)
        all_results.extend(site_results)

    print_results(all_results)
    print_recommendations(sites, all_results)


if __name__ == "__main__":
    asyncio.run(main())
