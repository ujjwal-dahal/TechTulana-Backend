
import pytest

from app.core.sites import get_all_sites
from scripts.test_sites import get_test_queries


def test_every_site_has_three_test_queries():
    sites = get_all_sites()

    assert sites

    for site in sites:
        queries = get_test_queries(site)

        assert len(queries) == 3
        assert all(query.strip() for query in queries)
        assert len(set(queries)) == 3


def test_mobile_site_uses_mobile_products():
    site = {
        "key": "test-mobile",
        "categories": ["mobile"],
    }

    queries = get_test_queries(site)

    assert len(queries) == 3
    assert "iPhone 15" in queries
    assert "Samsung Galaxy S24" in queries


def test_accessories_site_uses_accessories():
    site = {
        "key": "test-accessories",
        "categories": ["accessories"],
    }

    queries = get_test_queries(site)

    assert len(queries) == 3
    assert "Logitech mouse" in queries


def test_general_category_has_fallback_products():
    site = {
        "key": "test-general",
        "categories": ["general"],
    }

    queries = get_test_queries(site)

    assert len(queries) == 3
