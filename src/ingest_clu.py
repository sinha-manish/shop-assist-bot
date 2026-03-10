"""
Shop Assist CLU Optimized Ingestion Script
------------------------------------------
Enhanced version for better retrieval and question answering with comprehensive data coverage.

Key Improvements:
1. Better text generation for CLU processing
2. Enhanced metadata structure for comprehensive retrieval
3. Semantic field combinations for better question answering
4. Optimized field prioritization based on query patterns
5. Better handling of complex data relationships
"""

import os
import pandas as pd
import requests
import logging
import asyncio
import aiohttp
import warnings
from pathlib import Path
from chromadb import PersistentClient
from chromadb.config import Settings
from config import Config
import json
from datetime import datetime
from numbers import Number

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb").setLevel(logging.WARNING)

# Monkey-patch ChromaDB telemetry
try:
    import chromadb.telemetry.events as telemetry_events
    if hasattr(telemetry_events, 'capture'):
        original_capture = telemetry_events.capture
        def patched_capture(*args, **kwargs):
            try:
                return original_capture(*args, **kwargs)
            except:
                pass
        telemetry_events.capture = patched_capture
except:
    pass

# Image generation removed - using local image paths only
IMAGE_UTILS_AVAILABLE = False

# Read settings from config.yaml
config = Config()
CLU_ENDPOINT = config.get("CLU_ENDPOINT")
CLU_KEY = config.get("CLU_KEY")
CLU_PROJECT_NAME = config.get("CLU_PROJECT_NAME")
CLU_DEPLOYMENT_NAME = config.get("CLU_DEPLOYMENT_NAME")
DATA_DIR = Path(config.get("DATA_DIR", "data/documents"))
CHROMA_DB_PATH = config.get("CHROMA_DB_PATH", "chroma_db")
COLLECTION_NAME = config.get("COLLECTION_NAME", "shop_assist_retail_data_clu")
BATCH_SIZE = config.get("BATCH_SIZE", 10)

