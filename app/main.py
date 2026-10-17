import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import router
from app.core.config import settings
from app.graph.builder import build_graph

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
INDEX_HTML = TEMPLATE_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources once at startup."""

    # Compile the graph once per application process.
    app.state.graph = build_graph()

    max_concurrent = int(
        os.getenv("MAX_CONCURRENT_COMPARES", "2")
    )

    if max_concurrent < 1:
        raise ValueError("MAX_CONCURRENT_COMPARES must be >= 1")

    app.state.compare_semaphore = asyncio.Semaphore(
        max_concurrent
    )

    logger.info("Product comparison API started")

    yield

    logger.info("Product comparison API stopped")


app = FastAPI(
    title="TechTulana API",
    description=(
        "TechTulana Nepal API for comparing product prices "
        "across supported websites."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Frontend origins allowed to access the API.
default_origins = (
    "http://localhost:3000,"
    "http://127.0.0.1:3000,"
    "http://localhost:3001,"
    "http://127.0.0.1:3001",
    "https://tech-tulana.vercel.app/"
)

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        default_origins,
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register existing API routes.
app.include_router(router)


@app.get("/", include_in_schema=False)
async def home():
    """Serve the TechTulana backend landing page."""

    if not INDEX_HTML.is_file():
        logger.error("Landing page not found: %s", INDEX_HTML)
        return {
            "status": "error",
            "message": "Landing page HTML file was not found.",
        }

    return FileResponse(
        path=INDEX_HTML,
        media_type="text/html",
    )


@app.get("/health", tags=["Health"])
async def health():
    """Return the backend health and extractor configuration."""

    extractor_configured = bool(
        getattr(settings, "EXTRACTOR_API_URL", None)
    )

    return {
        "status": "ok",
        "extractor_configured": extractor_configured,
    }
