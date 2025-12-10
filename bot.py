"""
Telegram Bot for Udemy Free Courses
Fetches courses from multiple sources, validates 100% off coupons, and sends to bridge channel
"""

import os
import http.client
import json
import asyncio
import logging
from html import escape
from datetime import datetime, timedelta, time, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Import our multi-source scraper
from multi_source_scraper import MultiSourceCouponScraper
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UdemyBot:
    """RapidAPI client for fetching Udemy courses"""
    
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.host = "paid-udemy-course-for-free.p.rapidapi.com"
        self.base_path = "/"
        self.per_page = 10

    def _get_headers(self):
        return {
            'x-rapidapi-key': self.api_keys[self.current_key_index],
            'x-rapidapi-host': self.host
        }
    
    def _rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to API key #{self.current_key_index + 1}")

    def _make_request(self, endpoint):
        for attempt in range(len(self.api_keys)):
            try:
                conn = http.client.HTTPSConnection(self.host)
                conn.request("GET", endpoint, headers=self._get_headers())
                res = conn.getresponse()
                
                if res.status == 200:
                    return json.loads(res.read().decode('utf-8'))
                elif res.status == 429:  # Rate limit exceeded
                    logger.warning(f"Rate limit hit on key #{self.current_key_index + 1}")
                    self._rotate_key()
                else:
                    logger.error(f"API error {res.status}: {res.reason}")
            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
            finally:
                conn.close()
        return None

    def get_courses(self, page=0):
        return self._make_request(f"{self.base_path}?page={page}") or []

    def get_total_courses(self):
        result = self._make_request(f"{self.base_path}count")
        if not result:
            return 0
        try:
            if isinstance(result, dict):
                return int(result.get('count', 0))
            elif isinstance(result, int):
                return result
            return int(result)
        except (TypeError, ValueError):
            return 0

    def search_courses(self, query, page=0):
        return self._make_request(f"{self.base_path}search?s={query}&page={page}") or []
    
    def get_recent_courses(self, limit=10):
        """Get recent courses (optimized for free API)"""
        return self._make_request(f"{self.base_path}?page=0&limit={limit}") or []


def sanitize_html(text):
    """Sanitize text for HTML output"""
    return escape(text).replace("&amp;", "&") if text else ""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /help commands"""
    help_text = """
🎓 <b>Udemy Courses Bot</b> 🚀

<u>Available commands:</u>
/list - Show first page of courses
/count - Show total course count
/search [query] - Search courses (e.g. /search python)
/help - Show this help
    """
    await update.message.reply_html(help_text)


async def count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /count command"""
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    total = bot.get_total_courses()
    await update.message.reply_text(f"📚 Total courses available: {total}")


