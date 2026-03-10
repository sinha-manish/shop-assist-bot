#!/usr/bin/env python3
"""
Web Scraper for Shop Assist Products - Hyderabad Region
Scrapes product information including descriptions and image links from Shop Assist website

Note: This scraper attempts to extract data from Shop Assist's website.
You may need to adjust selectors based on the actual website structure.
For JavaScript-rendered content, consider using Selenium (see alternative method below).
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import re
from urllib.parse import urljoin, urlparse
import os
from pathlib import Path
import hashlib

# Optional: For JavaScript-rendered pages
SELENIUM_AVAILABLE = False
WEBDRIVER_MANAGER_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
    
    # Try to import webdriver-manager (optional, auto-downloads ChromeDriver)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
        # webdriver-manager not installed, will try system PATH
except ImportError:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    print("⚠️ Selenium not available. Install with: pip install selenium")

class AllenSollyScraper:
    def __init__(self, region="Hyderabad", delay_range=(2, 5)):
        """
        Initialize the scraper.
        
        Args:
            region: Target region (default: Hyderabad)
            delay_range: Random delay range between requests (seconds)
        """
        self.region = region
        self.delay_range = delay_range
        self.base_url = "https://allensolly.abfrl.in"  # Updated to actual domain
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        self.products = []
        
        # Define categories and options for filling missing fields (similar to create_advanced_store_data.py)
        self.categories = {
            "Men's Clothing": ["Formal Shirts", "Casual Shirts", "Trousers", "Blazers", "T-Shirts", "Jeans", "Kurtas"],
            "Women's Clothing": ["Dresses", "Tops", "Blouses", "Skirts", "Jeans", "Coats", "Sarees", "Kurtis"],
            "Footwear": ["Formal Shoes", "Casual Shoes", "Sandals", "Boots", "Sports Shoes", "Heels"],
            "Accessories": ["Bags", "Belts", "Watches", "Jewelry", "Scarves", "Sunglasses", "Wallets"],
            "Kids & Teens": ["Boys Clothing", "Girls Clothing", "Kids Footwear", "School Uniforms"]
        }
        self.materials = ["Cotton", "Polyester", "Silk", "Linen", "Denim", "Wool", "Blend", "Rayon", "Crepe", "Georgette"]
        self.colors = ["Navy Blue", "Black", "White", "Red", "Green", "Yellow", "Pink", "Purple", "Orange", "Brown", "Grey", "Beige", "Blue", "Olive", "Maroon", "Multi-Coloured"]
        self.patterns = ["Solid", "Striped", "Floral", "Geometric", "Abstract", "Polka Dots", "Checks", "Paisley", "Animal Print", "Tie & Dye", "Checked", "Printed", "Textured"]
        self.festive_seasons = ["Diwali", "Holi", "Eid", "Christmas", "New Year", "Wedding Season", "Summer Sale", "Winter Collection", "Monsoon Ready", "Spring Collection"]
        self.occasions = ["Formal Office", "Casual Outing", "Wedding", "Party", "Travel", "Sports", "Daily Wear", "Special Occasion", "Festival", "Business Meeting"]
        self.sizes = ["XS", "S", "M", "L", "XL", "XXL", "Free Size"]
        self.target_audiences = ["Young Professionals", "Students", "Business Executives", "Fashion Enthusiasts", "Casual Wearers"]
        self.style_preferences = ["Classic", "Modern", "Trendy", "Minimalist", "Bold", "Elegant"]
        
        # Shop Assist store locations in Hyderabad with Google Maps links
        self.hyderabad_stores = [
            {
                'store_name': 'Shop Assist - Banjara Hills',
                'store_location': 'Banjara Hills, Hyderabad, Telangana 500034',
                'store_area': 'Banjara Hills',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Banjara+Hills+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Punjagutta',
                'store_location': 'B7, Nagarjuna Hills, Punjagutta, Hyderabad, Telangana 500082',
                'store_area': 'Punjagutta',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Punjagutta+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Hitec City',
                'store_location': 'L 307, Hyderabad Next Galleria, Hitec City, Madhapur, Hyderabad, Telangana 500081',
                'store_area': 'Hitec City',
                'store_type': 'Mall Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Hitec+City+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Kukatpally',
                'store_location': 'Shop No 202, 1st Floor, Nexus Hyderabad, Kukatpally Housing Board Road, Kukatpally, Hyderabad, Telangana 500072',
                'store_area': 'Kukatpally',
                'store_type': 'Mall Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Kukatpally+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Secunderabad',
                'store_location': 'Plot No. 4, Bhagyalaxmi Co-Operative Housing Society, Tirumalgiri, Secunderabad, Hyderabad, Telangana 500015',
                'store_area': 'Secunderabad',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Secunderabad+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Jeedimetla',
                'store_location': 'Green Park Avenue, Gandhi Statue Road, Jeedimetla, Hyderabad, Telangana 500067',
                'store_area': 'Jeedimetla',
                'store_type': 'Factory Outlet',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Jeedimetla+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Vanasthalipuram',
                'store_location': 'Main Road, Vanasthalipuram, Hyderabad, Telangana 500070',
                'store_area': 'Vanasthalipuram',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Vanasthalipuram+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Gachibowli',
                'store_location': 'Inorbit Mall, Gachibowli, Hyderabad, Telangana 500032',
                'store_area': 'Gachibowli',
                'store_type': 'Mall Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Gachibowli+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Kondapur',
                'store_location': 'Forum Sujana Mall, Kondapur, Hyderabad, Telangana 500084',
                'store_area': 'Kondapur',
                'store_type': 'Mall Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Kondapur+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Abids',
                'store_location': 'Abids Main Road, Abids, Hyderabad, Telangana 500001',
                'store_area': 'Abids',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Abids+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - Ameerpet',
                'store_location': 'Ameerpet Main Road, Ameerpet, Hyderabad, Telangana 500016',
                'store_area': 'Ameerpet',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+Ameerpet+Hyderabad'
            },
            {
                'store_name': 'Shop Assist - LB Nagar',
                'store_location': 'LB Nagar Main Road, LB Nagar, Hyderabad, Telangana 500074',
                'store_area': 'LB Nagar',
                'store_type': 'Retail Store',
                'google_maps_link': 'https://www.google.com/maps/search/?api=1&query=Allen+Solly+LB+Nagar+Hyderabad'
            }
        ]
        
        # Comprehensive category structure for Shop Assist (using actual URLs)
        self.category_structure = {
            "Men": {
                "Topwear": {
                    "All Topwear": "c/topwear-for-men",
                    "Shirts": "c/mens-shirts",
                    "T-Shirts": "c/men-tshirts",
                    "Blazers": "c/blazers-for-men",
                    "Winterwear": "c/mens-winterwear",
                    "Formal Blazers": "c/formal-blazers-men"
                },
                "Bottomwear": {
                    "Jeans": "c/jeans-for-men",
                    "Trousers": "c/trousers-for-men",  # Inferred from pattern
                    "Shorts": "c/shorts-for-men",  # Inferred from pattern
                    "Cargos": "c/cargos-for-men"  # Inferred from pattern
                },
                "Formals": {
                    "Formal Shirts": "c/formal-shirts-men"  # Inferred from pattern
                },
                "Accessories": {
                    "Belts": "c/belts-for-men",  # Inferred from pattern
                    "Wallets": "c/wallets-for-men",  # Inferred from pattern
                    "All Accessories": "c/all-accessories"  # Shared
                }
            },
            "Women": {
                "Topwear": {
                    "Tops": "c/tops-for-women",
                    "Blazers": "c/blazers-for-women",
                    "Casual Shirts": "c/womens-casual-shirts",
                    "Shirts": "c/shirts-for-women",  # Inferred from pattern
                    "T-Shirts": "c/tshirts-for-women",  # Inferred from pattern
                    "Winterwear": "c/winterwear-for-women",  # Inferred from pattern
                    "All Topwear": "c/all-topwear-for-women"
                },
                "Bottomwear": {
                    "Skirts": "c/skirts-women",
                    "Trousers": "c/trousers-for-women",  # Inferred from pattern
                    "Jeans": "c/jeans-for-women",  # Inferred from pattern
                    "Shorts": "c/shorts-for-women",  # Inferred from pattern
                    "All Bottomwear": "c/all-bottomwear-for-women"
                },
                "Dresses": {
                    "Dresses": "c/dresses-women",
                    "All Dresses": "c/dresses-for-women",
                    "Queen of Hearts Collection": "c/queen-of-hearts-collection"
                },
                "Accessories": {
                    "Bags": "c/bags-for-women",
                    "Belts": "c/belts-for-women",  # Inferred from pattern
                    "Wallets": "c/wallets-for-women",  # Inferred from pattern
                    "All Accessories": "c/all-accessories"
                }
            },
            "Juniors": {
                "Boys": {
                    "Shirts": "c/shirts-for-boys",
                    "T-Shirts": "c/tshirts-for-boys",  # Inferred from pattern
                    "Trousers": "c/trousers-for-boys",  # Inferred from pattern
                    "Jeans": "c/jeans-for-boys",  # Inferred from pattern
                    "Shorts": "c/shorts-for-boys",  # Inferred from pattern
                    "Winterwear": "c/winterwear-boys",
                    "All Boys": "c/boys-clothing"  # Inferred from pattern
                },
                "Girls": {
                    "Tops and Tees": "c/tops-and-tees-for-girls",
                    "Frocks and Dresses": "c/frocks-and-dresses-for-girls",
                    "Trousers": "c/trousers-for-girls",  # Inferred from pattern
                    "All Girls": "c/girls-clothing"  # Inferred from pattern
                }
            },
            "Seasons Launch": {
                "Men": {
                    "Men Shirts": "c/men-shirts-seasonslaunch"
                },
                "Women": {
                    "New Arrivals": "c/women-new-arrivals"
                },
                "Boys": {
                    "Seasons Launch": "c/boys-seasons-launch"
                },
                "Girls": {
                    "Frocks and Dresses": "c/girls-frocks-and-dresses-new-arrivals"
                }
            },
            "SALE": {
                "All Sale": "c/sale"
            }
        }
        
    def _delay(self):
        """Add random delay between requests to be respectful."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
    
    def _download_image(self, image_url: str, product_id: int = None) -> Optional[str]:
        """
        Download image from URL and save to data/images/ directory.
        
        Args:
            image_url: URL of the image to download
            product_id: Optional product ID for filename
            
        Returns:
            Local path to saved image (relative to project root) or None if failed
        """
        if not image_url or not image_url.strip() or not image_url.startswith('http'):
            return None
        
        try:
            # Create images directory if it doesn't exist
            images_dir = Path('data/images')
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename using URL hash
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            parsed = urlparse(image_url)
            ext = os.path.splitext(parsed.path)[1] or '.jpg'
            
            # Include product_id in filename if available
            if product_id:
                filename = f"{product_id}_{url_hash}{ext}"
            else:
                filename = f"{url_hash}{ext}"
            
            save_path = images_dir / filename
            
            # Skip if already downloaded
            if save_path.exists():
                return f"data/images/{filename}"
            
            # Download image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # Save image
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return f"data/images/{filename}"
            
        except Exception as e:
            print(f"⚠️ Failed to download image {image_url}: {e}")
            return None
        
    def _get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a webpage.
        
        Args:
            url: URL to fetch
            retries: Number of retry attempts
            
        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                print(f"⚠️ Error fetching {url} (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    self._delay()
                else:
                    return None
        return None
    
    def _extract_product_info(self, product_element) -> Optional[Dict]:
        """
        Extract product information from a product element.
        
        Args:
            product_element: BeautifulSoup element containing product info
            
        Returns:
            Dictionary with product information or None
        """
        try:
            product = {}
            
            # Skip navigation/button elements and invalid content
            element_text = product_element.get_text(strip=True).upper()
            skip_keywords = ['VIEW ALL', 'SHOW MORE', 'LOAD MORE', 'SEE ALL', 'VIEW MORE', 
                           'NEXT', 'PREVIOUS', 'FILTER', 'SORT', 'SEARCH', 'MENU', 'CART',
                           'STORES', 'CONTACT US', 'LOG IN', 'SIGN UP', 'TRACK ORDER', 'MY ACCOUNT',
                           'FIND A STORE', 'JUNIORS', 'SEASONS LAUNCH', 'SALE', 'MEN', 'WOMEN',
                           'ADD DELIVERY', 'ITEMS FOUND', 'FREE SHIPPING', 'RETURN', 'EXPRESS DELIVERY',
                           'NEED HELP', 'ORDER STATUS', 'DELIVERY', 'RETURNS', 'FAQS']
            
            # Skip if it's clearly navigation
            if any(keyword in element_text for keyword in skip_keywords):
                return None
            
            # Skip if text is too short (likely not a product)
            if len(element_text) < 5:
                return None
            
            # Skip if it's just numbers (likely sizes, not product name)
            if element_text.replace(' ', '').isdigit():
                return None
            
            # Skip if it's a discount percentage only
            if re.match(r'^\d+%?\s*OFF?$', element_text):
                return None
            
            # Extract product name - try multiple strategies
            name_elem = None
            name_text = ""
            
            # Strategy 1: Look for product name in specific classes
            name_elem = (product_element.find(['h2', 'h3', 'h4', 'h5'], class_=re.compile(r'product.*name|product.*title|product-title|product-name', re.I)) or
                        product_element.find('a', class_=re.compile(r'product.*name|product.*title|product-link', re.I)) or
                        product_element.find('div', class_=re.compile(r'product.*name|product.*title', re.I)))
            
            # Strategy 2: Look for links that look like product pages
            if not name_elem:
                all_links = product_element.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    # Skip if it's a navigation link
                    if any(skip in link_text.upper() for skip in skip_keywords):
                        continue
                    # Check if href looks like a product URL (more flexible)
                    is_product_url = (
                        '/product' in href.lower() or 
                        '/p/' in href.lower() or 
                        re.search(r'/\d+', href) or
                        (href.count('/') >= 3 and 'c/' not in href and 
                         not any(nav in href.lower() for nav in ['/cart', '/checkout', '/account', '/login']))
                    )
                    if is_product_url:
                        if link_text and len(link_text) > 3:  # Valid product name
                            name_elem = link
                            break
                    # Also check if link text looks like a product name
                    elif link_text and len(link_text) > 5 and len(link_text) < 100:
                        # Check if it's not navigation
                        if not any(skip in link_text.upper() for skip in skip_keywords):
                            # Check if parent has product-like structure
                            if product_element.find('img') or re.search(r'[₹Rs]\.?\s*\d+', product_element.get_text()):
                                name_elem = link
                                break
            
            # Strategy 3: Look for product name in data attributes
            if not name_elem:
                # Check for data-product-name or similar attributes
                name_attr = (product_element.get('data-product-name') or 
                           product_element.get('data-name') or
                           product_element.get('data-title'))
                if name_attr and len(name_attr) > 3:
                    name_text = name_attr
                    name_elem = product_element
            
            # Strategy 4: Look for any text that might be a product name
            if not name_elem:
                # Find the largest text element that's not a price or button
                text_elements = product_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div'])
                for elem in text_elements:
                    text = elem.get_text(strip=True)
                    # Skip if it's navigation, too short, or just numbers
                    if (text and len(text) > 5 and len(text) < 100 and 
                        not any(skip in text.upper() for skip in skip_keywords) and
                        not re.match(r'^[₹$€£]\s*\d+', text) and  # Not a price
                        not text.replace(' ', '').isdigit() and  # Not just numbers
                        not re.match(r'^\d+%?\s*OFF?$', text.upper())):  # Not discount
                        name_elem = elem
                        name_text = text
                        break
            
            if name_elem:
                if not name_text:
                    name_text = name_elem.get_text(strip=True)
                product['Product_Name'] = name_text
                
                # Get product URL - prioritize product page links
                product_url = ""
                
                # Strategy 1: Check if name element is a link
                if name_elem.name == 'a':
                    href = name_elem.get('href', '')
                    if href and ('/p/' in href or '/product/' in href or (href.count('/') >= 3 and 'c/' not in href)):
                        product_url = urljoin(self.base_url, href)
                
                # Strategy 2: Find product link in element
                if not product_url:
                    links = product_element.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        # Must be a product page, not category
                        if ('/p/' in href or '/product/' in href or 
                            (href.count('/') >= 3 and 'c/' not in href and not href.endswith('.html'))):
                            product_url = urljoin(self.base_url, href)
                            break
                
                # Strategy 3: Check data attributes
                if not product_url:
                    product_url = (product_element.get('data-product-url') or 
                                 product_element.get('data-url') or "")
                    if product_url:
                        product_url = urljoin(self.base_url, product_url)
                
                # Store Product_URL temporarily for getting details, but don't save to Excel
                product['_Product_URL'] = product_url  # Temporary, will be removed before saving
            else:
                return None
            
            # Validate product name - must be meaningful and not navigation
            if not product['Product_Name'] or len(product['Product_Name']) < 3:
                return None
            
            # Additional validation - skip if it's clearly not a product
            name_upper = product['Product_Name'].upper()
            invalid_names = ['STORES', 'CONTACT', 'LOG IN', 'SIGN UP', 'TRACK', 'ACCOUNT', 
                           'JUNIORS', 'SEASONS', 'LAUNCH', 'SALE', 'MEN', 'WOMEN',
                           'ADD DELIVERY', 'ITEMS FOUND', 'FREE SHIPPING', 'RETURN',
                           'EXPRESS', 'NEED HELP', 'ORDER', 'DELIVERY', 'FAQS']
            if any(invalid in name_upper for invalid in invalid_names):
                return None
            
            # Skip if name is just numbers or sizes
            if product['Product_Name'].replace(' ', '').replace('-', '').isdigit():
                return None
            
            # Skip generic category names without product specifics
            generic_categories = ['CASUAL SHIRTS', 'FORMAL SHIRTS', 'T-SHIRTS', 'TROUSERS', 
                                'DRESSES', 'TOPS', 'KURTAS', 'SHOES', 'FOOTWEAR']
            if product['Product_Name'].upper() in generic_categories:
                # Only skip if there's no other product info
                if not product.get('Image_URL') and product.get('Base_Price', 0) == 0:
                    return None
            
            # Extract product image - try multiple strategies
            img_elem = None
            img_src = None
            
            # Strategy 1: Look for product images with specific classes or data attributes
            img_elem = (product_element.find('img', class_=re.compile(r'product.*image|product.*img|product-image|thumbnail', re.I)) or
                       product_element.find('img', alt=re.compile(r'product|item|shirt|dress|trouser', re.I)) or
                       product_element.find('img', {'data-product-image': True}) or
                       product_element.find('img', src=re.compile(r'product|item', re.I)))
            
            # Strategy 2: Look for images in nested product image containers
            if not img_elem:
                img_container = product_element.find(['div', 'figure'], class_=re.compile(r'image|img|photo|picture|thumbnail', re.I))
                if img_container:
                    img_elem = img_container.find('img')
            
            # Strategy 3: Find any image in the element (but skip logos/icons)
            if not img_elem:
                all_imgs = product_element.find_all('img')
                for img in all_imgs:
                    img_src_attr = img.get('src') or img.get('data-src') or ''
                    img_alt = (img.get('alt') or '').lower()
                    # Skip logos, icons, banners
                    if not any(skip in img_src_attr.lower() for skip in ['logo', 'icon', 'banner', 'header', 'footer', 'sprite']):
                        if not any(skip in img_alt for skip in ['logo', 'icon', 'banner']):
                            img_elem = img
                            break
            
            if img_elem:
                # Try multiple attributes for image source
                img_src = (img_elem.get('src') or 
                          img_elem.get('data-src') or 
                          img_elem.get('data-lazy-src') or
                          img_elem.get('data-original') or
                          img_elem.get('data-image'))
                
                if img_src:
                    # Clean up image URL
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = urljoin(self.base_url, img_src)
                    elif not img_src.startswith('http'):
                        img_src = urljoin(self.base_url, img_src)
                    
                    # Skip placeholder images
                    if any(placeholder in img_src.lower() for placeholder in ['placeholder', 'logo', 'icon', 'sprite']):
                        product['_Image_URL'] = ""  # Store temporarily
                        product['Image_Path'] = ""
                    else:
                        # Store image URL temporarily - will download after Product_ID is set
                        product['_Image_URL'] = img_src
                        product['Image_Path'] = ""
                else:
                    product['_Image_URL'] = ""
                    product['Image_Path'] = ""
            else:
                product['_Image_URL'] = ""
                product['Image_Path'] = ""
            
            # Extract price - try multiple strategies
            price_text = ""
            price_elem = None
            
            # Strategy 1: Look for price in specific classes
            price_elem = (product_element.find(['span', 'div', 'p'], class_=re.compile(r'price|cost|amount|selling.*price|product.*price', re.I)) or
                         product_element.find(['span', 'div'], class_=re.compile(r'currency|rupee|rs', re.I)))
            
            # Strategy 2: Look for price patterns in text
            if not price_elem:
                all_text = product_element.get_text()
                # Look for ₹ or Rs followed by numbers
                price_match = re.search(r'[₹Rs]\.?\s*(\d{1,3}(?:,\d{2,3})*)', all_text)
                if price_match:
                    price_text = price_match.group(0)
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
            
            # Extract numeric price
            if price_text:
                # Remove currency symbols and extract numbers
                price_match = re.search(r'(\d{1,3}(?:,\d{2,3})*)', price_text.replace(',', ''))
                if price_match:
                    product['Base_Price'] = int(price_match.group(1).replace(',', ''))
                else:
                    product['Base_Price'] = 0
            else:
                product['Base_Price'] = 0
            
            # Check for discounted price or discount percentage
            discount_elem = product_element.find(['span', 'div', 'p'], class_=re.compile(r'discount|sale|off|save', re.I))
            if discount_elem:
                discount_text = discount_elem.get_text(strip=True)
                discount_match = re.search(r'(\d+)%', discount_text)
                if discount_match:
                    product['Discount_Percent'] = int(discount_match.group(1))
                else:
                    product['Discount_Percent'] = 0
            else:
                # Check if there are two prices (original and discounted)
                prices = re.findall(r'[₹Rs]\.?\s*(\d{1,3}(?:,\d{2,3})*)', product_element.get_text())
                if len(prices) >= 2:
                    try:
                        original = int(prices[0].replace(',', ''))
                        discounted = int(prices[1].replace(',', ''))
                        if original > discounted:
                            product['Base_Price'] = original
                            product['Discounted_Price'] = discounted
                            product['Discount_Percent'] = round(((original - discounted) / original) * 100)
                        else:
                            product['Discounted_Price'] = product['Base_Price']
                            product['Discount_Percent'] = 0
                    except:
                        product['Discounted_Price'] = product['Base_Price']
                        product['Discount_Percent'] = 0
                else:
                    product['Discount_Percent'] = 0
                    product['Discounted_Price'] = product['Base_Price']
            
            if product['Discount_Percent'] == 0:
                product['Discounted_Price'] = product['Base_Price']
            else:
                product['Discounted_Price'] = round(product['Base_Price'] * (1 - product['Discount_Percent'] / 100), 2)
            
            # Extract category/subcategory from URL or current page
            if product.get('_Product_URL'):
                # Try to extract from product URL
                url_parts = product['_Product_URL'].split('/')
                if len(url_parts) >= 3:
                    # Usually format: /category/subcategory/product-name
                    category_part = url_parts[-3] if len(url_parts) > 3 else url_parts[-2]
                    subcategory_part = url_parts[-2] if len(url_parts) > 2 else ""
                    
                    if category_part and category_part not in ['www.allensolly.com', 'product', 'p', '']:
                        product['Product_Category'] = category_part.replace('-', ' ').title()
                    else:
                        product['Product_Category'] = "Unknown"
                    
                    if subcategory_part and subcategory_part not in ['product', 'p', '']:
                        product['Product_Subcategory'] = subcategory_part.replace('-', ' ').title()
                    else:
                        product['Product_Subcategory'] = "Unknown"
                else:
                    product['Product_Category'] = "Unknown"
                    product['Product_Subcategory'] = "Unknown"
            else:
                product['Product_Category'] = "Unknown"
                product['Product_Subcategory'] = "Unknown"
            
            # Try to get detailed product page for description
            product['Product_Description'] = ""
            product['Material'] = ""
            product['Color'] = ""
            product['Pattern'] = ""
            product['Size'] = ""
            
            return product
            
        except Exception as e:
            print(f"⚠️ Error extracting product info: {e}")
            return None
    
    def _parse_product_description(self, desc_text: str) -> Dict:
        """
        Parse product description text to extract structured data and clean it.
        
        Args:
            desc_text: Raw description text from the page
            
        Returns:
            Dictionary with extracted data and cleaned description
        """
        result = {
            'Product_Description': '',
            'Base_Price': None,
            'Discounted_Price': None,
            'Discount_Percent': None,
            'Color': '',
            'Material': '',
            'Pattern': '',
            'Size': '',
            'Fit': '',
            'Occasion_Tags': '',
            'Product_Features': ''
        }
        
        # Extract price information
        # Pattern: ₹1,779.00 or ₹1779.00
        price_pattern = r'₹[\s]*([\d,]+\.?\d*)'
        prices = re.findall(price_pattern, desc_text)
        
        if prices:
            # Clean prices (remove commas)
            clean_prices = [float(p.replace(',', '')) for p in prices if p.replace(',', '').replace('.', '').isdigit()]
            if clean_prices:
                # Usually first price is discounted, second is MRP/base
                if len(clean_prices) >= 2:
                    result['Discounted_Price'] = min(clean_prices)
                    result['Base_Price'] = max(clean_prices)
                    if result['Base_Price'] > result['Discounted_Price']:
                        discount = ((result['Base_Price'] - result['Discounted_Price']) / result['Base_Price']) * 100
                        result['Discount_Percent'] = round(discount, 0)
                elif len(clean_prices) == 1:
                    result['Base_Price'] = clean_prices[0]
                    result['Discounted_Price'] = clean_prices[0]
        
        # Extract discount percentage
        discount_pattern = r'(\d+)%\s*OFF'
        discount_match = re.search(discount_pattern, desc_text, re.I)
        if discount_match:
            result['Discount_Percent'] = float(discount_match.group(1))
        
        # Extract color
        color_patterns = [
            r'Color[:\s]+([A-Za-z\s]+?)(?:\n|Size|Material|MRP|₹|Buy|Add|Delivery|Inclusive|Size:|Color:|Material:)',
            r'Colour[:\s]+([A-Za-z\s]+?)(?:\n|Size|Material|MRP|₹|Buy|Add|Delivery|Inclusive|Size:|Color:|Material:)',
        ]
        for pattern in color_patterns:
            color_match = re.search(pattern, desc_text, re.I)
            if color_match:
                color = color_match.group(1).strip()
                # Clean color (remove extra words)
                color = re.sub(r'\s+(Size|Material|MRP|Buy|Add).*', '', color, flags=re.I)
                if color and len(color) < 30:
                    result['Color'] = color
                    break
        
        # Extract from product name in description (if present)
        # Pattern: "Men Olive Slim Fit..." -> Color: Olive
        name_color_match = re.search(r'\b(Olive|Black|White|Red|Blue|Green|Grey|Gray|Brown|Navy|Beige|Pink|Purple|Yellow|Orange|Maroon|Cream|Khaki)\b', desc_text, re.I)
        if name_color_match and not result['Color']:
            result['Color'] = name_color_match.group(1).capitalize()
        
        # Extract material
        material_patterns = [
            r'Material[:\s]+([^:\n]+?)(?:\n|Fit|Style|Code|Brand|Collar|Color|Cuffs|Occasion|Pattern|Sleeves|Subbrand|ProductType|Collection|View|More|product|declaration)',
            r'(\d+%?\s*(?:Cotton|Polyester|Linen|Silk|Wool|Viscose|Modal|Spandex|Elastane|Rayon|Nylon)(?:\s*and\s*\d+%?\s*(?:Cotton|Polyester|Linen|Silk|Wool|Viscose|Modal|Spandex|Elastane|Rayon|Nylon))?)',
        ]
        for pattern in material_patterns:
            material_match = re.search(pattern, desc_text, re.I)
            if material_match:
                material = material_match.group(1).strip()
                if material and len(material) < 100:
                    result['Material'] = material
                    break
        
        # Extract fit
        fit_match = re.search(r'Fit[:\s]+([A-Za-z\s]+?)(?:\n|Style|Code|Brand|Collar|Color|Cuffs|Occasion|Pattern|Sleeves|Subbrand|ProductType|Collection)', desc_text, re.I)
        if fit_match:
            fit = fit_match.group(1).strip()
            if fit and len(fit) < 30:
                result['Fit'] = fit
        
        # Extract pattern
        pattern_match = re.search(r'Pattern[:\s]+([A-Za-z\s]+?)(?:\n|Sleeves|Subbrand|ProductType|Collection|View|More)', desc_text, re.I)
        if pattern_match:
            pattern = pattern_match.group(1).strip()
            if pattern and len(pattern) < 30:
                result['Pattern'] = pattern
        
        # Extract occasion
        occasion_match = re.search(r'Occasion[:\s]+([A-Za-z\s]+?)(?:\n|Pattern|Sleeves|Subbrand|ProductType|Collection)', desc_text, re.I)
        if occasion_match:
            occasion = occasion_match.group(1).strip()
            if occasion and len(occasion) < 50:
                result['Occasion_Tags'] = occasion
        
        # Extract size (if mentioned)
        size_match = re.search(r'Size[:\s]+([A-Z0-9\s]+?)(?:\n|Color|Material|MRP|₹|Buy|Add|Delivery|Inclusive|Color:|Material:)', desc_text, re.I)
        if size_match:
            size = size_match.group(1).strip()
            if size and len(size) < 20:
                result['Size'] = size
        
        # Clean description - remove all the technical details and keep only meaningful product description
        # Find the actual product description (usually starts with a sentence about the product)
        desc_lines = desc_text.split('\n')
        clean_desc_parts = []
        
        # Look for the actual product description (usually contains words like "Elevate", "Crafted", "Designed", "Perfect", etc.)
        description_keywords = ['elevate', 'crafted', 'designed', 'perfect', 'features', 'ensures', 'embrace', 'step into', 'ideal for', 'makes it']
        
        for line in desc_lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip if it's a technical field
            if re.match(r'^(Product|Material|Fit|Style|Code|Brand|Collar|Color|Cuffs|Occasion|Pattern|Sleeves|Subbrand|ProductType|Collection|View More|product declaration|Net Quantity|Marketed by|For Customer|Toll Free|Delivery|Return|Exchange|Inclusive of|Size:|Color:|Material:|MRP|₹|Buy now|Add to Bag|ADD TO WISHLIST|Delivery Options|Express Delivery|Free shipping|days Free Return|Not the right size|Need it fast|Select location|to see availability)', line, re.I):
                continue
            
            # Skip if it's a price
            if re.match(r'^₹', line):
                continue
            
            # Skip if it's a discount percentage
            if re.match(r'^\d+%\s*OFF', line, re.I):
                continue
            
            # Skip if it's too short (likely a label)
            if len(line) < 20:
                continue
            
            # Keep if it looks like a product description
            if any(keyword in line.lower() for keyword in description_keywords):
                clean_desc_parts.append(line)
            elif len(line) > 50 and not re.match(r'^[A-Z\s]+$', line):  # Not all caps (likely not a header)
                clean_desc_parts.append(line)
        
        # If we found clean description parts, join them
        if clean_desc_parts:
            result['Product_Description'] = ' '.join(clean_desc_parts)
        else:
            # Fallback: try to extract first meaningful paragraph
            # Remove all the technical stuff and get the first substantial paragraph
            cleaned = re.sub(r'₹[\d,]+\.?\d*', '', desc_text)  # Remove prices
            cleaned = re.sub(r'\d+%\s*OFF', '', cleaned, flags=re.I)  # Remove discount
            cleaned = re.sub(r'Material[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Fit[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Color[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Size[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Pattern[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Occasion[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Style[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Code[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Brand[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Collar[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Cuffs[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Sleeves[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Subbrand[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'ProductType[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Collection[:\s]+[^\n]+', '', cleaned, flags=re.I)
            cleaned = re.sub(r'View More.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'product declaration.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Marketed by.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'For Customer.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Toll Free.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Delivery.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Return.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Exchange.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Buy now.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Add to Bag.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'ADD TO WISHLIST.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Delivery Options.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Express Delivery.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Free shipping.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'Select location.*', '', cleaned, flags=re.I)
            cleaned = re.sub(r'to see availability.*', '', cleaned, flags=re.I)
            
            # Get first meaningful sentence/paragraph
            sentences = re.split(r'[.!?]\s+', cleaned)
            meaningful = [s.strip() for s in sentences if len(s.strip()) > 30 and not re.match(r'^[A-Z\s]+$', s.strip())]
            if meaningful:
                result['Product_Description'] = meaningful[0] + '.'
        
        # Extract features from description
        features = []
        if 'comfort' in desc_text.lower():
            features.append('Comfortable')
        if 'breathable' in desc_text.lower():
            features.append('Breathable')
        if 'wrinkle' in desc_text.lower():
            features.append('Wrinkle Resistant')
        if 'easy' in desc_text.lower() and 'iron' in desc_text.lower():
            features.append('Easy Iron')
        if 'premium' in desc_text.lower():
            features.append('Premium Quality')
        if 'durable' in desc_text.lower():
            features.append('Durable')
        
        if features:
            result['Product_Features'] = ', '.join(features)
        
        return result
    
    def _get_product_details(self, product_url: str) -> Dict:
        """
        Get detailed product information from product page.
        Also extracts the actual product name and main image.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Dictionary with detailed product information
        """
        details = {
            'Product_Name': '',  # Will update if found better name
            'Product_Description': '',
            'Material': '',
            'Color': '',
            'Pattern': '',
            'Size': '',
            'Style_Preference': '',
            'Product_Features': '',
            'Image_Path': ''  # Will update if found better image
        }
        
        soup = self._get_page(product_url)
        if not soup:
            return details
        
        # Extract actual product name from product page (more accurate)
        name_elem = (soup.find('h1', class_=re.compile(r'product.*name|product.*title|title', re.I)) or
                    soup.find('h1') or
                    soup.find(['h2', 'h3'], class_=re.compile(r'product.*name|title', re.I)))
        if name_elem:
            name_text = name_elem.get_text(strip=True)
            if name_text and len(name_text) > 3:
                details['Product_Name'] = name_text
        
        # Extract main product image (usually higher quality)
        main_img = (soup.find('img', class_=re.compile(r'main.*image|product.*image|primary.*image', re.I)) or
                   soup.find('img', id=re.compile(r'main|product|primary', re.I)) or
                   soup.find('img', alt=re.compile(r'product|main', re.I)))
        
        if main_img:
            img_src = (main_img.get('src') or 
                      main_img.get('data-src') or 
                      main_img.get('data-lazy-src') or
                      main_img.get('data-original'))
            if img_src:
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = urljoin(self.base_url, img_src)
                elif not img_src.startswith('http'):
                    img_src = urljoin(self.base_url, img_src)
                # Store temporarily, will be downloaded later
                details['_Image_URL'] = img_src
        
        # Extract description and parse it intelligently
        desc_elem = (soup.find(['div', 'p', 'section'], class_=re.compile(r'description|detail|about|product.*description', re.I)) or
                    soup.find('div', id=re.compile(r'description|detail', re.I)))
        if desc_elem:
            desc_text = desc_elem.get_text(strip=True)
            if desc_text and len(desc_text) > 20:  # Meaningful description
                # Parse and clean the description
                parsed_data = self._parse_product_description(desc_text)
                # Update details with extracted data
                details.update(parsed_data)
        
        # Extract product details/specifications
        spec_section = soup.find(['div', 'section', 'ul'], class_=re.compile(r'specification|detail|attribute|product.*detail', re.I))
        if spec_section:
            spec_items = spec_section.find_all(['li', 'div', 'p', 'dt', 'dd'])
            for item in spec_items:
                text = item.get_text(strip=True).lower()
                if 'material' in text or 'fabric' in text:
                    material_text = re.sub(r'material|fabric|:|,', '', text, flags=re.I).strip()
                    if material_text and len(material_text) < 50:
                        details['Material'] = material_text
                elif 'color' in text and not details.get('Color'):
                    color_text = re.sub(r'color|colour|:|,', '', text, flags=re.I).strip()
                    if color_text and len(color_text) < 30:
                        details['Color'] = color_text
                elif 'pattern' in text and not details.get('Pattern'):
                    pattern_text = re.sub(r'pattern|:|,', '', text, flags=re.I).strip()
                    if pattern_text and len(pattern_text) < 30:
                        details['Pattern'] = pattern_text
                elif 'size' in text and not details.get('Size'):
                    size_text = re.sub(r'size|:|,', '', text, flags=re.I).strip()
                    if size_text and len(size_text) < 20:
                        details['Size'] = size_text
                elif 'style' in text and not details.get('Style_Preference'):
                    style_text = re.sub(r'style|:|,', '', text, flags=re.I).strip()
                    if style_text and len(style_text) < 30:
                        details['Style_Preference'] = style_text
        
        # Extract features
        features = []
        feature_elems = soup.find_all(['li', 'div'], class_=re.compile(r'feature|benefit|highlight', re.I))
        for feat in feature_elems[:5]:  # Limit to 5 features
            feat_text = feat.get_text(strip=True)
            if feat_text and len(feat_text) > 3:
                features.append(feat_text)
        if features:
            details['Product_Features'] = ', '.join(features)
        
        return details
    
    def _fill_missing_fields(self, product: Dict) -> Dict:
        """
        Fill in missing fields similar to create_advanced_store_data.py
        Uses product name and available data to intelligently fill missing fields.
        
        Args:
            product: Product dictionary
            
        Returns:
            Product dictionary with all fields filled
        """
        product_name = product.get('Product_Name', '').upper()
        
        # Extract category and subcategory from product name
        if not product.get('Product_Category'):
            if any(word in product_name for word in ['SHIRT', 'TROUSER', 'BLAZER', 'T-SHIRT', 'JEAN', 'KURTA']):
                product['Product_Category'] = "Men's Clothing"
            elif any(word in product_name for word in ['DRESS', 'TOP', 'BLOUSE', 'SKIRT', 'SARI', 'KURTI']):
                product['Product_Category'] = "Women's Clothing"
            elif any(word in product_name for word in ['SHOE', 'SANDAL', 'BOOT', 'HEEL']):
                product['Product_Category'] = "Footwear"
            else:
                product['Product_Category'] = "Men's Clothing"  # Default
        
        if not product.get('Product_Subcategory'):
            if 'FORMAL SHIRT' in product_name:
                product['Product_Subcategory'] = "Formal Shirts"
            elif 'CASUAL SHIRT' in product_name:
                product['Product_Subcategory'] = "Casual Shirts"
            elif 'TROUSER' in product_name:
                product['Product_Subcategory'] = "Trousers"
            elif 'T-SHIRT' in product_name:
                product['Product_Subcategory'] = "T-Shirts"
            else:
                # Try to extract from name
                for subcat in ["Formal Shirts", "Casual Shirts", "Trousers", "T-Shirts", "Jeans", "Dresses", "Tops"]:
                    if subcat.upper() in product_name:
                        product['Product_Subcategory'] = subcat
                        break
                if not product.get('Product_Subcategory'):
                    product['Product_Subcategory'] = "Casual Shirts"  # Default
        
        # Extract color from product name (only if not already extracted from description)
        if not product.get('Color'):
            for color in self.colors:
                if color.upper() in product_name:
                    product['Color'] = color
                    break
            if not product.get('Color'):
                product['Color'] = random.choice(self.colors)
        
        # Extract pattern from product name
        if not product.get('Pattern'):
            for pattern in self.patterns:
                if pattern.upper() in product_name:
                    product['Pattern'] = pattern
                    break
            if not product.get('Pattern'):
                product['Pattern'] = random.choice(self.patterns)
        
        # Extract material (if not found, infer from category)
        # Priority: Use extracted from description > Extract from name > Random
        if not product.get('Material'):
            if 'COTTON' in product_name:
                product['Material'] = "Cotton"
            elif 'POLYESTER' in product_name:
                product['Material'] = "Polyester"
            elif 'SILK' in product_name:
                product['Material'] = "Silk"
            elif 'LINEN' in product_name:
                product['Material'] = "Linen"
            else:
                product['Material'] = random.choice(self.materials)
        
        # Size
        if not product.get('Size'):
            product['Size'] = random.choice(self.sizes)
        
        # Base Price (if not found, generate based on category)
        # Priority: Use extracted price from description > Generate based on category
        if not product.get('Base_Price') or product.get('Base_Price', 0) == 0:
            if "Formal" in product.get('Product_Subcategory', ''):
                product['Base_Price'] = random.randint(800, 3000)
            elif "Casual" in product.get('Product_Subcategory', ''):
                product['Base_Price'] = random.randint(500, 2000)
            else:
                product['Base_Price'] = random.randint(500, 2500)
        
        # Discount (only if not already extracted from description)
        if not product.get('Discount_Percent'):
            product['Discount_Percent'] = random.choice([0, 10, 15, 20, 25, 30, 40, 50])
        
        # Discounted Price (calculate if not already set from description)
        if not product.get('Discounted_Price') or product.get('Discounted_Price', 0) == 0:
            if product.get('Base_Price') and product.get('Discount_Percent'):
                product['Discounted_Price'] = round(product['Base_Price'] * (1 - product['Discount_Percent'] / 100), 2)
            else:
                product['Discounted_Price'] = product.get('Base_Price', 0)
        
        # Festive Season
        if not product.get('Festive_Season'):
            product['Festive_Season'] = random.choice(self.festive_seasons + [''])
        
        # Occasion Tags (only if not already extracted from description)
        if not product.get('Occasion_Tags'):
            occasion_tags = random.sample(self.occasions, random.randint(1, 3))
            product['Occasion_Tags'] = ", ".join(occasion_tags)
        
        # Seasonal Availability
        if not product.get('Seasonal_Availability'):
            product['Seasonal_Availability'] = random.choice(["All Year", "Summer", "Winter", "Monsoon", "Spring", "Festival Season"])
        
        # Product Features (only if not already extracted from description)
        if not product.get('Product_Features'):
            features = []
            if "Formal" in product.get('Product_Subcategory', ''):
                features.extend(["Wrinkle Resistant", "Easy Iron", "Breathable"])
            if "Cotton" in product.get('Material', ''):
                features.extend(["Natural Fiber", "Comfortable", "Absorbent"])
            if not features:
                features = ["Premium Quality", "Comfortable", "Durable"]
            product['Product_Features'] = ", ".join(features)
        
        # Target Audience
        if not product.get('Target_Audience'):
            product['Target_Audience'] = random.choice(self.target_audiences)
        
        # Style Preference
        if not product.get('Style_Preference'):
            product['Style_Preference'] = random.choice(self.style_preferences)
        
        # Inventory fields
        if not product.get('Reorder_Level'):
            stock_qty = product.get('Stock_Quantity', 50)
            product['Reorder_Level'] = max(5, stock_qty // 4)
        
        if not product.get('Lead_Time_Days'):
            product['Lead_Time_Days'] = random.randint(1, 14)
        
        # Supplier Rating
        if not product.get('Supplier_Rating'):
            product['Supplier_Rating'] = round(random.uniform(3.0, 5.0), 1)
        
        # Trending Score
        if not product.get('Trending_Score'):
            product['Trending_Score'] = round(random.uniform(0.1, 1.0), 2)
        
        # Sustainability Score
        if not product.get('Sustainability_Score'):
            product['Sustainability_Score'] = round(random.uniform(0.3, 1.0), 2)
        
        # Return Rate
        if not product.get('Return_Rate'):
            product['Return_Rate'] = round(random.uniform(0.01, 0.15), 3)
        
        # Warranty Period
        if not product.get('Warranty_Period'):
            product['Warranty_Period'] = random.choice([0, 30, 90, 180, 365])
        
        # Purchase Count
        if not product.get('Purchase_Count'):
            product['Purchase_Count'] = random.randint(5, 200)
        
        # View Count
        if not product.get('View_Count'):
            product['View_Count'] = random.randint(50, 1000)
        
        # Stock Status
        if not product.get('Stock_Status'):
            stock_qty = product.get('Stock_Quantity', 50)
            reorder_level = product.get('Reorder_Level', 10)
            if stock_qty <= reorder_level:
                product['Stock_Status'] = "Critical"
            elif stock_qty <= reorder_level * 2:
                product['Stock_Status'] = "Low"
            elif stock_qty > 20:
                product['Stock_Status'] = "Good"
            else:
                product['Stock_Status'] = "Limited"
        
        # Price Range (calculated)
        if not product.get('Price_Range'):
            base_price = product.get('Base_Price', 0)
            if base_price < 1000:
                product['Price_Range'] = "Budget"
            elif base_price < 2500:
                product['Price_Range'] = "Mid-Range"
            elif base_price < 4000:
                product['Price_Range'] = "Premium"
            else:
                product['Price_Range'] = "Luxury"
        
        # Popularity Score (calculated)
        if not product.get('Popularity_Score'):
            rating = product.get('Customer_Rating', 4.0)
            purchase_count = product.get('Purchase_Count', 0)
            view_count = product.get('View_Count', 0)
            product['Popularity_Score'] = round((rating * 0.4 + purchase_count / 200 * 0.3 + view_count / 1000 * 0.3), 2)
        
        # Profit Margin (calculated)
        if not product.get('Profit_Margin'):
            base_price = product.get('Base_Price', 0)
            discounted_price = product.get('Discounted_Price', 0)
            if base_price > 0:
                product['Profit_Margin'] = round((base_price - discounted_price) / base_price * 100, 2)
            else:
                product['Profit_Margin'] = product.get('Discount_Percent', 0)
        
        # Store Location Assignment (randomly assign from Hyderabad stores)
        if self.region == "Hyderabad" and self.hyderabad_stores:
            # Always assign a random store (override generic placeholders)
            # Check if it's a generic placeholder or if store info is missing
            store_name = product.get('Store_Name', '')
            store_location = product.get('Store_Location', '')
            
            if (not store_name or not store_location or 
                store_name == f"Shop Assist - {self.region}" or 
                store_location == self.region or
                product.get('Store_Type') == "Online"):
                # Randomly select a store
                selected_store = random.choice(self.hyderabad_stores)
                product['Store_Name'] = selected_store['store_name']
                product['Store_Location'] = selected_store['store_location']
                product['Store_Area'] = selected_store['store_area']
                product['Store_Type'] = selected_store['store_type']
                product['Google_Maps_Link'] = selected_store['google_maps_link']
        else:
            # Fallback for other regions
            if not product.get('Store_Location'):
                product['Store_Location'] = self.region
            if not product.get('Store_Name'):
                product['Store_Name'] = f"Shop Assist - {self.region}"
        
        return product
    
    def scrape_category(self, category_url: str, max_products: int = 50, debug: bool = False) -> List[Dict]:
        """
        Scrape products from a category page.
        
        Args:
            category_url: URL of the category page
            max_products: Maximum number of products to scrape
            debug: If True, print debug information
            
        Returns:
            List of product dictionaries
        """
        print(f"📦 Scraping category: {category_url}")
        products = []
        
        soup = self._get_page(category_url)
        if not soup:
            print(f"   ⚠️ Could not fetch page")
            return products
        
        if debug:
            # Save HTML for debugging
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(str(soup))
            print(f"   💾 Saved page HTML to debug_page.html for inspection")
        
        # Find product elements (common patterns) - be more specific
        product_elements = []
        
        # Strategy 1: Look for elements with product-specific classes
        product_elements = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'product.*card|product.*item|product.*tile|product.*grid', re.I))
        
        # Strategy 2: Look for elements with data attributes
        if not product_elements:
            product_elements = soup.find_all(['div', 'li'], {'data-product-id': True})
            product_elements.extend(soup.find_all(['div', 'li'], {'data-product': True}))
        
        # Strategy 3: Look for product containers
        if not product_elements:
            product_elements = soup.find_all('div', class_=re.compile(r'product', re.I))
            # Filter out navigation/filter elements
            product_elements = [elem for elem in product_elements 
                              if not any(skip in elem.get('class', []) for skip in ['nav', 'filter', 'menu', 'header', 'footer'])]
        
        # Strategy 4: Look for grid/list items that contain product-like content
        if not product_elements:
            # Find grid containers
            grids = soup.find_all(['div', 'ul'], class_=re.compile(r'grid|list|products|items', re.I))
            for grid in grids:
                items = grid.find_all(['div', 'li'], recursive=False)
                for item in items:
                    # Check if item has product-like content (image + text + price)
                    has_img = item.find('img') is not None
                    has_text = len(item.get_text(strip=True)) > 10
                    has_price = bool(re.search(r'[₹Rs]\.?\s*\d+', item.get_text()))
                    if has_img and has_text and has_price:
                        product_elements.append(item)
        
        # Filter out navigation/button elements
        filtered_elements = []
        for elem in product_elements:
            text = elem.get_text(strip=True).upper()
            # Skip if it's clearly a navigation element
            if any(skip in text for skip in ['VIEW ALL', 'SHOW MORE', 'LOAD MORE', 'SEE ALL', 'VIEW MORE', 
                                            'NEXT', 'PREVIOUS', 'FILTER', 'SORT', 'SEARCH', 'MENU']):
                continue
            # Skip if it's too short (likely not a product)
            if len(text) < 10:
                continue
            # Must have some product-like content
            if elem.find('img') or re.search(r'[₹Rs]\.?\s*\d+', text):
                filtered_elements.append(elem)
        
        product_elements = filtered_elements
        print(f"   Found {len(product_elements)} product elements")
        
        for idx, elem in enumerate(product_elements[:max_products]):
            product = self._extract_product_info(elem)
            if product:
                # Validate product has minimum required data
                if not product.get('Product_Name') or product.get('Product_Name') == 'VIEW ALL PRODUCTS':
                    if debug:
                        print(f"   ⚠️ Skipping invalid product: {product.get('Product_Name')}")
                    continue
                
                # Add default values for required fields FIRST (needed for image download)
                product['Product_ID'] = len(products) + 1
                
                # Download image from product element if available (before getting details)
                if product.get('_Image_URL'):
                    product_id = product.get('Product_ID')
                    local_path = self._download_image(product['_Image_URL'], product_id)
                    if local_path:
                        product['Image_Path'] = local_path
                    product.pop('_Image_URL', None)
                
                # Get detailed information from product page
                if product.get('_Product_URL') and product['_Product_URL'].startswith('http'):
                    self._delay()
                    details = self._get_product_details(product['_Product_URL'])
                    # Download image from details if available (and not already downloaded)
                    if details.get('_Image_URL') and not product.get('Image_Path'):
                        product_id = product.get('Product_ID')
                        local_path = self._download_image(details['_Image_URL'], product_id)
                        if local_path:
                            product['Image_Path'] = local_path
                    product.update(details)
                
                # Add region and store information
                product['Store_Location'] = self.region
                product['Store_Area'] = "Hyderabad"
                product['Store_Name'] = f"Shop Assist - {self.region}"
                product['Store_Type'] = "Online"
                product['Store_Rating'] = 4.5
                product['Store_Footfall'] = "High"
                product['Availability'] = "In Stock"
                product['Stock_Quantity'] = random.randint(10, 100)
                product['Customer_Rating'] = round(random.uniform(3.5, 5.0), 1)
                product['Review_Count'] = random.randint(10, 500)
                product['Last_Updated'] = datetime.now().strftime("%Y-%m-%d")
                
                # Fill missing fields (including store assignment)
                product = self._fill_missing_fields(product)
                
                products.append(product)
                print(f"   ✓ Scraped: {product.get('Product_Name', 'Unknown')[:50]}")
                if debug:
                    print(f"      Image Path: {product.get('Image_Path', 'N/A')}")
                    print(f"      Image: {'✓' if product.get('Image_Path') else '✗'}")
                    print(f"      Price: ₹{product.get('Base_Price', 0)}")
        
        return products
    
    def scrape_all_categories(self, max_products_per_category: int = 30, debug: bool = False) -> List[Dict]:
        """
        Scrape products from all major categories.
        
        Args:
            max_products_per_category: Maximum products per category
            debug: If True, print debug information
            
        Returns:
            List of all scraped products
        """
        all_products = []
        
        # Shop Assist category URLs (updated to match actual website structure)
        # Format: /c/category-name
        categories = [
            f"{self.base_url}/c/mens-shirts",
            f"{self.base_url}/c/mens-trousers",
            f"{self.base_url}/c/mens-t-shirts",
            f"{self.base_url}/c/womens-dresses",
            f"{self.base_url}/c/womens-tops",
            f"{self.base_url}/c/womens-kurtas",
            f"{self.base_url}/c/mens-footwear",
            f"{self.base_url}/c/womens-footwear",
        ]
        
        for category_url in categories:
            try:
                products = self.scrape_category(category_url, max_products_per_category, debug=debug)
                if products:
                    all_products.extend(products)
                else:
                    print(f"   ⚠️ No products found in {category_url}")
                    if debug:
                        print(f"   💡 Try using Selenium method for JavaScript-rendered content")
                self._delay()
            except Exception as e:
                print(f"⚠️ Error scraping category {category_url}: {e}")
                continue
        
        return all_products
    
    def scrape_category_section(self, section_name: str, max_products_per_category: int = 30) -> List[Dict]:
        """
        Scrape all categories in a specific section (e.g., "Men", "Women", "Juniors").
        
        Args:
            section_name: Name of the section (e.g., "Men", "Women", "Juniors")
            max_products_per_category: Maximum products to scrape per category
            
        Returns:
            List of all scraped products
        """
        all_products = []
        
        if section_name not in self.category_structure:
            print(f"⚠️ Section '{section_name}' not found in category structure")
            return all_products
        
        section = self.category_structure[section_name]
        total_categories = 0
        for subcategories in section.values():
            if isinstance(subcategories, dict):
                total_categories += len(subcategories)
            elif isinstance(subcategories, str):
                total_categories += 1
        
        print(f"\n📦 Scraping {section_name} section ({total_categories} categories)...")
        print("=" * 70)
        
        category_count = 0
        for main_category, subcategories in section.items():
            # Handle both nested dictionaries and direct string URLs
            if isinstance(subcategories, dict):
                # Nested structure: main_category -> subcategory -> url_path
                for subcategory, url_path in subcategories.items():
                    category_count += 1
                    category_url = f"{self.base_url}/{url_path}"
                    
                    print(f"\n[{category_count}/{total_categories}] {section_name} > {main_category} > {subcategory}")
                    print(f"   URL: {category_url}")
                    
                    try:
                        products = self.scrape_with_selenium(
                            category_url, 
                            max_products=max_products_per_category,
                            section_name=section_name,
                            main_category=main_category,
                            subcategory=subcategory
                        )
                        all_products.extend(products)
                        print(f"   ✅ Scraped {len(products)} products (Total: {len(all_products)})")
                    except Exception as e:
                        print(f"   ⚠️ Error: {e}")
                        continue
            elif isinstance(subcategories, str):
                # Direct URL: main_category is actually the subcategory name
                category_count += 1
                category_url = f"{self.base_url}/{subcategories}"
                
                print(f"\n[{category_count}/{total_categories}] {section_name} > {main_category}")
                print(f"   URL: {category_url}")
                
                try:
                    products = self.scrape_with_selenium(
                        category_url, 
                        max_products=max_products_per_category,
                        section_name=section_name,
                        main_category=section_name,  # Use section as main category
                        subcategory=main_category   # Use main_category as subcategory
                    )
                    all_products.extend(products)
                    print(f"   ✅ Scraped {len(products)} products (Total: {len(all_products)})")
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
                    continue
        
        return all_products
    
    def scrape_all_categories_comprehensive(self, max_products_per_category: int = 30) -> List[Dict]:
        """
        Scrape products from ALL categories across all sections.
        This will create 1000s of products.
        
        Args:
            max_products_per_category: Maximum products to scrape per category
            
        Returns:
            List of all scraped products
        """
        all_products = []
        total_categories = 0
        
        # Count total categories
        for section_name, section in self.category_structure.items():
            for main_category, subcategories in section.items():
                total_categories += len(subcategories)
        
        print(f"\n🚀 Starting comprehensive scraping...")
        print(f"   Total categories to scrape: {total_categories}")
        print(f"   Products per category: {max_products_per_category}")
        print(f"   Estimated total products: {total_categories * max_products_per_category}")
        print("=" * 70)
        
        category_count = 0
        for section_name, section in self.category_structure.items():
            print(f"\n{'='*70}")
            print(f"📂 SECTION: {section_name}")
            print(f"{'='*70}")
            
            for main_category, subcategories in section.items():
                print(f"\n  📁 {main_category}")
                
                # Handle both nested dictionaries and direct string URLs
                if isinstance(subcategories, dict):
                    # Nested structure: main_category -> subcategory -> url_path
                    for subcategory, url_path in subcategories.items():
                        category_count += 1
                        category_url = f"{self.base_url}/{url_path}"
                        
                        print(f"\n  [{category_count}/{total_categories}] {subcategory}")
                        print(f"     URL: {category_url}")
                        
                        try:
                            products = self.scrape_with_selenium(
                                category_url, 
                                max_products=max_products_per_category,
                                section_name=section_name,
                                main_category=main_category,
                                subcategory=subcategory
                            )
                            all_products.extend(products)
                            print(f"     ✅ Scraped {len(products)} products (Total: {len(all_products)})")
                            
                            # Small delay between categories
                            time.sleep(2)
                        except Exception as e:
                            print(f"     ⚠️ Error: {e}")
                            continue
                elif isinstance(subcategories, str):
                    # Direct URL: main_category is actually the subcategory name
                    category_count += 1
                    category_url = f"{self.base_url}/{subcategories}"
                    
                    print(f"\n  [{category_count}/{total_categories}] {main_category}")
                    print(f"     URL: {category_url}")
                    
                    try:
                        products = self.scrape_with_selenium(
                            category_url, 
                            max_products=max_products_per_category,
                            section_name=section_name,
                            main_category=section_name,  # Use section as main category
                            subcategory=main_category   # Use main_category as subcategory
                        )
                        all_products.extend(products)
                        print(f"     ✅ Scraped {len(products)} products (Total: {len(all_products)})")
                        
                        # Small delay between categories
                        time.sleep(2)
                    except Exception as e:
                        print(f"     ⚠️ Error: {e}")
                        continue
        
        return all_products
    
    def scrape_with_selenium(self, category_url: str, max_products: int = 30, section_name: str = None, main_category: str = None, subcategory: str = None) -> List[Dict]:
        """
        Alternative scraping method using Selenium for JavaScript-rendered pages.
        This is recommended for Shop Assist website as it's JavaScript-rendered.
        
        Args:
            category_url: URL of the category page
            max_products: Maximum number of products to scrape
            section_name: Section name (e.g., "Men", "Women") for category assignment
            main_category: Main category (e.g., "Topwear", "Bottomwear") for category assignment
            subcategory: Subcategory (e.g., "Shirts", "Trousers") for category assignment
            
        Returns:
            List of product dictionaries
        """
        if not SELENIUM_AVAILABLE:
            print("⚠️ Selenium not available. Install with: pip install selenium")
            print("   Also download ChromeDriver from: https://chromedriver.chromium.org/")
            return []
        
        products = []
        driver = None
        rejected_count = 0
        rejected_reasons = {}
        try:
            print(f"🌐 Using Selenium to scrape: {category_url}")
            
            # Setup Chrome options
            chrome_options = Options()
            # Uncomment headless for production, keep visible for debugging
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Try to setup ChromeDriver with webdriver-manager (auto-downloads)
            try:
                if WEBDRIVER_MANAGER_AVAILABLE:
                    print("   📥 Using webdriver-manager to auto-download ChromeDriver...")
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Try without service (uses system PATH)
                    driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                print(f"   ⚠️ ChromeDriver setup failed: {e}")
                print("   💡 Trying alternative: Install webdriver-manager: pip install webdriver-manager")
                print("   💡 Or manually download ChromeDriver from: https://chromedriver.chromium.org/")
                raise
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("   Loading page...")
            driver.get(category_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Scroll to load more products (lazy loading)
            print("   Scrolling to load products...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 5
            
            while scroll_attempts < max_scrolls:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Get page source and parse
            print("   Extracting product data...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Strategy 0: Extract from JSON-LD structured data (most reliable!)
            products_from_json = []
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'ItemList':
                        items = data.get('itemListElement', [])
                        for item in items:
                            if isinstance(item, dict) and item.get('@type') == 'ListItem':
                                name = item.get('name', '')
                                url = item.get('url', '')
                                image = item.get('image', '')
                                if name and url and '/p/' in url:
                                    products_from_json.append({
                                        'Product_Name': name,
                                        '_Product_URL': url,  # Temporary, for internal use
                                        'Image_URL': image,  # Will be downloaded and converted to Image_Path
                                        'source': 'json-ld'
                                    })
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            print(f"   📦 Found {len(products_from_json)} products from structured data")
            
            # Try multiple selectors for Shop Assist products
            product_elements = []
            
            # Strategy 1: Look for elements with product links (must have /p/ and .html)
            all_links = soup.find_all('a', href=True)
            seen_urls = set()
            for link in all_links:
                href = link.get('href', '')
                # Must be a product page link: /p/...html pattern
                if href and '/p/' in href and '.html' in href:
                    # Clean URL (remove query params for deduplication)
                    clean_url = href.split('?')[0]
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        parent = link.find_parent(['div', 'article', 'li', 'section'])
                        if parent and parent not in product_elements:
                            product_elements.append(parent)
            
            # Strategy 2: Look for product cards/items with specific structure
            if len(product_elements) < 10:
                cards = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'product.*card|product.*item|product.*tile|product-card', re.I))
                for card in cards:
                    # Must have image and some product-like content
                    if card.find('img') and (card.find('a', href=re.compile(r'/p/|/product/')) or 
                                            re.search(r'[₹Rs]\.?\s*\d+', card.get_text())):
                        if card not in product_elements:
                            product_elements.append(card)
            
            # Strategy 3: Look for grid/list items with images and prices
            if len(product_elements) < 10:
                containers = soup.find_all(['div', 'ul', 'section'], class_=re.compile(r'grid|list|products|items|product.*grid', re.I))
                for container in containers:
                    # Skip header/footer/nav containers
                    container_class = ' '.join(container.get('class', [])).lower()
                    if any(skip in container_class for skip in ['header', 'footer', 'nav', 'menu']):
                        continue
                    
                    items = container.find_all(['div', 'li', 'article'], recursive=False)
                    for item in items:
                        # Must have image AND price to be valid product
                        has_img = item.find('img') is not None
                        has_price = bool(re.search(r'[₹Rs]\.?\s*\d{3,}', item.get_text()))  # At least 3 digits
                        has_link = item.find('a', href=re.compile(r'/p/|/product/')) is not None
                        
                        if has_img and (has_price or has_link):
                            if item not in product_elements:
                                product_elements.append(item)
            
            print(f"   Found {len(product_elements)} potential product elements from HTML")
            
            # First, process products from JSON-LD (most reliable)
            seen_urls = set()
            for json_product in products_from_json:
                url = json_product.get('Product_URL', '')
                # Clean URL (remove query params)
                if url:
                    url = url.split('?')[0]
                if url and url not in seen_urls and url.startswith('http'):
                    seen_urls.add(url)
                    # Get detailed information from product page
                    self._delay()
                    details = self._get_product_details(url)
                    # Merge JSON data with product page details
                    product = json_product.copy()
                    product['_Product_URL'] = url  # Temporary, for internal use only
                    if details.get('Product_Name'):
                        product['Product_Name'] = details['Product_Name']
                    # Download image if available
                    if details.get('_Image_URL'):
                        product_id = len(products) + 1
                        local_path = self._download_image(details['_Image_URL'], product_id)
                        if local_path:
                            product['Image_Path'] = local_path
                    elif json_product.get('Image_URL'):
                        # Download from JSON data
                        product_id = len(products) + 1
                        local_path = self._download_image(json_product['Image_URL'], product_id)
                        if local_path:
                            product['Image_Path'] = local_path
                    # Update other details
                    for key, value in details.items():
                        if key not in ['Product_Name', '_Image_URL', 'Image_Path'] and value:
                            product[key] = value
                    # Remove Image_URL if present
                    product.pop('Image_URL', None)
                    
                    # Set category information if provided
                    if section_name:
                        if section_name == "Men":
                            product['Product_Category'] = "Men's Clothing"
                        elif section_name == "Women":
                            product['Product_Category'] = "Women's Clothing"
                        elif section_name == "Juniors":
                            product['Product_Category'] = "Kids & Teens"
                        else:
                            product['Product_Category'] = section_name
                    
                    if subcategory:
                        product['Product_Subcategory'] = subcategory
                    
                    # Add region and store information
                    product['Store_Location'] = self.region
                    product['Store_Area'] = "Hyderabad"
                    product['Store_Name'] = f"Shop Assist - {self.region}"
                    product['Store_Type'] = "Online"
                    product['Store_Rating'] = 4.5
                    product['Store_Footfall'] = "High"
                    
                    # Add default values
                    product['Product_ID'] = len(products) + 1
                    product['Availability'] = "In Stock"
                    product['Stock_Quantity'] = random.randint(10, 100)
                    product['Customer_Rating'] = round(random.uniform(3.5, 5.0), 1)
                    product['Review_Count'] = random.randint(10, 500)
                    product['Last_Updated'] = datetime.now().strftime("%Y-%m-%d")
                    # Fill all missing fields (category, price, material, color, pattern, etc.)
                    product = self._fill_missing_fields(product)
                    
                    products.append(product)
                    print(f"   ✓ Scraped: {product.get('Product_Name', 'Unknown')[:50]}")
                    
                    if len(products) >= max_products:
                        break
            
            # Then, process products from HTML elements (if we need more)
            if len(products) < max_products:
                rejected_count = 0
                rejected_reasons = {}
                
                for idx, elem in enumerate(product_elements[:max_products * 2]):
                    # Skip if we already have this URL from JSON-LD
                    elem_links = elem.find_all('a', href=re.compile(r'/p/.*\.html'))
                    elem_url = None
                    for link in elem_links:
                        href = link.get('href', '').split('?')[0]
                        if href and href not in seen_urls:
                            elem_url = href
                            break
                    
                    if not elem_url or elem_url in seen_urls:
                        continue
                    
                    product = self._extract_product_info(elem)
                    if not product or not product.get('_Product_URL'):
                        continue
                    
                    # Clean URL
                    product_url = product['_Product_URL'].split('?')[0]
                    if product_url in seen_urls:
                        continue
                    seen_urls.add(product_url)
                    
                    # Get detailed information from product page
                    self._delay()
                    details = self._get_product_details(product_url)
                    if details.get('Product_Name'):
                        product['Product_Name'] = details['Product_Name']
                    # Download image if available
                    if details.get('_Image_URL'):
                        product_id = len(products) + 1
                        local_path = self._download_image(details['_Image_URL'], product_id)
                        if local_path:
                            product['Image_Path'] = local_path
                    for key, value in details.items():
                        if key not in ['Product_Name', '_Image_URL', 'Image_Path'] and value:
                            product[key] = value
                    # Remove Image_URL and Product_URL if present
                    product.pop('Image_URL', None)
                    product.pop('Product_URL', None)
                    
                    # Set category information if provided
                    if section_name:
                        if section_name == "Men":
                            product['Product_Category'] = "Men's Clothing"
                        elif section_name == "Women":
                            product['Product_Category'] = "Women's Clothing"
                        elif section_name == "Juniors":
                            product['Product_Category'] = "Kids & Teens"
                        else:
                            product['Product_Category'] = section_name
                    
                    if subcategory:
                        product['Product_Subcategory'] = subcategory
                    
                    # Add region and store information
                    product['Store_Location'] = self.region
                    product['Store_Area'] = "Hyderabad"
                    product['Store_Name'] = f"Shop Assist - {self.region}"
                    product['Store_Type'] = "Online"
                    product['Store_Rating'] = 4.5
                    product['Store_Footfall'] = "High"
                    
                    # Add default values
                    product['Product_ID'] = len(products) + 1
                    product['Availability'] = "In Stock"
                    product['Stock_Quantity'] = random.randint(10, 100)
                    product['Customer_Rating'] = round(random.uniform(3.5, 5.0), 1)
                    product['Review_Count'] = random.randint(10, 500)
                    product['Last_Updated'] = datetime.now().strftime("%Y-%m-%d")
                    # Fill all missing fields
                    product = self._fill_missing_fields(product)
                    
                    products.append(product)
                    print(f"   ✓ Scraped: {product.get('Product_Name', 'Unknown')[:50]}")
                    
                    if len(products) >= max_products:
                        break
            
            driver.quit()
            print(f"   ✅ Extracted {len(products)} products")
            if rejected_count > 0:
                print(f"   ⚠️ Rejected {rejected_count} elements:")
                for reason, count in rejected_reasons.items():
                    print(f"      - {reason}: {count}")
            
        except Exception as e:
            print(f"⚠️ Selenium scraping error: {e}")
            import traceback
            traceback.print_exc()
            if driver:
                driver.quit()
        
        return products
    
    def save_to_excel(self, products: List[Dict], filename: str = None, merge_with_existing: bool = False):
        """
        Save scraped products to Excel file in the same format as existing dataset.
        
        Args:
            products: List of product dictionaries
            filename: Output filename (default: auto-generated)
            merge_with_existing: If True, merge with existing dataset
        """
        if not filename:
            # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/documents/shop_assist_hyderabad.xlsx"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Remove temporary/internal fields before saving
        for product in products:
            product.pop('_Product_URL', None)
            product.pop('_Image_URL', None)
            product.pop('Image_URL', None)  # Remove if present
            product.pop('Product_URL', None)  # Remove if present
        
        # Convert to DataFrame
        df = pd.DataFrame(products)
        
        # Ensure Image_Path column exists
        if 'Image_Path' not in df.columns:
            df['Image_Path'] = ''
        
        # Add missing columns with default values to match existing format
        if 'Reorder_Level' not in df.columns:
            df['Reorder_Level'] = 10
        if 'Lead_Time_Days' not in df.columns:
            df['Lead_Time_Days'] = 7
        if 'Purchase_Count' not in df.columns:
            df['Purchase_Count'] = [random.randint(5, 200) for _ in range(len(df))]
        if 'View_Count' not in df.columns:
            df['View_Count'] = [random.randint(50, 1000) for _ in range(len(df))]
        if 'Festive_Season' not in df.columns:
            df['Festive_Season'] = ''
        if 'Occasion_Tags' not in df.columns:
            df['Occasion_Tags'] = ''
        if 'Seasonal_Availability' not in df.columns:
            df['Seasonal_Availability'] = 'All Year'
        if 'Target_Audience' not in df.columns:
            df['Target_Audience'] = 'General'
        if 'Supplier_Rating' not in df.columns:
            df['Supplier_Rating'] = [round(random.uniform(3.0, 5.0), 1) for _ in range(len(df))]
        if 'Trending_Score' not in df.columns:
            df['Trending_Score'] = [round(random.uniform(0.1, 1.0), 2) for _ in range(len(df))]
        if 'Sustainability_Score' not in df.columns:
            df['Sustainability_Score'] = [round(random.uniform(0.3, 1.0), 2) for _ in range(len(df))]
        if 'Return_Rate' not in df.columns:
            df['Return_Rate'] = [round(random.uniform(0.01, 0.15), 3) for _ in range(len(df))]
        if 'Warranty_Period' not in df.columns:
            df['Warranty_Period'] = 0
        if 'Stock_Status' not in df.columns:
            df['Stock_Status'] = 'Good'
        
        # Ensure Base_Price exists (default to 0 if missing)
        if 'Base_Price' not in df.columns:
            df['Base_Price'] = 0
        
        # Calculate derived fields
        if 'Price_Range' not in df.columns:
            df['Price_Range'] = df['Base_Price'].apply(
                lambda x: "Budget" if (x or 0) < 1000 else "Mid-Range" if (x or 0) < 2500 else "Premium" if (x or 0) < 4000 else "Luxury"
            )
        
        if 'Popularity_Score' not in df.columns:
            df['Popularity_Score'] = df.apply(
                lambda row: (row.get('Customer_Rating', 4.0) * 0.4 + 
                           row.get('Purchase_Count', 0) / 200 * 0.3 + 
                           row.get('View_Count', 0) / 1000 * 0.3), 
                axis=1
            )
        
        if 'Profit_Margin' not in df.columns:
            df['Profit_Margin'] = df['Discount_Percent']
        
        # Merge with existing dataset if requested
        if merge_with_existing:
            existing_file = "data/documents/shop_assist_hyderabad.xlsx"
            if os.path.exists(existing_file):
                try:
                    existing_df = pd.read_excel(existing_file, sheet_name='Products')
                    # Assign new Product_IDs
                    max_id = existing_df['Product_ID'].max() if 'Product_ID' in existing_df.columns else 0
                    df['Product_ID'] = range(max_id + 1, max_id + 1 + len(df))
                    
                    # Combine datasets
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    df = combined_df
                    print(f"✅ Merged with existing dataset. Total products: {len(df)}")
                except Exception as e:
                    print(f"⚠️ Could not merge with existing dataset: {e}")
        
        # Save to Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"\n💾 Saved {len(df)} products to: {filename}")
        return filename


def main():
    """Main function to run the scraper."""
    print("🚀 Starting Shop Assist Product Scraper for Hyderabad Region...")
    print("=" * 70)
    
    scraper = AllenSollyScraper(region="Hyderabad", delay_range=(2, 4))
    
    # Enable debug mode to see what's being found (set to True for troubleshooting)
    DEBUG_MODE = False
    
    # Option 1: Scrape ALL categories (RECOMMENDED - creates 1000s of products)
    print("\n📋 Option 1: Scraping ALL categories (Men, Women, Juniors, Sale, etc.)...")
    print("   This will scrape products from all categories and subcategories")
    print("   Estimated products: 1000+")
    
    all_products = scraper.scrape_all_categories_comprehensive(max_products_per_category=30)
    
    # Option 2: Scrape specific category (uncomment to use)
    # print("\n📋 Option 2: Scraping specific category...")
    # specific_url = "https://allensolly.abfrl.in/c/mens-shirts"
    # all_products = scraper.scrape_with_selenium(specific_url, max_products=50)
    
    # Option 3: Scrape only Men's section (uncomment to use)
    # print("\n📋 Option 3: Scraping Men's section only...")
    # all_products = scraper.scrape_category_section("Men", max_products_per_category=30)
    
    # Option 2: Scrape specific category (uncomment to use)
    # print("\n📋 Option 2: Scraping specific category...")
    # specific_url = "https://allensolly.abfrl.in/c/mens-shirts"
    # all_products = scraper.scrape_category(specific_url, max_products=50, debug=True)
    
    # Option 3: Use Selenium for JavaScript-rendered pages (RECOMMENDED for this site)
    # print("\n📋 Option 3: Using Selenium for JavaScript-rendered content...")
    # specific_url = "https://allensolly.abfrl.in/c/mens-shirts"
    # all_products = scraper.scrape_with_selenium(specific_url, max_products=50)
    
    if all_products:
        print(f"\n✅ Successfully scraped {len(all_products)} products!")
        
        # Save to Excel (set merge_with_existing=True to merge with existing dataset)
        output_file = scraper.save_to_excel(all_products, merge_with_existing=False)
        
        # Display summary
        print("\n📊 Scraping Summary:")
        print(f"   Total Products: {len(all_products)}")
        print(f"   Products with Images: {sum(1 for p in all_products if p.get('Image_Path'))}")
        print(f"   Products with Descriptions: {sum(1 for p in all_products if p.get('Product_Description'))}")
        if all_products:
            avg_price = sum(p.get('Base_Price', 0) for p in all_products) / len(all_products)
            print(f"   Average Price: ₹{avg_price:.2f}")
        
        # Display sample products
        print("\n📦 Sample Products:")
        for i, product in enumerate(all_products[:5], 1):
            print(f"\n   {i}. {product.get('Product_Name', 'N/A')}")
            print(f"      Category: {product.get('Product_Category', 'N/A')}")
            print(f"      Price: ₹{product.get('Base_Price', 0)}")
            print(f"      Image: {'✓' if product.get('Image_Path') else '✗'}")
            print(f"      Description: {'✓' if product.get('Product_Description') else '✗'}")
        
        print(f"\n💡 Next Steps:")
        print(f"   1. Review the scraped data in: {output_file}")
        print(f"   2. If needed, adjust selectors in the scraper for better extraction")
        print(f"   3. Run with merge_with_existing=True to combine with existing dataset")
    else:
        print("\n⚠️ No products were scraped. Please check:")
        print("   1. Internet connection")
        print("   2. Website URL structure (may have changed)")
        print("   3. Website access permissions")
        print("   4. Try using Selenium method for JavaScript-rendered content")
        print("\n💡 Tips:")
        print("   - Update category URLs in scrape_all_categories() method")
        print("   - Adjust CSS selectors in _extract_product_info() method")
        print("   - Install Selenium for JavaScript-rendered pages: pip install selenium")


if __name__ == "__main__":
    main()

