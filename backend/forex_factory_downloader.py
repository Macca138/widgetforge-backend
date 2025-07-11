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

def download_with_direct_scraping():
    """Download using direct HTML scraping without browser automation"""
    try:
        print("📅 Fetching Forex Factory calendar page...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Get the main calendar page
        response = requests.get("https://www.forexfactory.com/calendar", headers=headers, timeout=15)
        response.raise_for_status()
        
        print("🔍 Searching for JSON export link on calendar page...")
        page_content = response.text
        
        # Look for links that contain "json" text or have json-related hrefs
        json_link_patterns = [
            r'<a[^>]*href=["\']([^"\']*ff_calendar_thisweek\.json[^"\']*)["\'][^>]*>.*?json.*?</a>',  # Link with href containing json file and text "json"
            r'<a[^>]*href=["\']([^"\']*ff_calendar_thisweek\.json[^"\']*)["\']',  # Any link to the json file
            r'href=["\']([^"\']*nfs\.faireconomy\.media/ff_calendar_thisweek\.json[^"\']*)["\']',  # Direct href to the domain
        ]
        
        json_url = None
        for pattern in json_link_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE | re.DOTALL)
            if matches:
                # Get the first match and ensure it's a full URL
                href = matches[0]
                if href.startswith('http'):
                    json_url = href
                elif href.startswith('//'):
                    json_url = 'https:' + href
                elif href.startswith('/'):
                    json_url = 'https://www.forexfactory.com' + href
                else:
                    json_url = 'https://nfs.faireconomy.media/' + href
                
                print(f"✅ Found JSON export link: {json_url}")
                
                # Test if the URL works
                try:
                    test_response = requests.head(json_url, headers=headers, timeout=10)
                    if test_response.status_code == 200:
                        print(f"✅ Confirmed JSON URL is accessible")
                        break
                    else:
                        print(f"⚠️  JSON URL found but not accessible (status {test_response.status_code}), trying next pattern...")
                        json_url = None
                except:
                    print(f"⚠️  Could not test JSON URL accessibility, trying next pattern...")
                    json_url = None
        
        if not json_url:
            print("⚠️  No valid JSON URL found in page source, using fallback...")
            json_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json?version=e21710366e7e3dd646b0025695e9ed82"
        
        # Download the JSON data
        print(f"📥 Downloading calendar data from: {json_url}")
        
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
        print(f"❌ Error with direct scraping: {e}")
        return None

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
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "calendar"))
        )
        
        # Look for the weekly export URL in page source or JavaScript
        print("🔍 Searching for weekly export URL...")
        
        # Try to find JSON data in page source
        page_source = driver.page_source
        
        # Look for calendar data or export URLs (updated for current domain)
        patterns = [
            r'https://nfs\.faireconomy\.media/ff_calendar_thisweek\.json\?version=([a-f0-9]+)',
            r'nfs\.faireconomy\.media/ff_calendar_thisweek\.json\?version=([a-f0-9]+)',
            r'ff_calendar_thisweek\.json\?version=([a-f0-9]+)'
        ]
        
        json_url = None
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                version = matches[0]
                json_url = f"https://nfs.faireconomy.media/ff_calendar_thisweek.json?version={version}"
                print(f"✅ Found JSON URL with version {version}")
                break
        
        if not json_url:
            print("⚠️  No specific version found, trying current URL you provided...")
            json_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json?version=e21710366e7e3dd646b0025695e9ed82"
        
        # Close browser
        driver.quit()
        driver = None
        
        if not json_url:
            print("❌ Could not find any working JSON URL")
            return None
        
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
        # Try the simple URL first (no version parameter)
        urls_to_try = [
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",  # Simple URL without version
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json?version=e21710366e7e3dd646b0025695e9ed82"  # Fallback with version
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.forexfactory.com/'
        }
        
        for url in urls_to_try:
            print(f"📥 Trying direct download: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                break
        else:
            print("❌ All direct download URLs failed")
            return None
        
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

def download_simple_no_version():
    """Try the simplest method first - direct URL without version"""
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.forexfactory.com/'
        }
        
        print(f"📥 Trying simple URL (no version): {url}")
        response = requests.get(url, headers=headers, timeout=10)
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
        print(f"❌ Simple URL failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Forex Factory Calendar Downloader")
    print("=====================================")
    
    # Try the simplest method first - no version parameter needed!
    result = download_simple_no_version()
    
    # If that fails, try direct scraping for versioned URL
    if not result:
        print("🔄 Trying direct page scraping...")
        result = download_with_direct_scraping()
    
    # If that fails, try browser automation
    if not result:
        print("🔄 Trying browser automation method...")
        result = download_forex_factory_calendar(headless=True)
    
    # If that fails, try simple request with hardcoded URL
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