
#Multiple Websites bata aayeko Price lai Same Numeric Format (Float) ma Convert garna lai

import re


def clean_price(value) -> float | None:
    """Convert a raw price value into a float."""

    # 1. If price is already numeric, convert it to float.
    if isinstance(value, (int, float)):
        return float(value)

    # 2. Handle missing or empty values.
    if value is None:
        return None

    text = str(value).strip()
    #strip() le string ko start and end ko whitespace remove garcha

    #eddi Empty string cha bhane
    if not text:
        return None

    # 3. Remove commas from the text.
    text = text.replace(",", "")

    # 4. Extract all numbers from the text.
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    
    #numbers list ho

    # 5. Return None if no number is found.
    if not numbers:
        return None

    # 6. Return the first number.
    return float(numbers[0])
