import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from langgraph.errors import GraphRecursionError

from app.core.retry_config import TOTAL_BUDGET_SECONDS
from app.schemas.api import CompareRequest, CompareResponse
from app.schemas.comparison import ComparisonResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Product Comparison"])


def result_to_response(
    result: dict,
    elapsed_seconds: float,
) -> CompareResponse:
    """Map graph output to a stable frontend response."""

    parsed = result.get("parsed")
    comparison = result.get("comparison")
    sites = result.get("sites", [])
    errors = result.get("errors", [])

    if parsed is not None and not parsed.is_valid_query:
        return CompareResponse(
            status="invalid_query",
            message=parsed.reason or "Please enter a valid product query.",
            elapsed_seconds=elapsed_seconds,
        )

    if parsed is None and errors:
        return CompareResponse(
            status="error",
            message="Kehi galat bhayo. Feri try garnus.",
            elapsed_seconds=elapsed_seconds,
        )

    if not sites:
        return CompareResponse(
            status="unsupported_category",
            message=(
                result.get("message")
                or "Yo product category aile supported chhaina."
            ),
            elapsed_seconds=elapsed_seconds,
        )

    if (
        isinstance(comparison, ComparisonResult)
        and comparison.groups
    ):
        return CompareResponse(
            status="ok",
            message="Product comparison completed.",
            comparison=comparison,
            elapsed_seconds=elapsed_seconds,
        )

    return CompareResponse(
        status="no_results",
        message=(
            result.get("message")
            or "Kunai website ma yo product bhetiyena."
        ),
        elapsed_seconds=elapsed_seconds,
    )


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Compare a product across supported websites",
)
async def compare_products(
    payload: CompareRequest,
    request: Request,
) -> CompareResponse:
    request_id = uuid.uuid4().hex[:8]
    started_at = time.monotonic()

    # Non-blocking admission: slot नभए request तुरुन्त reject गर।
    semaphore: asyncio.Semaphore = request.app.state.compare_semaphore

    if semaphore.locked():
        logger.warning(
            "request_id=%s status=busy",
            request_id,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "status": "busy",
                "message": (
                    "Aile dherai request chha, "
                    "kehi sec pachi feri try garnus."
                ),
            },
        )

    await semaphore.acquire()

    try:
        logger.info(
            "request_id=%s query=%r event=compare_started",
            request_id,
            payload.query,
        )

        initial_state = {
            "user_query": payload.query,
            "attempt": 0,
            "started_at": time.monotonic(),
            "errors": [],
            "retry_messages": [],
        }

        try:
            result = await asyncio.wait_for(
                request.app.state.graph.ainvoke(
                    initial_state,
                    config={"recursion_limit": 15},
                ),
                timeout=TOTAL_BUDGET_SECONDS + 20,
            )

        except asyncio.TimeoutError:
            elapsed = round(time.monotonic() - started_at, 2)

            logger.warning(
                "request_id=%s status=timeout elapsed=%.2f",
                request_id,
                elapsed,
            )

            raise HTTPException(
                status_code=504,
                detail={
                    "status": "timeout",
                    "message": "Dherai time lagyo, feri try garnus.",
                },
            )

        except GraphRecursionError:
            logger.exception(
                "request_id=%s graph recursion limit reached",
                request_id,
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": "Kehi galat bhayo.",
                },
            )

        elapsed = round(time.monotonic() - started_at, 2)
        response = result_to_response(result, elapsed)

        # Log site-level result without exposing internal exceptions.
        for site_result in result.get("site_results", []):
            logger.info(
                "request_id=%s site=%s site_status=%s "
                "elapsed=%.2f",
                request_id,
                site_result.website,
                site_result.status,
                site_result.elapsed_seconds or 0,
            )

        logger.info(
            "request_id=%s status=%s elapsed=%.2f",
            request_id,
            response.status,
            elapsed,
        )

        return response

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "request_id=%s unexpected comparison error",
            request_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Kehi galat bhayo.",
            },
        )

    finally:
        semaphore.release()