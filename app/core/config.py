import os

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int, minimum: int = 1) -> int:
    """Read an int env var safely. Bad/missing value ma default use garne."""
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


class Settings:
    # Extractor API
    EXTRACTOR_API_URL = os.getenv("EXTRACTOR_API_URL")
    EXTRACTOR_API_KEY = os.getenv("EXTRACTOR_API_KEY") or None
    MAX_CONCURRENT_EXTRACTS = _get_int("MAX_CONCURRENT_EXTRACTS", default=1)

    # model1
    MODEL_NAME_1 = os.getenv("MODEL_NAME_1")
    MODEL_API_KEY_1 = os.getenv("MODEL_API_KEY_1")
    MODEL_PROVIDER_1 = os.getenv("MODEL_PROVIDER_1")

    # model2
    MODEL_NAME_2 = os.getenv("MODEL_NAME_2")
    MODEL_API_KEY_2 = os.getenv("MODEL_API_KEY_2")
    MODEL_PROVIDER_2 = os.getenv("MODEL_PROVIDER_2")

    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")


settings = Settings()