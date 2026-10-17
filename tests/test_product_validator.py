import pytest

from app.schemas.product import Product, EachWebsiteResult
from app.services.product_validator import validate_rules


def make_product(
    name: str,
    price: float,
    url: str,
) -> Product:
    return Product(
        name=name,
        url=url,
        website="example.com",
        price=price,
        currency="NPR",
        brand=None,
        key_specs={},
    )


def make_result(
    products: list[Product],
) -> EachWebsiteResult:
    return EachWebsiteResult(
        website="example.com",
        status="ok",
        products=products,
    )


@pytest.mark.parametrize(
    ("name", "price", "query", "category", "expected"),
    [
        (
            "iPhone 15",
            399,
            "iPhone 15",
            "mobile",
            "price_floor",
        ),
        (
            "Prodigee Balance Case for iPhone 15 Series",
            6500,
            "iPhone 15",
            "mobile",
            "accessory",
        ),
        (
            "PULWTOP MacBook Docking Station",
            15420,
            "MacBook Pro M3",
            "laptop",
            "accessory",
        ),
        (
            "iPhone 15 Pro Max",
            206000,
            "iPhone 15",
            "mobile",
            "variant_word",
        ),
        (
            "iPhone 15",
            119499,
            "iPhone 15",
            "mobile",
            None,
        ),
        (
            "Logitech Pebble Mouse 2",
            4200,
            "Logitech Pebble Mouse 2",
            "accessories",
            None,
        ),
    ],
)
def test_validation_rules(
    name,
    price,
    query,
    category,
    expected,
):
    product = make_product(
        name,
        price,
        f"https://example.com/products/{price}",
    )

    accepted, rejected = validate_rules(
        site_results=[make_result([product])],
        product_name=query,
        category=category,
    )

    if expected is None:
        assert len(accepted) == 1
        assert rejected == []
    else:
        assert accepted == []
        assert rejected[0]["reason_code"] == expected


def test_duplicate_product_is_removed():
    first = make_product(
        "iPhone 15",
        119499,
        "https://example.com/iphone-15",
    )

    duplicate = make_product(
        "iPhone 15",
        119499,
        "https://example.com/iphone-15/",
    )

    accepted, rejected = validate_rules(
        site_results=[
            make_result([first, duplicate]),
        ],
        product_name="iPhone 15",
        category="mobile",
    )

    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0]["reason_code"] == "duplicate"