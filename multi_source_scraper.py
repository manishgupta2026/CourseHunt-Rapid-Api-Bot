"""
Multi-Source Coupon Scraper
Fetches free Udemy courses from multiple sources and validates 100% off coupons
"""

import asyncio
import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup as bs
import cloudscraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiSourceCouponScraper:
    """Scraper that fetches 100% free Udemy courses from multiple sources"""
    
    DEFAULT_USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    COUPON_PARAM_NAMES = ['couponcode', 'coupon_code', 'coupon']
    
    def __init__(self, validate_coupons: bool = True, request_timeout: int = 30):
        """
        Initialize the scraper.
        
        Args:
            validate_coupons: Whether to validate coupons via Udemy API
            request_timeout: Default timeout for HTTP requests in seconds
        """
        self.validate_coupons = validate_coupons
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.DEFAULT_USER_AGENT})
        self.cloudscraper = cloudscraper.create_scraper()
        self._validation_cache: dict[str, bool] = {}
        
    def cleanup_link(self, link: str) -> Optional[str]:
        """
        Clean up Udemy course links and preserve coupon code.
        
        Removes tracking parameters while keeping coupon-related params.
        
        Args:
            link: Raw URL that may contain tracking parameters
            
        Returns:
            Cleaned URL with only coupon parameters, or None if invalid
        """
        if not link or "udemy.com" not in link:
            return None
            
        parsed = urlparse(link)
        if "/course/" not in parsed.path:
            return None
        
        # Normalize path (remove trailing slashes, ensure leading slash)
        path = parsed.path.rstrip('/')
        if not path.startswith('/'):
            path = '/' + path
            
        query_params = parse_qs(parsed.query)
        clean_params = {}
        
        for key, value in query_params.items():
            if key.lower() in self.COUPON_PARAM_NAMES:
                clean_params[key] = value[0] if isinstance(value, list) else value
                
        clean_url = f"https://www.udemy.com{path}"
        if clean_params:
            clean_url += f"?{urlencode(clean_params)}"
            
        return clean_url

    def is_free_coupon(self, url: str) -> bool:
        """
        Check via Udemy API if the course coupon provides 100% discount.
        
        Makes an API call to Udemy to verify the coupon is valid and
        provides a full discount.
        
        Args:
            url: Udemy course URL with coupon code
            
        Returns:
            True if the coupon is valid and provides 100% discount
        """
        clean_url = self.cleanup_link(url)
        if not clean_url:
            logger.debug(f"❌ Invalid URL format: {url}")
            return False
        
        # Check cache first to avoid redundant API calls
        if clean_url in self._validation_cache:
            cached_result = self._validation_cache[clean_url]
            logger.debug(f"📦 Cache hit for {clean_url}: {cached_result}")
            return cached_result
        
        try:
            parsed = urlparse(clean_url)
            path_parts = parsed.path.split("/course/")
            if len(path_parts) < 2:
                logger.debug(f"❌ Invalid course path: {clean_url}")
                return False
                
            slug = path_parts[-1].strip("/")
            query_params = parse_qs(parsed.query)
            
            # Find coupon code from various parameter names
            coupon_code = ""
            for param_name in self.COUPON_PARAM_NAMES:
                for key, value in query_params.items():
                    if key.lower() == param_name:
                        coupon_code = value[0] if isinstance(value, list) else value
                        break
                if coupon_code:
                    break
            
            if not coupon_code:
                logger.debug(f"❌ No coupon code found in URL: {clean_url}")
                self._validation_cache[clean_url] = False
                return False
            
            # Query Udemy API with correct fields for coupon validation
            api_url = (
                f"https://www.udemy.com/api-2.0/courses/{slug}/"
                f"?fields[course]=is_paid,price,discounted_price,discount,has_discount&couponCode={coupon_code}"
            )
            logger.debug(f"🔍 Checking Udemy API: {api_url}")
            
            response = self.session.get(
                api_url,
                timeout=15,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code != 200:
                logger.debug(f"❌ API error {response.status_code} for {slug} with coupon {coupon_code}")
                self._validation_cache[clean_url] = False
                return False
                
            data = response.json()
            logger.debug(f"📥 API Response for {slug}: {data}")
            
            # Check for 100% discount using multiple validation criteria
            discount = data.get("discount", {})
            discount_percent = discount.get("discount_percent", 0)
            
            # Check if discount price amount is 0 (handle nested structure safely)
            discount_amount = discount.get("price", {}).get("amount") if discount else None
            
            # Also check if price string indicates free
            price = data.get("price", "")
            
            # A course is free if ANY of these conditions are true:
            # 1. discount_percent is 100
            # 2. discount.price.amount is 0
            # 3. price field starts with "Free"
            is_free = False
            reason = ""
            
            if discount_percent == 100:
                is_free = True
                reason = f"discount_percent is 100%"
            elif discount_amount is not None and discount_amount == 0:
                is_free = True
                reason = f"discount amount is 0"
            elif isinstance(price, str) and price.startswith("Free"):
                is_free = True
                reason = "price field shows 'Free'"
            else:
                reason = f"discount_percent={discount_percent}, discount_amount={discount_amount}, price={price}"
            
            if is_free:
                logger.debug(f"✅ Course {slug} is FREE: {reason}")
            else:
                logger.debug(f"❌ Course {slug} is NOT free: {reason}")
            
            self._validation_cache[clean_url] = is_free
            return is_free
            
        except Exception as e:
            logger.debug(f"❌ Coupon validation error for {url}: {e}")
            self._validation_cache[clean_url] = False
            return False

    def _should_include_course(self, url: str) -> bool:
        """Check if course should be included based on validation settings."""
        if not self.validate_coupons:
            return True
        return self.is_free_coupon(url)

    def scrape_real_discount(self) -> list:
        """
        Scrape Real.discount for free Udemy courses.
        
        Real.discount provides a JSON API that returns course data directly.
        """
        try:
            logger.info("🔍 Scraping Real.discount...")
            headers = {
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Host": "cdn.real.discount",
                "Connection": "Keep-Alive",
                "Referer": "https://www.real.discount/",
            }
            
            url = (
                "https://cdn.real.discount/api/courses"
                "?page=1&limit=100&sortBy=sale_start&store=Udemy&freeOnly=true"
            )
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            
            if response.status_code != 200:
                logger.warning(f"❌ Real.discount failed: HTTP {response.status_code}")
                return []
                
            data = response.json()
            courses = []
            
            for item in data.get("items", []):
                if item.get("store") == "Sponsored":
                    continue
                    
                link = item.get("url", "")
                clean_link = self.cleanup_link(link)
                
                if clean_link and self._should_include_course(link):
                    courses.append({
                        'title': item.get("name", ""),
                        'url': clean_link
                    })
                    
            logger.info(f"✅ Real.discount: Found {len(courses)} valid courses")
            return courses
            
        except Exception as e:
            logger.error(f"❌ Real.discount error: {e}")
            return []

    def scrape_discudemy(self) -> list:
        """
        Scrape Discudemy for free courses.
        
        Discudemy requires two-step scraping:
        1. Get course list from main pages
        2. Follow each link to get the actual Udemy URL
        """
        try:
            logger.info("🔍 Scraping Discudemy...")
            courses = []
            headers = {
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.discudemy.com",
            }

            # Scrape first 3 pages
            for page in range(1, 4):
                try:
                    url = f"https://www.discudemy.com/all/{page}"
                    response = self.session.get(
                        url, headers=headers, timeout=self.request_timeout
                    )
                    
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
                            
                            # Follow to get actual Udemy link
                            detail_response = self.session.get(
                                detail_url, headers=headers, timeout=15
                            )
                            
                            if detail_response.status_code == 200:
                                detail_soup = bs(detail_response.content, 'html.parser')
                                segment = detail_soup.find("div", {"class": "ui segment"})
                                
                                if segment and segment.a:
                                    link = segment.a["href"]
                                    clean_link = self.cleanup_link(link)
                                    
                                    if clean_link and self._should_include_course(link):
                                        courses.append({
                                            'title': title,
                                            'url': clean_link
                                        })
                            
                            # Rate limiting - be respectful to the server
                            time.sleep(0.3)
                            
                        except Exception:
                            continue
                    
                    # Delay between pages
                    time.sleep(1)
                    
                except Exception:
                    continue
                    
            logger.info(f"✅ Discudemy: Found {len(courses)} valid courses")
            return courses
            
        except Exception as e:
            logger.error(f"❌ Discudemy error: {e}")
            return []

    def scrape_course_vania(self) -> list:
        """
        Scrape CourseVania for free courses.
        
        CourseVania uses WordPress with AJAX loading:
        1. Get the page to extract the security nonce
        2. Make AJAX request to get course grid
        3. Parse each course detail page for Udemy links
        """
        try:
            logger.info("🔍 Scraping CourseVania...")
            courses = []
            
            # Step 1: Get main page to extract nonce
            response = self.session.get(
                "https://coursevania.com/courses/",
                timeout=self.request_timeout
            )
            
            if response.status_code != 200:
                logger.warning("❌ CourseVania: Failed to get main page")
                return []
            
            # Step 2: Extract AJAX nonce from page
            nonce_match = re.search(r"load_content\":\"(.*?)\"", response.text)
            if not nonce_match:
                logger.warning("❌ CourseVania: Nonce not found")
                return []
                
            nonce = nonce_match.group(1)
            
            # Step 3: Make AJAX request for course data
            ajax_url = (
                f"https://coursevania.com/wp-admin/admin-ajax.php"
                f"?&template=courses/grid"
                f"&args={{%22posts_per_page%22:%22100%22}}"
                f"&action=stm_lms_load_content&sort=date_high&nonce={nonce}"
            )
            ajax_response = self.session.get(ajax_url, timeout=self.request_timeout)
            
            if ajax_response.status_code != 200:
                logger.warning("❌ CourseVania: AJAX request failed")
                return []
                
            data = ajax_response.json()
            soup = bs(data.get("content", ""), 'html.parser')
            page_items = soup.find_all("div", {"class": "stm_lms_courses__single--title"})
            
            # Step 4: Parse each course detail page
            for item in page_items[:20]:  # Limit to avoid being aggressive
                try:
                    title = item.h5.string if item.h5 else ""
                    if not title or not item.a:
                        continue
                        
                    course_page_url = item.a["href"]
                    detail_response = self.session.get(course_page_url, timeout=15)
                    
                    if detail_response.status_code == 200:
                        detail_soup = bs(detail_response.content, 'html.parser')
                        udemy_links = detail_soup.find_all(
                            "a", href=re.compile(r"udemy\.com")
                        )
                        
                        for link_elem in udemy_links:
                            link = link_elem.get("href", "")
                            clean_link = self.cleanup_link(link)
                            
                            if clean_link and self._should_include_course(link):
                                courses.append({
                                    'title': title,
                                    'url': clean_link
                                })
                                break
                    
                    # Rate limiting
                    time.sleep(0.3)
                    
                except Exception:
                    continue
                    
            logger.info(f"✅ CourseVania: Found {len(courses)} valid courses")
            return courses
            
        except Exception as e:
            logger.error(f"❌ CourseVania error: {e}")
            return []

    def scrape_udemy_freebies(self) -> list:
        """
        Scrape UdemyFreebies for free courses.
        
        Simple scraper that finds all Udemy links on the page.
        """
        try:
            logger.info("🔍 Scraping UdemyFreebies...")
            courses = []
            
            response = self.session.get(
                "https://www.udemyfreebies.com/free-udemy-courses",
                timeout=self.request_timeout
            )
            
            if response.status_code != 200:
                logger.warning("❌ UdemyFreebies: Failed to get page")
                return []
                
            soup = bs(response.content, 'html.parser')
            course_links = soup.find_all("a", href=re.compile(r"udemy\.com"))
            
            for link_elem in course_links[:30]:  # Limit to first 30
                try:
                    link = link_elem.get("href", "")
                    clean_link = self.cleanup_link(link)
                    
                    if clean_link and self._should_include_course(link):
                        title = link_elem.get_text(strip=True) or "Udemy Course"
                        courses.append({
                            'title': title[:100],  # Truncate long titles
                            'url': clean_link
                        })
                        
                except Exception:
                    continue
                    
            logger.info(f"✅ UdemyFreebies: Found {len(courses)} valid courses")
            return courses
            
        except Exception as e:
            logger.error(f"❌ UdemyFreebies error: {e}")
            return []

    async def scrape_all_sources(self) -> list:
        """
        Scrape all sources concurrently and return unique 100% free courses.
        
        Uses asyncio to run all scrapers in parallel for better performance.
        Deduplicates results based on URL.
        
        Returns:
            List of unique courses with validated coupons
        """
        logger.info("🚀 Starting multi-source scraping...")
        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        
        # Run all scrapers concurrently
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
                logger.error(f"❌ Scraper error: {result}")
                
        # Remove duplicates based on URL
        seen_urls = set()
        unique_courses = []
        
        for course in all_courses:
            url = course['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_courses.append(course)
        
        elapsed = time.time() - start_time
        logger.info(
            f"📊 Scraping complete: {len(unique_courses)} unique courses "
            f"found in {elapsed:.2f}s"
        )
        
        return unique_courses


async def test_scrapers():
    """Test function to verify scrapers are working."""
    scraper = MultiSourceCouponScraper(validate_coupons=True)
    courses = await scraper.scrape_all_sources()
    
    print(f"\n📋 Found {len(courses)} courses:\n")
    for i, course in enumerate(courses[:10]):
        print(f"{i+1}. {course['title'][:60]}...")
        print(f"   {course['url']}\n")


if __name__ == "__main__":
    asyncio.run(test_scrapers())
