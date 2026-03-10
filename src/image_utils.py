#!/usr/bin/env python3
"""
Image Utility Module for Product Images
========================================
Provides multiple options for getting product images:
1. Unsplash API (free stock photos)
2. Placeholder services (via.pics, placeholder.com)
3. AI-generated images (optional, requires API key)
4. Manual image URLs from existing data
"""

import os
import requests
from typing import Optional, Dict, List
import hashlib
from pathlib import Path

# Configuration
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")  # Optional: Get from https://unsplash.com/developers
IMAGE_CACHE_DIR = Path("image_cache")
IMAGE_CACHE_DIR.mkdir(exist_ok=True)


def build_detailed_image_query(
    product_name: str = "",
    category: str = "",
    subcategory: str = "",
    color: str = "",
    material: str = "",
    pattern: str = "",
    style: str = ""
) -> str:
    """
    Prioritizes: color + material + subcategory/category + pattern
    """
    query_parts = []
    
    # Priority 1: Color (most visual attribute)
    if color and color.strip() and color.lower() not in ["none", "n/a", ""]:
        query_parts.append(color.strip())
    
    # Priority 2: Material (important for appearance)
    if material and material.strip() and material.lower() not in ["none", "n/a", ""]:
        material_clean = material.strip().lower()
        # Map common materials to search-friendly terms
        material_map = {
            "cotton": "cotton",
            "silk": "silk",
            "denim": "denim jeans",
            "wool": "wool",
            "polyester": "polyester",
            "linen": "linen",
            "rayon": "rayon",
            "georgette": "georgette",
            "crepe": "crepe"
        }
        if material_clean in material_map:
            query_parts.append(material_map[material_clean])
        else:
            query_parts.append(material.strip())
    
    # Priority 3: Subcategory or Category (product type)
    if subcategory and subcategory.strip():
        subcategory_clean = subcategory.strip().lower()
        # Clean up subcategory names for better search
        subcategory_map = {
            "formal shirts": "formal shirt",
            "casual shirts": "casual shirt",
            "t-shirts": "t-shirt",
            "dresses": "dress",
            "jeans": "jeans",
            "trousers": "trousers pants",
            "blazers": "blazer",
            "kurtas": "kurta",
            "kurtis": "kurti",
            "sarees": "saree",
            "formal shoes": "formal shoes",
            "casual shoes": "casual shoes",
            "sports shoes": "sports shoes",
            "heels": "heels",
            "sandals": "sandals"
        }
        if subcategory_clean in subcategory_map:
            query_parts.append(subcategory_map[subcategory_clean])
        else:
            query_parts.append(subcategory.strip())
    elif category and category.strip():
        category_clean = category.strip().lower()
        if category_clean not in ["none", "n/a", ""]:
            query_parts.append(category.strip())
    
    # Priority 4: Pattern (if not solid)
    if pattern and pattern.strip() and pattern.lower() not in ["solid", "none", "n/a", ""]:
        pattern_clean = pattern.strip().lower()
        pattern_map = {
            "floral": "floral print",
            "striped": "striped",
            "polka dots": "polka dot",
            "checks": "checked",
            "geometric": "geometric pattern",
            "paisley": "paisley",
            "animal print": "animal print",
            "abstract": "abstract pattern"
        }
        if pattern_clean in pattern_map:
            query_parts.append(pattern_map[pattern_clean])
        else:
            query_parts.append(pattern.strip())
    
    # Priority 5: Style (if available)
    if style and style.strip() and style.lower() not in ["none", "n/a", ""]:
        style_clean = style.strip().lower()
        if "formal" in style_clean:
            query_parts.append("formal")
        elif "casual" in style_clean:
            query_parts.append("casual")
        elif "party" in style_clean:
            query_parts.append("party")
    
    # Fallback: Use product name if we don't have enough attributes
    if len(query_parts) < 2 and product_name:
        # Extract key words from product name
        name_words = product_name.lower().split()
        for word in name_words[:2]:
            if word not in ["the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for"]:
                if word not in " ".join(query_parts).lower():
                    query_parts.append(word)
                    if len(query_parts) >= 3:
                        break
    
    # Limit to 3-4 most important terms for better results
    query = " ".join(query_parts[:4])
    return query.strip()


