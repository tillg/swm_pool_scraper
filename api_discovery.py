#!/usr/bin/env python3
"""
API Discovery Tool for SWM Website
Intercepts network traffic to find API endpoints
"""

import json
import time
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager
import requests


def setup_driver_with_logging() -> webdriver.Chrome:
    """Setup Chrome with network logging enabled"""
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL", "browser": "ALL"})
    
    # Enable network logging
    caps = DesiredCapabilities.CHROME
    caps["goog:loggingPrefs"] = {"performance": "ALL"}
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def extract_network_calls(driver: webdriver.Chrome) -> List[Dict[str, Any]]:
    """Extract all network calls from browser logs"""
    logs = driver.get_log("performance")
    network_calls = []
    
    for entry in logs:
        log = json.loads(entry["message"])["message"]
        
        # Filter for network events
        if "Network.response" in log.get("method", "") or "Network.requestWillBeSent" in log.get("method", ""):
            params = log.get("params", {})
            
            # Extract request details
            if "request" in params:
                request = params["request"]
                url = request.get("url", "")
                method = request.get("method", "")
                
                # Filter out static resources
                if any(ext in url for ext in [".css", ".js", ".png", ".jpg", ".gif", ".ico", ".woff", ".ttf"]):
                    continue
                    
                # Look for API patterns
                if any(pattern in url for pattern in ["api", "ajax", "json", "data", "service", "rest"]):
                    network_calls.append({
                        "url": url,
                        "method": method,
                        "headers": request.get("headers", {}),
                        "postData": request.get("postData", None)
                    })
                    
            # Extract response details
            elif "response" in params:
                response = params["response"]
                url = response.get("url", "")
                
                # Check for JSON responses
                mime_type = response.get("mimeType", "")
                if "json" in mime_type or "api" in url:
                    network_calls.append({
                        "url": url,
                        "status": response.get("status"),
                        "mimeType": mime_type,
                        "type": "response"
                    })
    
    return network_calls


def intercept_fetch_calls(driver: webdriver.Chrome) -> List[str]:
    """Inject JavaScript to intercept fetch/XHR calls"""
    
    # Inject fetch interceptor
    fetch_interceptor = """
    // Store original fetch
    const originalFetch = window.fetch;
    window.interceptedCalls = [];
    
    // Override fetch
    window.fetch = function(...args) {
        console.log('FETCH INTERCEPTED:', args[0]);
        window.interceptedCalls.push({
            type: 'fetch',
            url: args[0],
            options: args[1] || {},
            timestamp: new Date().toISOString()
        });
        return originalFetch.apply(this, args);
    };
    
    // Intercept XMLHttpRequest
    const originalXHR = window.XMLHttpRequest.prototype.open;
    window.XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        console.log('XHR INTERCEPTED:', method, url);
        window.interceptedCalls.push({
            type: 'xhr',
            method: method,
            url: url,
            timestamp: new Date().toISOString()
        });
        return originalXHR.apply(this, [method, url, ...rest]);
    };
    
    return 'Interceptors installed';
    """
    
    driver.execute_script(fetch_interceptor)
    return []


