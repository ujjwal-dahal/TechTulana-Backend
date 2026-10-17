import logging
from urllib.parse import urlparse

#project imports
from app.core.logging_config import setup_logging
from app.core.config import settings

#tavily
from tavily import TavilyClient


#logging setup
setup_logging()
logger = logging.getLogger(__name__)


#tavily search tool

def search_web(
    product_name: str,
    max_results: int = 10,
) -> list[dict]:
  
    """Product Search garcha Nepal ma and URL , Domain provide garcha"""

    api_key = settings.TAVILY_API_KEY

    if not api_key or not product_name.strip():
        return []

    try:
        #tavily client banako
        client = TavilyClient(api_key=api_key)

        
        response = client.search(
          #strip() le string ko start and end whitespace lai remove garcha
            query=f"{product_name.strip()} price in Nepal",
            max_results=max(1, min(max_results, 20)),
        )

        results = []

        for item in response.get("results", []):
            url = item.get("url", "").strip()

            if not url:
                continue

            parsed = urlparse(url)
            domain = parsed.netloc.lower().removeprefix("www.")

            if not domain:
                continue

            results.append(
                {
                    "domain": domain,
                    "url": url,
                    "title": item.get("title", ""),
                }
            )

        return results

    except Exception:
        logger.exception("Tavily web search failed")
        return []