def score_image_relevance(image_data: Dict, product_attributes: Dict) -> float:
    """
    Score an image based on how well it matches product attributes.
    Uses image description, tags, and alt text from Unsplash/Pexels.
    
    Args:
        image_data: Image data dictionary from API response
        product_attributes: Dictionary with product attributes (color, material, etc.)
    
    Returns:
        Relevance score between 0.0 and 1.0
    """
    score = 0.0
    max_score = 0.0
    
    # Extract image metadata (Unsplash format)
    description = (image_data.get("description") or image_data.get("alt_description") or "").lower()
    tags = []
    if "tags" in image_data:
        tags = [tag.get("title", "").lower() if isinstance(tag, dict) else str(tag).lower() 
                for tag in image_data.get("tags", [])]
    
    # Pexels format (different structure)
    if "photographer" in image_data:
        description = (image_data.get("alt", "") or "").lower()
    
    all_text = " ".join([description] + tags).lower()
    
    # Normalize attributes
    attributes = {
        "color": (product_attributes.get("color", "") or "").lower().strip(),
        "material": (product_attributes.get("material", "") or "").lower().strip(),
        "category": ((product_attributes.get("subcategory") or product_attributes.get("category", "")) or "").lower().strip(),
        "pattern": (product_attributes.get("pattern", "") or "").lower().strip(),
        "style": (product_attributes.get("style", "") or "").lower().strip()
    }
    
    # Weighted scoring (higher weight = more important)
    # Color match (highest weight - most visual)
    if attributes["color"] and attributes["color"] not in ["none", "n/a", ""]:
        if attributes["color"] in all_text:
            score += 3.0
    max_score += 3.0
    
    # Material match
    if attributes["material"] and attributes["material"] not in ["none", "n/a", ""]:
        if attributes["material"] in all_text:
            score += 2.0
    max_score += 2.0
    
    # Category/Subcategory match
    if attributes["category"] and attributes["category"] not in ["none", "n/a", ""]:
        if attributes["category"] in all_text:
            score += 2.0
    max_score += 2.0
    
    # Pattern match (only if not solid/none)
    if attributes["pattern"] and attributes["pattern"] not in ["solid", "none", "n/a", ""]:
        if attributes["pattern"] in all_text:
            score += 1.5
    max_score += 1.5
    
    # Style match
    if attributes["style"] and attributes["style"] not in ["none", "n/a", ""]:
        if attributes["style"] in all_text:
            score += 1.0
    max_score += 1.0
    
    # Return normalized score
    return score / max_score if max_score > 0 else 0.0


def get_best_image_from_results(results: List[Dict], product_attributes: Dict) -> Optional[Dict]:
    """
    Analyze multiple image results and return the best matching one.
    
    Args:
        results: List of image data dictionaries from API
        product_attributes: Dictionary with product attributes
    
    Returns:
        Best matching image data dictionary, or None
    """
    if not results:
        return None
    
    # Score all images
    scored_images = []
    for result in results:
        score = score_image_relevance(result, product_attributes)
        scored_images.append((score, result))
    
    # Sort by score (highest first)
    scored_images.sort(key=lambda x: x[0], reverse=True)
    
    # Return best match if score > 0.3 (30% match threshold)
    # Otherwise return first result (API's best guess)
    if scored_images[0][0] > 0.3:
        return scored_images[0][1]
    else:
        # If no good match found, return first result (API's default ranking)
        return results[0]


