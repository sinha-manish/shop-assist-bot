#!/usr/bin/env python3
"""
Merge Shop Assist Stock + Response Data into Azure CLU Utterance JSON
- Uses both shop_assist_hyderabad.xlsx and test_shop_assist_responses.xlsx
- Generates utterances, extracts entities, maps intents
"""

import pandas as pd
import json
import re

# Input / Output
STOCK_FILE = "data\\documents\\shop_assist_hyderabad.xlsx"
RESPONSES_FILE = "data\\response\\test_shop_assist_responses.xlsx"
OUTPUT_JSON = "shop_assist_clu_full.json"

# Intent mapping (can expand as needed)
intent_map = {
    "search_product": "Search",
    "find_deal": "FindDeal",
    "filter_by_festive": "FestiveFilter",
    "check_availability": "CheckAvailability",
    "find_store_stock": "FindStoreStock",
    "general_query": "GeneralQuery",
}

# ---------------------------
# 1. Load datasets
# ---------------------------
stock_df = pd.read_excel(STOCK_FILE)
resp_df = pd.read_excel(RESPONSES_FILE)

utterances = []
seen_texts = set()

# ---------------------------
# 2. Helpers: entity extraction aligned with ingestion schema
# ---------------------------

# Dataset field -> CLU entity category mapping (aligned with app retrieval)
# Updated to include new fields from scrape_shop_assist_products.py
FIELD_TO_CATEGORY = {
    "Product_Name": "product_name",
    "Product_Category": "product_category",
    "Product_Subcategory": "product_subcategory",
    "Color": "color",
    "Size": "size",
    "Material": "material",
    "Pattern": "pattern",
    "Fit": "fit",  # New field from scraper
    "Store_Name": "store_name",
    "Store_Location": "store_location",
    "Store_Area": "store_area",  # New field from scraper (e.g., "Banjara Hills", "Kukatpally")
    "Store_Type": "store_type",  # New field from scraper (e.g., "Retail Store", "Mall Store")
    "Occasion_Tags": "occasion",
    "Seasonal_Availability": "seasonal_availability",
    "Availability": "availability",
    "Stock_Status": "stock_status",
    "Price_Range": "price_range",
    "Discount_Percent": "discount",  # New field from scraper (for deal queries)
}

def _find_case_insensitive(text: str, value: str):
    try:
        pattern = re.escape(value)
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.start(), m.end()
    except Exception:
        pass
    return -1, -1

def extract_entities(text: str, field_values: dict):
    """
    Build CLU entities by locating dataset values inside the utterance text.
    - Avoid overlapping spans
    - Case-insensitive matching
    - Also detects gender keywords (men/women/boys/girls) and maps to product_category
    """
    entities = []
    used_spans = []  # list of (start, end)
    
    # First, extract gender keywords and map to product_category
    gender_map = {
        "men": "Men's Clothing",
        "man": "Men's Clothing",
        "male": "Men's Clothing",
        "women": "Women's Clothing",
        "woman": "Women's Clothing",
        "female": "Women's Clothing",
        "boys": "Kids & Teens",
        "boy": "Kids & Teens",
        "girls": "Kids & Teens",
        "girl": "Kids & Teens"
    }
    
    text_lower = text.lower()
    for gender_keyword, category_value in gender_map.items():
        if gender_keyword in text_lower:
            # Find the position of the gender keyword
            start = text_lower.find(gender_keyword)
            if start != -1:
                end = start + len(gender_keyword)
                span = (start, end)
                # Check for overlap
                if not any(not (end <= s or start >= e) for s, e in used_spans):
                    # Check if the category matches
                    product_category = field_values.get("Product_Category", "")
                    if category_value in product_category:
                        entities.append({
                            "category": "product_category",
                            "offset": start,
                            "length": end - start
                        })
                        used_spans.append(span)
    
    # Then extract other entities
    for field, category in FIELD_TO_CATEGORY.items():
        val = field_values.get(field)
        if not isinstance(val, str) or not val.strip():
            continue
        start, end = _find_case_insensitive(text, val.strip())
        if start == -1:
            continue
        span = (start, end)
        # prevent overlap
        if any(not (end <= s or start >= e) for s, e in used_spans):
            continue
        entities.append({
            "category": category,
            "offset": start,
            "length": end - start
        })
        used_spans.append(span)
    return entities

