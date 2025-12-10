#!/usr/bin/env python3
"""
Test the enhanced validation system with multiple bypass methods
"""

import asyncio
from multi_source_scraper import MultiSourceCouponScraper

async def test_enhanced_validation():
    """Test the enhanced validation system"""
    print("🚀 Testing enhanced validation system...")
    
    # Test courses that should be free
    test_courses = [
        "https://www.udemy.com/course/associate-professional-risk-manager-aprm-certificate?couponCode=852C10A383469BF3AFC",
        "https://www.udemy.com/course/graphics-design-video-editing-for-beginner-to-advanced?couponCode=73B3E1FC7A069BCC8129",
        "https://www.udemy.com/course/mindful-choices-in-a-complex-world-living-without-regret?couponCode=PRA_13DEC_TT"
    ]
    
    scraper = MultiSourceCouponScraper(validate_coupons=True)
    
    print(f"🔍 Testing {len(test_courses)} courses with enhanced validation...")
    
    free_count = 0
    for i, url in enumerate(test_courses, 1):
        print(f"\nCourse {i}: {url.split('/')[-1].split('?')[0]}")
        
        is_free = scraper.is_free_coupon(url)
        
        if is_free:
            print(f"  ✅ VALIDATED as FREE")
            free_count += 1
        else:
            print(f"  ❌ NOT validated as free")
    
    print(f"\n📊 Results: {free_count}/{len(test_courses)} courses validated as free")
    
    # Test with full scraper
    print(f"\n🔍 Testing full scraper with enhanced validation...")
    courses = await scraper.scrape_all_sources()
    
    print(f"📊 Enhanced scraper found: {len(courses)} validated courses")
    
    if courses:
        print("✅ Sample validated courses:")
        for i, course in enumerate(courses[:5]):
            print(f"  {i+1}. {course['title'][:50]}...")
    
    return len(courses)

if __name__ == "__main__":
    asyncio.run(test_enhanced_validation())