def build_multiple_query_variations(product_name: str = "", category: str = "", 
                                   subcategory: str = "", color: str = "",
                                   material: str = "", pattern: str = "", 
                                   style: str = "") -> List[str]:
    """
    Build multiple query variations to increase chances of finding exact match.
    Different query combinations work better for different image databases.
    
    Args:
        product_name: Product name
        category: Product category
        subcategory: Product subcategory
        color: Product color
        material: Product material
        pattern: Product pattern
        style: Product style
    
    Returns:
        List of query strings (up to 3 variations)
    """
    queries = []
    
    # Variation 1: Full detailed query (current approach - most specific)
    query1 = build_detailed_image_query(
        product_name, category, subcategory, color, material, pattern, style
    )
    if query1:
        queries.append(query1)
    
    # Variation 2: Color + Material + Category (most important attributes)
    if color and (subcategory or category) and material:
        cat = subcategory or category
        query2 = f"{color} {material} {cat}"
        if query2.strip() not in queries:
            queries.append(query2.strip())
    
    # Variation 3: Category + Color + Pattern (if pattern is distinctive)
    if (subcategory or category) and color and pattern and pattern.lower() not in ["solid", "none", "n/a", ""]:
        cat = subcategory or category
        query3 = f"{color} {pattern} {cat}"
        if query3.strip() not in queries:
            queries.append(query3.strip())
    
    # Variation 4: Product name + Color (if product name is descriptive)
    if product_name and color:
        name_words = product_name.lower().split()[:3]
        query4 = f"{color} {' '.join(name_words)}"
        if query4.strip() not in queries and len(queries) < 3:
            queries.append(query4.strip())
    
    return queries[:3]  # Limit to 3 variations to avoid too many API calls


def get_image_url_unsplash(product_name: str = "", category: str = "", color: str = "",
                          material: str = "", pattern: str = "", subcategory: str = "", 
                          style: str = "") -> Optional[str]:
    """
    Enhanced Unsplash search with multiple queries and intelligent result selection.
    Fetches multiple results, scores them for relevance, and returns the best match.
    
    Requires: Set UNSPLASH_ACCESS_KEY environment variable (optional, has free tier)
    """
    if not UNSPLASH_ACCESS_KEY:
        return None
    
    product_attributes = {
        "color": color,
        "material": material,
        "category": category,
        "subcategory": subcategory,
        "pattern": pattern,
        "style": style
    }
    
    # Build multiple query variations
    queries = build_multiple_query_variations(
        product_name, category, subcategory, color, material, pattern, style
    )
    
    if not queries:
        return None
    
    all_results = []
    
    # Try each query variation
    for query in queries:
        try:
            url = "https://api.unsplash.com/search/photos"
            headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
            params = {
                "query": query,
                "per_page": 5,  # Get more results for better selection
                "orientation": "portrait"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=3)  # Reduced timeout for faster failure
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    # Take top 3 from each query to avoid too many results
                    all_results.extend(data["results"][:3])
        except Exception as e:
            print(f"⚠️ Unsplash query '{query}' failed: {e}")
            continue
    
    if not all_results:
        return None
    
    # Remove duplicates by image ID
    seen_ids = set()
    unique_results = []
    for result in all_results:
        img_id = result.get("id")
        if img_id and img_id not in seen_ids:
            seen_ids.add(img_id)
            unique_results.append(result)
    
    # Select best matching image
    best_image = get_best_image_from_results(unique_results, product_attributes)
    
    if best_image:
        return best_image["urls"]["regular"]
    
    return None


def get_image_url_placeholder(product_name: str, category: str = "", color: str = "") -> str:
    """
    Get placeholder image URL from via.pics (free, no API key needed).
    Returns a placeholder image with text.
    """
    try:
        # Create descriptive text
        text_parts = []
        if product_name:
            text_parts.append(product_name.replace(" ", "%20"))
        if category:
            text_parts.append(category.replace(" ", "%20"))
        
        text = "%20".join(text_parts[:2]) if text_parts else "Product"
        
        # via.pics placeholder service
        # Format: https://via.pics/width/height?text=YourText
        url = f"https://via.pics/400/500?text={text}"
        return url
    except Exception:
        # Fallback to placeholder.com
        return f"https://via.placeholder.com/400x500?text={product_name or 'Product'}"


