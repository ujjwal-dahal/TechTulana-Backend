
import json

from app.schemas.llm_response import ParsedQuery
from app.schemas.product import Product, EachWebsiteResult
from app.schemas.product_validator import ValidatedProduct
from app.services.comparison_service import build_comparison


def make_item(
    site: str,
    price: float,
    variant_key: str = "8GB|512GB|13in",
    stock: bool | None = True,
    verified: bool = True,
) -> ValidatedProduct:
    product = Product(
    name=f"Laptop {variant_key.replace('|', ' ')}",
    url=f"https://{site}/product-{price}",
    website=site,
    price=price,
    currency="NPR",
    in_stock=stock,
    )
    return ValidatedProduct(
        product=product,
        verified=verified,
        variant_key=variant_key,
        ram=None if "?" in variant_key.split("|")[0] else "8GB",
        storage=None if "?" in variant_key.split("|")[1] else "512GB",
        screen_size=None if "?" in variant_key.split("|")[2] else "13in",
    )


def make_parsed() -> ParsedQuery:
    return ParsedQuery(
        product_name="Laptop",
        brand="Apple",
        category="laptop",
        is_valid_query=True,
        reason="",
    )


def make_site(
    name: str,
    status: str = "ok",
    products: list[Product] | None = None,
) -> EachWebsiteResult:
    return EachWebsiteResult(
        website=name,
        status=status,
        products=products or [],
    )


def compare(
    products: list[ValidatedProduct],
    sites: list[EachWebsiteResult] | None = None,
):
    return build_comparison(
        parsed=make_parsed(),
        valid_products=products,
        site_results=sites or [],
    )


def test_two_sites_same_variant():
    result = compare([
        make_item("site-a.com", 100000),
        make_item("site-b.com", 90000),
    ])

    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.is_comparable is True
    assert group.best_offer is not None
    assert group.best_offer.site_key == "site-b.com"
    assert group.best_offer.price == 90000


def test_different_variants_are_not_comparable():
    result = compare([
        make_item("site-a.com", 100000, "8GB|512GB|13in"),
        make_item("site-b.com", 90000, "16GB|512GB|15in"),
    ])

    assert len(result.groups) == 2
    assert all(not group.is_comparable for group in result.groups)


def test_same_site_keeps_only_cheapest_offer():
    result = compare([
        make_item("site-a.com", 100000),
        make_item("site-a.com", 90000),
        make_item("site-b.com", 95000),
    ])

    group = result.groups[0]
    site_a_offers = [
        offer for offer in group.offers
        if offer.site_key == "site-a.com"
    ]

    assert len(site_a_offers) == 1
    assert site_a_offers[0].price == 90000


def test_out_of_stock_cheapest_offer_is_not_best():
    result = compare([
        make_item("site-a.com", 80000, stock=False),
        make_item("site-b.com", 100000, stock=True),
    ])

    group = result.groups[0]
    assert group.best_offer is not None
    assert group.best_offer.site_key == "site-b.com"
    assert group.price_min == 100000
    assert group.price_max == 100000
    assert group.spread_amount == 0


def test_all_offers_out_of_stock():
    result = compare([
        make_item("site-a.com", 90000, stock=False),
        make_item("site-b.com", 100000, stock=False),
    ])

    group = result.groups[0]
    assert group.best_offer is None
    assert group.price_min is None
    assert any("out of stock" in warning for warning in result.warnings)


def test_low_price_outlier_is_flagged():
    result = compare([
        make_item("site-a.com", 100000),
        make_item("site-b.com", 110000),
        make_item("site-c.com", 20000),
    ])

    group = result.groups[0]
    outlier = next(
        offer for offer in group.offers
        if offer.site_key == "site-c.com"
    )

    assert "price_outlier" in outlier.flags
    assert len(group.offers) == 3


def test_unknown_variant_is_not_comparable():
    result = compare([
        make_item("site-a.com", 90000, "?|512GB|?"),
        make_item("site-b.com", 95000, "?|512GB|?"),
    ])

    group = result.groups[0]
    assert group.label == "Unspecified variant"
    assert group.is_comparable is False
    assert any("Spec thaha nabhayeko" in w for w in result.warnings)


def test_empty_products_do_not_crash():
    result = compare(
        [],
        sites=[
            make_site("site-a.com", status="empty"),
            make_site("site-b.com", status="error"),
            make_site("site-c.com", status="ok"),
        ],
    )

    assert result.groups == []
    assert len(result.site_status) == 3
    assert result.site_status[0].message == "Product not found"
    assert result.site_status[1].message == "Site did not respond"
    assert (
        result.site_status[2].message
        == "Only accessories/other models found"
    )


def test_comparison_result_is_json_serializable():
    result = compare([
        make_item("site-a.com", 100000),
        make_item("daraz.com.np", 90000, verified=False),
    ])

    payload = result.model_dump(mode="json")
    encoded = json.dumps(payload)

    assert '"query": "Laptop"' in encoded
    assert payload["groups"][0]["best_offer"]["price"] == 90000
    assert payload["groups"][0]["best_offer"]["source_type"] == "marketplace"
