#!/usr/bin/env python3
"""
Check if coupon codes change over time or if there are multiple active codes
"""

import asyncio
import time
from multi_source_scraper import MultiSourceCouponScraper

async def test_validation_timing():
    """Test if validation results change over time"""
    
    print("🔍 Testing validation timing and consistency...")
    
    # Get fresh courses
    scraper_no_validation = MultiSourceCouponScraper(validate_coupons=False)
    scraper_with_validation = MultiSourceCouponScraper(validate_coupons=True)
    
    # Get a few courses
    print("📚 Getting fresh courses...")
    courses = await scraper_no_validation.scrape_all_sources()
    
    if not courses:
        print("❌ No courses found")
        return
    
    print(f"Found {len(courses)} courses")
    
    # Test first 5 courses with validation
    print("\n🔍 Testing validation on first 5 courses...")
    
    free_count = 0
    for i, course in enumerate(courses[:5]):
        print(f"\nCourse {i+1}: {course['title'][:50]}...")
        print(f"URL: {course['url']}")
        
        # Test validation
        is_free = scraper_with_validation.is_free_coupon(course['url'])
        print(f"Validation result: {'✅ FREE' if is_free else '❌ NOT FREE'}")
        
        if is_free:
            free_count += 1
    
    print(f"\n📊 Results: {free_count}/5 courses are truly free")
    
    # Now test the scraper with validation enabled
    print(f"\n🔍 Testing scraper with validation enabled...")
    validated_courses = await scraper_with_validation.scrape_all_sources()
    
    print(f"📊 Scraper with validation found: {len(validated_courses)} courses")
    
    if validated_courses:
        print("✅ Sample validated courses:")
        for i, course in enumerate(validated_courses[:3]):
            print(f"  {i+1}. {course['title'][:50]}...")
    else:
        print("❌ No courses passed validation")
    
    return len(validated_courses)

if __name__ == "__main__":
    asyncio.run(test_validation_timing())