#!/usr/bin/env python3
"""
Test different approaches to access Udemy API
"""

import requests
import time
import random

def test_basic_udemy_access():
    """Test basic access to Udemy"""
    print("🔍 Testing basic Udemy access...")
    
    # Test different endpoints
    test_urls = [
        "https://www.udemy.com/",
        "https://www.udemy.com/api-2.0/courses/",
        "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate/",
    ]
    
    headers_variants = [
        # Basic headers
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        # More complete headers
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        },
        # API-specific headers
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    ]
    
    for i, url in enumerate(test_urls):
        print(f"\n📍 Testing URL {i+1}: {url}")
        
        for j, headers in enumerate(headers_variants):
            print(f"  Headers variant {j+1}:")
            try:
                response = requests.get(url, headers=headers, timeout=10)
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    ✅ Success! Content length: {len(response.content)}")
                elif response.status_code == 403:
                    print(f"    ❌ 403 Forbidden")
                elif response.status_code == 429:
                    print(f"    ⚠️ 429 Rate Limited")
                else:
                    print(f"    ⚠️ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
            
            # Small delay between requests
            time.sleep(1)

def test_with_session():
    """Test using a session with cookies"""
    print("\n🔍 Testing with session and cookies...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        # First, get the main page to establish session
        print("📍 Getting main page to establish session...")
        response = session.get("https://www.udemy.com/", timeout=10)
        print(f"Main page status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Session established. Cookies: {len(session.cookies)}")
            
            # Now try API call
            print("📍 Trying API call with session...")
            api_url = "https://www.udemy.com/api-2.0/courses/associate-professional-risk-manager-aprm-certificate/?fields[course]=price&couponCode=852C10A383469BF3AFC"
            
            api_response = session.get(api_url, timeout=10)
            print(f"API status: {api_response.status_code}")
            
            if api_response.status_code == 200:
                print("✅ API call successful!")
                data = api_response.json()
                print(f"Response: {data}")
            else:
                print(f"❌ API call failed: {api_response.status_code}")
        else:
            print(f"❌ Failed to establish session: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Session test error: {e}")

def test_alternative_validation():
    """Test alternative validation methods"""
    print("\n🔍 Testing alternative validation methods...")
    
    # Method 1: Check if course page loads with coupon
    test_url = "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate/?couponCode=852C10A383469BF3AFC"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print(f"📍 Testing course page access...")
        response = requests.get(test_url, headers=headers, timeout=15)
        print(f"Course page status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Look for free indicators
            free_indicators = [
                'enroll for free',
                'free course',
                '"price":"Free"',
                '"amount":0',
                'discount_percent":100'
            ]
            
            found = []
            for indicator in free_indicators:
                if indicator.lower() in content.lower():
                    found.append(indicator)
            
            if found:
                print(f"✅ Found free indicators: {found}")
                return True
            else:
                print("❌ No free indicators found")
                return False
        else:
            print(f"❌ Course page access failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Alternative validation error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Udemy access methods...\n")
    
    test_basic_udemy_access()
    test_with_session()
    is_free = test_alternative_validation()
    
    print(f"\n📊 Summary:")
    print(f"Alternative validation result: {'✅ FREE' if is_free else '❌ NOT FREE'}")

if __name__ == "__main__":
    main()