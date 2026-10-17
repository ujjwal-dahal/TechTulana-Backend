
import pytest
from pydantic import ValidationError

from app.schemas.product import RawExtractedProduct, to_product


@pytest.fixture
def test_products():
    return [
        {
            "name": "MacBook Pro M5",
            "url": "https://gadgetbytenepal.com/macbook-pro-m5",
            "price": 250000,
            "regular_price": 270000,
            "currency": "NPR",
            "in_stock": True,
            "brand": "Apple",
            "specifications": {},
        }
    ]


@pytest.mark.parametrize("price", [None, 0])
def test_invalid_price_returns_none(test_products, price):
    data = test_products[0].copy()
    data["price"] = price

    raw = RawExtractedProduct(**data)

    assert to_product(raw, "gadgetbytenepal.com") is None


def test_negative_price_is_rejected_by_raw_model(test_products):
    data = test_products[0].copy()
    data["price"] = -100

    with pytest.raises(ValidationError):
        RawExtractedProduct(**data)