HEADERS = {
    "Ocp-Apim-Subscription-Key": CLU_KEY,
    "Content-Type": "application/json"
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Field prioritization for different types of queries
FIELD_PRIORITIES = {
    "product_search": [
        "Product_Name", "Product_Category", "Product_Subcategory", 
        "Material", "Color", "Pattern", "Size", "Style_Preference"
    ],
    "availability": [
        "Availability", "Stock_Status", "Stock_Quantity", "Store_Name", 
        "Store_Location", "Store_Area", "Store_Type"
    ],
    "pricing": [
        "Base_Price", "Discounted_Price", "Discount_Percent", 
        "Price_Range", "Profit_Margin"
    ],
    "trending": [
        "Trending_Score", "Popularity_Score", "Customer_Rating", 
        "Review_Count", "Purchase_Count", "View_Count"
    ],
    "seasonal": [
        "Seasonal_Availability", "Festive_Season", "Occasion_Tags",
        "Target_Audience", "Product_Features"
    ],
    "store_info": [
        "Store_Name", "Store_Location", "Store_Area", "Store_Type",
        "Store_Rating", "Store_Footfall"
    ]
}

def generate_optimized_text(row_data, query_type="general"):
    """
    Generate optimized text for CLU processing based on query type.
    Creates multiple text variations for better retrieval coverage.
    """
    texts = []
    
    # Primary text - comprehensive product information
    primary_fields = FIELD_PRIORITIES.get(query_type, FIELD_PRIORITIES["product_search"])
    primary_text = []
    
    # Add Product_Description first if available (most important from scraped data)
    if "Product_Description" in row_data and pd.notna(row_data["Product_Description"]):
        desc = str(row_data["Product_Description"]).strip()
        if len(desc) > 10:
            primary_text.append(f"Description: {desc}")
    
    for field in primary_fields:
        if field in row_data and pd.notna(row_data[field]):
            value = str(row_data[field]).strip()
            if value:  # Only add non-empty values
                primary_text.append(f"{field}: {value}")
    
    if primary_text:
        texts.append(", ".join(primary_text))
    
    # Secondary text - availability and store information
    availability_fields = FIELD_PRIORITIES["availability"]
    availability_text = []
    
    for field in availability_fields:
        if field in row_data and pd.notna(row_data[field]):
            availability_text.append(f"{field}: {row_data[field]}")
    
    if availability_text:
        texts.append(", ".join(availability_text))
    
    # Pricing text
    pricing_fields = FIELD_PRIORITIES["pricing"]
    pricing_text = []
    
    for field in pricing_fields:
        if field in row_data and pd.notna(row_data[field]):
            pricing_text.append(f"{field}: {row_data[field]}")
    
    if pricing_text:
        texts.append(", ".join(pricing_text))
    
    # Semantic search text - natural language descriptions
    semantic_parts = []
    
    # Product description - use Product_Description if available (from scraped data)
    if "Product_Description" in row_data and pd.notna(row_data["Product_Description"]):
        desc = str(row_data["Product_Description"]).strip()
        if len(desc) > 20:  # Only use if meaningful
            semantic_parts.append(desc)
    
    # Product name and category
    if "Product_Name" in row_data and pd.notna(row_data["Product_Name"]):
        semantic_parts.append(f"This is a {row_data['Product_Name']}")
    
    if "Product_Category" in row_data and pd.notna(row_data["Product_Category"]):
        semantic_parts.append(f"in the {row_data['Product_Category']} category")
    
    if "Product_Subcategory" in row_data and pd.notna(row_data["Product_Subcategory"]):
        semantic_parts.append(f"specifically {row_data['Product_Subcategory']}")
    
    if "Color" in row_data and pd.notna(row_data["Color"]):
        semantic_parts.append(f"in {row_data['Color']} color")
    
    if "Size" in row_data and pd.notna(row_data["Size"]):
        semantic_parts.append(f"size {row_data['Size']}")
    
    if "Material" in row_data and pd.notna(row_data["Material"]):
        semantic_parts.append(f"made of {row_data['Material']}")
    
    if "Pattern" in row_data and pd.notna(row_data["Pattern"]):
        semantic_parts.append(f"with {row_data['Pattern']} pattern")
    
    # Product features (from scraped data)
    if "Product_Features" in row_data and pd.notna(row_data["Product_Features"]):
        features = str(row_data["Product_Features"])
        if features:
            semantic_parts.append(f"Features include: {features}")
    
    # Store and availability
    if "Store_Name" in row_data and pd.notna(row_data["Store_Name"]):
        semantic_parts.append(f"available at {row_data['Store_Name']}")
    
    if "Store_Location" in row_data and pd.notna(row_data["Store_Location"]):
        semantic_parts.append(f"in {row_data['Store_Location']}")
    
    if "Availability" in row_data and pd.notna(row_data["Availability"]):
        semantic_parts.append(f"currently {row_data['Availability']}")
    
    if "Stock_Status" in row_data and pd.notna(row_data["Stock_Status"]):
        semantic_parts.append(f"with {row_data['Stock_Status']} status")
    
    # Pricing information
    if "Discounted_Price" in row_data and pd.notna(row_data["Discounted_Price"]):
        semantic_parts.append(f"priced at {row_data['Discounted_Price']}")
    elif "Base_Price" in row_data and pd.notna(row_data["Base_Price"]):
        semantic_parts.append(f"priced at {row_data['Base_Price']}")
    
    if "Discount_Percent" in row_data and pd.notna(row_data["Discount_Percent"]):
        semantic_parts.append(f"with {row_data['Discount_Percent']}% discount")
    
    # Occasion and seasonal information
    if "Occasion_Tags" in row_data and pd.notna(row_data["Occasion_Tags"]):
        semantic_parts.append(f"perfect for {row_data['Occasion_Tags']}")
    
    if "Seasonal_Availability" in row_data and pd.notna(row_data["Seasonal_Availability"]):
        semantic_parts.append(f"available during {row_data['Seasonal_Availability']}")
    
    if "Target_Audience" in row_data and pd.notna(row_data["Target_Audience"]):
        semantic_parts.append(f"designed for {row_data['Target_Audience']}")
    
    if semantic_parts:
        texts.append(". ".join(semantic_parts) + ".")
    
    # CLU API has a hard limit of 1000 characters - we must prioritize important information
    # All detailed information is still preserved in metadata (prevents hallucination)
    
    # Strategy: Build a prioritized text that fits within 1000 chars
    MAX_TEXT_LENGTH = 950  # Leave some buffer for CLU API (hard limit is 1000)
    
    # Priority order: Description > Name+Category > Price > Availability > Features
    prioritized_parts = []
    current_length = 0
    
    # 1. Product Description (most important - from scraped data)
    if texts and len(texts) > 0:
        # Find description text
        for text in texts:
            if "Description:" in text or "Product_Description" in text:
                desc_text = text[:400]  # Limit description to 400 chars
                if current_length + len(desc_text) + 3 <= MAX_TEXT_LENGTH:
                    prioritized_parts.append(desc_text)
                    current_length += len(desc_text) + 3
                break
    
    # 2. Product Name and Category (essential for identification)
    for text in texts:
        if current_length >= MAX_TEXT_LENGTH:
            break
        if any(keyword in text for keyword in ["Product_Name", "Product_Category", "Product_Subcategory"]):
            remaining = MAX_TEXT_LENGTH - current_length
            if remaining > 50:
                part = text[:remaining-3]
                prioritized_parts.append(part)
                current_length += len(part) + 3
    
    # 3. Price information (important for queries)
    for text in texts:
        if current_length >= MAX_TEXT_LENGTH:
            break
        if any(keyword in text for keyword in ["Base_Price", "Discounted_Price", "Price"]):
            remaining = MAX_TEXT_LENGTH - current_length
            if remaining > 30:
                part = text[:remaining-3]
                prioritized_parts.append(part)
                current_length += len(part) + 3
    
    # 4. Availability (important for queries)
    for text in texts:
        if current_length >= MAX_TEXT_LENGTH:
            break
        if any(keyword in text for keyword in ["Availability", "Stock", "Store"]):
            remaining = MAX_TEXT_LENGTH - current_length
            if remaining > 30:
                part = text[:remaining-3]
                prioritized_parts.append(part)
                current_length += len(part) + 3
    
    # 5. Fill remaining space with other important info
    for text in texts:
        if current_length >= MAX_TEXT_LENGTH:
            break
        if text not in prioritized_parts:
            remaining = MAX_TEXT_LENGTH - current_length
            if remaining > 20:
                part = text[:remaining-3]
                prioritized_parts.append(part)
                current_length += len(part) + 3
    
    combined_text = " | ".join(prioritized_parts) if prioritized_parts else (texts[0] if texts else "")
    
    # Final safety check - ensure we're under 1000 chars
    if len(combined_text) > MAX_TEXT_LENGTH:
        combined_text = combined_text[:MAX_TEXT_LENGTH]
    
    return combined_text if combined_text else (texts[0][:MAX_TEXT_LENGTH] if texts else "")

def correct_product_data(row_data):
    """
    Auto-correct product category and subcategory based on product name.
    Fixes data quality issues where bags are labeled as dresses, etc.
    """
    product_name = str(row_data.get("Product_Name", "")).lower()
    
    # Correct subcategory based on product name
    corrected_subcategory = row_data.get("Product_Subcategory")
    corrected_category = row_data.get("Product_Category")
    
    # Define product type patterns
    subcategory_patterns = {
        # Bags
        ('handbag', 'tote bag', 'laptop bag', 'sling bag', 'clutch', 'backpack'): 'Handbags',
        # Dresses
        ('dress',): 'All Dresses',
        # Shirts
        ('shirt',): 'Shirts',
        # T-shirts
        ('t-shirt', 'tshirt', 'polo'): 'T-Shirts',
        # Jeans
        ('jeans', 'jean', 'denim'): 'Jeans',
        # Trousers/Pants
        ('trouser', 'pant', 'cargo', 'chino'): 'Trousers',
        # Shorts
        ('shorts', 'short'): 'Shorts',
        # Skirts
        ('skirt',): 'Skirts',
        # Blazers
        ('blazer',): 'Blazers',
        # Jackets
        ('jacket', 'coat'): 'Jackets',
        # Wallets
        ('wallet',): 'Wallets',
        # Belts
        ('belt',): 'Belts',
        # Kurtas
        ('kurta', 'kurti'): 'Kurtas',
    }
    
    for keywords, correct_subcat in subcategory_patterns.items():
        if any(kw in product_name for kw in keywords):
            # Only correct if current subcategory seems wrong
            current_subcat = str(corrected_subcategory or "").lower()
            # Check if current subcategory doesn't match product name
            mismatch = False
            if 'bag' in product_name and 'bag' not in current_subcat and 'handbag' not in current_subcat:
                mismatch = True
            elif 'dress' in product_name and 'dress' not in current_subcat and 'bag' in current_subcat:
                mismatch = True
            elif any(kw in product_name for kw in keywords) and not any(kw in current_subcat for kw in keywords):
                mismatch = True
            
            if mismatch:
                corrected_subcategory = correct_subcat
                logging.debug(f"Corrected subcategory: '{row_data.get('Product_Subcategory')}' -> '{correct_subcat}' for '{product_name[:50]}'")
            break
    
    # Correct category based on product name (Women's vs Men's vs Kids)
    if 'women' in product_name or 'woman' in product_name:
        if "Men's Clothing" in str(corrected_category):
            corrected_category = "Women's Clothing"
            logging.debug(f"Corrected category to Women's Clothing for '{product_name[:50]}'")
    elif 'men ' in product_name or product_name.startswith('men'):
        if "Women's Clothing" in str(corrected_category):
            corrected_category = "Men's Clothing"
            logging.debug(f"Corrected category to Men's Clothing for '{product_name[:50]}'")
    elif any(kw in product_name for kw in ['boys', 'girls', 'kids', 'boy ', 'girl ']):
        if "Men's Clothing" in str(corrected_category) or "Women's Clothing" in str(corrected_category):
            corrected_category = "Kids & Teens"
            logging.debug(f"Corrected category to Kids & Teens for '{product_name[:50]}'")
    
    return corrected_category, corrected_subcategory

def create_enhanced_metadata(row_data, row_index, source_file):
    """
    Create enhanced metadata structure for better retrieval and question answering.
    """
    # Auto-correct category and subcategory based on product name
    corrected_category, corrected_subcategory = correct_product_data(row_data)
    
    meta = {
        # Basic identification
        "source_file": str(source_file),
        "row_index": row_index,
        "record_type": "retail_data",
        "chroma_id": f"{Path(source_file).stem}_{row_index}",
        "ingestion_timestamp": datetime.now().isoformat(),
        
        # Product information (with corrected values)
        "product_id": row_data.get("Product_ID"),
        "product_name": row_data.get("Product_Name"),
        "product_category": corrected_category,
        "product_subcategory": corrected_subcategory,
        "product_description": row_data.get("Product_Description", ""),  # From scraped data
        "product_url": row_data.get("Product_URL", ""),  # From scraped data
        "material": row_data.get("Material"),
        "color": row_data.get("Color"),
        "pattern": row_data.get("Pattern"),
        "size": row_data.get("Size"),
        "style_preference": row_data.get("Style_Preference"),
        "product_features": row_data.get("Product_Features", ""),  # From scraped data
        
        # Pricing information
        "base_price": row_data.get("Base_Price"),
        "discounted_price": row_data.get("Discounted_Price"),
        "discount_percent": row_data.get("Discount_Percent"),
        "price_range": row_data.get("Price_Range"),
        "profit_margin": row_data.get("Profit_Margin"),
        
        # Availability and stock
        "availability": row_data.get("Availability"),
        "stock_status": row_data.get("Stock_Status"),
        "stock_quantity": row_data.get("Stock_Quantity"),
        "reorder_level": row_data.get("Reorder_Level"),
        "lead_time_days": row_data.get("Lead_Time_Days"),
        
        # Store information
        "store_name": row_data.get("Store_Name"),
        "store_location": row_data.get("Store_Location"),
        "store_area": row_data.get("Store_Area"),
        "store_type": row_data.get("Store_Type"),
        "store_rating": row_data.get("Store_Rating"),
        "store_footfall": row_data.get("Store_Footfall"),
        
        # Customer feedback and ratings
        "customer_rating": row_data.get("Customer_Rating"),
        "review_count": row_data.get("Review_Count"),
        "purchase_count": row_data.get("Purchase_Count"),
        "view_count": row_data.get("View_Count"),
        
        # Trending and popularity
        "trending_score": row_data.get("Trending_Score"),
        "popularity_score": row_data.get("Popularity_Score"),
        "sustainability_score": row_data.get("Sustainability_Score"),
        
        # Seasonal and occasion
        "festive_season": row_data.get("Festive_Season"),
        "occasion_tags": row_data.get("Occasion_Tags"),
        "seasonal_availability": row_data.get("Seasonal_Availability"),
        "target_audience": row_data.get("Target_Audience"),
        "product_features": row_data.get("Product_Features"),
        
        # Business metrics
        "return_rate": row_data.get("Return_Rate"),
        "warranty_period": row_data.get("Warranty_Period"),
        "supplier_rating": row_data.get("Supplier_Rating"),
        
        # Search and recommendation
        "recommended_flag": row_data.get("Recommended_Flag"),
        "collaborative_group": row_data.get("Collaborative_Group"),
        "similarity_score": row_data.get("Similarity_Score"),
        
        # User interaction
        "user_views": row_data.get("User_Views"),
        "user_clicks": row_data.get("User_Clicks"),
        "user_purchases": row_data.get("User_Purchases"),
        
        # Forecasting
        "predicted_demand": row_data.get("Predicted_Demand"),
        "forecasted_stockout": row_data.get("Forecasted_Stockout"),
        "sales_projection": row_data.get("Sales_Projection"),
        
        # Search optimization
        "search_keywords": generate_search_keywords(row_data),
        "query_categories": generate_query_categories(row_data),
    }
    
    # Handle image - use local Image_Path only (no generation/enhancement)
    image_path = row_data.get("Image_Path") or row_data.get("image_path") or ""
    existing_image = row_data.get("Image_URL") or row_data.get("image_url") or ""
    
    # Priority 1: Use local image path if available
    if image_path and isinstance(image_path, str) and image_path.strip():
        meta["Image_Path"] = image_path
        meta["image_path"] = image_path
        # Also store as image_url for backward compatibility (will be served via Flask route)
        meta["image_url"] = image_path
        meta["Image_URL"] = image_path
        meta["image_source"] = "local"
    # Priority 2: If we have a scraped image URL, use it directly
    elif existing_image and isinstance(existing_image, str) and existing_image.strip():
        meta["image_url"] = existing_image
        meta["Image_URL"] = existing_image
        meta["image_source"] = "scraped"
    else:
        # No image available - leave empty (no generation)
        meta["image_url"] = ""
        meta["Image_URL"] = ""
        meta["image_source"] = "none"
    
    # Add Product_URL if available (from scraped data)
    if "Product_URL" in row_data and pd.notna(row_data["Product_URL"]):
        meta["product_url"] = row_data["Product_URL"]
    
    # Add all original fields for completeness, ensuring ChromaDB compatibility
    # This is CRITICAL to prevent hallucination - all scraped data must be preserved
    for field, value in row_data.items():
        if field not in meta and pd.notna(value):
            # Normalize field name (lowercase, replace spaces with underscores) for consistency
            normalized_field = field.lower().replace(" ", "_")
            
            # Convert to ChromaDB-compatible types
            if isinstance(value, (str, int, float, bool)):
                meta[normalized_field] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                meta[normalized_field] = ", ".join([str(item) for item in value])
            else:
                # Convert other types to string
                meta[normalized_field] = str(value)
    
    # Ensure critical scraped fields are always present (even if empty)
    # This prevents the chatbot from hallucinating missing information
    critical_fields = {
        "Image_URL": "image_url",
        "Product_URL": "product_url", 
        "Product_Description": "product_description",
        "Product_Features": "product_features"
    }
    for original_field, meta_key in critical_fields.items():
        if meta_key not in meta or not meta[meta_key]:
            meta[meta_key] = row_data.get(original_field, "") or ""
    
    return meta

def sanitize_metadata_for_chromadb(metadata: dict) -> dict:
    """
    Ensure metadata contains only ChromaDB-supported primitive values.
    - Drops keys with None values
    - Converts lists to comma-separated strings
    - Converts numpy/decimal/other numeric types to float
    - Casts any remaining unsupported types to string
    """
    sanitized: dict = {}
    for key, value in metadata.items():
        if value is None:
            continue
        # Primitive primitives allowed
        if isinstance(value, (str, bool, int, float)):
            sanitized[key] = value
            continue
        # numpy numeric types and other numerics
        if isinstance(value, Number):
            try:
                sanitized[key] = float(value)
            except Exception:
                sanitized[key] = str(value)
            continue
        # lists/tuples -> comma separated
        if isinstance(value, (list, tuple, set)):
            sanitized[key] = ", ".join([str(item) for item in value])
            continue
        # fall back to string
        sanitized[key] = str(value)
    return sanitized

def generate_search_keywords(row_data):
    """
    Generate search keywords for better text matching.
    Returns a comma-separated string instead of list for ChromaDB compatibility.
    """
    keywords = []
    
    # Product keywords
    if "Product_Name" in row_data and pd.notna(row_data["Product_Name"]):
        keywords.extend(row_data["Product_Name"].lower().split())
    
    if "Product_Category" in row_data and pd.notna(row_data["Product_Category"]):
        keywords.extend(row_data["Product_Category"].lower().split())
    
    if "Color" in row_data and pd.notna(row_data["Color"]):
        keywords.append(row_data["Color"].lower())
    
    if "Size" in row_data and pd.notna(row_data["Size"]):
        keywords.append(row_data["Size"].lower())
    
    if "Material" in row_data and pd.notna(row_data["Material"]):
        keywords.append(row_data["Material"].lower())
    
    if "Pattern" in row_data and pd.notna(row_data["Pattern"]):
        keywords.append(row_data["Pattern"].lower())
    
    if "Occasion_Tags" in row_data and pd.notna(row_data["Occasion_Tags"]):
        keywords.extend(row_data["Occasion_Tags"].lower().split())
    
    if "Store_Name" in row_data and pd.notna(row_data["Store_Name"]):
        keywords.extend(row_data["Store_Name"].lower().split())
    
    if "Store_Location" in row_data and pd.notna(row_data["Store_Location"]):
        keywords.extend(row_data["Store_Location"].lower().split())
    
    # Return as comma-separated string for ChromaDB compatibility
    return ", ".join(list(set(keywords)))

def generate_query_categories(row_data):
    """
    Generate query categories for better query routing.
    Returns a comma-separated string instead of list for ChromaDB compatibility.
    """
    categories = []
    
    # Product type categories
    if "Product_Category" in row_data and pd.notna(row_data["Product_Category"]):
        categories.append(f"category_{row_data['Product_Category'].lower().replace(' ', '_')}")
    
    if "Product_Subcategory" in row_data and pd.notna(row_data["Product_Subcategory"]):
        categories.append(f"subcategory_{row_data['Product_Subcategory'].lower().replace(' ', '_')}")
    
    # Size categories
    if "Size" in row_data and pd.notna(row_data["Size"]):
        categories.append(f"size_{row_data['Size'].lower()}")
    
    # Color categories
    if "Color" in row_data and pd.notna(row_data["Color"]):
        categories.append(f"color_{row_data['Color'].lower()}")
    
    # Store categories
    if "Store_Location" in row_data and pd.notna(row_data["Store_Location"]):
        categories.append(f"location_{row_data['Store_Location'].lower().replace(' ', '_')}")
    
    if "Store_Type" in row_data and pd.notna(row_data["Store_Type"]):
        categories.append(f"store_type_{row_data['Store_Type'].lower().replace(' ', '_')}")
    
    # Price categories
    if "Price_Range" in row_data and pd.notna(row_data["Price_Range"]):
        categories.append(f"price_{row_data['Price_Range'].lower().replace(' ', '_')}")
    
    # Availability categories
    if "Stock_Status" in row_data and pd.notna(row_data["Stock_Status"]):
        categories.append(f"stock_{row_data['Stock_Status'].lower().replace(' ', '_')}")
    
    # Return as comma-separated string for ChromaDB compatibility
    return ", ".join(categories)

async def get_clu_embedding_async(session, text, row_index):
    """
    Send text to Microsoft CLU and get back its meaning (intent/entities).
    """
    payload = {
        "kind": "Conversation",
        "analysisInput": {
            "conversationItem": {
                "id": str(row_index),
                "participantId": "1",
                "text": text,
                "modality": "text",
                "language": "en"
            }
        },
        "parameters": {
            "projectName": CLU_PROJECT_NAME,
            "deploymentName": CLU_DEPLOYMENT_NAME,
            "stringIndexType": "TextElement_V8"
        }
    }
    
    url = CLU_ENDPOINT
    try:
        async with session.post(url, json=payload, headers=HEADERS, timeout=30) as response:
            if response.status == 429:
                logging.error(f"CLU API rate limit hit for row {row_index}. Retrying after delay.")
                await asyncio.sleep(1)
                return {"error": "429 Too Many Requests"}
            if response.status == 400:
                error_detail = await response.text()
                logging.error(f"CLU API Bad Request for row {row_index}: {error_detail}")
                return {"error": f"400 Bad Request: {error_detail}"}
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        logging.error(f"CLU API error for row {row_index}: {e}")
        return {"error": str(e)}

async def excel_to_documents_async(excel_path):
    """
    Enhanced Excel processing with optimized text generation and metadata.
    """
    logging.info(f"📖 Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    total_rows = len(df)
    logging.info(f"📊 Found {total_rows} rows to process")
    
    docs = []
    metadatas = []
    texts = []
    idxs = []
    processed_count = 0

    for idx, row in df.iterrows():
        processed_count += 1
        
        # Log progress every 10 rows
        if processed_count % 10 == 0 or processed_count == total_rows:
            logging.info(f"🔄 Processing row {processed_count}/{total_rows} ({processed_count/total_rows*100:.1f}%)")
        
        clean_row = row.dropna().to_dict()
        
        # Generate optimized text for CLU processing
        text = generate_optimized_text(clean_row)
        
        if not text:
            logging.warning(f"⚠️ Skipping row {idx}: No meaningful data")
            continue  # Skip rows with no meaningful data
        
        # Enforce CLU input size limit (CLU API hard limit is 1000 characters)
        MAX_LEN = 950  # Leave buffer for CLU API (hard limit is 1000)
        safe_text = text[:MAX_LEN] if len(text) > MAX_LEN else text
        
        # Log if text was truncated (for debugging)
        if len(text) > MAX_LEN:
            logging.debug(f"⚠️ Text truncated for row {idx}: {len(text)} -> {len(safe_text)} chars (all data preserved in metadata)")
        
        texts.append(safe_text)
        idxs.append(idx)
        
        # Create enhanced metadata
        meta = create_enhanced_metadata(clean_row, idx, excel_path)
        
        # Send to CLU for analysis
        logging.debug(f"🔍 Sending row {idx} to CLU API...")
        async with aiohttp.ClientSession() as session:
            clu_result = await get_clu_embedding_async(session, safe_text, idx)
            
            # Add CLU results to metadata
            if isinstance(clu_result, dict):
                if "error" in clu_result:
                    meta["clu_error"] = str(clu_result["error"])
                    logging.warning(f"⚠️ CLU error for row {idx}: {clu_result['error']}")
                else:
                    # Extract CLU results
                    result = clu_result.get("result", {})
                    prediction = result.get("prediction", {})
                    
                    meta["clu_intent"] = prediction.get("topIntent", "None")
                    meta["clu_confidence"] = prediction.get("intents", [{}])[0].get("confidence", 0.0)
                    
                    # Extract entities
                    entities = prediction.get("entities", [])
                    meta["clu_entities"] = ", ".join([entity.get("text", "") for entity in entities])
                    meta["clu_entity_types"] = ", ".join([entity.get("category", "") for entity in entities])
                    
                    logging.debug(f"✅ CLU processed row {idx}: Intent={meta['clu_intent']}, Confidence={meta['clu_confidence']:.2f}")
        
        docs.append(safe_text)
        metadatas.append(meta)

    logging.info(f"✅ Completed processing {len(docs)} valid rows from {excel_path}")
    return docs, metadatas

async def ingest_excel_docs_async():
    """
    Enhanced ingestion process with better error handling and reporting.
    """
    logging.info("🔗 Connecting to ChromaDB...")
    client = PersistentClient(path=CHROMA_DB_PATH, settings=Settings(anonymized_telemetry=False))
    
    if COLLECTION_NAME not in [c.name for c in client.list_collections()]:
        collection = client.create_collection(COLLECTION_NAME)
        logging.info(f"✅ Created new collection: {COLLECTION_NAME}")
    else:
        collection = client.get_collection(COLLECTION_NAME)
        logging.info(f"✅ Using existing collection: {COLLECTION_NAME}")
    
    total_processed = 0
    total_successful = 0
    total_failed = 0
    
    # Find all Excel files
    excel_files = list(DATA_DIR.glob("*.xlsx"))
    logging.info(f"📁 Found {len(excel_files)} Excel files to process")
    
    for file_num, file in enumerate(excel_files, 1):
        logging.info(f"📄 Processing file {file_num}/{len(excel_files)}: {file.name}")
        
        try:
            docs, metadatas = await excel_to_documents_async(file)
            
            if not docs:
                logging.warning(f"⚠️ No documents generated from {file.name}")
                continue
            
            # Separate successful and failed rows
            successful_docs = []
            successful_metadatas = []
            successful_ids = []
            file_failed = 0
            
            for doc, meta in zip(docs, metadatas):
                if "clu_error" not in meta:
                    successful_docs.append(doc)
                    successful_metadatas.append(meta)
                    successful_ids.append(meta["chroma_id"])
                else:
                    file_failed += 1
                    total_failed += 1
            
            # Add successful documents to ChromaDB
            if successful_docs:
                logging.info(f"💾 Adding {len(successful_docs)} documents to ChromaDB...")
                # Sanitize metadata to ensure ChromaDB compatibility
                sanitized_metadatas = [sanitize_metadata_for_chromadb(m) for m in successful_metadatas]
                # Optional: log a small sample for diagnostics
                if sanitized_metadatas:
                    logging.debug(f"Sample sanitized metadata keys: {list(sanitized_metadatas[0].keys())[:6]}")
                collection.add(
                    documents=successful_docs,
                    metadatas=sanitized_metadatas,
                    ids=successful_ids
                )
                
                total_successful += len(successful_docs)
                logging.info(f"✅ Successfully indexed {len(successful_docs)} rows from {file.name}")
            
            if file_failed > 0:
                logging.warning(f"⚠️ {file_failed} rows failed CLU processing in {file.name}")
            
            total_processed += len(docs)
            
        except Exception as e:
            logging.error(f"❌ Error processing {file.name}: {e}")
            total_failed += 1
    
    # Final summary
    success_rate = (total_successful/total_processed*100) if total_processed > 0 else 0
    logging.info(f"""
    📊 Ingestion Summary:
    - Total rows processed: {total_processed}
    - Successfully indexed: {total_successful}
    - Failed: {total_failed}
    - Success rate: {success_rate:.1f}%
    - Collection: {COLLECTION_NAME}
    - Database path: {CHROMA_DB_PATH}
    """)

if __name__ == "__main__":
    logging.info("🚀 Starting optimized CLU ingestion...")
    asyncio.run(ingest_excel_docs_async())
    logging.info("✅ Optimized CLU ingestion complete!")
