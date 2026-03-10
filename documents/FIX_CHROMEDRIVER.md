# Fix ChromeDriver Issue

## Quick Fix (Recommended)

Install `webdriver-manager` which automatically downloads and manages ChromeDriver:

```bash
pip install webdriver-manager
```

Then run the scraper again:
```bash
python scrape_shop_assist_products.py
```

## Alternative: Manual ChromeDriver Setup

1. **Check your Chrome version:**
   - Open Chrome → Settings → About Chrome
   - Note the version number (e.g., 120.0.6099.109)

2. **Download matching ChromeDriver:**
   - Visit: https://chromedriver.chromium.org/downloads
   - Or: https://googlechromelabs.github.io/chrome-for-testing/
   - Download the version matching your Chrome

3. **Add to PATH:**
   - Extract `chromedriver.exe`
   - Option A: Place in project folder `D:\rag\`
   - Option B: Add to system PATH

4. **Or specify path in code:**
   Update `scrape_with_selenium()` method:
   ```python
   from selenium.webdriver.chrome.service import Service
   service = Service(r'D:\rag\chromedriver.exe')  # Your path
   driver = webdriver.Chrome(service=service, options=chrome_options)
   ```

## Alternative: Use Requests Method (No Selenium)

If Selenium continues to fail, the scraper will automatically fallback to requests method. However, this may not work well for JavaScript-rendered sites.

## Test ChromeDriver

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
driver = webdriver.Chrome(options=options)
driver.get("https://www.google.com")
print("✅ ChromeDriver works!")
driver.quit()
```