def get_image_url_pexels(product_name: str = "", category: str = "", color: str = "",
                         material: str = "", pattern: str = "", subcategory: str = "", 
                         style: str = "") -> Optional[str]:
    """
    Enhanced Pexels search with multiple queries and intelligent result selection.
    Fetches multiple results, scores them for relevance, and returns the best match.
    
    Requires: Set PEXELS_API_KEY environment variable (free tier available)
    """
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    if not pexels_key:
        return None
    
    product_attributes = {
        "color": color,
        "material": material,
        "category": category,
        "subcategory": subcategory,
        "pattern": pattern,
        "style": style
    }
    
    # Build multiple query variations
    queries = build_multiple_query_variations(
        product_name, category, subcategory, color, material, pattern, style
    )
    
    if not queries:
        return None
    
    all_results = []
    
    # Try each query variation
    for query in queries:
        try:
            url = "https://api.pexels.com/v1/search"
            headers = {"Authorization": pexels_key}
            params = {
                "query": query,
                "per_page": 5,  # Get more results
                "orientation": "portrait"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=3)  # Reduced timeout for faster failure
            if response.status_code == 200:
                data = response.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    # Pexels uses "photos" instead of "results"
                    # Take top 3 from each query
                    all_results.extend(data["photos"][:3])
        except Exception as e:
            print(f"⚠️ Pexels query '{query}' failed: {e}")
            continue
    
    if not all_results:
        return None
    
    # Remove duplicates by image ID
    seen_ids = set()
    unique_results = []
    for result in all_results:
        img_id = result.get("id")
        if img_id and img_id not in seen_ids:
            seen_ids.add(img_id)
            unique_results.append(result)
    
    # Select best matching image
    best_image = get_best_image_from_results(unique_results, product_attributes)
    
    if best_image:
        return best_image["src"]["large"]
    
    return None


def get_image_url_category_based(category: str, subcategory: str = "", color: str = "") -> str:
    """
    Get category-based placeholder image.
    Uses predefined mappings for common apparel categories.
    """
    # Category-based image mappings (using placeholder services with category-specific images)
    category_map = {
        "shirt": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400",
        "dress": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400",
        "pants": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400",
        "shoes": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400",
        "accessories": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400",
        "jacket": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=400",
        "t-shirt": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400",
    }
    
    category_lower = (category or "").lower()
    subcategory_lower = (subcategory or "").lower()
    
    # Try to find matching category
    for key, url in category_map.items():
        if key in category_lower or key in subcategory_lower:
            return url
    
    # Default placeholder
    return get_image_url_placeholder(category or "Product", category, color)


def get_product_image_url(
    product_name: str = "",
    category: str = "",
    subcategory: str = "",
    color: str = "",
    material: str = "",
    pattern: str = "",
    style: str = "",
    product_id: str = "",
    existing_image_url: Optional[str] = None,
    method: str = "auto"
) -> str:
    """
    Main function to get product image URL.
    
    Args:
        product_name: Name of the product
        category: Product category
        subcategory: Product subcategory
        color: Product color
        product_id: Product ID
        existing_image_url: If product already has an image URL, use it
        method: "auto", "unsplash", "pexels", "placeholder", "category", or "existing"
    
    Returns:
        Image URL string
    """
    # Priority 1: Use existing image URL if provided
    if existing_image_url and existing_image_url.strip() and method != "placeholder":
        if existing_image_url.startswith(("http://", "https://")):
            return existing_image_url.strip()
    
    # Priority 2: Use specified method
    if method == "unsplash":
        url = get_image_url_unsplash(
            product_name=product_name,
            category=category,
            subcategory=subcategory,
            color=color,
            material=material,
            pattern=pattern,
            style=style
        )
        if url:
            return url
    
    if method == "pexels":
        url = get_image_url_pexels(
            product_name=product_name,
            category=category,
            subcategory=subcategory,
            color=color,
            material=material,
            pattern=pattern,
            style=style
        )
        if url:
            return url
    
    if method == "category":
        return get_image_url_category_based(category, subcategory, color)
    
    if method == "placeholder":
        return get_image_url_placeholder(product_name, category, color)
    
    # Priority 3: Auto mode - try multiple sources
    if method == "auto":
        # Try Unsplash first (with all attributes)
        url = get_image_url_unsplash(
            product_name=product_name,
            category=category,
            subcategory=subcategory,
            color=color,
            material=material,
            pattern=pattern,
            style=style
        )
        if url:
            return url
        
        # Try Pexels (with all attributes)
        url = get_image_url_pexels(
            product_name=product_name,
            category=category,
            subcategory=subcategory,
            color=color,
            material=material,
            pattern=pattern,
            style=style
        )
        if url:
            return url
        
        # Try category-based
        if category:
            url = get_image_url_category_based(category, subcategory, color)
            if url and not url.startswith("https://via.pics") and not url.startswith("https://via.placeholder"):
                return url
    
    # Fallback: Use placeholder
    return get_image_url_placeholder(product_name, category, color)


