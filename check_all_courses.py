#!/usr/bin/env python3
"""
Check all courses found by scrapers and their validation status
"""

import asyncio
import requests
from urllib.parse import urlparse, parse_qs
from multi_source_scraper import MultiSourceCouponScraper

async def analyze_all_courses():
    """Get all courses and analyze their validation status"""
    print("🔍 Fetching all courses from scrapers...")
    
    # Get courses without validation first
    scraper = MultiSourceCouponScraper(validate_coupons=False)
    all_courses = await scraper.scrape_all_sources()
    
    print(f"📚 Found {len(all_courses)} total courses")
    print("🔍 Analyzing validation status for each course...\n")
    
    # Track statistics
    stats = {
        'total': len(all_courses),
        'validated_free': 0,
        'partial_discount': 0,
        'validation_failed': 0,
        'no_coupon': 0,
        'discount_ranges': {
            '100%': 0,
            '90-99%': 0,
            '80-89%': 0,
            '70-79%': 0,
            '60-69%': 0,
            '50-59%': 0,
            '<50%': 0,
            'unknown': 0
        }
    }
    
    # Sample courses for detailed analysis
    sample_courses = []
    
    for i, course in enumerate(all_courses):
        print(f"Course {i+1}/{len(all_courses)}: {course['title'][:50]}...")
        
        # Extract course info
        url = course['url']
        parsed = urlparse(url)
        path_parts = parsed.path.split("/course/")
        
        if len(path_parts) < 2:
            print("  ❌ Invalid course path")
            stats['validation_failed'] += 1
            continue
            
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
        
        if not coupon_code:
            print("  ❌ No coupon code found")
            stats['no_coupon'] += 1
            continue
        
        # Test Udemy API
        try:
            api_url = (
                f"https://www.udemy.com/api-2.0/courses/{slug}/"
                f"?fields[course]=is_paid,price,discounted_price,discount,has_discount&couponCode={coupon_code}"
            )
            
            response = requests.get(api_url, timeout=10, headers={'Accept': 'application/json'})
            
            if response.status_code != 200:
                print(f"  ❌ API error: {response.status_code}")
                stats['validation_failed'] += 1
                continue
                
            data = response.json()
            discount = data.get("discount", {})
            discount_percent = discount.get("discount_percent", 0)
            
            # Categorize discount
            if discount_percent == 100:
                print(f"  ✅ 100% FREE!")
                stats['validated_free'] += 1
                stats['discount_ranges']['100%'] += 1
                sample_courses.append({
                    'title': course['title'],
                    'url': url,
                    'discount': discount_percent,
                    'status': 'FREE'
                })
            elif discount_percent >= 90:
                print(f"  🟡 {discount_percent}% off (not free)")
                stats['partial_discount'] += 1
                stats['discount_ranges']['90-99%'] += 1
            elif discount_percent >= 80:
                print(f"  🟠 {discount_percent}% off")
                stats['partial_discount'] += 1
                stats['discount_ranges']['80-89%'] += 1
            elif discount_percent >= 70:
                print(f"  🔴 {discount_percent}% off")
                stats['partial_discount'] += 1
                stats['discount_ranges']['70-79%'] += 1
            elif discount_percent >= 60:
                print(f"  🔴 {discount_percent}% off")
                stats['partial_discount'] += 1
                stats['discount_ranges']['60-69%'] += 1
            elif discount_percent >= 50:
                print(f"  🔴 {discount_percent}% off")
                stats['partial_discount'] += 1
                stats['discount_ranges']['50-59%'] += 1
            elif discount_percent > 0:
                print(f"  🔴 {discount_percent}% off")
                stats['partial_discount'] += 1
                stats['discount_ranges']['<50%'] += 1
            else:
                print(f"  ❌ No discount")
                stats['validation_failed'] += 1
                stats['discount_ranges']['unknown'] += 1
            
            # Add to sample if interesting
            if len(sample_courses) < 10:
                sample_courses.append({
                    'title': course['title'],
                    'url': url,
                    'discount': discount_percent,
                    'status': 'FREE' if discount_percent == 100 else f'{discount_percent}% off'
                })
                
        except Exception as e:
            print(f"  ❌ Validation error: {e}")
            stats['validation_failed'] += 1
            stats['discount_ranges']['unknown'] += 1
        
        # Small delay to be respectful to Udemy API
        if i % 10 == 0:
            await asyncio.sleep(1)
    
    # Print detailed statistics
    print("\n" + "="*80)
    print("📊 DETAILED ANALYSIS RESULTS")
    print("="*80)
    
    print(f"\n📚 Total Courses Analyzed: {stats['total']}")
    print(f"✅ Truly FREE (100% off): {stats['validated_free']}")
    print(f"🟡 Partial Discounts: {stats['partial_discount']}")
    print(f"❌ Validation Failed: {stats['validation_failed']}")
    print(f"❌ No Coupon Code: {stats['no_coupon']}")
    
    print(f"\n📈 Discount Distribution:")
    for range_name, count in stats['discount_ranges'].items():
        if count > 0:
            percentage = (count / stats['total']) * 100
            print(f"   {range_name}: {count} courses ({percentage:.1f}%)")
    
    print(f"\n🎯 Success Rate: {(stats['validated_free'] / stats['total']) * 100:.1f}% truly free")
    
    if sample_courses:
        print(f"\n📋 Sample Courses:")
        for i, course in enumerate(sample_courses[:10], 1):
            print(f"   {i}. {course['title'][:60]}...")
            print(f"      Status: {course['status']}")
            print(f"      URL: {course['url']}")
            print()
    
    return stats

if __name__ == "__main__":
    asyncio.run(analyze_all_courses())