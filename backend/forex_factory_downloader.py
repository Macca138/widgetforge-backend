#!/usr/bin/env python3
"""
Forex Factory Calendar Downloader for WidgetForge
Downloads weekly economic calendar data from Forex Factory
"""

import requests
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def download_forex_factory_calendar(headless=True):
    """Download this week's Forex Factory calendar using browser automation"""
    
    # Setup Chrome options
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    
    driver = None
    try:
        # Initialize driver
        driver = webdriver.Chrome(options=chrome_options)
        
        print("📅 Navigating to Forex Factory calendar...")
        driver.get("https://www.forexfactory.com/calendar")
        
        # Wait for page to load
        WebDriverWait(driver, 10).wait(
            EC.presence_of_element_located((By.CLASS_NAME, "calendar"))
        )
        
        # Look for the weekly export URL in page source or JavaScript
        print("🔍 Searching for weekly export URL...")
        
        # Try to find JSON data in page source
        page_source = driver.page_source
        
        # Look for calendar data or export URLs
        json_pattern = r'https://nfs\.forexfactory\.com/ff_calendar_thisweek\.json\?version=(\d+)'
        matches = re.findall(json_pattern, page_source)
        
        if matches:
            version = matches[0]
            json_url = f"https://nfs.forexfactory.com/ff_calendar_thisweek.json?version={version}"
            print(f"✅ Found JSON URL with version {version}")
        else:
            # Fallback - try common version numbers
            print("⚠️  No specific version found, trying latest...")
            import random
            version = random.randint(1000000, 9999999)  # Random version number
            json_url = f"https://nfs.forexfactory.com/ff_calendar_thisweek.json?version={version}"
        
        # Close browser
        driver.quit()
        driver = None
        
        # Download the JSON data
        print(f"📥 Downloading calendar data from: {json_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.forexfactory.com/'
        }
        
        response = requests.get(json_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse JSON data
        calendar_data = response.json()
        
        # Save to cache directory
        cache_dir = os.path.join(os.path.dirname(__file__), "..", ".cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ff_calendar_{timestamp}.json"
        filepath = os.path.join(cache_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(calendar_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Downloaded {len(calendar_data)} events to {filename}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error downloading Forex Factory calendar: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def download_simple_request():
    """Simple fallback method using direct request"""
    try:
        # Try direct request to known URL patterns
        base_url = "https://nfs.forexfactory.com/ff_calendar_thisweek.json"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.forexfactory.com/'
        }
        
        # Try with current timestamp as version
        version = int(datetime.now().timestamp())
        url = f"{base_url}?version={version}"
        
        print(f"📥 Trying direct download: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            calendar_data = response.json()
            
            # Save to cache directory  
            cache_dir = os.path.join(os.path.dirname(__file__), "..", ".cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ff_calendar_{timestamp}.json"
            filepath = os.path.join(cache_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(calendar_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Downloaded {len(calendar_data)} events to {filename}")
            return filepath
        else:
            print(f"❌ Request failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Simple download failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Forex Factory Calendar Downloader")
    print("=====================================")
    
    # Try browser automation first
    result = download_forex_factory_calendar(headless=True)
    
    # If that fails, try simple request
    if not result:
        print("🔄 Trying simple request method...")
        result = download_simple_request()
    
    if result:
        print(f"🎉 Success! Calendar data saved to: {result}")
    else:
        print("💥 All download methods failed!")
        print("📝 You may need to manually download the calendar data from:")
        print("   https://www.forexfactory.com/calendar")
        print("   Look for 'weekly export' option and save as ff_calendar_YYYYMMDD_HHMMSS.json")