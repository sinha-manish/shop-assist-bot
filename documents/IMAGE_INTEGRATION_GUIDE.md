# Image Integration Guide

## 🖼️ Overview

Your RAG system now supports product images! Images are automatically generated/fetched and displayed in search results.

## ✨ Features

1. **Automatic Image Generation** - Images are automatically added during data ingestion
2. **Multiple Image Sources** - Supports Unsplash, Pexels, placeholders, and category-based images
3. **Frontend Display** - Images are displayed in the chat interface with product cards
4. **Fallback Support** - If one source fails, automatically tries the next

## 📦 Image Sources

### 1. **Placeholder Images** (Default - Always Works)
- Uses `via.pics` or `placeholder.com`
- No API key required
- Works immediately
- Shows product name/category as text on image

### 2. **Unsplash API** (Optional - Free Tier Available)
- High-quality stock photos
- Requires API key: `UNSPLASH_ACCESS_KEY`
- Get key from: https://unsplash.com/developers
- Free tier: 50 requests/hour

### 3. **Pexels API** (Optional - Free Tier Available)
- Free stock photos
- Requires API key: `PEXELS_API_KEY`
- Get key from: https://www.pexels.com/api/
- Free tier: 200 requests/hour

### 4. **Category-Based Images** (Automatic)
- Pre-defined images for common categories (shirts, dresses, shoes, etc.)
- Uses Unsplash direct image links
- No API key needed

## 🚀 Setup Instructions

### Option 1: Use Placeholder Images (No Setup Required)
The system works immediately with placeholder images. No configuration needed!

### Option 2: Enable Unsplash API (Recommended)
1. Sign up at https://unsplash.com/developers
2. Create a new application
3. Get your Access Key
4. Set environment variable:
   ```bash
   # Windows PowerShell
   $env:UNSPLASH_ACCESS_KEY="your_access_key_here"
   
   # Linux/Mac
   export UNSPLASH_ACCESS_KEY="your_access_key_here"
   ```

### Option 3: Enable Pexels API
1. Sign up at https://www.pexels.com/api/
2. Get your API key
3. Set environment variable:
   ```bash
   # Windows PowerShell
   $env:PEXELS_API_KEY="your_api_key_here"
   
   # Linux/Mac
   export PEXELS_API_KEY="your_api_key_here"
   ```

## 📝 How It Works

### During Data Ingestion

When you run `ingest_clu.py`, the system automatically:
1. Checks if product already has an image URL
2. If not, generates one using the `image_utils.py` module
3. Tries multiple sources in order:
   - Existing image URL (if provided)
   - Unsplash API (if configured)
   - Pexels API (if configured)
   - Category-based images
   - Placeholder images (fallback)

### Image URL Storage

Image URLs are stored in ChromaDB metadata as:
- `image_url` (primary field)
- `Image_URL` (alternative field name)

### In Search Results

When users search for products:
1. RAG system retrieves products with image URLs
2. Flask app extracts image URLs from metadata
3. Frontend displays images in a grid layout
4. Each image shows:
   - Product image
   - Product name
   - Price (if available)

## 🔄 Re-indexing with Images

To add images to existing data:

```bash
# Re-run ingestion script
python ingest_clu.py
```

The script will:
- Generate image URLs for all products
- Store them in ChromaDB metadata
- Existing products without images will get new image URLs

## 🎨 Frontend Display

Images are displayed in the chat interface as:
- **Grid Layout**: Responsive grid of product cards
- **Product Cards**: Each card shows:
  - Product image (200px height)
  - Product name
  - Price
- **Error Handling**: Failed images are automatically hidden

## 🔧 Customization

### Change Image Source Priority

Edit `ingest_clu.py` line 286:
```python
method="auto"  # Change to: "unsplash", "pexels", "placeholder", or "category"
```

### Add Custom Image URLs

If your data already has image URLs, add them to your Excel/CSV file as:
- Column name: `Image_URL` or `image_url`
- Value: Full URL (http:// or https://)

### Customize Image Display

Edit `static/js/app.js` to customize:
- Image card size
- Grid layout
- Styling

## 📊 Image Source Priority (Auto Mode)

When `method="auto"`, the system tries sources in this order:
1. Existing image URL (from data)
2. Unsplash API (if configured)
3. Pexels API (if configured)
4. Category-based images
5. Placeholder images (always works)

## 🐛 Troubleshooting

### Images Not Showing
1. Check browser console for errors
2. Verify image URLs are in metadata:
   ```python
   # In Python
   from advanced_rag import AdvancedRAG
   rag = AdvancedRAG()
   results = rag.search("shirt", n_results=1)
   print(results[0]['metadata'].get('image_url'))
   ```

### Placeholder Images Only
- This is normal if API keys aren't set
- Placeholders work fine for development
- Set API keys for production-quality images

### API Rate Limits
- Unsplash: 50 requests/hour (free tier)
- Pexels: 200 requests/hour (free tier)
- System automatically falls back to placeholders if rate limited

## 📝 Example Usage

### Test Image Generation
```python
from image_utils import get_product_image_url

# Get image for a product
image_url = get_product_image_url(
    product_name="Blue Cotton Shirt",
    category="Shirts",
    color="Blue",
    method="auto"
)
print(image_url)
```

### Batch Image Generation
```python
from image_utils import generate_image_urls_for_batch

products = [
    {"Product_ID": "1", "Product_Name": "Shirt", "Product_Category": "Shirts"},
    {"Product_ID": "2", "Product_Name": "Dress", "Product_Category": "Dresses"},
]

image_urls = generate_image_urls_for_batch(products, method="auto")
print(image_urls)
```

## ✅ What's Been Added

1. ✅ `image_utils.py` - Image generation utility
2. ✅ Updated `ingest_clu.py` - Adds image URLs during ingestion
3. ✅ Updated `advanced_rag.py` - Includes images in results
4. ✅ Updated `app_flask.py` - Extracts and sends image data
5. ✅ Updated `static/js/app.js` - Displays images in UI

## 🎯 Next Steps

1. **Test the system**: Run a search query and see images appear
2. **Optional**: Set up API keys for better image quality
3. **Re-index data**: Run `ingest_clu.py` to add images to existing products
4. **Customize**: Adjust image display styling if needed

## 📚 Files Modified

- `image_utils.py` (NEW) - Image generation utilities
- `ingest_clu.py` - Added image URL generation
- `advanced_rag.py` - Added `query_rag_with_images()` method
- `app_flask.py` - Extract and return image data
- `static/js/app.js` - Display images in chat interface

---

**Note**: The system works immediately with placeholder images. API keys are optional for better image quality.

