
import pytest

from app.services.product_validation import validate_product_match


@pytest.mark.parametrize(
    ("query", "title", "expected"),
    [
        (
            "MacBook Air M3",
            "Apple MacBook Air M3 13-inch",
            True,
        ),
        (
            "MacBook Air M3",
            "MacBook Air M3 Case",
            False,
        ),
        (
            "iPhone 15",
            "Prodigee SideKick For iPhone 15 Series",
            False,
        ),
        (
            "iPhone 15",
            "Buy iPhone 11 12 13 and 14 Online",
            False,
        ),
        (
            "Logitech mouse",
            "Logitech Pop Mouse With Emoji",
            True,
        ),
        (
            "MacBook Pro M5",
            'Apple MacBook Pro M5 14"',
            True,
        ),
    ],
)
def test_validate_product_match(query, title, expected):
    is_match, reason = validate_product_match(query, title)

    assert is_match is expected
