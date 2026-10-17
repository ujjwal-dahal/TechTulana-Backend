
from copy import deepcopy
from typing import Any


CATEGORIES = {
    "mobile",
    "laptop",
    "tv",
    "appliance",
    "accessories",
    "fashion",
    "general",
    "other",
}


SITES = [
    {
        "key": "gadgetbyte",
        "name": "GadgetByte Nepal",
        "url": "https://www.gadgetbytenepal.com/",
        "tier": 1,
        "source_type": "editorial",
        "categories": ["mobile", "laptop", "accessories"],
        "enabled": True,
        "disabled_reason": (
            "Editorial/review site, not a retailer. "
            "Keep separate from retailer price comparison."
        ),
        "last_tested": "2026-10-17",
    },
    {
        "key": "evostore",
        "name": "EvoStore",
        "url": "https://evostore.com.np/",
        "tier": 1,
        "source_type": "retailer",
        "categories": ["mobile", "laptop", "accessories"],
        "enabled": False,
        "disabled_reason": (
            "0/3 successful extraction results in the latest integration test. "
            "Investigate extraction support before enabling."
        ),
        "last_tested": "2026-10-17",
    },
    # {
    #     "key": "oliz",
    #     "name": "Oliz Store",
    #     "url": "https://www.olizstore.com/",
    #     "tier": 1,
    #     "source_type": "retailer",
    #     "categories": ["mobile", "laptop", "accessories"],
    #     "enabled": True,
    #     "disabled_reason": None,
    #     "last_tested": "2026-10-17",
    # },
    # {
    #     "key": "bigbyte",
    #     "name": "Bigbyte IT World",
    #     "url": "https://bigbyte.com.np/",
    #     "tier": 1,
    #     "source_type": "retailer",
    #     "categories": ["laptop", "accessories", "tv"],
    #     "enabled": True,
    #     "disabled_reason": None,
    #     "last_tested": "2026-10-17",
    # },
    {
        "key": "hukut",
        "name": "Hukut",
        "url": "https://www.hukut.com/",
        "tier": 1,
        "source_type": "retailer",
        "categories": ["mobile", "laptop", "accessories", "tv"],
        "enabled": False,
        "disabled_reason": (
            "0/3 successful extraction results in the latest integration test. "
            "Investigate extraction support before enabling."
        ),
        "last_tested": "2026-10-17",
    },
    {
        "key": "itti",
        "name": "ITTI",
        "url": "https://itti.com.np/",
        "tier": 1,
        "source_type": "retailer",
        "categories": ["laptop", "accessories"],
        "enabled": False,
        "disabled_reason": (
            "No reliable results in the latest integration test; "
            "requests returned empty results or timed out."
        ),
        "last_tested": "2026-10-17",
    },
    # {
    #     "key": "daraz",
    #     "name": "Daraz Nepal",
    #     "url": "https://www.daraz.com.np/",
    #     "tier": 2,
    #     "source_type": "marketplace",
    #     "categories": [
    #         "mobile",
    #         "laptop",
    #         "tv",
    #         "appliance",
    #         "accessories",
    #         "fashion",
    #         "general",
    #     ],
    #     "enabled": True,
    #     "disabled_reason": None,
    #     "last_tested": "2026-10-17",
    # },
    {
        "key": "sastodeal",
        "name": "Sastodeal",
        "url": "https://www.sastodeal.com/",
        "tier": 2,
        "source_type": "marketplace",
        "categories": [
            "mobile",
            "laptop",
            "tv",
            "appliance",
            "accessories",
            "fashion",
            "general",
        ],
        "enabled": False,
        "disabled_reason": (
            "All tested requests timed out at approximately 60 seconds. "
            "Investigate connectivity and extraction support before enabling."
        ),
        "last_tested": "2026-10-17",
    },
]


def get_all_sites() -> list[dict[str, Any]]:
    """Return all registered websites."""
    # deepcopy le original SITES data lai accidental modification bata bachauchha.
    return deepcopy(SITES)


def get_sites_by_category(
    category: str,
) -> list[dict[str, Any]]:
    """Return enabled retailer/marketplace websites supporting the category."""

    # strip() le string ko agadi ra pachhadiko whitespace remove garchha.
    normalized_category = category.strip().lower()

    # CATEGORIES set ma chaina bhane unsupported category ho.
    if normalized_category not in CATEGORIES:
        raise ValueError(
            f"Unsupported category: {category}"
        )

    # "other" ko lagi specific product category match garna sakidaina.
    if normalized_category == "other":
        return []

    # Enabled retailer ra marketplace matra select gara.
    # Editorial sites lai price comparison bata exclude gara.
    # "general" category bhayeko marketplace lai sabai supported category ko candidate manna sakincha.
    return [
        deepcopy(site)
        for site in SITES
        if site.get("enabled", False)
        and site.get("source_type") in {"retailer", "marketplace"}
        and (
            normalized_category in site.get("categories", [])
            or "general" in site.get("categories", [])
        )
    ]


def get_site(key: str) -> dict[str, Any] | None:
    """Return website details using its unique key."""

    # key bhaneko each website ko unique identifier ho, jastai 'oliz' wa 'daraz'.
    normalized_key = key.strip().lower()

    # Registered sites madhye matching key khoja.
    for site in SITES:
        if normalized_key == site["key"]:
            return deepcopy(site)

    # Key bhetiyena bhane None return gara.
    return None
