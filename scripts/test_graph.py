
import asyncio
import sys
import time
from pathlib import Path

# Project root lai Python import path ma add gara.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.builder import graph


TEST_QUERIES = [
    "iPhone 15",
    "macbook air m3 price in nepal",
    "asdfgh123",
    "Nike running shoes",
]


async def test_one_query(query: str) -> None:
    print("\n" + "=" * 70)
    print(f"Input: {query}")

    start_time = time.perf_counter()

    try:
        result = await graph.ainvoke({"user_query": query})
    except Exception:
        print("Graph execution failed:")
        raise

    total_time = time.perf_counter() - start_time

    print(f"Total time: {total_time:.2f}s")
    print(f"Message: {result.get('message', '')}")

    parsed = result.get("parsed")
    if parsed is not None:
        print(f"Parsed query: {parsed}")
    else:
        print("Parsed query: Not available")

    sites = result.get("sites") or []
    site_names = [
        site.get("name", "Unknown site")
        for site in sites
        if isinstance(site, dict)
    ]
    print(f"Selected sites: {site_names}")

    site_results = result.get("site_results") or []

    if not site_results:
        print("Site results: None (early exit or no results)")
        return

    for site_result in site_results:
        # None result aaye crash nahos.
        if site_result is None:
            print("\nWarning: None result received from fetcher.")
            continue

        # Pydantic model lai dictionary ma convert gara.
        if hasattr(site_result, "model_dump"):
            data = site_result.model_dump()
        elif isinstance(site_result, dict):
            data = site_result
        else:
            print(
                "\nWarning: Unexpected result type:"
                f" {type(site_result).__name__}"
            )
            continue

        if not isinstance(data, dict):
            print(f"\nWarning: Invalid result data: {data!r}")
            continue

        products = data.get("products") or []

        print(
            f"\nWebsite: {data.get('website', 'Unknown')}"
            f" | Status: {data.get('status', 'Unknown')}"
            f" | Products: {len(products)}"
            f" | Elapsed: {data.get('elapsed_seconds')}s"
        )

        if data.get("error_message"):
            print(f"  Error: {data['error_message']}")

        # iPhone 15 ko first 2 products matra display gara.
        if query == "iPhone 15":
            for product in products[:2]:
                if product is None:
                    continue

                if hasattr(product, "model_dump"):
                    product = product.model_dump()

                if not isinstance(product, dict):
                    continue

                print(
                    f"  - {product.get('name', 'Unknown product')}"
                    f" | Price: {product.get('price')}"
                    f" | Currency: {product.get('currency', 'NPR')}"
                )


async def main() -> None:
    for query in TEST_QUERIES:
        await test_one_query(query)


if __name__ == "__main__":
    asyncio.run(main())
