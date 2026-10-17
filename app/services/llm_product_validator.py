import logging
import re

from langchain.chat_models import init_chat_model

from app.core.config import settings
from app.core.validation_config import LLM_BATCH_SIZE
from app.schemas.product import Product
from app.schemas.product_validator import (
    BatchVerdict,
    ProductVerdict,
    ValidatedProduct,
)

logger = logging.getLogger(__name__)


def build_variant_key(
    ram: str | None,
    storage: str | None,
    screen_size: str | None,
) -> str:
    """Build a key from known product specifications."""
    return "|".join([
        normalize_spec(ram, "ram") or "?",
        normalize_spec(storage, "storage") or "?",
        normalize_spec(screen_size, "screen_size") or "?",
    ])


def normalize_spec(value: str | None, spec_name: str) -> str | None:
    """Use one spelling for equivalent values such as 14-inch and 14"."""
    if not value:
        return None

    text = " ".join(str(value).strip().lower().split())
    text = text.replace("″", '"').replace("”", '"')

    if spec_name == "screen_size":
        match = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*(?:-?\s*inch(?:es)?|\"|in)",
            text,
        )
        if match:
            return f"{match.group(1)}in"

    if spec_name in {"ram", "storage"}:
        text = re.sub(r"\s*(gb|tb)\b", lambda match: match.group(1).upper(), text)
        text = re.sub(r"\s+", "", text)

    return text


def get_product_specs(
    product: Product,
) -> dict[str, str | None]:
    """Read relevant specs without sending the entire raw data."""

    specs = product.key_specs or {}

    return {
        "ram": specs.get("ram") or specs.get("RAM"),
        "storage": specs.get("storage") or specs.get("Storage"),
        "screen_size": (
            specs.get("screen_size")
            or specs.get("screen size")
            or specs.get("display")
        ),
        "chip": (
            specs.get("chip")
            or specs.get("processor")
            or specs.get("cpu")
        ),
    }


def build_identity_key(product_name: str, product: Product, chip: str | None) -> str:
    """Use the requested model as the shared identity, plus known chip data."""
    identity = " ".join(re.findall(r"[a-z0-9]+", product_name.lower()))
    normalized_chip = normalize_spec(chip, "chip")
    return f"{identity}|chip={normalized_chip}" if normalized_chip else identity


def create_llm():
    """Create the configured structured-output model."""

    if not settings.MODEL_NAME_1:
        raise ValueError("MODEL_NAME_1 is missing")

    if not settings.MODEL_API_KEY_1:
        raise ValueError("MODEL_API_KEY_1 is missing")

    model = init_chat_model(
        model=settings.MODEL_NAME_1,
        model_provider=settings.MODEL_PROVIDER_1,
        api_key=settings.MODEL_API_KEY_1,
        temperature=0,
    )

    return model.with_structured_output(BatchVerdict)


def _validate_one_batch(
    llm,
    product_name: str,
    products: list[tuple[int, Product]],
) -> list[ProductVerdict]:
    """Validate one batch of products."""

    payload = []

    for product_id, product in products:
        payload.append({
            "id": product_id,
            "name": product.name,
            "price": product.price,
            "brand": product.brand,
            "key_specs": get_product_specs(product),
        })

    prompt = f"""
You are a strict product identity validator for an e-commerce
price comparison application.

Requested product: {product_name}

For each supplied product:
- Accept only the same product model and generation.
- Reject accessories, cases, chargers, docks and replacement parts.
- Reject a different model or generation.
- Do not reject solely because RAM or storage differs.
- Never invent missing specifications.
- Extract RAM, storage and screen size only when supported
  by the supplied name or key specifications.
- Extract the processor chip only when supported by the supplied name
  or key specifications.
- Return one verdict per supplied ID.

Products:
{payload}
"""

    response = llm.invoke(prompt)
    return response.verdicts


def validate_products_with_llm(
    product_name: str,
    products: list[Product],
) -> tuple[list[ValidatedProduct], list[dict]]:
    """
    Validate products in batches.

    LLM failures do not discard products that passed code rules.
    Missing verdicts remain unverified.
    """

    if not products:
        return [], []

    validated: list[ValidatedProduct] = []
    rejected: list[dict] = []

    try:
        llm = create_llm()
    except Exception:
        logger.exception("Could not initialize the product validation LLM")
        return [
            ValidatedProduct(
                product=product,
                verified=False,
                variant_key=build_variant_key(
                    get_product_specs(product)["ram"],
                    get_product_specs(product)["storage"],
                    get_product_specs(product)["screen_size"],
                ),
                identity_key=build_identity_key(
                    product_name,
                    product,
                    get_product_specs(product)["chip"],
                ),
                **get_product_specs(product),
            )
            for product in products
        ], []

    indexed_products = list(enumerate(products))

    for start in range(0, len(indexed_products), LLM_BATCH_SIZE):
        batch = indexed_products[start:start + LLM_BATCH_SIZE]
        expected_ids = {product_id for product_id, _ in batch}

        try:
            verdicts = _validate_one_batch(
                llm=llm,
                product_name=product_name,
                products=batch,
            )

            verdict_by_id = {
                verdict.id: verdict
                for verdict in verdicts
                if verdict.id in expected_ids
            }

        except Exception:
            logger.exception("LLM product validation batch failed")
            verdict_by_id = {}

        for product_id, product in batch:
            verdict = verdict_by_id.get(product_id)

            if verdict is not None and not verdict.is_match:
                rejected.append({
                    "site": product.website,
                    "name": product.name,
                    "price": product.price,
                    "reason_code": "llm_not_match",
                })
                continue

            original_specs = get_product_specs(product)

            ram = (
                verdict.ram if verdict and verdict.ram
                else original_specs["ram"]
            )
            storage = (
                verdict.storage if verdict and verdict.storage
                else original_specs["storage"]
            )
            screen_size = (
                verdict.screen_size if verdict and verdict.screen_size
                else original_specs["screen_size"]
            )
            chip = (
                verdict.chip if verdict and verdict.chip
                else original_specs["chip"]
            )

            validated.append(
                ValidatedProduct(
                    product=product,
                    verified=verdict is not None,
                    variant_key=build_variant_key(
                        ram,
                        storage,
                        screen_size,
                    ),
                    ram=ram,
                    storage=storage,
                    screen_size=screen_size,
                    chip=chip,
                    identity_key=build_identity_key(
                        product_name,
                        product,
                        chip,
                    ),
                    # Identity and specification verification are separate.
                    specs_verified=verdict is not None and all(
                        value is not None
                        for value in (ram, storage, screen_size)
                    ),
                )
            )

    return validated, rejected