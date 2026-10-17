
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, ValidationError

#Esko kaam chai Each Website bata Extract bhaeko Data lai Validate garcha
class RawExtractedProduct(BaseModel):
    """Raw product data extracted from an e-commerce website."""
    
    
    # extra="forbid" → Extra field आयो भने reject गर्छ र Validation Error दिन्छ।
    
    # extra="ignore" → Extra field आयो भने त्यसलाई ignore गर्छ र बाँकी valid data स्वीकार गर्छ।

    #Website bata Extract garda Unwanted Fields haru aauna sakcha 
    # so Teslai Ignore garne
    
    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    name: str = Field(
        ...,
        title="Product Name",
        description="Name or title of the extracted product.",
        min_length=1,
    )

    url: HttpUrl = Field(
        ...,
        title="Product URL",
        description="Canonical or source URL of the product page.",
    )

    brand: str | None = Field(
        default=None,
        description="Brand or manufacturer of the product.",
    )

    image: HttpUrl | None = Field(
        default=None,
        description="URL of the main product image.",
    )

    price: float | None = Field(
        default=None,
        ge=0,
        description="Current selling price of the product.",
    )

    regular_price: float | None = Field(
        default=None,
        ge=0,
        description="Original or regular price before discounts.",
    )

    currency: str | None = Field(
        default=None,
        description="ISO 4217 currency code, such as NPR, USD, or INR.",
        min_length=3,
        max_length=3,
    )

    in_stock: bool | None = Field(
        default=None,
        description="Whether the product is currently available for purchase.",
    )

    specifications: dict[str, Any] = Field(
        default_factory=dict,
        description="Product specifications, such as RAM, storage, processor, and display.",
    )

    match_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Normalized product matching confidence score from 0 to 1.",
    )

    source: str | None = Field(
        default=None,
        description="Name of the website or platform from which the product was extracted.",
    )


#Each Website bata Extracted Product lai Same Format ma banaucha
class Product(BaseModel):
    """Multiple Website bata Extracted Data lai Common Format ma rakhnalai"""
    

    #ConfigDict() le chai Product Model ko laagi Rules banauna lai ho
    
    #str_strip_whitespace le chai String ko Agadi or Pachdi ko whitespace lai remove garcha
    
    
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(
        ...,
        min_length=1,
        description="Name of the product.",
    )

    url: HttpUrl = Field(
        ...,
        description="URL of the product page.",
    )

    website: str = Field(
        ...,
        min_length=1,
        description="Domain of the source website, assigned by our backend.",
    )

    price: float = Field(
        ...,
        gt=0,
        description="Current selling price. Must be greater than zero.",
    )

    regular_price: float | None = Field(
        default=None,
        gt=0,
        description="Original price before discount, if available.",
    )

    currency: str = Field(
        default="NPR",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code, such as NPR, USD, or INR.",
    )

    in_stock: bool | None = Field(
        default=None,
        description="Product availability. None means unknown.",
    )

    image: HttpUrl | None = Field(
        default=None,
        description="URL of the product image, if available.",
    )

    brand: str | None = Field(
        default=None,
        description="Product brand or manufacturer.",
    )

    match_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Product matching confidence score from 0 to 1.",
    )

    key_specs: dict[str, str] = Field(
        default_factory=dict,
        description="Selected key specifications for product comparison.",
    )
    
    
#Each Website le Return garne Result ko Format
class EachWebsiteResult(BaseModel):
    """Each Website le Return garne Result Format"""

    model_config = ConfigDict(extra="forbid")

    website: str = Field(
        ...,
        min_length=1,
        description="Domain of the website being extracted.",
    )

    status: Literal["ok", "empty", "error"] = Field(
        ...,
        description="Extraction status: success, no products found, or failure.",
    )

    products: list[Product] = Field(
        default_factory=list,
        description="Products extracted from this website.",
    )
    
    error_message: str | None = Field(
        default=None,
        description="Error details if extraction fails.",
    )
    
    elapsed_seconds: float | None = Field(
    default=None,
    ge=0,
    description="Time taken to fetch results from this website in seconds.",
    )
    
    
    retryable: bool = Field(
    default=False,
    description="Whether this site failure can be retried.",
)


#Extracted Product lai Clean Product Format ma convert garnalai


#Article haru ma Price None or 0 huncha so Tyo Extracted Product lai Ignore garne
def to_product(
    raw: RawExtractedProduct,
    website: str,
) -> Product | None:
    """Convert raw extracted data into a clean Product."""

    # Skip products without a valid selling price.
    if raw.price is None or raw.price <= 0:
        return None
      #return None garda tyo Extracted Product jasko Price None or 0 cha tyo Ignore huncha

    try:
        return Product(
            name=raw.name,
            url=raw.url,
            website=website,
            price=raw.price,
            regular_price=raw.regular_price,
            currency=raw.currency or "NPR",
            in_stock=raw.in_stock,
            image=raw.image,
            brand=raw.brand,
            match_score=raw.match_score,
            # Keep the extractor's useful specifications for later matching.
            key_specs={
                str(key).strip().lower().replace(" ", "_"): str(value).strip()
                for key, value in raw.specifications.items()
                if value is not None and str(value).strip()
            },
        )

    except ValidationError:
        return None


""" 
-> Let say : website बाट यी ३ वटा items extract भए

raw_products = [
    {"name": "MacBook Pro", "price": 250000},
    {"name": "MacBook Review Article", "price": None},
    {"name": "MacBook Air", "price": 180000},
]

Converter function ले process गर्दा:
- MacBook Pro → Product object बन्छ।
- MacBook Review Article → None return हुन्छ।
- MacBook Air → Product object बन्छ।

त्यसैले price नभएको article वा invalid product skip हुन्छ।


IMP : 

return None ले आफैँ product लाई list बाट delete गर्दैन। 
यसले function को result मात्र None बनाउँछ।


"""