# ---------------------------
# 3. Add utterances from response file
# ---------------------------
for _, row in resp_df.iterrows():
    text = str(row.get("Questions", "")).strip()
    if not text or text.lower() in seen_texts:
        continue
    seen_texts.add(text.lower())

    entities = extract_entities(text, {
        "Size": None,  # Could refine further if size info is extracted
        "StoreName": None
    })

    utterances.append({
        "intent": "CheckAvailability",  # default intent for response queries
        "language": "en-us",
        "text": text,
        "entities": entities
    })

# ---------------------------
# 4. Generate synthetic utterances from stock data
# ---------------------------
for _, row in stock_df.iterrows():
    row_vals = {k: (str(row.get(k)).strip() if pd.notna(row.get(k)) else "") for k in FIELD_TO_CATEGORY.keys()}
    product = row_vals.get("Product_Category", "")
    subcat = row_vals.get("Product_Subcategory", "")
    color = row_vals.get("Color", "")
    size = row_vals.get("Size", "")
    store_loc = row_vals.get("Store_Location", "")
    store_name = row_vals.get("Store_Name", "")
    store_area = row_vals.get("Store_Area", "")  # New field
    store_type = row_vals.get("Store_Type", "")  # New field
    material = row_vals.get("Material", "")
    pattern = row_vals.get("Pattern", "")
    fit = row_vals.get("Fit", "")  # New field
    occasion = row_vals.get("Occasion_Tags", "")
    season = row_vals.get("Seasonal_Availability", "")
    discount = row_vals.get("Discount_Percent", "")  # New field

    if not product and not subcat:
        continue

    # Extract gender from category for better query generation
    gender_keyword = ""
    if "Men" in product or "Men's" in product:
        gender_keyword = "men"
    elif "Women" in product or "Women's" in product:
        gender_keyword = "women"
    elif "Boys" in product or "Boys'" in product:
        gender_keyword = "boys"
    elif "Girls" in product or "Girls'" in product:
        gender_keyword = "girls"
    
    # Diverse, information-rich utterances to embed multiple entity values
    # Include gender keywords explicitly for better CLU recognition
    sample_queries = []
    
    if gender_keyword:
        # Queries with explicit gender keywords
        sample_queries.extend([
            f"Do you have {color} {subcat or product} for {gender_keyword} in size {size} at {store_loc}?",
            f"Show me {color} {subcat or product} for {gender_keyword} available at {store_name or store_loc}",
            f"Find {color} {subcat or product} for {gender_keyword} in {store_loc}",
            f"Looking for {color} {subcat or product} for {gender_keyword} ({size}) in {store_name or store_loc}",
            f"I need {color} {subcat or product} for {gender_keyword}",
            f"Any {color} {subcat or product} for {gender_keyword}?",
        ])
        
        # Queries with fit (if available)
        if fit:
            sample_queries.extend([
                f"Do you have {fit} fit {color} {subcat or product} for {gender_keyword}?",
                f"Show me {fit} fit {subcat or product} for {gender_keyword} in {store_area or store_loc}",
            ])
        
        # Queries with store area (if available)
        if store_area:
            sample_queries.extend([
                f"Where can I find {color} {subcat or product} for {gender_keyword} in {store_area}?",
                f"Any {subcat or product} for {gender_keyword} at {store_area} store?",
            ])
    
    # Generic queries (without gender, but category will be extracted)
    sample_queries.extend([
        f"Do you have {color} {subcat or product} in size {size} at {store_loc}?",
        f"Show me {material} {color} {subcat or product} with {pattern} pattern available at {store_name or store_loc}",
        f"Find {subcat or product} for {occasion} available during {season} in {store_loc}",
        f"Which store in {store_loc} has size {size} {subcat or product}?",
        f"Looking for {color} {subcat or product} ({size}) in {store_name or store_loc}",
    ])
    
    # Queries with fit (if available)
    if fit:
        sample_queries.extend([
            f"Do you have {fit} fit {color} {subcat or product}?",
            f"Show me {fit} fit {subcat or product} in {store_area or store_loc}",
        ])
    
    # Queries with store area (if available)
    if store_area:
        sample_queries.extend([
            f"Where can I find {color} {subcat or product} in {store_area}?",
            f"Any {subcat or product} at {store_area} store?",
            f"Which store in {store_area} has {subcat or product}?",
        ])
    
    # Queries with discount (if available and > 0)
    if discount and str(discount).strip() and str(discount) != "0" and str(discount) != "0.0":
        try:
            disc_val = float(discount)
            if disc_val > 0:
                sample_queries.extend([
                    f"Show me {subcat or product} with {discount}% discount",
                    f"Find {color} {subcat or product} on sale",
                    f"Any deals on {subcat or product}?",
                ])
        except (ValueError, TypeError):
            pass

    for text in sample_queries:
        norm = text.strip().lower()
        if not norm or norm in seen_texts:
            continue
        seen_texts.add(norm)

        entities = extract_entities(text, row_vals)
        utterances.append({
            "intent": "Search",
            "language": "en-us",
            "text": text,
            "entities": entities
        })

