"""
Multi-Source Coupon Scraper
Integrates multiple coupon sources with the RapidAPI bot
"""

import asyncio
import concurrent.futures
import json
import re
import threading
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup as bs
import cloudscraper


class MultiSourceCouponScraper:
    """Scraper that fetches coupons from multiple sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
        })
        self.cloudscraper = cloudscraper.create_scraper()
        
    def cleanup_link(self, link: str) -> str:
        """Clean up Udemy course links"""
        if "udemy.com" not in link:
            return None
            
        # Parse URL and extract course path
        parsed = urlparse(link)
        if "/course/" not in parsed.path:
            return None
            
        # Clean URL - remove tracking parameters but keep coupon code
        query_params = parse_qs(parsed.query)
        clean_params = {}
        
        # Keep only coupon-related parameters
        for key, value in query_params.items():
            if key.lower() in ['couponcode', 'coupon_code', 'coupon']:
                clean_params[key] = value[0] if isinstance(value, list) else value
                
        # Reconstruct clean URL
        clean_url = f"https://www.udemy.com{parsed.path}"
        if clean_params:
            params_str = "&".join([f"{k}={v}" for k, v in clean_params.items()])
            clean_url += f"?{params_str}"
            
        return clean_url

    def scrape_real_discount(self) -> list:
        """Scrape Real.discount for free Udemy courses"""
        try:
            print("🔍 Scraping Real.discount...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Host": "cdn.real.discount",
                "Connection": "Keep-Alive",
                "referer": "https://www.real.discount/",
            }
            
            url = "https://cdn.real.discount/api/courses?page=1&limit=100&sortBy=sale_start&store=Udemy&freeOnly=true"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Real.discount failed: {response.status_code}")
                return []
                
            data = response.json()
            courses = []
            
            for item in data.get("items", []):
                if item.get("store") == "Sponsored":
                    continue
                    
                title = item.get("name", "")
                link = item.get("url", "")
                
                clean_link = self.cleanup_link(link)
                if clean_link:
                    courses.append({
                        'title': title,
                        'url': clean_link,
                        'source': 'Real.discount'
                    })
                    
            print(f"✅ Real.discount: Found {len(courses)} courses")
            return courses
            
        except Exception as e:
            print(f"❌ Real.discount error: {str(e)}")
            return []

    def scrape_discudemy(self) -> list:
        """Scrape Discudemy for free courses"""
        try:
            print("🔍 Scraping Discudemy...")
            courses = []
            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "referer": "https://www.discudemy.com",
            }

            # Scrape first 3 pages to avoid being too aggressive
            for page in range(1, 4):
                try:
                    url = f"https://www.discudemy.com/all/{page}"
                    response = requests.get(url, headers=headers, timeout=30)
                    
                    if response.status_code != 200:
                        continue
                        
                    soup = bs(response.content, 'html.parser')
                    page_items = soup.find_all("a", {"class": "card-header"})
                    
                    for item in page_items:
                        try:
                            title = item.string
                            if not title:
                                continue
                                
                            course_url = item["href"].split("/")[-1]
                            detail_url = f"https://www.discudemy.com/go/{course_url}"
                            
                            # Get course details
                            detail_response = requests.get(detail_url, headers=headers, timeout=15)
                            if detail_response.status_code == 200:
                                detail_soup = bs(detail_response.content, 'html.parser')
                                segment = detail_soup.find("div", {"class": "ui segment"})
                                if segment and segment.a:
                                    link = segment.a["href"]
                                    clean_link = self.cleanup_link(link)
                                    if clean_link:
                                        courses.append({
                                            'title': title,
                                            'url': clean_link,
                                            'source': 'Discudemy'
                                        })
                                        
                            # Small delay to be respectful
                            time.sleep(0.5)
                            
                        except Exception as e:
                            continue
                            
                    # Delay between pages
                    time.sleep(1)
                    
                except Exception as e:
                    continue
                    
            print(f"✅ Discudemy: Found {len(courses)} courses")
            return courses
            
        except Exception as e:
            print(f"❌ Discudemy error: {str(e)}")
            return []

    def scrape_course_vania(self) -> list:
        """Scrape CourseVania for free courses"""
        try:
            print("🔍 Scraping CourseVania...")
            courses = []
            
            # Get main page to extract nonce
            response = requests.get("https://coursevania.com/courses/", timeout=30)
            if response.status_code != 200:
                print("❌ CourseVania: Failed to get main page")
                return []
                
            # Extract nonce for AJAX request
            nonce_match = re.search(r"load_content\":\"(.*?)\"", response.text)
            if not nonce_match:
                print("❌ CourseVania: Nonce not found")
                return []
                
            nonce = nonce_match.group(1)
            
            # Make AJAX request for courses
            ajax_url = f"https://coursevania.com/wp-admin/admin-ajax.php?&template=courses/grid&args={{%22posts_per_page%22:%22100%22}}&action=stm_lms_load_content&sort=date_high&nonce={nonce}"
            ajax_response = requests.get(ajax_url, timeout=30)
            
            if ajax_response.status_code != 200:
                print("❌ CourseVania: AJAX request failed")
                return []
                
            data = ajax_response.json()
            soup = bs(data.get("content", ""), 'html.parser')
            page_items = soup.find_all("div", {"class": "stm_lms_courses__single--title"})
            
            for item in page_items[:20]:  # Limit to first 20 to avoid being aggressive
                try:
                    title = item.h5.string if item.h5 else ""
                    if not title or not item.a:
                        continue
                        
                    course_page_url = item.a["href"]
                    
                    # Get course details page
                    detail_response = requests.get(course_page_url, timeout=15)
                    if detail_response.status_code == 200:
                        detail_soup = bs(detail_response.content, 'html.parser')
                        
                        # Look for Udemy link
                        udemy_links = detail_soup.find_all("a", href=re.compile(r"udemy\.com"))
                        for link_elem in udemy_links:
                            link = link_elem.get("href", "")
                            clean_link = self.cleanup_link(link)
                            if clean_link:
                                courses.append({
                                    'title': title,
                                    'url': clean_link,
                                    'source': 'CourseVania'
                                })
                                break
                                
                    # Small delay
                    time.sleep(0.5)
                    
                except Exception as e:
                    continue
                    
            print(f"✅ CourseVania: Found {len(courses)} courses")
            return courses
            
        except Exception as e:
            print(f"❌ CourseVania error: {str(e)}")
            return []

    def scrape_udemy_freebies(self) -> list:
        """Scrape UdemyFreebies for free courses"""
        try:
            print("🔍 Scraping UdemyFreebies...")
            courses = []
            
            # Try to get courses from UdemyFreebies
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            # UdemyFreebies often changes structure, so this is a basic implementation
            response = requests.get("https://www.udemyfreebies.com/free-udemy-courses", headers=headers, timeout=30)
            
            if response.status_code != 200:
                print("❌ UdemyFreebies: Failed to get page")
                return []
                
            soup = bs(response.content, 'html.parser')
            
            # Look for course links (structure may vary)
            course_links = soup.find_all("a", href=re.compile(r"udemy\.com"))
            
            for link_elem in course_links[:30]:  # Limit to first 30
                try:
                    link = link_elem.get("href", "")
                    title = link_elem.get_text(strip=True) or "Udemy Course"
                    
                    clean_link = self.cleanup_link(link)
                    if clean_link:
                        courses.append({
                            'title': title[:100],  # Limit title length
                            'url': clean_link,
                            'source': 'UdemyFreebies'
                        })
                        
                except Exception as e:
                    continue
                    
            print(f"✅ UdemyFreebies: Found {len(courses)} courses")
            return courses
            
        except Exception as e:
            print(f"❌ UdemyFreebies error: {str(e)}")
            return []

    async def scrape_all_sources(self) -> list:
        """Scrape all sources concurrently"""
        print("🚀 Starting multi-source scraping...")
        
        # Run scrapers concurrently
        loop = asyncio.get_event_loop()
        
        tasks = [
            loop.run_in_executor(None, self.scrape_real_discount),
            loop.run_in_executor(None, self.scrape_discudemy),
            loop.run_in_executor(None, self.scrape_course_vania),
            loop.run_in_executor(None, self.scrape_udemy_freebies),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all results
        all_courses = []
        for result in results:
            if isinstance(result, list):
                all_courses.extend(result)
            elif isinstance(result, Exception):
                print(f"❌ Scraper error: {result}")
                
        # Remove duplicates based on URL
        seen_urls = set()
        unique_courses = []
        
        for course in all_courses:
            url = course['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_courses.append(course)
                
        print(f"📊 Total unique courses found: {len(unique_courses)}")
        return unique_courses


# Test function
async def test_scrapers():
    scraper = MultiSourceCouponScraper()
    courses = await scraper.scrape_all_sources()
    
    print(f"\n📋 Sample courses:")
    for i, course in enumerate(courses[:5]):
        print(f"{i+1}. {course['title'][:50]}... ({course['source']})")
        print(f"   URL: {course['url']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_scrapers())