from unittest.mock import patch

from app.schemas.product import Product
from app.schemas.product_validator import (
    BatchVerdict,
    ProductVerdict,
)
from app.services.llm_product_validator import (
    validate_products_with_llm,
)


def make_product(name: str, price: float = 120000) -> Product:
    return Product(
        name=name,
        url=f"https://example.com/{price}",
        website="example.com",
        price=price,
        currency="NPR",
        key_specs={},
    )


def test_matching_product_is_verified():
    product = make_product("Apple iPhone 15 128GB")

    fake_llm = object()

    with (
        patch(
            "app.services.llm_product_validator.create_llm",
            return_value=fake_llm,
        ),
        patch(
            "app.services.llm_product_validator._validate_one_batch",
            return_value=[
                ProductVerdict(
                    id=0,
                    is_match=True,
                    reason="Same model",
                    storage="128GB",
                )
            ],
        ),
    ):
        accepted, rejected = validate_products_with_llm(
            "iPhone 15",
            [product],
        )

    assert len(accepted) == 1
    assert accepted[0].verified is True
    assert accepted[0].storage == "128GB"
    assert rejected == []


def test_non_matching_product_is_rejected():
    product = make_product("Apple iPhone 15 Pro Max")

    with (
        patch(
            "app.services.llm_product_validator.create_llm",
            return_value=object(),
        ),
        patch(
            "app.services.llm_product_validator._validate_one_batch",
            return_value=[
                ProductVerdict(
                    id=0,
                    is_match=False,
                    reason="Different model variant",
                )
            ],
        ),
    ):
        accepted, rejected = validate_products_with_llm(
            "iPhone 15",
            [product],
        )

    assert accepted == []
    assert rejected[0]["reason_code"] == "llm_not_match"


def test_missing_verdict_keeps_product_unverified():
    product = make_product("Apple iPhone 15")

    with (
        patch(
            "app.services.llm_product_validator.create_llm",
            return_value=object(),
        ),
        patch(
            "app.services.llm_product_validator._validate_one_batch",
            return_value=[],
        ),
    ):
        accepted, rejected = validate_products_with_llm(
            "iPhone 15",
            [product],
        )

    assert len(accepted) == 1
    assert accepted[0].verified is False
    assert rejected == []


def test_llm_failure_keeps_product_unverified():
    product = make_product("Apple iPhone 15")

    with (
        patch(
            "app.services.llm_product_validator.create_llm",
            return_value=object(),
        ),
        patch(
            "app.services.llm_product_validator._validate_one_batch",
            side_effect=TimeoutError("Mock timeout"),
        ),
    ):
        accepted, rejected = validate_products_with_llm(
            "iPhone 15",
            [product],
        )

    assert len(accepted) == 1
    assert accepted[0].verified is False
    assert rejected == []