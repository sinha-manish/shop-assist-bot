#!/usr/bin/env python3
"""
Download Product Images Script
Downloads images from Image_URL column in Excel sheet and saves them locally.
Updates the Excel sheet with local image paths.
"""

import pandas as pd
import requests
import os
from pathlib import Path
from urllib.parse import urlparse
import time
from tqdm import tqdm
import hashlib

def get_image_filename(url, product_id=None, row_index=None):
    """Generate a unique filename for the image"""
    # Extract extension from URL
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1] or '.jpg'
    
    # Use URL hash to ensure uniqueness (since Product_IDs may not be unique)
    # This ensures each unique image URL gets a unique filename
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    
    # If product_id is available, include it in filename for readability
    if product_id:
        filename = f"{product_id}_{url_hash}{ext}"
    else:
        filename = f"{url_hash}{ext}"
    
    return filename

def download_image(url, save_path, timeout=10, max_retries=3):
    """Download an image from URL"""
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Save image
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
                continue
            else:
                print(f"ERROR: Failed to download {url}: {e}")
                return False
    return False

def download_all_images(excel_path, images_dir='data/images', column_name='Image_URL', 
                       product_id_column='Product_ID', local_path_column='Image_Path'):
    """
    Download all images from Excel sheet and update with local paths.
    
    Args:
        excel_path: Path to Excel file
        images_dir: Directory to save images
        column_name: Name of column containing image URLs
        product_id_column: Name of column containing product IDs (for naming)
        local_path_column: Name of new column to store local paths
    """
    # Create images directory if it doesn't exist
    images_path = Path(images_dir)
    images_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    
    if column_name not in df.columns:
        print(f"ERROR: Column '{column_name}' not found in Excel file!")
        print(f"Available columns: {df.columns.tolist()}")
        return
    
    print(f"Total rows: {len(df)}")
    print(f"Rows with images: {df[column_name].notna().sum()}")
    
    # Initialize local path column if it doesn't exist
    if local_path_column not in df.columns:
        df[local_path_column] = None
    
    # Track statistics
    downloaded = 0
    skipped = 0
    failed = 0
    already_exists = 0
    
    # Download images with progress bar
    print(f"\nDownloading images to: {images_dir}")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
        image_url = row[column_name]
        
        # Skip if no URL
        if pd.isna(image_url) or not str(image_url).strip():
            skipped += 1
            continue
        
        # Generate filename first to check if file already exists
        product_id = None
        if product_id_column in df.columns:
            product_id = row.get(product_id_column)
            if pd.notna(product_id):
                product_id = str(product_id).strip()
        
        row_index = idx
        filename = get_image_filename(image_url, product_id, row_index)
        save_path = images_path / filename
        
        # Check if file already exists on disk (not just in Excel)
        if save_path.exists():
            # Update Excel with correct path even if file exists
            relative_path = f"{images_dir}/{filename}"
            df.at[idx, local_path_column] = relative_path
            already_exists += 1
            continue
        
        # Filename already generated above in the "already exists" check
        
        # Download image
        if download_image(image_url, save_path):
            # Store relative path (from project root)
            relative_path = f"{images_dir}/{filename}"
            df.at[idx, local_path_column] = relative_path
            downloaded += 1
        else:
            failed += 1
    
    # Save updated Excel file
    print(f"\nSaving updated Excel file...")
    df.to_excel(excel_path, index=False)
    
    # Print statistics
    print(f"\nDownload complete!")
    print(f"   Downloaded: {downloaded}")
    print(f"   Skipped: {skipped}")
    print(f"   Failed: {failed}")
    print(f"   Already exists: {already_exists}")
    print(f"   Images saved to: {images_dir}")
    print(f"   Excel file updated: {excel_path}")

if __name__ == "__main__":
    excel_path = "data/documents/shop_assist_hyderabad.xlsx"
    images_dir = "data/images"
    
    download_all_images(
        excel_path=excel_path,
        images_dir=images_dir,
        column_name='Image_URL',
        product_id_column='Product_ID',
        local_path_column='Image_Path'
    )