def is_placeholder_image(image_url: str) -> bool:
    """
    Check if an image URL is a placeholder or generic image.
    
    Args:
        image_url: Image URL to check
    
    Returns:
        True if the image is a placeholder/generic, False otherwise
    """
    if not image_url or not isinstance(image_url, str):
        return True
    
    image_url_lower = image_url.lower()
    
    # Check for placeholder services
    placeholder_indicators = [
        "via.pics",
        "via.placeholder",
        "placeholder.com",
        "placehold.it",
        "dummyimage.com",
        "loremflickr.com",
        "picsum.photos",  # Lorem Picsum
    ]
    
    for indicator in placeholder_indicators:
        if indicator in image_url_lower:
            return True
    
    # Check for empty or invalid URLs
    if not image_url.strip() or image_url.strip() in ["", "none", "n/a", "not available"]:
        return True
    
    return False


def enhance_image_url_from_metadata(metadata: Dict, force_regenerate: bool = False) -> str:
    """
    Enhance or regenerate image URL from product metadata at query time.
    This ensures images are always relevant to the product description.
    
    Args:
        metadata: Product metadata dictionary with all product attributes
        force_regenerate: If True, always regenerate even if image exists
    
    Returns:
        Enhanced/relevant image URL
    """
    # Extract product attributes from metadata (handle both naming conventions)
    product_name = (
        metadata.get("product_name") or 
        metadata.get("Product_Name") or 
        metadata.get("name") or 
        ""
    )
    category = (
        metadata.get("product_category") or 
        metadata.get("Product_Category") or 
        metadata.get("category") or 
        ""
    )
    subcategory = (
        metadata.get("product_subcategory") or 
        metadata.get("Product_Subcategory") or 
        metadata.get("subcategory") or 
        ""
    )
    color = (
        metadata.get("color") or 
        metadata.get("Color") or 
        ""
    )
    material = (
        metadata.get("material") or 
        metadata.get("Material") or 
        ""
    )
    pattern = (
        metadata.get("pattern") or 
        metadata.get("Pattern") or 
        ""
    )
    style = (
        metadata.get("style_preference") or 
        metadata.get("Style_Preference") or 
        metadata.get("style") or 
        ""
    )
    
    # Get existing image URL
    existing_image_url = (
        metadata.get("image_url") or 
        metadata.get("Image_URL") or 
        ""
    )
    
    # If we have a good existing image and not forcing regeneration, check if it's valid
    if existing_image_url and not force_regenerate:
        # Only use existing image if it's not a placeholder
        if not is_placeholder_image(existing_image_url):
            return existing_image_url
    
    # Regenerate image with all product attributes for better relevance
    enhanced_image_url = get_product_image_url(
        product_name=product_name,
        category=category,
        subcategory=subcategory,
        color=color,
        material=material,
        pattern=pattern,
        style=style,
        product_id=str(metadata.get("product_id") or metadata.get("Product_ID") or ""),
        existing_image_url=existing_image_url if not force_regenerate else None,
        method="auto"  # Try best sources first
    )
    
    return enhanced_image_url


