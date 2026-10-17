import time

from app.core.retry_config import MAX_RETRIES
from app.graph.nodes import route_after_extract
from app.schemas.product import EachWebsiteResult


def test_retry_policy_allows_only_one_retry():
    state = {
        "attempt": 0,
        "started_at": time.monotonic(),
        "site_results": [
            EachWebsiteResult(
                website="daraz.com.np",
                status="error",
                retryable=True,
            )
        ],
    }

    assert route_after_extract(state) == "retry_extract"
    state["attempt"] = MAX_RETRIES
    assert route_after_extract(state) == "validate"


def test_empty_results_are_not_retryable():
    state = {
        "attempt": 0,
        "started_at": time.monotonic(),
        "site_results": [
            EachWebsiteResult(
                website="daraz.com.np",
                status="empty",
                retryable=False,
            )
        ],
    }

    assert route_after_extract(state) == "validate"
