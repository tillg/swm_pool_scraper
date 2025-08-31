#!/usr/bin/env python3
"""
Extract organization IDs and pool names from HTML
Look for data attributes, JavaScript variables, or other mappings
"""

import re
import json
import time
from typing import Dict, List, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """Setup Chrome driver"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def extract_mappings_from_html(driver: webdriver.Chrome) -> Dict[int, str]:
    """Extract org ID to name mappings from HTML"""
    
    print("🔍 Loading SWM website...")
    driver.get("https://www.swm.de/baeder/auslastung")
    time.sleep(5)  # Wait for dynamic content
    
    mappings = {}
    
    # Get page source
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    print("\n📝 Searching for org ID references in HTML...\n")
    
    # Method 1: Look for data attributes
    print("1. Checking data attributes...")
    elements_with_data = soup.find_all(attrs={"data-organization-id": True})
    for elem in elements_with_data:
        org_id = elem.get('data-organization-id')
        name = elem.get_text(strip=True)
        if org_id and name:
            mappings[int(org_id)] = name
            print(f"   Found: {org_id} -> {name}")
    
    elements_with_data = soup.find_all(attrs={"data-org-id": True})
    for elem in elements_with_data:
        org_id = elem.get('data-org-id')
        name = elem.get_text(strip=True)
        if org_id and name:
            mappings[int(org_id)] = name
            print(f"   Found: {org_id} -> {name}")
    
    # Method 2: Look in JavaScript variables
    print("\n2. Checking JavaScript variables...")
    scripts = soup.find_all('script')
    
    # Common patterns for JS objects/arrays containing mappings
    patterns = [
        r'organizationUnits?\s*[=:]\s*(\{[^}]+\})',
        r'facilities\s*[=:]\s*(\[[^\]]+\])',
        r'poolData\s*[=:]\s*(\{[^}]+\})',
        r'var\s+(\w+)\s*=\s*\{[^}]*["\']30\d{3}["\'][^}]*\}',
    ]
    
    for script in scripts:
        if script.string:
            for pattern in patterns:
                matches = re.findall(pattern, script.string, re.DOTALL)
                for match in matches:
                    # Try to find org IDs and names in the match
                    id_matches = re.findall(r'["\']?(\d{5})["\']?\s*:\s*["\']([^"\']+)["\']', match)
                    for org_id, name in id_matches:
                        if org_id.startswith('30'):
                            mappings[int(org_id)] = name
                            print(f"   Found in JS: {org_id} -> {name}")
    
    # Method 3: Look for API calls in inline scripts
    print("\n3. Checking for API configuration...")
    
    # Search for patterns like: loadOccupancy(30195, "Bad Giesing")
    func_patterns = [
        r'loadOccupancy\((\d+),\s*["\']([^"\']+)["\']',
        r'fetchData\((\d+),\s*["\']([^"\']+)["\']',
        r'getCapacity\((\d+),\s*["\']([^"\']+)["\']',
    ]
    
    for script in scripts:
        if script.string:
            for pattern in func_patterns:
                matches = re.findall(pattern, script.string)
                for org_id, name in matches:
                    if org_id.startswith('30'):
                        mappings[int(org_id)] = name
                        print(f"   Found in function call: {org_id} -> {name}")
    
    # Method 4: Check for configuration objects
    print("\n4. Checking window object for configuration...")
    
    # Execute JavaScript to search window object
    js_code = """
    const results = {};
    
    // Search for objects containing org IDs
    for (let key in window) {
        try {
            const val = window[key];
            if (typeof val === 'object' && val !== null) {
                const str = JSON.stringify(val);
                // Look for our known org IDs
                if (str.includes('30195') || str.includes('30190')) {
                    results[key] = str.substring(0, 500);
                }
            }
        } catch(e) {}
    }
    
    // Also check for specific config patterns
    if (window.config) results.config = JSON.stringify(window.config);
    if (window.facilities) results.facilities = JSON.stringify(window.facilities);
    if (window.pools) results.pools = JSON.stringify(window.pools);
    if (window.APP_CONFIG) results.APP_CONFIG = JSON.stringify(window.APP_CONFIG);
    
    return results;
    """
    
    window_data = driver.execute_script(js_code)
    for key, value in window_data.items():
        print(f"   Found window.{key}: {value[:100]}...")
        
        # Try to extract mappings from the JSON strings
        id_name_patterns = [
            r'"(\d{5})"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
            r'\{"id"\s*:\s*(\d{5})[^}]*"name"\s*:\s*"([^"]+)"',
            r'"organizationUnitId"\s*:\s*(\d{5})[^}]*"name"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in id_name_patterns:
            matches = re.findall(pattern, value)
            for org_id, name in matches:
                if org_id.startswith('30'):
                    mappings[int(org_id)] = name
                    print(f"      Extracted: {org_id} -> {name}")
    
    # Method 5: Look at the actual pool cards/sections
    print("\n5. Analyzing pool display elements...")
    
    # Find pool containers
    pool_sections = soup.find_all(['div', 'section', 'article'], class_=re.compile('pool|bad|facility|occupancy', re.I))
    
    for section in pool_sections:
        # Look for pool name
        name_elem = section.find(['h2', 'h3', 'h4', 'span'], string=re.compile('Bad|bad|Sauna'))
        if name_elem:
            pool_name = name_elem.get_text(strip=True)
            
            # Check if there's a nearby element with org ID
            parent = section
            for _ in range(3):  # Check up to 3 parent levels
                if parent:
                    # Check all attributes for org IDs
                    for attr, value in parent.attrs.items():
                        if '30' in str(value) and re.search(r'30\d{3}', str(value)):
                            org_id_match = re.search(r'(30\d{3})', str(value))
                            if org_id_match:
                                org_id = int(org_id_match.group(1))
                                mappings[org_id] = pool_name
                                print(f"   Found in element: {org_id} -> {pool_name}")
                    parent = parent.parent
    
    # Method 6: Intercept the actual API calls and match with displayed names
    print("\n6. Matching API calls with displayed names...")
    
    # Get all displayed pool names
    displayed_pools = []
    
    # Look for pool names in specific patterns
    pool_name_patterns = [
        r'(Bad Giesing-Harlaching|Cosimawellenbad|Michaelibad|Nordbad|Südbad|Westbad|Müller[\'\']sches Volksbad|Dantebad)',
    ]
    
    full_text = soup.get_text()
    for pattern in pool_name_patterns:
        matches = re.findall(pattern, full_text)
        displayed_pools.extend(matches)
    
    displayed_pools = list(set(displayed_pools))
    print(f"   Found {len(displayed_pools)} pool names in text: {displayed_pools}")
    
    # Now intercept API calls to get org IDs
    print("\n7. Intercepting API calls to match with names...")
    
    # Inject network interceptor
    driver.execute_script("""
    window.interceptedAPICalls = [];
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const url = args[0];
        if (url.includes('organizationUnitIds')) {
            const match = url.match(/organizationUnitIds=(\d+)/);
            if (match) {
                window.interceptedAPICalls.push(match[1]);
            }
        }
        return originalFetch.apply(this, args);
    };
    """)
    
    # Reload to trigger API calls
    driver.refresh()
    time.sleep(5)
    
    # Get intercepted org IDs
    intercepted_ids = driver.execute_script("return window.interceptedAPICalls || []")
    print(f"   Intercepted org IDs: {intercepted_ids}")
    
    # Try to match based on order (this is a heuristic)
    if len(intercepted_ids) >= len(displayed_pools):
        for i, pool_name in enumerate(displayed_pools):
            if i < len(intercepted_ids):
                org_id = int(intercepted_ids[i])
                if org_id not in mappings:
                    mappings[org_id] = pool_name
                    print(f"   Matched by position: {org_id} -> {pool_name}")
    
    return mappings


def main():
    """Main function to extract and display mappings"""
    driver = setup_driver(headless=False)
    
    try:
        mappings = extract_mappings_from_html(driver)
        
        print("\n" + "="*50)
        print("📊 EXTRACTED MAPPINGS:")
        print("="*50)
        
        if mappings:
            for org_id, name in sorted(mappings.items()):
                print(f"  {org_id}: {name}")
            
            # Save to file
            output = {
                "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mappings": [
                    {"org_id": org_id, "name": name}
                    for org_id, name in sorted(mappings.items())
                ]
            }
            
            with open("extracted_mappings.json", "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Saved {len(mappings)} mappings to extracted_mappings.json")
        else:
            print("❌ No mappings found. The org IDs might not be directly embedded in the HTML.")
            print("\nThis means:")
            print("1. The mapping is done server-side")
            print("2. We need to maintain our own mapping file")
            print("3. Or reverse-engineer by matching API call order with display order")
    
    finally:
        input("\nPress Enter to close browser...")
        driver.quit()


if __name__ == "__main__":
    main()