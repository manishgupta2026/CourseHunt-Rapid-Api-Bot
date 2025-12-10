#!/usr/bin/env python3
"""
Test validation on specific courses to see why they're being filtered
"""

from multi_source_scraper import MultiSourceCouponScraper
import requests

def test_specific_courses():
    """Test validation on specific courses"""
    scraper = MultiSourceCouponScraper(validate_coupons=True)
    
    # Test courses from our scraping results
    test_courses = [
        "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate?couponCode=852C10A383469BF3AFC",
        "https://www.udemy.com/course/graphics-design-video-editing-for-beginner-to-advanced?couponCode=73B3E1FC7A069BCC8129",
        "https://www.udemy.com/course/web-development-beginners-to-advanced?couponCode=93E6FA12D84A2B0F244F"
    ]
    
    print("🔍 Testing specific course validations...\n")
    
    for i, url in enumerate(test_courses, 1):
        print(f"Course {i}:")
        print(f"URL: {url}")
        
        # Test cleanup
        clean_url = scraper.cleanup_link(url)
        print(f"Clean URL: {clean_url}")
        
        # Test validation with detailed logging
        is_free = scraper.is_free_coupon(url)
        print(f"Is 100% free: {is_free}")
        print("-" * 80)

def test_udemy_api_directly():
    """Test Udemy API directly to see what we get"""
    print("\n🔍 Testing Udemy API directly...")
    
    # Extract course slug and coupon from a test URL
    test_url = "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate?couponCode=852C10A383469BF3AFC"
    slug = "associate-professional-risk-manager-aprm-certificate"
    coupon = "852C10A383469BF3AFC"
    
    api_url = f"https://www.udemy.com/api-2.0/courses/{slug}/?fields[course]=is_paid,price,discounted_price,discount,has_discount&couponCode={coupon}"
    
    print(f"API URL: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=15, headers={'Accept': 'application/json'})
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Raw API Response:")
            print(f"  is_paid: {data.get('is_paid')}")
            print(f"  price: {data.get('price')}")
            print(f"  discounted_price: {data.get('discounted_price')}")
            print(f"  discount: {data.get('discount')}")
            print(f"  has_discount: {data.get('has_discount')}")
            
            # Check discount details
            discount = data.get("discount", {})
            if discount:
                print(f"  discount.discount_percent: {discount.get('discount_percent')}")
                print(f"  discount.price: {discount.get('price')}")
        else:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    test_specific_courses()
    test_udemy_api_directly()