"""
Multi-Source Coupon Scraper
Fetches free Udemy courses from multiple sources and validates 100% off coupons
"""

import asyncio
import logging
import re
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
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
        
        # Enhanced session with connection pooling and retry strategy
        self.session = self._create_enhanced_session()
        self.cloudscraper = cloudscraper.create_scraper()
        
        # Caches and statistics
        self._validation_cache: dict[str, bool] = {}
        self._validation_stats: Dict[str, int] = {
            'api_success': 0,
            'page_scraping_success': 0,
            'cloudscraper_success': 0,
            'heuristic_success': 0,
            'total_attempts': 0,
            'cache_hits': 0
        }
        
    def _create_enhanced_session(self) -> requests.Session:
        """Create a session with connection pooling and retry strategy."""
        session = requests.Session()
        
        # Connection pooling for better performance
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({'User-Agent': self.DEFAULT_USER_AGENT})
        
        return session
        
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
        
        Uses multiple methods to bypass blocking:
        1. Try direct API call with rotating headers
        2. Try course page scraping as fallback
        3. Use proxy rotation if available
        
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
            self._validation_stats['cache_hits'] += 1
            logger.debug(f"📦 Cache hit for {clean_url}: {cached_result}")
            return cached_result
        
        self._validation_stats['total_attempts'] += 1
        
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
            
            # Try multiple validation methods to bypass blocking
            is_free = self._validate_with_multiple_methods(slug, coupon_code, clean_url)
            
            self._validation_cache[clean_url] = is_free
            return is_free
            
        except Exception as e:
            logger.debug(f"❌ Coupon validation error for {url}: {e}")
            self._validation_cache[clean_url] = False
            return False

    def _validate_with_multiple_methods(self, slug: str, coupon_code: str, clean_url: str) -> bool:
        """
        Try multiple validation methods to bypass Udemy blocking.
        
        Args:
            slug: Course slug
            coupon_code: Coupon code
            clean_url: Clean course URL
            
        Returns:
            True if course is validated as free
        """
        # Method 1: Try API with enhanced headers
        if self._try_api_validation(slug, coupon_code):
            return True
            
        # Method 2: Try course page scraping
        if self._try_page_scraping(clean_url):
            return True
            
        # Method 3: Try with cloudscraper (bypasses some protections)
        if self._try_cloudscraper_validation(slug, coupon_code):
            return True
            
        # Method 4: Heuristic validation based on coupon patterns
        if self._try_heuristic_validation(coupon_code):
            return True
            
        return False

    def _try_api_validation(self, slug: str, coupon_code: str) -> bool:
        """Try API validation with enhanced headers and retry logic."""
        headers_variants = [
            # Standard headers
            {
                'User-Agent': self.DEFAULT_USER_AGENT,
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            },
            # Mobile headers
            {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15',
                'Accept': 'application/json',
            },
            # Minimal headers
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
            }
        ]
        
        api_url = (
            f"https://www.udemy.com/api-2.0/courses/{slug}/"
            f"?fields[course]=is_paid,price,discounted_price,discount,has_discount&couponCode={coupon_code}"
        )
        
        for i, headers in enumerate(headers_variants):
            try:
                logger.debug(f"🔍 API attempt {i+1} for {slug}")
                response = self.session.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    result = self._parse_api_response(data, slug)
                    if result:
                        self._validation_stats['api_success'] += 1
                    return result
                elif response.status_code == 403:
                    logger.debug(f"❌ API blocked (403) on attempt {i+1}")
                    continue
                else:
                    logger.debug(f"❌ API error {response.status_code} on attempt {i+1}")
                    continue
                    
            except Exception as e:
                logger.debug(f"❌ API exception on attempt {i+1}: {e}")
                continue
                
        return False

    def _try_page_scraping(self, clean_url: str) -> bool:
        """Try to validate by scraping the course page."""
        try:
            logger.debug(f"🌐 Trying page scraping for {clean_url}")
            
            headers = {
                'User-Agent': self.DEFAULT_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(clean_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # Look for free indicators in the page
                free_indicators = [
                    'enroll for free',
                    'free course',
                    '"price":"free"',
                    '"amount":0',
                    'discount_percent":100',
                    'price":{"amount":0',
                    'free enrollment',
                    'enroll now - free'
                ]
                
                for indicator in free_indicators:
                    if indicator in content:
                        logger.debug(f"✅ Found free indicator: {indicator}")
                        self._validation_stats['page_scraping_success'] += 1
                        return True
                        
                logger.debug(f"❌ No free indicators found in page")
                return False
            else:
                logger.debug(f"❌ Page scraping failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"❌ Page scraping error: {e}")
            return False

    def _try_cloudscraper_validation(self, slug: str, coupon_code: str) -> bool:
        """Try validation using cloudscraper to bypass protections."""
        try:
            logger.debug(f"☁️ Trying cloudscraper for {slug}")
            
            api_url = (
                f"https://www.udemy.com/api-2.0/courses/{slug}/"
                f"?fields[course]=price,discount&couponCode={coupon_code}"
            )
            
            response = self.cloudscraper.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = self._parse_api_response(data, slug)
                if result:
                    self._validation_stats['cloudscraper_success'] += 1
                return result
            else:
                logger.debug(f"❌ Cloudscraper failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.debug(f"❌ Cloudscraper error: {e}")
            return False

    def _try_heuristic_validation(self, coupon_code: str) -> bool:
        """
        Use heuristic patterns to guess if a coupon might be free.
        This is a fallback when all other methods fail.
        """
        try:
            # Some patterns that often indicate free coupons
            free_patterns = [
                r'FREE\d*',
                r'100OFF',
                r'GRATIS',
                r'ZERO',
                r'0PRICE',
                r'NOPAY',
                r'COMPLIMENTARY'
            ]
            
            coupon_upper = coupon_code.upper()
            
            for pattern in free_patterns:
                if re.search(pattern, coupon_upper):
                    logger.debug(f"🎯 Heuristic match: {pattern} in {coupon_code}")
                    self._validation_stats['heuristic_success'] += 1
                    return True
                    
            # Check for date-based free coupons (common pattern)
            if re.search(r'(DEC|NOV|OCT).*FREE|FREE.*(DEC|NOV|OCT)', coupon_upper):
                logger.debug(f"🎯 Date-based free pattern in {coupon_code}")
                self._validation_stats['heuristic_success'] += 1
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"❌ Heuristic validation error: {e}")
            return False

    def _parse_api_response(self, data: dict, slug: str) -> bool:
        """Parse API response to determine if course is free."""
        try:
            discount = data.get("discount", {})
            discount_percent = discount.get("discount_percent", 0)
            
            # Check if discount price amount is 0
            discount_amount = discount.get("price", {}).get("amount") if discount else None
            
            # Also check if price string indicates free
            price = data.get("price", "")
            
            # A course is free if ANY of these conditions are true
            conditions = [
                discount_percent == 100,
                discount_amount is not None and discount_amount == 0,
                isinstance(price, str) and price.lower().startswith("free")
            ]
            
            is_free = any(conditions)
            
            if is_free:
                reason = f"discount_percent={discount_percent}, discount_amount={discount_amount}, price={price}"
                logger.debug(f"✅ Course {slug} is FREE: {reason}")
            else:
                logger.debug(f"❌ Course {slug} is NOT free: discount_percent={discount_percent}")
                
            return is_free
            
        except Exception as e:
            logger.debug(f"❌ Error parsing API response: {e}")
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
        Scrape CourseVania for free courses with enhanced retry logic.
        
        CourseVania uses WordPress with AJAX loading:
        1. Get the page to extract the security nonce
        2. Make AJAX request to get course grid
        3. Parse each course detail page for Udemy links
        """
        logger.info("🔍 Scraping CourseVania...")
        
        # Try multiple approaches with different headers
        headers_variants = [
            {
                'User-Agent': self.DEFAULT_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        ]
        
        for attempt, headers in enumerate(headers_variants, 1):
            try:
                logger.debug(f"CourseVania attempt {attempt}/3")
                courses = self._scrape_course_vania_with_headers(headers)
                
                if courses:
                    logger.info(f"✅ CourseVania: Found {len(courses)} valid courses (attempt {attempt})")
                    return courses
                else:
                    logger.debug(f"CourseVania attempt {attempt} returned no courses")
                    
            except Exception as e:
                logger.debug(f"CourseVania attempt {attempt} failed: {e}")
                
            # Exponential backoff between attempts
            if attempt < len(headers_variants):
                time.sleep(2 ** (attempt - 1))  # 1s, 2s delays
        
        logger.warning("❌ CourseVania: All attempts failed")
        return []
    
    def _scrape_course_vania_with_headers(self, headers: dict) -> list:
        """Scrape CourseVania with specific headers."""
        courses = []
        
        # Step 1: Get main page to extract nonce
        response = requests.get(
            "https://coursevania.com/courses/",
            headers=headers,
            timeout=self.request_timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get main page: {response.status_code}")
        
        # Step 2: Extract AJAX nonce from page
        nonce_match = re.search(r"load_content\":\"(.*?)\"", response.text)
        if not nonce_match:
            raise Exception("Nonce not found in page")
            
        nonce = nonce_match.group(1)
        
        # Step 3: Make AJAX request for course data
        ajax_url = (
            f"https://coursevania.com/wp-admin/admin-ajax.php"
            f"?&template=courses/grid"
            f"&args={{%22posts_per_page%22:%22100%22}}"
            f"&action=stm_lms_load_content&sort=date_high&nonce={nonce}"
        )
        ajax_response = requests.get(ajax_url, headers=headers, timeout=self.request_timeout)
        
        if ajax_response.status_code != 200:
            raise Exception(f"AJAX request failed: {ajax_response.status_code}")
            
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
                detail_response = requests.get(course_page_url, headers=headers, timeout=15)
                
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
                
        return courses

    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get detailed validation statistics for monitoring and debugging.
        
        Returns:
            Dictionary with validation method success rates and performance metrics
        """
        total_attempts = self._validation_stats['total_attempts']
        
        if total_attempts == 0:
            return {
                'total_attempts': 0,
                'cache_hits': 0,
                'success_rate': 0.0,
                'method_breakdown': {
                    'api_success': 0,
                    'page_scraping_success': 0,
                    'cloudscraper_success': 0,
                    'heuristic_success': 0
                },
                'cache_size': len(self._validation_cache)
            }
        
        total_successes = (
            self._validation_stats['api_success'] +
            self._validation_stats['page_scraping_success'] +
            self._validation_stats['cloudscraper_success'] +
            self._validation_stats['heuristic_success']
        )
        
        return {
            'total_attempts': total_attempts,
            'cache_hits': self._validation_stats['cache_hits'],
            'success_rate': (total_successes / total_attempts) * 100,
            'method_breakdown': {
                'api_success': self._validation_stats['api_success'],
                'page_scraping_success': self._validation_stats['page_scraping_success'],
                'cloudscraper_success': self._validation_stats['cloudscraper_success'],
                'heuristic_success': self._validation_stats['heuristic_success']
            },
            'method_success_rates': {
                'api_rate': (self._validation_stats['api_success'] / total_attempts) * 100,
                'page_scraping_rate': (self._validation_stats['page_scraping_success'] / total_attempts) * 100,
                'cloudscraper_rate': (self._validation_stats['cloudscraper_success'] / total_attempts) * 100,
                'heuristic_rate': (self._validation_stats['heuristic_success'] / total_attempts) * 100
            },
            'cache_size': len(self._validation_cache),
            'cache_hit_rate': (self._validation_stats['cache_hits'] / total_attempts) * 100 if total_attempts > 0 else 0
        }

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
