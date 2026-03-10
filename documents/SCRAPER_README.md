# Shop Assist Product Scraper - Hyderabad Region

## 📋 Overview

This scraper extracts product information from Shop Assist's website, specifically focusing on products available in the Hyderabad region. It collects:
- Product names and descriptions
- Product images (URLs)
- Prices (base and discounted)
- Categories and subcategories
- Material, color, pattern, size information
- Store information (Hyderabad region)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install requests beautifulsoup4 pandas openpyxl
```

### 2. Optional: Install Selenium (for JavaScript-rendered pages)

```bash
pip install selenium
# Also download ChromeDriver from https://chromedriver.chromium.org/
```

### 3. Run the Scraper

```bash
python scrape_shop_assist_products.py
```

## 📝 Usage Options

### Option 1: Scrape All Categories (Default)
The scraper will attempt to scrape products from multiple categories:
- Men's Shirts, Trousers, T-Shirts
- Women's Dresses, Tops, Kurtas
- Footwear (Men & Women)

### Option 2: Scrape Specific Category
Uncomment and modify in `main()`:
```python
specific_url = "https://www.shopassist.com/men/shirts"
all_products = scraper.scrape_category(specific_url, max_products=50)
```

### Option 3: Use Selenium (for JavaScript-rendered pages)
Uncomment and modify in `main()`:
```python
specific_url = "https://www.shopassist.com/men/shirts"
all_products = scraper.scrape_with_selenium(specific_url, max_products=50)
```

## ⚙️ Configuration

### Update Category URLs
If the default URLs don't work, update them in `scrape_all_categories()` method:
```python
categories = [
    f"{self.base_url}/men/shirts",
    f"{self.base_url}/men/trousers",
    # Add more categories as needed
]
```

### Adjust CSS Selectors
If products aren't being extracted correctly, adjust selectors in `_extract_product_info()`:
```python
# Update these selectors based on actual website structure
name_elem = product_element.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'product.*name|title|name', re.I))
img_elem = product_element.find('img')
price_elem = product_element.find(['span', 'div'], class_=re.compile(r'price|cost|amount', re.I))
```

### Merge with Existing Dataset
To merge scraped data with your existing dataset:
```python
output_file = scraper.save_to_excel(all_products, merge_with_existing=True)
```

## 📊 Output Format

The scraper saves data in Excel format matching your existing dataset structure:
- **File Location**: `data/documents/shop_assist_hyderabad_scraped_[timestamp].xlsx`
- **Format**: Same columns as `advanced_shop_assist_store_data.xlsx`

### Key Fields Extracted:
- Product_ID, Product_Name, Product_Category, Product_Subcategory
- Image_URL (direct link to product image)
- Product_Description (from product detail page)
- Base_Price, Discount_Percent, Discounted_Price
- Material, Color, Pattern, Size
- Store_Name, Store_Location (Hyderabad), Store_Area
- And all other required fields with default values

## 🔧 Troubleshooting

### Issue: No products scraped
**Solutions:**
1. Check internet connection
2. Verify website URLs are correct
3. Website structure may have changed - update selectors
4. Try Selenium method for JavaScript-rendered content
5. Check if website requires authentication

### Issue: Missing product information
**Solutions:**
1. Update CSS selectors in `_extract_product_info()`
2. Check product detail page structure
3. Adjust `_get_product_details()` method

### Issue: Rate limiting / Blocked
**Solutions:**
1. Increase delay between requests: `delay_range=(5, 10)`
2. Use proxies if needed
3. Respect robots.txt
4. Don't scrape too aggressively

## 📝 Important Notes

1. **Website Structure**: Shop Assist's website structure may change. You may need to update selectors periodically.

2. **Legal & Ethical**: 
   - Always respect website's Terms of Service
   - Check robots.txt before scraping
   - Use reasonable delays between requests
   - Don't overload the server

3. **Data Quality**: 
   - Review scraped data for accuracy
   - Some fields may need manual correction
   - Image URLs should be verified

4. **Hyderabad Region**: The scraper tags all products with Hyderabad region. If you need to filter by actual availability, you may need to check product detail pages or use location-based APIs.

## 🎯 Next Steps

1. **Run the scraper** and review the output
2. **Adjust selectors** if needed based on actual website structure
3. **Merge with existing dataset** if desired
4. **Ingest into RAG system** using your existing ingestion pipeline

## 📞 Support

If you encounter issues:
1. Check the website structure manually
2. Update selectors accordingly
3. Try Selenium method for dynamic content
4. Review error messages for specific issues

---

**Happy Scraping! 🎉**

