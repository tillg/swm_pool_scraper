#!/usr/bin/env python3
"""
Test the discovered Ticos API endpoints
"""

import requests
import json
from typing import Dict, List

# Organization IDs discovered from network traffic
ORGANIZATION_IDS = [
    30195, 30190, 30208, 30197, 30184, 30187, 
    30199, 30191, 30200, 30203, 30185, 30188, 30207
]

API_BASE = "https://counter.ticos-systems.cloud/api/gates/counter"


def test_api_endpoint(org_id: int) -> Dict:
    """Test a single organization unit endpoint"""
    url = f"{API_BASE}?organizationUnitIds={org_id}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.swm.de',
        'Referer': 'https://www.swm.de/',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"\n✅ Organization ID {org_id}:")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"   Error: {response.text[:200]}")
            return {}
            
    except Exception as e:
        print(f"\n❌ Organization ID {org_id}: {e}")
        return {}


def main():
    print("🔍 Testing Ticos API endpoints...")
    print("=" * 50)
    
    all_data = {}
    
    for org_id in ORGANIZATION_IDS[:3]:  # Test first 3 to avoid rate limiting
        data = test_api_endpoint(org_id)
        if data:
            all_data[org_id] = data
    
    print("\n" + "=" * 50)
    print("📊 Summary of API responses:")
    
    for org_id, data in all_data.items():
        print(f"\nOrg {org_id}:")
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"  - {key}: {value}")
        elif isinstance(data, list) and len(data) > 0:
            print(f"  - Found {len(data)} items")
            if isinstance(data[0], dict):
                print(f"  - First item keys: {list(data[0].keys())}")


if __name__ == "__main__":
    main()