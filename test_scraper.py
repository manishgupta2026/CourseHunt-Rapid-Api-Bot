#!/usr/bin/env python3
"""
Test script for the multi-source scraper
"""

import asyncio
from multi_source_scraper import MultiSourceCouponScraper

async def test_without_validation():
    print('Testing scraper WITHOUT validation (raw results):')
    scraper = MultiSourceCouponScraper(validate_coupons=False)
    courses = await scraper.scrape_all_sources()
    
    print(f'Found {len(courses)} courses without validation:')
    for i, course in enumerate(courses[:5]):
        print(f'{i+1}. {course["title"][:50]}...')
        print(f'   URL: {course["url"]}')
        print()
    
    return len(courses)

async def test_with_validation():
    print('\nTesting scraper WITH validation (100% free only):')
    scraper = MultiSourceCouponScraper(validate_coupons=True)
    courses = await scraper.scrape_all_sources()
    
    print(f'Found {len(courses)} validated free courses:')
    for i, course in enumerate(courses[:5]):
        print(f'{i+1}. {course["title"][:50]}...')
        print(f'   URL: {course["url"]}')
        print()
    
    return len(courses)

async def main():
    raw_count = await test_without_validation()
    validated_count = await test_with_validation()
    
    print(f'\n📊 Summary:')
    print(f'   Raw courses found: {raw_count}')
    print(f'   Validated free courses: {validated_count}')
    print(f'   Filtered out: {raw_count - validated_count}')
    print(f'   Validation rate: {(validated_count/max(raw_count,1)*100):.1f}%')

if __name__ == "__main__":
    asyncio.run(main())