# ---------------------------
# 5. Save to JSON
# ---------------------------
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(utterances, f, ensure_ascii=False, indent=4)

print(f"✅ Exported {len(utterances)} unique utterances to {OUTPUT_JSON}")
print(f"👉 Intents used: {[u['intent'] for u in utterances[:10]]} ...")

# ---------------------------
# 6. (Optional) Export CLU schema stubs for entities and intents
#    These JSONs can help bootstrap CLU project configuration
# ---------------------------

def export_clu_schema(stock_df: pd.DataFrame):
    # Build phrase lists from stock for each FIELD_TO_CATEGORY
    entities_schema = []
    for field, category in FIELD_TO_CATEGORY.items():
        if field not in stock_df.columns:
            continue
        # Collect unique non-empty strings
        values = (
            stock_df[field]
            .dropna()
            .astype(str)
            .str.strip()
            .replace("nan", "")
            .replace("None", "")
        )
        unique_vals = sorted({v for v in values.tolist() if v})
        # Limit list size to keep file manageable
        if len(unique_vals) > 5000:
            unique_vals = unique_vals[:5000]
        entities_schema.append({
            "category": category,
            "type": "list",
            "values": unique_vals
        })

    intents_schema = [
        {"name": "Search"},
        {"name": "CheckAvailability"},
        {"name": "FindDeal"},
        {"name": "FindStoreStock"},
        {"name": "FestiveFilter"},
        {"name": "TrendingItems"},
        {"name": "NewArrivals"},
        {"name": "Bestsellers"},
        {"name": "PriceInquiry"},
        {"name": "StoreInfo"},
        {"name": "CompareProducts"},
        {"name": "GeneralQuery"},
    ]

    with open("clu_entities_schema.json", "w", encoding="utf-8") as f:
        json.dump({"entities": entities_schema}, f, ensure_ascii=False, indent=2)
    with open("clu_intents_schema.json", "w", encoding="utf-8") as f:
        json.dump({"intents": intents_schema}, f, ensure_ascii=False, indent=2)

    print("✅ Exported CLU schema stubs: clu_entities_schema.json, clu_intents_schema.json")

# Export schema stubs
export_clu_schema(stock_df)