def analyze_javascript_sources(driver: webdriver.Chrome) -> List[str]:
    """Scan JavaScript source for API endpoints"""
    
    # Extract all script sources
    scripts = driver.find_elements("tag name", "script")
    api_patterns = []
    
    for script in scripts:
        src = script.get_attribute("src")
        if src:
            try:
                # Fetch and analyze external scripts
                if src.startswith("http"):
                    response = requests.get(src, timeout=5)
                    content = response.text
                else:
                    # Relative URL
                    base_url = driver.current_url.split('/')[0:3]
                    full_url = "/".join(base_url) + "/" + src.lstrip("/")
                    response = requests.get(full_url, timeout=5)
                    content = response.text
                
                # Look for API patterns in JavaScript
                import re
                
                # Common API endpoint patterns
                patterns = [
                    r'["\']/(api/[^"\']*)["\']',
                    r'["\']https?://[^"\']*/(api/[^"\']*)["\']',
                    r'endpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'url["\']?\s*[:=]\s*["\']([^"\']+\.json)["\']',
                    r'fetch\(["\']([^"\']+)["\']',
                    r'\.get\(["\']([^"\']+)["\']',
                    r'\.post\(["\']([^"\']+)["\']',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    api_patterns.extend(matches)
                    
            except Exception as e:
                continue
    
    # Also check inline scripts
    inline_scripts = driver.execute_script("return document.documentElement.innerHTML")
    for pattern in patterns:
        matches = re.findall(pattern, inline_scripts)
        api_patterns.extend(matches)
    
    return list(set(api_patterns))


def discover_websocket_connections(driver: webdriver.Chrome) -> List[str]:
    """Check for WebSocket connections"""
    
    ws_check = """
    const sockets = [];
    // Check if any WebSocket connections exist
    if (window.WebSocket) {
        // Override WebSocket constructor to track connections
        const OriginalWebSocket = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            console.log('WebSocket connection:', url);
            sockets.push(url);
            return new OriginalWebSocket(url, protocols);
        };
    }
    return sockets;
    """
    
    return driver.execute_script(ws_check)


def test_swm_api_discovery():
    """Main discovery function for SWM website"""
    print("🔍 Starting API Discovery for SWM Website...")
    
    driver = setup_driver_with_logging()
    
    try:
        # Load page with network monitoring
        print("\n1. Loading page and monitoring network traffic...")
        driver.get("https://www.swm.de/baeder/auslastung")
        
        # Inject interceptors before page fully loads
        print("\n2. Installing JavaScript interceptors...")
        intercept_fetch_calls(driver)
        
        # Wait for dynamic content
        time.sleep(10)
        
        # Get intercepted calls
        intercepted = driver.execute_script("return window.interceptedCalls || []")
        print(f"\n3. Intercepted {len(intercepted)} API calls:")
        for call in intercepted:
            print(f"   - {call.get('type', 'unknown').upper()}: {call.get('url', 'unknown')}")
        
        # Extract network logs
        print("\n4. Analyzing network logs...")
        network_calls = extract_network_calls(driver)
        for call in network_calls:
            if call.get("url"):
                print(f"   - {call.get('method', 'GET')}: {call['url'][:100]}")
        
        # Analyze JavaScript sources
        print("\n5. Scanning JavaScript for API endpoints...")
        js_apis = analyze_javascript_sources(driver)
        for api in js_apis[:10]:  # Limit output
            print(f"   - Found pattern: {api}")
        
        # Check for WebSockets
        print("\n6. Checking for WebSocket connections...")
        ws_connections = discover_websocket_connections(driver)
        if ws_connections:
            for ws in ws_connections:
                print(f"   - WebSocket: {ws}")
        
        # Check localStorage/sessionStorage for API tokens or endpoints
        print("\n7. Checking browser storage...")
        local_storage = driver.execute_script("return Object.entries(localStorage)")
        session_storage = driver.execute_script("return Object.entries(sessionStorage)")
        
        for key, value in local_storage:
            if any(term in key.lower() for term in ["api", "token", "endpoint", "url"]):
                print(f"   - localStorage[{key}]: {value[:50]}...")
        
        for key, value in session_storage:
            if any(term in key.lower() for term in ["api", "token", "endpoint", "url"]):
                print(f"   - sessionStorage[{key}]: {value[:50]}...")
        
        # Try to find data in window object
        print("\n8. Checking window object for data...")
        window_check = """
        const results = [];
        for (let key in window) {
            if (key.toLowerCase().includes('data') || 
                key.toLowerCase().includes('api') ||
                key.toLowerCase().includes('pool')) {
                try {
                    const val = window[key];
                    if (typeof val === 'object' && val !== null) {
                        results.push({key: key, sample: JSON.stringify(val).substring(0, 100)});
                    }
                } catch(e) {}
            }
        }
        return results;
        """
        window_data = driver.execute_script(window_check)
        for item in window_data[:5]:
            print(f"   - window.{item['key']}: {item['sample']}...")
        
        # Check for GraphQL
        print("\n9. Checking for GraphQL endpoints...")
        graphql_check = driver.execute_script("""
            return document.documentElement.innerHTML.includes('graphql') || 
                   document.documentElement.innerHTML.includes('__APOLLO__');
        """)
        if graphql_check:
            print("   - Possible GraphQL endpoint detected!")
        
        print("\n✅ Discovery complete! Check the output above for potential APIs.")
        
    finally:
        input("\nPress Enter to close browser...")
        driver.quit()


if __name__ == "__main__":
    test_swm_api_discovery()