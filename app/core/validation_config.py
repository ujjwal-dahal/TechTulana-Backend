
# Category anusar minimum sensible price
PRICE_FLOORS: dict[str, float] = {
    "mobile": 10_000,
    "laptop": 30_000,
    "tv": 10_000,
}

# Accessory chinna use hune complete words
ACCESSORY_KEYWORDS: set[str] = {
    "for",
    "case",
    "cover",
    "protector",
    "guard",
    "dock",
    "docking",
    "stand",
    "charger",
    "cable",
    "strap",
    "holder",
    "adapter",
    "sleeve",
    "skin",
    "tempered",
}

# Query ma nabhaye reject garna milne product variants
VARIANT_WORDS: set[str] = {
    "plus",
    "pro",
    "max",
    "ultra",
    "mini",
    "se",
    "fe",
    "lite",
}

# LLM batch size; Layer 3 ma use garne
LLM_BATCH_SIZE = 30
