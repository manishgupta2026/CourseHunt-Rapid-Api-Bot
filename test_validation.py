#!/usr/bin/env python3
"""
Test coupon validation manually
"""

from multi_source_scraper import MultiSourceCouponScraper

def test_validation():
    scraper = MultiSourceCouponScraper(validate_coupons=True)
    
    # Test with a sample URL from the results
    test_url = "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate?couponCode=852C10A383469BF3AFC"
    
    print(f"Testing validation for:")
    print(f"URL: {test_url}")
    print()
    
    # Test cleanup
    clean_url = scraper.cleanup_link(test_url)
    print(f"Cleaned URL: {clean_url}")
    print()
    
    # Test validation
    is_free = scraper.is_free_coupon(test_url)
    print(f"Is 100% free: {is_free}")
    
    return is_free

if __name__ == "__main__":
    test_validation()