def enhance_query_results_with_images(results: list, force_regenerate: bool = False) -> list:
    """
    Enhance query results by regenerating/validating images for each product.
    This ensures images match product descriptions at query time.
    
    Args:
        results: List of query result dictionaries with metadata
        force_regenerate: If True, always regenerate images even if they exist
    
    Returns:
        Enhanced results with relevant image URLs
    """
    enhanced_results = []
    
    for result in results:
        metadata = result.get("metadata", {})
        
        # Enhance image URL from metadata
        enhanced_image_url = enhance_image_url_from_metadata(metadata, force_regenerate)
        
        # Update metadata with enhanced image URL
        if "metadata" in result:
            result["metadata"]["image_url"] = enhanced_image_url
            result["metadata"]["Image_URL"] = enhanced_image_url
        
        enhanced_results.append(result)
    
    return enhanced_results


def generate_image_urls_for_batch(products_data: list, method: str = "auto") -> Dict[str, str]:
    """
    Generate image URLs for a batch of products with all product attributes.
    
    Args:
        products_data: List of dicts with product info (name, category, color, material, pattern, etc.)
        method: Image source method
    
    Returns:
        Dict mapping product_id to image_url
    """
    image_urls = {}
    
    for product in products_data:
        product_id = str(product.get("Product_ID") or product.get("product_id") or "")
        if not product_id:
            continue
        
        image_url = get_product_image_url(
            product_name=product.get("Product_Name") or product.get("product_name", ""),
            category=product.get("Product_Category") or product.get("product_category", ""),
            subcategory=product.get("Product_Subcategory") or product.get("product_subcategory", ""),
            color=product.get("Color") or product.get("color", ""),
            material=product.get("Material") or product.get("material", ""),
            pattern=product.get("Pattern") or product.get("pattern", ""),
            style=product.get("Style_Preference") or product.get("style_preference", ""),
            product_id=product_id,
            existing_image_url=product.get("Image_URL") or product.get("image_url"),
            method=method
        )
        
        image_urls[product_id] = image_url
    
    return image_urls


# Example usage and testing
if __name__ == "__main__":
    # Test the image utilities
    print("Testing Image Utilities...")
    
    # Test 1: Placeholder (always works)
    print("\n1. Placeholder image:")
    url1 = get_product_image_url(
        product_name="Blue Cotton Shirt",
        category="Shirts",
        color="Blue",
        method="placeholder"
    )
    print(f"   URL: {url1}")
    
    # Test 2: Category-based
    print("\n2. Category-based image:")
    url2 = get_product_image_url(
        product_name="Formal Shirt",
        category="Shirt",
        method="category"
    )
    print(f"   URL: {url2}")
    
    # Test 3: Auto mode with detailed attributes (NEW - uses all attributes)
    print("\n3. Auto mode with detailed attributes (NEW):")
    url3 = get_product_image_url(
        product_name="Red Floral Party Dress",
        category="Dresses",
        subcategory="Dresses",
        color="Red",
        material="Silk",
        pattern="Floral",
        style="Party",
        method="auto"
    )
    query3 = build_detailed_image_query(
        product_name="Red Floral Party Dress",
        category="Dresses",
        subcategory="Dresses",
        color="Red",
        material="Silk",
        pattern="Floral",
        style="Party"
    )
    print(f"   Query built: {query3}")
    print(f"   URL: {url3}")
    
    print("\n✅ Image utilities test complete!")
    print("\nNote: To use Unsplash or Pexels APIs, set environment variables:")
    print("  - UNSPLASH_ACCESS_KEY (get from https://unsplash.com/developers)")
    print("  - PEXELS_API_KEY (get from https://www.pexels.com/api/)")
    print("\n✨ ENHANCED FEATURES:")
    print("   - Uses ALL product attributes (color, material, pattern, style)")
    print("   - Multiple query variations for better matching")
    print("   - Intelligent result scoring and selection")
    print("   - Analyzes image descriptions/tags for relevance")
    print("   - Returns the best matching image, not just the first result!")

