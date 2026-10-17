from app.schemas.product import Product, RawExtractedProduct, to_product
from app.schemas.product_validator import ValidatedProduct
from app.services.comparison_service import build_comparison
from app.services.llm_product_validator import build_variant_key
from app.schemas.llm_response import ParsedQuery


def parsed_query() -> ParsedQuery:
    return ParsedQuery(
        product_name="MacBook Pro M5",
        brand="Apple",
        category="laptop",
        is_valid_query=True,
        reason="",
    )


def product(name: str, site: str, price: float, stock: bool | None = True):
    return Product(
        name=name,
        url=f"https://{site}/{price}",
        website=site,
        price=price,
        in_stock=stock,
        currency="NPR",
    )


def validated(
    name: str,
    site: str,
    price: float,
    screen_size: str | None,
    ram: str | None = None,
    storage: str | None = None,
    stock: bool | None = True,
    identity_key: str = "macbook pro m5",
) -> ValidatedProduct:
    return ValidatedProduct(
        product=product(name, site, price, stock),
        verified=True,
        identity_key=identity_key,
        variant_key=build_variant_key(ram, storage, screen_size),
        ram=ram,
        storage=storage,
        screen_size=screen_size,
    )


def test_screen_size_formats_normalize_to_one_value():
    assert build_variant_key(None, None, "14-inch") == "?|?|14in"
    assert build_variant_key(None, None, "14 inch") == "?|?|14in"
    assert build_variant_key(None, None, '14"') == "?|?|14in"


def test_extracted_specs_are_preserved_without_inventing_missing_values():
    raw = RawExtractedProduct(
        name="Apple MacBook Pro M5 14-inch",
        url="https://example.com/macbook",
        price=376500,
        specifications={"screen size": '14"', "chip": "M5"},
    )

    converted = to_product(raw, "example.com")

    assert converted is not None
    assert converted.key_specs["screen_size"] == '14"'
    assert "ram" not in converted.key_specs
    assert "storage" not in converted.key_specs


def test_missing_screen_size_can_join_but_is_not_reliable_comparison():
    result = build_comparison(
        parsed_query(),
        [
            validated(
                "Apple MacBook Pro M5 14-inch",
                "bigbyte.com",
                464800,
                "14-inch",
            ),
            validated(
                'Apple MacBook Pro M5 14"',
                "oliz.com",
                376500,
                None,
            ),
        ],
        [],
    )

    assert len(result.groups) == 1
    assert len(result.groups[0].offers) == 2
    assert result.groups[0].is_comparable is False


def test_confirmed_ram_or_storage_conflicts_stay_separate():
    result = build_comparison(
        parsed_query(),
        [
            validated("MacBook Pro M5 8GB", "a.com", 400000, "14in", ram="8GB"),
            validated("MacBook Pro M5 16GB", "b.com", 450000, "14in", ram="16GB"),
        ],
        [],
    )

    assert len(result.groups) == 2


def test_out_of_stock_offers_never_become_best():
    result = build_comparison(
        parsed_query(),
        [
            validated("MacBook Pro M5", "a.com", 300000, "14in", stock=False),
            validated("MacBook Pro M5", "b.com", 350000, "14in", stock=False),
        ],
        [],
    )

    group = result.groups[0]
    assert group.best_offer is None
    assert group.price_min is None
    assert group.price_max is None
