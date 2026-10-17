
import re



ACCESSORY_KEYWORDS = {
    "case",
    "cover",
    "protector",
    "screen protector",
    "tempered glass",
    "replacement battery",
    "keyboard cover",
    "sleeve",
    "skin",
    "stand",
    "charger",
    "cable",
    "adapter",
    "compatible with",
    "sidekick",
}


#user le query ma yo words haru halda ignore garne

#example : best price of iphone 15 garda 
#-> best , price ,of haru ignore garne
IGNORED_QUERY_WORDS = {
    "buy",
    "best",
    "price",
    "in",
    "nepal",
    "online",
    "of",
}


def normalize_text(text: str) -> str:
    """Convert text into lowercase, normalized words."""
    # Treat common screen-size spellings as the same words.
    text = text.lower().replace("″", '"').replace("”", '"')
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*(?:-?\s*inch(?:es)?|\"|in)(?=\s|$|[^a-z0-9])",
        r"\1 inch",
        text,
    )
    return " ".join(
      re.findall(r"[a-z0-9]+", text)
      )
    
    #"join" le list ko items haru lai Single String ma Join garcha


def validate_product_match(
    product_name: str,
    extracted_name: str,
):
    """Check whether an extracted title matches the search query."""

    query = normalize_text(product_name)
    title = normalize_text(extracted_name)
    #website bata extract bhako product title

    #eddi User ko Query Empty or Title Empty cha bhane
    if not query or not title:
        return False, "empty product name"

    # Reject likely accessories.
    padded_title = f" {title} "

    for keyword in ACCESSORY_KEYWORDS:
        normalized_keyword = normalize_text(keyword)

        #eddi ACCESSORY_KEYWORDS ma bhaeko Keyword chai "padded_title" ma cha bhane Accessory Detected
        
        
        #meaning : 
        #Let say Extracted Product ko Title : Iphone 15 Case cha 
        
        #abo hamro ACCESSORY_KEYWORDS ma "case" bhanne ni keyword cha
        
        #so padded_title ma cha "case" keyword 
        #so accessory detected
        
        if f" {normalized_keyword} " in padded_title:
            return False, f"accessory detected: {keyword}"

    # Every meaningful query token should appear in the title.
    query_tokens = [
        token
        for token in query.split()
        #split le chai String lai Whitespace ko basis ma List ma split garcha
        if token not in IGNORED_QUERY_WORDS
    ]

    missing_tokens = [
        token
        for token in query_tokens
        if token not in title.split()
    ]

    if missing_tokens:
        return False, f"missing query terms: {missing_tokens}"

    return True, "title matches query"
