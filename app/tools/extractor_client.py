
import logging
import httpx
from pydantic import ValidationError
from urllib.parse import urlparse
import asyncio
import time

#project imports
from app.core.logging_config import setup_logging
from app.core.config import settings
from app.core.retry_config import PER_SITE_TIMEOUT
from app.schemas.product import (
  RawExtractedProduct,
  to_product,
  EachWebsiteResult
)
from app.services.product_validation import validate_product_match

#logger setup
setup_logging()
logger = logging.getLogger(__name__)



#Website URL bata Website pauna
def get_website_name(url : str):
  """URL bata Website ko Domain or Hostname Extract garne"""
  parsed_url = urlparse(url)
  hostname = parsed_url.hostname
  
  if not hostname:
    return ""
  
  website = hostname.lower().removeprefix("www.")
  return website


#Error dekhauda ko Case ma
#Error aauda Same Format ma dekhaunalai
def error_result(
    website: str,
    error_message: str,
    retryable: bool = False,
) -> EachWebsiteResult:
    return EachWebsiteResult(
        website=website,
        status="error",
        products=[],
        error_message=error_message,
        retryable=retryable,
    )



#Product Extractor API bata Data Fetch garne Function

async def fetch_website(
  website_url : str , 
  product_name : str ,
  max_results : int = 5
) -> EachWebsiteResult:
  """Euta Website bata Product Fetch garne"""
  
  website_name = get_website_name(website_url)
  started_at = time.perf_counter()
  
  try:
    
    if not settings.EXTRACTOR_API_URL:
      return error_result(
        website=website_name,
        error_message="EXTRACTOR_API_URL is not configured"
      )
      
    endpoint = f"{settings.EXTRACTOR_API_URL}/extract"
    
    
    async with httpx.AsyncClient(timeout=60) as client:
      response = await client.post(
        url=endpoint,
        json={
          "website_url" : website_url,
          "product_name" : product_name,
          "max_results" : max_results
        }
      )
      
    #handle HTTP Errors
    if response.status_code != 200:
      try:
        payload = response.json()
        #yo payload abo Python Dictionary huncha
        #.json() le chai Response Body JSON ma huda Python Dictionary huncha
        
        detail = payload.get(
          "detail",
          f"HTTP {response.status_code}"
        )
      
      except ValueError:
        #response body JSON ma nahuda response.json() le error dina sakcha
        
         detail = f"HTTP {response.status_code}"
         
      return error_result(
            website=website_name,
            error_message=str(detail),
            retryable=500 <= response.status_code < 600,
        )
    
    # Parse the successful response.
    payload = response.json()
    
    
    #payload esto huncha
          # {
          #   "count": 2,
          #   "products": [
          #     {
          #       "name": "iPhone 15",
          #       "price": 125000
          #     },
          #     {
          #       "name": "iPhone 15 128GB",
          #       "price": 130000
          #     }
          #   ]
          # }
          
    raw_products = payload.get("products", [])
    
    # products List huna parcha
    if not isinstance(raw_products, list):
      return error_result(
          website_name,
          "Invalid extractor response: products must be a list",
      )
      
    count = payload.get("count", len(raw_products))
    
    if count == 0 or not raw_products:
      return EachWebsiteResult(
          website=website_name,
          status="empty",
          products=[],
      )
      
    products = []
    
    for item in raw_products:
      #item dictionary huncha
      try:
          raw = RawExtractedProduct(**item)
          
          is_match, reason = validate_product_match(
              product_name=product_name,
              extracted_name=raw.name,
          )

          if not is_match:
              logger.info(
                  "Skipping product from %s: %s | Reason: %s",
                  website_name,
                  raw.name,
                  reason,
              )
              continue

          product = to_product(raw, website_name)

          if product is not None:
              products.append(product)

      except ValidationError:
          # Skip malformed product data without failing the site.
          logger.warning(
              "Skipping invalid product from %s",
              website_name,
          )

    # Products may all have been filtered out.
    return EachWebsiteResult(
        website=website_name,
        status="ok" if products else "empty",
        products=products,
    )

  except httpx.TimeoutException:
    logger.warning(
          "Extractor timeout site=%s elapsed=%.2f",
          website_name,
          time.perf_counter() - started_at,
    )
    return error_result(
        website_name,
        "timeout",
        retryable=True,
    )

  except httpx.ConnectError:
      logger.warning(
          "Extractor connection failure site=%s elapsed=%.2f",
          website_name,
          time.perf_counter() - started_at,
      )
      return error_result(
          website_name,
          "extractor unreachable",
          retryable=True,
      )

  except Exception:
      logger.exception(
          "Unexpected extractor error for %s",
          website_name,
      )
      return error_result(
          website_name,
          "unexpected extractor error",
          retryable=False,
      )
    
    
async def fetch_many(
    urls: list[str],
    product_name: str,
    max_results: int = 5,
) -> list[EachWebsiteResult]:
    """Fetch products from multiple websites concurrently."""

    # Same time ma maximum 3 ota website fetch garne.
    semaphore = asyncio.Semaphore(3)

    async def limited_fetch(url: str) -> EachWebsiteResult:
        async with semaphore:
            # Website ko actual fetch time measure gara.
            start_time = time.perf_counter()

            result = await fetch_website(
                website_url=url,
                product_name=product_name,
                max_results=max_results,
            )

            # Kunai unexpected condition ma None aaye safe fallback deu.
            if result is None:
                logger.error(
                    "fetch_website returned None for %s",
                    url,
                )
                result = error_result(
                    website=get_website_name(url),
                    error_message="Fetcher returned an empty result",
                )

            # Result ma elapsed time seconds ma rakha.
            result.elapsed_seconds = round(
                time.perf_counter() - start_time,
                2,
            )

            if result.elapsed_seconds >= PER_SITE_TIMEOUT * 0.8:
                logger.warning(
                    "Slow extractor site=%s status=%s elapsed=%.2f",
                    result.website,
                    result.status,
                    result.elapsed_seconds,
                )

            # IMPORTANT: Result return garna nabirsinu.
            return result

    tasks = [
        limited_fetch(url)
        for url in urls
    ]

    # Sabai websites ko result collect gara.
    return await asyncio.gather(*tasks)

