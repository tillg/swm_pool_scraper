#!/usr/bin/env python3
"""
Test runner script for SWM Pool Scraper
Provides convenient access to run different test suites
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n🧪 {description}")
    print("=" * 50)
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")
        
    return result.returncode == 0


def main():
    """Main test runner"""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [all|models|api|storage|quick]")
        print("")
        print("Options:")
        print("  all     - Run complete test suite")
        print("  models  - Run only model tests")
        print("  api     - Run only API scraper tests")  
        print("  storage - Run only data storage tests")
        print("  quick   - Run fast tests only (excludes selenium)")
        sys.exit(1)
    
    test_type = sys.argv[1].lower()
    
    # Ensure we're in virtual environment
    activate_cmd = "source .venv/bin/activate"
    
    commands = {
        'models': (f"{activate_cmd} && python -m pytest tests/test_models.py -v", 
                  "Model Tests"),
        'api': (f"{activate_cmd} && python -m pytest tests/test_api_scraper.py -v", 
               "API Scraper Tests"),
        'storage': (f"{activate_cmd} && python -m pytest tests/test_data_storage.py -v", 
                   "Data Storage Tests"),
        'all': (f"{activate_cmd} && python -m pytest tests/ -v", 
               "Complete Test Suite"),
        'quick': (f"{activate_cmd} && python -m pytest tests/ -v -m 'not selenium'", 
                 "Quick Test Suite")
    }
    
    if test_type not in commands:
        print(f"Unknown test type: {test_type}")
        sys.exit(1)
    
    cmd, description = commands[test_type]
    success = run_command(cmd, description)
    
    if success:
        print(f"\n🎉 All {description.lower()} passed!")
    else:
        print(f"\n💥 Some {description.lower()} failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()