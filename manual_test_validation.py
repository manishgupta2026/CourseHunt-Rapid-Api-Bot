#!/usr/bin/env python3
"""
Manual test of the validation logic to find the bug
"""

import requests
from urllib.parse import urlparse, parse_qs

def test_course_manually(url):
    """Test a single course manually with detailed API response"""
    print(f"🔍 Testing: {url}")
    
    # Parse URL
    parsed = urlparse(url)
    path_parts = parsed.path.split("/course/")
    if len(path_parts) < 2:
        print("❌ Invalid course path")
        return
        
    slug = path_parts[-1].strip("/")
    query_params = parse_qs(parsed.query)
    
    # Find coupon code
    coupon_code = ""
    for param_name in ['couponcode', 'coupon_code', 'coupon']:
        for key, value in query_params.items():
            if key.lower() == param_name:
                coupon_code = value[0] if isinstance(value, list) else value
                break
        if coupon_code:
            break
    
    print(f"📝 Course slug: {slug}")
    print(f"📝 Coupon code: {coupon_code}")
    
    if not coupon_code:
        print("❌ No coupon code found")
        return
    
    # Test different API endpoints and parameters
    test_apis = [
        # Original API call
        f"https://www.udemy.com/api-2.0/courses/{slug}/?fields[course]=is_paid,price,discounted_price,discount,has_discount&couponCode={coupon_code}",
        
        # Try without fields filter
        f"https://www.udemy.com/api-2.0/courses/{slug}/?couponCode={coupon_code}",
        
        # Try with different fields
        f"https://www.udemy.com/api-2.0/courses/{slug}/?fields[course]=price,discount&couponCode={coupon_code}",
        
        # Try course-taking endpoint (this might show the actual enrollment price)
        f"https://www.udemy.com/api-2.0/course-taking/{slug}/?couponCode={coupon_code}",
    ]
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for i, api_url in enumerate(test_apis, 1):
        print(f"\n🔍 API Test {i}:")
        print(f"URL: {api_url}")
        
        try:
            response = requests.get(api_url, timeout=15, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Print relevant fields
                relevant_fields = ['price', 'discount', 'discounted_price', 'is_paid', 'has_discount']
                print("Response data:")
                for field in relevant_fields:
                    if field in data:
                        print(f"  {field}: {data[field]}")
                
                # Check discount details
                if 'discount' in data and data['discount']:
                    discount = data['discount']
                    print("Discount details:")
                    for key, value in discount.items():
                        print(f"  discount.{key}: {value}")
                        
            elif response.status_code == 403:
                print("❌ 403 Forbidden - API access denied")
            elif response.status_code == 404:
                print("❌ 404 Not Found - Course or coupon not found")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

def test_direct_course_page(url):
    """Test by accessing the course page directly"""
    print(f"\n🌐 Testing course page directly...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Course page status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Look for price indicators in the HTML
            price_indicators = [
                'Free',
                '₹0',
                '$0',
                'price":0',
                'amount":0',
                'discount_percent":100',
                'enroll-now-free',
                'free-course'
            ]
            
            found_indicators = []
            for indicator in price_indicators:
                if indicator.lower() in content.lower():
                    found_indicators.append(indicator)
            
            if found_indicators:
                print(f"✅ Found free indicators: {found_indicators}")
            else:
                print("❌ No free indicators found in page")
                
            # Look for price in JSON data
            import re
            json_matches = re.findall(r'"price":\s*"([^"]*)"', content)
            if json_matches:
                print(f"📝 Found prices in page: {json_matches}")
                
        else:
            print(f"❌ Failed to load course page: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error loading course page: {e}")

def main():
    """Test the courses that should be free"""
    test_courses = [
        "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate?couponCode=852C10A383469BF3AFC",
        "https://www.udemy.com/course/graphics-design-video-editing-for-beginner-to-advanced?couponCode=73B3E1FC7A069BCC8129",
        "https://www.udemy.com/course/mindful-choices-in-a-complex-world-living-without-regret?couponCode=PRA_13DEC_TT"
    ]
    
    for i, url in enumerate(test_courses, 1):
        print("="*80)
        print(f"TESTING COURSE {i}")
        print("="*80)
        
        test_course_manually(url)
        test_direct_course_page(url)
        
        print("\n")

if __name__ == "__main__":
    main()