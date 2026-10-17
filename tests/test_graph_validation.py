
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.builder import build_graph
from app.schemas.llm_response import ParsedQuery
from app.schemas.product import EachWebsiteResult, Product
from app.schemas.product_validator import ValidatedProduct


@pytest.mark.anyio
async def test_graph_runs_through_validation():
    product = Product(
        name="Apple iPhone 15 128GB",
        url="https://example.com/iphone-15",
        website="example.com",
        price=119499,
        currency="NPR",
        key_specs={"storage": "128GB"},
    )

    parsed_query = ParsedQuery(
        product_name="iPhone 15",
        brand="Apple",
        category="mobile",
        is_valid_query=True,
        reason="",
    )

    website_result = EachWebsiteResult(
        website="example.com",
        status="ok",
        products=[product],
    )

    validated_product = ValidatedProduct(
        product=product,
        verified=True,
        variant_key="?|128GB|?",
        storage="128GB",
    )

    with (
        patch(
            "app.graph.nodes.parse_query",
            return_value=parsed_query,
        ),
        patch(
            "app.graph.nodes.select_sites",
            return_value=[
                {"url": "https://example.com"}
            ],
        ),
        patch(
            "app.graph.nodes.fetch_many",
            new_callable=AsyncMock,
            return_value=[website_result],
        ),
        patch(
            "app.graph.nodes.validate_rules",
            return_value=([product], []),
        ),
        patch(
            "app.graph.nodes.validate_products_with_llm",
            return_value=([validated_product], []),
        ),
    ):
        graph = build_graph()

        result = await graph.ainvoke(
            {"user_query": "iPhone 15"}
        )

    assert len(result["valid_products"]) == 1
    assert result["valid_products"][0].verified is True
    assert result["rejected"] == []
    assert result["message"] == ""
