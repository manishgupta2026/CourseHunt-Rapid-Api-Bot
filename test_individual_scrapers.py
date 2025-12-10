#!/usr/bin/env python3
"""
Test each scraper individually to check if they're working
"""

import asyncio
import time
from multi_source_scraper import MultiSourceCouponScraper

async def test_real_discount():
    """Test Real.discount scraper specifically"""
    print("🔍 Testing Real.discount scraper...")
    scraper = MultiSourceCouponScraper(validate_coupons=False)
    
    try:
        courses = scraper.scrape_real_discount()
        print(f"✅ Real.discount: Found {len(courses)} courses")
        
        if courses:
            print("📋 Sample courses:")
            for i, course in enumerate(courses[:3]):
                print(f"  {i+1}. {course['title'][:60]}...")
                print(f"     URL: {course['url']}")
        else:
            print("❌ No courses found from Real.discount")
            
        return courses
    except Exception as e:
        print(f"❌ Real.discount error: {e}")
        return []

async def test_discudemy():
    """Test Discudemy scraper specifically"""
    print("\n🔍 Testing Discudemy scraper...")
    scraper = MultiSourceCouponScraper(validate_coupons=False)
    
    try:
        courses = scraper.scrape_discudemy()
        print(f"✅ Discudemy: Found {len(courses)} courses")
        
        if courses:
            print("📋 Sample courses:")
            for i, course in enumerate(courses[:3]):
                print(f"  {i+1}. {course['title'][:60]}...")
                print(f"     URL: {course['url']}")
        else:
            print("❌ No courses found from Discudemy")
            
        return courses
    except Exception as e:
        print(f"❌ Discudemy error: {e}")
        return []

async def test_course_vania():
    """Test CourseVania scraper specifically"""
    print("\n🔍 Testing CourseVania scraper...")
    scraper = MultiSourceCouponScraper(validate_coupons=False)
    
    try:
        courses = scraper.scrape_course_vania()
        print(f"✅ CourseVania: Found {len(courses)} courses")
        
        if courses:
            print("📋 Sample courses:")
            for i, course in enumerate(courses[:3]):
                print(f"  {i+1}. {course['title'][:60]}...")
                print(f"     URL: {course['url']}")
        else:
            print("❌ No courses found from CourseVania")
            
        return courses
    except Exception as e:
        print(f"❌ CourseVania error: {e}")
        return []

async def test_udemy_freebies():
    """Test UdemyFreebies scraper specifically"""
    print("\n🔍 Testing UdemyFreebies scraper...")
    scraper = MultiSourceCouponScraper(validate_coupons=False)
    
    try:
        courses = scraper.scrape_udemy_freebies()
        print(f"✅ UdemyFreebies: Found {len(courses)} courses")
        
        if courses:
            print("📋 Sample courses:")
            for i, course in enumerate(courses[:3]):
                print(f"  {i+1}. {course['title'][:60]}...")
                print(f"     URL: {course['url']}")
        else:
            print("❌ No courses found from UdemyFreebies")
            
        return courses
    except Exception as e:
        print(f"❌ UdemyFreebies error: {e}")
        return []

async def test_real_discount_api_directly():
    """Test Real.discount API directly to see raw response"""
    print("\n🔍 Testing Real.discount API directly...")
    
    import requests
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Host": "cdn.real.discount",
            "Connection": "Keep-Alive",
            "Referer": "https://www.real.discount/",
        }
        
        url = "https://cdn.real.discount/api/courses?page=1&limit=10&sortBy=sale_start&store=Udemy&freeOnly=true"
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"Raw API response: {len(items)} items found")
            
            if items:
                print("📋 Raw API sample:")
                for i, item in enumerate(items[:3]):
                    print(f"  {i+1}. {item.get('name', 'No title')}")
                    print(f"     Store: {item.get('store', 'Unknown')}")
                    print(f"     URL: {item.get('url', 'No URL')}")
            else:
                print("❌ No items in API response")
                print(f"Full response: {data}")
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Direct API test error: {e}")

async def main():
    """Run all individual scraper tests"""
    print("🚀 Testing individual scrapers...\n")
    
    # Test Real.discount API directly first
    await test_real_discount_api_directly()
    
    # Test each scraper
    real_courses = await test_real_discount()
    discudemy_courses = await test_discudemy()
    coursevania_courses = await test_course_vania()
    freebies_courses = await test_udemy_freebies()
    
    # Summary
    total = len(real_courses) + len(discudemy_courses) + len(coursevania_courses) + len(freebies_courses)
    
    print(f"\n📊 Summary:")
    print(f"   Real.discount: {len(real_courses)} courses")
    print(f"   Discudemy: {len(discudemy_courses)} courses")
    print(f"   CourseVania: {len(coursevania_courses)} courses")
    print(f"   UdemyFreebies: {len(freebies_courses)} courses")
    print(f"   Total: {total} courses")
    
    if total == 0:
        print("\n❌ No courses found from any source - investigating...")
    else:
        print(f"\n✅ Found courses from {sum(1 for x in [real_courses, discudemy_courses, coursevania_courses, freebies_courses] if x)} sources")

if __name__ == "__main__":
    asyncio.run(main())