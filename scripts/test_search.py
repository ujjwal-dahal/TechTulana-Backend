
from app.tools.search_tool import search_web


QUERIES = [
    "iPhone 15",
    "MacBook Air M3",
    "asdfgh123",
]


def main():
    for query in QUERIES:
        results = search_web(query)

        # Remove duplicate domains while preserving order.
        domains = list(
            dict.fromkeys(
                item["domain"] for item in results
            )
        )

        print(f"\n{query} -> {', '.join(domains) or 'No results'}")


if __name__ == "__main__":
    main()
