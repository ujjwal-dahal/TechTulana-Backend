
import time

from app.agents.query_parser_Agent1 import parse_query, select_sites


TEST_QUERIES = [
    "iPhone 15",
    "macbook air m3 price in nepal",
    "Samsung 43 inch smart tv",
    "Logitech mouse",
    "asdfgh123",
    "sasto laptop dekhau",
]


def main():
    for query in TEST_QUERIES:
        # Pratyek request ko execution time measure gara.
        start_time = time.perf_counter()

        parsed = parse_query(query)

        elapsed = time.perf_counter() - start_time

        print("\n" + "=" * 60)
        print(f"Input: {query}")
        print(f"Time: {elapsed:.2f} seconds")

        # Pydantic object lai readable JSON ma print gara.
        print(parsed.model_dump_json(indent=2))

        # Site selection LLM bina Python bata huncha.
        sites = select_sites(parsed)
        site_names = [site["name"] for site in sites]

        print(f"Selected sites: {site_names or 'No supported sites'}")


if __name__ == "__main__":
    main()
