#!/usr/bin/env python3
"""
Debug the validation logic to find why it's rejecting free courses
"""

from multi_source_scraper import MultiSourceCouponScraper
import requests
from urllib.parse import urlparse, parse_qs

def debug_validation_logic():
    """Debug why validation is failing for free courses"""
    
    # Test with a course we know is 100% free
    test_url = "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate?couponCode=852C10A383469BF3AFC"
    
    print("🔍 Debugging validation logic...")
    print(f"Test URL: {test_url}")
    
    # Create scraper with validation enabled
    scraper = MultiSourceCouponScraper(validate_coupons=True)
    
    # Test the validation step by step
    print("\n1. Testing cleanup_link()...")
    clean_url = scraper.cleanup_link(test_url)
    print(f"   Clean URL: {clean_url}")
    
    print("\n2. Testing is_free_coupon() with debug...")
    
    # Extract course details manually
    parsed = urlparse(clean_url)
    path_parts = parsed.path.split("/course/")
    slug = path_parts[-1].strip("/")
    query_params = parse_qs(parsed.query)
    
    coupon_code = ""
    for param_name in ['couponcode', 'coupon_code', 'coupon']:
        for key, value in query_params.items():
            if key.lower() == param_name:
                coupon_code = value[0] if isinstance(value, list) else value
                break
        if coupon_code:
            break
    
    print(f"   Course slug: {slug}")
    print(f"   Coupon code: {coupon_code}")
    
    # Test API call manually
    api_url = (
        f"https://www.udemy.com/api-2.0/courses/{slug}/"
        f"?fields[course]=is_paid,price,discounted_price,discount,has_discount&couponCode={coupon_code}"
    )
    
    print(f"\n3. Testing API call...")
    print(f"   API URL: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=15, headers={'Accept': 'application/json'})
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Raw response: {data}")
            
            # Test validation logic step by step
            discount = data.get("discount", {})
            discount_percent = discount.get("discount_percent", 0)
            discount_amount = discount.get("price", {}).get("amount") if discount else None
            price = data.get("price", "")
            
            print(f"\n4. Validation criteria:")
            print(f"   discount_percent: {discount_percent}")
            print(f"   discount_amount: {discount_amount}")
            print(f"   price: {price}")
            
            # Test each condition
            condition1 = discount_percent == 100
            condition2 = discount_amount is not None and discount_amount == 0
            condition3 = isinstance(price, str) and price.startswith("Free")
            
            print(f"\n5. Condition checks:")
            print(f"   discount_percent == 100: {condition1}")
            print(f"   discount_amount == 0: {condition2}")
            print(f"   price starts with 'Free': {condition3}")
            
            is_free = condition1 or condition2 or condition3
            print(f"\n6. Final result: {is_free}")
            
            # Now test the actual method
            print(f"\n7. Testing actual is_free_coupon() method...")
            method_result = scraper.is_free_coupon(test_url)
            print(f"   Method result: {method_result}")
            
            if is_free != method_result:
                print(f"   ❌ MISMATCH! Manual: {is_free}, Method: {method_result}")
            else:
                print(f"   ✅ Match! Both return: {is_free}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    debug_validation_logic()