async def list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command with pagination"""
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    
    try:
        page = int(context.args[0]) if context.args else 0
    except (ValueError, IndexError):
        page = 0
    
    courses = bot.get_courses(page)
    if not courses:
        await update.message.reply_text("⚠️ Failed to fetch courses. Please try again later.")
        return
        
    total = bot.get_total_courses()
    total_pages = (total // bot.per_page) + (1 if total % bot.per_page else 0) if total > 0 else 1
    
    response = f"📖 <b>Page {page+1}/{total_pages}</b>\n\n"
    for i, course in enumerate(courses, 1):
        title = sanitize_html(course.get('title', 'Untitled Course'))
        coupon = course.get('coupon', '#')
        rating = course.get('rating', 'N/A')
        duration = course.get('duration', 'N/A')
        category = sanitize_html(course.get('category', 'Unknown'))
        
        response += f"<b>{i}. {title}</b>\n"
        response += f"🔗 <code>{coupon}</code>\n"
        response += f"⭐ Rating: {rating} | 🕒 Duration: {duration}h\n"
        response += f"🏷️ Category: {category}\n\n"
    
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list:{page-1}"))
    if page < total_pages - 1:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"list:{page+1}"))
    
    try:
        await update.message.reply_html(
            response,
            reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        plain_response = f"Page {page+1}/{total_pages}\n\n"
        for i, course in enumerate(courses, 1):
            plain_response += f"{i}. {course.get('title', 'Untitled Course')}\n"
            plain_response += f"URL: {course.get('coupon', 'Not available')}\n"
            plain_response += f"Rating: {course.get('rating', 'N/A')} | Duration: {course.get('duration', 'N/A')}h\n"
            plain_response += f"Category: {course.get('category', 'Unknown')}\n\n"
        await update.message.reply_text(plain_response)


async def search_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command"""
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    
    if not context.args:
        await update.message.reply_text("🔍 Please provide search term: /search react")
        return
    
    try:
        page = int(context.args[-1])
        query = " ".join(context.args[:-1])
    except ValueError:
        page = 0
        query = " ".join(context.args)
    
    courses = bot.search_courses(query, page)
    if not courses:
        await update.message.reply_text("⚠️ No courses found or API error. Try different search term.")
        return
    
    response = f"🔍 <b>Results for '{query}' (Page {page+1})</b>\n\n"
    for i, course in enumerate(courses, 1):
        title = sanitize_html(course.get('title', 'Untitled Course'))
        coupon = course.get('coupon', '#')
        rating = course.get('rating', 'N/A')
        duration = course.get('duration', 'N/A')
        
        response += f"<b>{i}. {title}</b>\n"
        response += f"🔗 <code>{coupon}</code>\n"
        response += f"⭐ Rating: {rating} | 🕒 Duration: {duration}h\n\n"
    
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search:{query}:{page-1}"))
    keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"search:{query}:{page+1}"))
    
    try:
        await update.message.reply_html(
            response,
            reply_markup=InlineKeyboardMarkup([keyboard]),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        plain_response = f"Results for '{query}' (Page {page+1})\n\n"
        for i, course in enumerate(courses, 1):
            plain_response += f"{i}. {course.get('title', 'Untitled Course')}\n"
            plain_response += f"URL: {course.get('coupon', 'Not available')}\n"
            plain_response += f"Rating: {course.get('rating', 'N/A')} | Duration: {course.get('duration', 'N/A')}h\n\n"
        await update.message.reply_text(plain_response)


async def handle_udemy_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Udemy URLs posted in group chats"""
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    
    url = update.message.text
    course = bot.get_course_by_url(url)
    
    if not course:
        await update.message.reply_text("⚠️ Could not find course details for this URL.")
        return
    
    title = sanitize_html(course.get('title', 'Untitled Course'))
    coupon = course.get('coupon', '#')
    rating = course.get('rating', 'N/A')
    duration = course.get('duration', 'N/A')
    category = sanitize_html(course.get('category', 'Unknown'))
    description = sanitize_html(course.get('desc_text', 'No description available'))
    
    # Truncate description if too long
    if len(description) > 500:
        description = description[:500] + "..."
    
    response = f"🎓 <b>{title}</b>\n\n"
    response += f"🔗 <code>{coupon}</code>\n\n"
    response += f"⭐ <b>Rating:</b> {rating}\n"
    response += f"🕒 <b>Duration:</b> {duration}h\n"
    response += f"🏷️ <b>Category:</b> {category}\n\n"
    response += f"📝 <b>Description:</b>\n{description}"
    
    await update.message.reply_html(
        response,
        disable_web_page_preview=True
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    command = data[0]
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    
    try:
        if command == "list":
            page = int(data[1])
            courses = bot.get_courses(page)
            if not courses:
                await query.edit_message_text("⚠️ Failed to fetch courses. Please try again later.")
                return
                
            total = bot.get_total_courses()
            total_pages = (total // bot.per_page) + (1 if total % bot.per_page else 0) if total > 0 else 1
            
            response = f"📖 <b>Page {page+1}/{total_pages}</b>\n\n"
            for i, course in enumerate(courses, 1):
                title = sanitize_html(course.get('title', 'Untitled Course'))
                coupon = course.get('coupon', '#')
                rating = course.get('rating', 'N/A')
                duration = course.get('duration', 'N/A')
                category = sanitize_html(course.get('category', 'Unknown'))
                
                response += f"<b>{i}. {title}</b>\n"
                response += f"🔗 <code>{coupon}</code>\n"
                response += f"⭐ Rating: {rating} | 🕒 Duration: {duration}h\n"
                response += f"🏷️ Category: {category}\n\n"
            
            keyboard = []
            if page > 0:
                keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list:{page-1}"))
            if page < total_pages - 1:
                keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"list:{page+1}"))
            
            await query.edit_message_text(
                response,
                reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
        elif command == "search":
            search_query = data[1]
            page = int(data[2])
            courses = bot.search_courses(search_query, page)
            
            if not courses:
                await query.edit_message_text("⚠️ No more results found")
                return
                
            response = f"🔍 <b>Results for '{search_query}' (Page {page+1})</b>\n\n"
            for i, course in enumerate(courses, 1):
                title = sanitize_html(course.get('title', 'Untitled Course'))
                coupon = course.get('coupon', '#')
                rating = course.get('rating', 'N/A')
                duration = course.get('duration', 'N/A')
                
                response += f"<b>{i}. {title}</b>\n"
                response += f"🔗 <code>{coupon}</code>\n"
                response += f"⭐ Rating: {rating} | 🕒 Duration: {duration}h\n\n"
            
            keyboard = []
            if page > 0:
                keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search:{search_query}:{page-1}"))
            keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"search:{search_query}:{page+1}"))
            
            await query.edit_message_text(
                response,
                reply_markup=InlineKeyboardMarkup([keyboard]),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
    except Exception as e:
        logger.error(f"Error handling callback: {str(e)}")
        await query.edit_message_text("⚠️ Error loading content. Please try again.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ An error occurred. Please try again later.")


async def check_and_send_new_courses(context: ContextTypes.DEFAULT_TYPE):
    """
    Check for new courses from multiple sources and send them to bridge channel.
    Only sends courses with validated 100% off coupons.
    """
    # Check if fetching is paused
    if context.bot_data.get('fetching_paused', False):
        logger.info("⏸️ Course fetching is paused - skipping this cycle")
        return
    
    # Get bridge channel ID
    bridge_channel_id = os.environ.get('BRIDGE_CHANNEL_ID')
    if not bridge_channel_id:
        logger.warning("❌ BRIDGE_CHANNEL_ID not set - using TARGET_GROUP_ID as fallback")
        bridge_channel_id = os.environ.get('TARGET_GROUP_ID')
        if not bridge_channel_id:
            logger.error("❌ No channel ID configured")
            return
    
    # Initialize sent course IDs cache
    if 'sent_course_ids' not in context.bot_data:
        context.bot_data['sent_course_ids'] = set()
    
    sent_ids = context.bot_data['sent_course_ids']
    new_count = 0
    total_courses = 0
    
    logger.info("🚀 Starting multi-source course fetching...")
    
    # Initialize scraper for validation
    multi_scraper = MultiSourceCouponScraper(validate_coupons=True)
    
    # 1. Fetch from RapidAPI and validate coupons
    rapidapi_courses = []
    api_keys_env = os.environ.get('RAPIDAPI_KEYS')
    if api_keys_env:
        api_keys = api_keys_env.split(',')
        bot = UdemyBot(api_keys)
        
        logger.info("📡 Fetching from RapidAPI...")
        rapidapi_total = 0
        rapidapi_filtered = 0
        
        for page in range(3):
            courses = bot.get_courses(page=page)
            if courses:
                for course in courses:
                    course_url = course.get('coupon', '')
                    if course_url and course_url.startswith('http'):
                        rapidapi_total += 1
                        # Validate coupon before adding to queue
                        if multi_scraper.is_free_coupon(course_url):
                            rapidapi_courses.append({
                                'title': course.get('title', 'Unknown Course'),
                                'url': course_url
                            })
                        else:
                            rapidapi_filtered += 1
        
        logger.info(f"📡 RapidAPI: Validated {len(rapidapi_courses)} of {rapidapi_total} courses ({rapidapi_filtered} filtered out)")
    
    # 2. Fetch from multiple coupon sites with validation enabled
    scraped_courses = []
    
    try:
        scraped_courses = await multi_scraper.scrape_all_sources()
        logger.info(f"🌐 Multi-source scrapers: Found {len(scraped_courses)} validated courses")
    except Exception as e:
        logger.error(f"❌ Multi-source scraping failed: {str(e)}")
    
    # 3. Combine all sources
    all_courses = rapidapi_courses + scraped_courses
    total_courses = len(all_courses)
    
    # 4. Remove duplicates and send new courses
    seen_urls = set()
    for course in all_courses:
        course_url = course['url']
        
        # Skip duplicates within this batch
        if course_url in seen_urls:
            continue
        seen_urls.add(course_url)
        
        # Skip if already sent previously
        if course_url in sent_ids:
            continue
        
        # Send course URL to bridge channel
        try:
            await context.bot.send_message(
                chat_id=bridge_channel_id,
                text=course_url,
                disable_web_page_preview=True
            )
            sent_ids.add(course_url)
            new_count += 1
            logger.info(f"✅ Sent NEW course: {course['title'][:50]}...")
            
            # Delay to avoid Telegram flood control
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"❌ Failed to send: {str(e)}")
    
    # Keep only last 2000 IDs to prevent memory issues
    if len(sent_ids) > 2000:
        context.bot_data['sent_course_ids'] = set(list(sent_ids)[-2000:])
    
    # Update bot statistics
    if 'bot_stats' not in context.bot_data:
        context.bot_data['bot_stats'] = {
            'start_time': datetime.now(),
            'total_runs': 0,
            'total_courses_found': 0,
            'total_courses_sent': 0,
            'rapidapi_courses': 0,
            'scraped_courses': 0,
            'last_run': None
        }
    
    stats = context.bot_data['bot_stats']
    stats['total_runs'] += 1
    stats['total_courses_found'] += total_courses
    stats['total_courses_sent'] += new_count
    stats['rapidapi_courses'] += len(rapidapi_courses)
    stats['scraped_courses'] += len(scraped_courses)
    stats['last_run'] = datetime.now()
    
    logger.info(f"📊 MULTI-SOURCE Summary:")
    logger.info(f"   📚 Total courses found: {total_courses}")
    logger.info(f"   ✅ New courses sent: {new_count}")
    logger.info(f"   🔄 Duplicates skipped: {total_courses - new_count}")
    logger.info(f"   📡 RapidAPI: {len(rapidapi_courses)} courses")
    logger.info(f"   🌐 Scraped (validated): {len(scraped_courses)} courses")


# Admin user ID
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '900041837'))


def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if 'bot_stats' not in context.bot_data:
        await update.message.reply_text("📊 No statistics available yet. Bot hasn't run any cycles.")
        return
    
    stats = context.bot_data['bot_stats']
    start_time = stats.get('start_time', datetime.now())
    uptime = datetime.now() - start_time
    
    # Calculate rates
    hours_running = max(uptime.total_seconds() / 3600, 0.1)
    courses_per_hour = stats['total_courses_sent'] / hours_running
    
    stats_text = f"""📊 **Multi-Source Bot Statistics**

⏰ **Uptime**: {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m

🔄 **Runs**: {stats['total_runs']} cycles completed
📚 **Total Found**: {stats['total_courses_found']} courses
✅ **Total Sent**: {stats['total_courses_sent']} courses
📈 **Success Rate**: {(stats['total_courses_sent']/max(stats['total_courses_found'],1)*100):.1f}%

⚡ **Performance**:
   • {courses_per_hour:.1f} courses/hour
   • {stats['total_courses_sent']/max(stats['total_runs'],1):.1f} courses/run
   • Last run: {stats.get('last_run', 'Never').strftime('%H:%M:%S') if stats.get('last_run') else 'Never'}

📡 **Sources**:
   • RapidAPI: {stats['rapidapi_courses']} courses
   • Scraped (validated): {stats['scraped_courses']} courses"""
    
    # System stats
    try:
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.Process().cpu_percent()
        stats_text += f"\n\n💻 **System**:\n   • Memory: {memory_mb:.1f} MB\n   • CPU: {cpu_percent:.1f}%"
    except:
        pass
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the bot (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    await update.message.reply_text("🔄 Restarting bot... This may take a moment.")
    
    if 'bot_stats' in context.bot_data:
        logger.info("💾 Saving stats before restart...")
    
    os._exit(0)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the bot completely (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    await update.message.reply_text("🛑 Stopping bot... Bot will be offline until manually restarted.")
    
    if 'bot_stats' in context.bot_data:
        stats = context.bot_data['bot_stats']
        logger.info(f"💾 Final stats - Runs: {stats['total_runs']}, Courses sent: {stats['total_courses_sent']}")
    
    logger.info("🛑 Bot stopped by admin command")
    
    await context.application.stop()
    await context.application.shutdown()
    
    os._exit(1)


async def restart_heroku_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart Heroku dyno (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if 'DYNO' not in os.environ:
        await update.message.reply_text("❌ Not running on Heroku. Use /restart instead.")
        return
    
    await update.message.reply_text("🔄 Restarting Heroku dyno... This will take 10-30 seconds.")
    
    try:
        heroku_token = os.environ.get('HEROKU_API_TOKEN')
        app_name = os.environ.get('HEROKU_APP_NAME', 'rapid-api-bot')
        
        if heroku_token:
            import requests
            headers = {
                'Authorization': f'Bearer {heroku_token}',
                'Accept': 'application/vnd.heroku+json; version=3'
            }
            
            response = requests.delete(
                f'https://api.heroku.com/apps/{app_name}/dynos',
                headers=headers
            )
            
            if response.status_code == 202:
                logger.info("✅ Heroku dyno restart initiated via API")
            else:
                logger.warning(f"⚠️ Heroku API restart failed: {response.status_code}")
                raise Exception("API restart failed")
        else:
            raise Exception("No Heroku API token")
            
    except Exception as e:
        logger.warning(f"⚠️ Heroku API restart failed: {e}")
        logger.info("🔄 Falling back to process restart...")
        
        await update.message.reply_text("🔄 API restart failed, using process restart...")
        
        if 'bot_stats' in context.bot_data:
            logger.info("💾 Saving stats before restart...")
        
        os._exit(0)


async def force_run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force run the course fetching cycle (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    await update.message.reply_text("🚀 Starting manual course fetch cycle...")
    
    try:
        await check_and_send_new_courses(context)
        await update.message.reply_text("✅ Manual fetch cycle completed! Check logs for details.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error during manual fetch: {str(e)}")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if 'bot_stats' not in context.bot_data:
        is_paused = context.bot_data.get('fetching_paused', False)
        pause_status = "⏸️ PAUSED" if is_paused else "▶️ Active"
        status_text = f"🤖 **Bot Status**: Starting up\n🔄 **Fetching**: {pause_status}\n📊 No statistics available yet"
    else:
        stats = context.bot_data['bot_stats']
        last_run = stats.get('last_run')
        
        if last_run:
            time_since_last = datetime.now() - last_run
            next_run_in = timedelta(seconds=7200) - time_since_last
            
            if next_run_in.total_seconds() > 0:
                next_run_str = f"{int(next_run_in.total_seconds()//3600)}h {int((next_run_in.total_seconds()//60)%60)}m"
            else:
                next_run_str = "Due now"
        else:
            next_run_str = "Unknown"
        
        is_paused = context.bot_data.get('fetching_paused', False)
        pause_status = "⏸️ PAUSED" if is_paused else "▶️ Active"
        
        status_text = f"""🤖 **Bot Status**: Running

⏰ **Schedule**: Every 2 hours
🔄 **Fetching**: {pause_status}
⏭️ **Next Run**: {next_run_str if not is_paused else 'Paused'}
📊 **Total Runs**: {stats['total_runs']}
✅ **Last Success**: {last_run.strftime('%H:%M:%S') if last_run else 'Never'}

📡 **RapidAPI Courses**: {stats['rapidapi_courses']}
🌐 **Scraped Courses**: {stats['scraped_courses']}
📚 **Total Sent**: {stats['total_courses_sent']}"""
    
    try:
        sent_ids_count = len(context.bot_data.get('sent_course_ids', set()))
        status_text += f"\n💾 **Cache**: {sent_ids_count} course IDs stored"
    except:
        pass
    
    await update.message.reply_text(status_text, parse_mode='Markdown')


async def clear_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the course cache (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if 'sent_course_ids' in context.bot_data:
        cache_size = len(context.bot_data['sent_course_ids'])
        context.bot_data['sent_course_ids'] = set()
        await update.message.reply_text(f"🗑️ Cleared {cache_size} course IDs from cache.\n⚠️ Next run will send all courses as new.")
    else:
        await update.message.reply_text("📭 Cache is already empty.")


async def pause_fetching_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause automatic course fetching (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    context.bot_data['fetching_paused'] = True
    await update.message.reply_text(
        "⏸️ <b>Course fetching paused</b>\n\n"
        "• Automatic scraping is now disabled\n"
        "• Bot will skip all scheduled fetch cycles\n"
        "• Use <code>/resume</code> to re-enable fetching\n"
        "• <code>/forcerun</code> will still work for manual fetches",
        parse_mode='HTML'
    )


async def resume_fetching_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume automatic course fetching (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    context.bot_data['fetching_paused'] = False
    await update.message.reply_text(
        "▶️ <b>Course fetching resumed</b>\n\n"
        "• Automatic scraping is now enabled\n"
        "• Bot will resume normal 2-hour cycles\n"
        "• Next fetch will happen as scheduled",
        parse_mode='HTML'
    )


async def help_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin help (admin only)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    help_text = """🔧 <b>Admin Commands</b>

📊 <code>/stats</code> - Detailed bot statistics
🔄 <code>/restart</code> - Restart the bot process
🛑 <code>/stop</code> - Stop the bot completely
⚡ <code>/restart_heroku</code> - Restart Heroku dyno
🚀 <code>/forcerun</code> - Manual course fetch cycle
📱 <code>/status</code> - Quick bot status
🗑️ <code>/clearcache</code> - Clear course cache
⏸️ <code>/pause</code> - Pause automatic fetching
▶️ <code>/resume</code> - Resume automatic fetching
❓ <code>/adminhelp</code> - This help message

🤖 <b>Bot Info</b>:
• Runs every 2 hours automatically
• Fetches from 5 sources (RapidAPI + 4 scrapers)
• Validates 100% off coupons via Udemy API
• Sends only validated free courses to bridge channel
• Maintains cache to avoid duplicates

⚠️ <b>Notes</b>:
• Only admin can use these commands
• Restart will reset temporary stats
• Clear cache will resend all courses
• Pause/Resume controls automatic fetching only
• Stop command requires manual restart"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')


def main():
    """Main function to run the bot"""
    # Create Telegram Application
    application = Application.builder().token(os.environ['TELEGRAM_TOKEN']).build()
    
    # User command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("count", count))
    application.add_handler(CommandHandler("list", list_courses))
    application.add_handler(CommandHandler("search", search_courses))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # Admin command handlers
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("restart_heroku", restart_heroku_command))
    application.add_handler(CommandHandler("forcerun", force_run_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("clearcache", clear_cache_command))
    application.add_handler(CommandHandler("pause", pause_fetching_command))
    application.add_handler(CommandHandler("resume", resume_fetching_command))
    application.add_handler(CommandHandler("adminhelp", help_admin_command))
    
    # URL handler for group chats
    url_pattern = r'https?://(?:www\.)?udemy\.com/course/[^/]+/?'
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(url_pattern) & filters.ChatType.GROUPS,
        handle_udemy_url
    ))
    
    # Set up periodic job to check for new courses every 2 hours
    job_queue = application.job_queue
    job_queue.run_repeating(
        check_and_send_new_courses,
        interval=7200,  # 2 hours
        first=10  # Start 10 seconds after bot starts
    )
    
    # Start bot
    logger.info("🚀 Multi-Source Udemy Bot is running!")
    logger.info("📊 Checking multiple sources every 2 hours:")
    logger.info("   📡 RapidAPI: 3 pages per check")
    logger.info("   🌐 Real.discount: Free courses")
    logger.info("   🌐 Discudemy: Discounted courses")
    logger.info("   🌐 CourseVania: Course deals")
    logger.info("   🌐 UdemyFreebies: Free courses")
    logger.info("   ✅ Coupon validation: 100% off only")
    logger.info("📊 API Usage: 36 RapidAPI requests/day (within 100/day limit)")
    logger.info("📊 Expected: 50-200+ validated courses per check from all sources")
    logger.info(f"🔧 Admin ID: {ADMIN_USER_ID} (use /adminhelp for commands)")
    application.run_polling()


if __name__ == "__main__":
    main()
