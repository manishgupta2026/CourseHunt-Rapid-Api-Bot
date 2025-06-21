import os
import http.client
import json
from html import escape
from datetime import time, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

class UdemyBot:
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
        print(f"Rotated to API key #{self.current_key_index + 1}")

    def _make_request(self, endpoint):
        for attempt in range(len(self.api_keys)):
            try:
                conn = http.client.HTTPSConnection(self.host)
                conn.request("GET", endpoint, headers=self._get_headers())
                res = conn.getresponse()
                
                if res.status == 200:
                    return json.loads(res.read().decode('utf-8'))
                elif res.status == 429:  # Rate limit exceeded
                    print(f"Rate limit hit on key #{self.current_key_index + 1}")
                    self._rotate_key()
                else:
                    print(f"API error {res.status}: {res.reason}")
            except Exception as e:
                print(f"Connection error: {str(e)}")
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
    
    def get_top_courses(self):
        """Get top 20 courses without pagination"""
        return self._make_request(f"{self.base_path}?page=0&limit=20") or []

def sanitize_html(text):
    return escape(text).replace("&amp;", "&") if text else ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    total = bot.get_total_courses()
    await update.message.reply_text(f"📚 Total courses available: {total}")

async def list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        print(f"Failed to send message: {str(e)}")
        plain_response = f"Page {page+1}/{total_pages}\n\n"
        for i, course in enumerate(courses, 1):
            plain_response += f"{i}. {course.get('title', 'Untitled Course')}\n"
            plain_response += f"URL: {course.get('coupon', 'Not available')}\n"
            plain_response += f"Rating: {course.get('rating', 'N/A')} | Duration: {course.get('duration', 'N/A')}h\n"
            plain_response += f"Category: {course.get('category', 'Unknown')}\n\n"
        await update.message.reply_text(plain_response)

async def search_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        print(f"Failed to send message: {str(e)}")
        plain_response = f"Results for '{query}' (Page {page+1})\n\n"
        for i, course in enumerate(courses, 1):
            plain_response += f"{i}. {course.get('title', 'Untitled Course')}\n"
            plain_response += f"URL: {course.get('coupon', 'Not available')}\n"
            plain_response += f"Rating: {course.get('rating', 'N/A')} | Duration: {course.get('duration', 'N/A')}h\n\n"
        await update.message.reply_text(plain_response)

async def handle_udemy_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        print(f"Error handling callback: {str(e)}")
        await query.edit_message_text("⚠️ Error loading content. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")
    if update.message:
        await update.message.reply_text("⚠️ An error occurred. Please try again later.")

async def send_daily_courses_to_group(context: ContextTypes.DEFAULT_TYPE):
    """Send top 20 courses as separate messages to a group"""
    api_keys = os.environ['RAPIDAPI_KEYS'].split(',')
    bot = UdemyBot(api_keys)
    courses = bot.get_top_courses()
    
    if not courses:
        print("Failed to fetch courses for daily group update")
        return
    
    # Get target group ID from environment variables
    try:
        group_id = int(os.environ['TARGET_GROUP_ID'])
    except (KeyError, ValueError):
        print("TARGET_GROUP_ID not set or invalid")
        return
    
    # Send each course URL as a separate message
    for course in courses:
        url = course.get('coupon', '')
        if not url.startswith('http'):
            continue  # Skip invalid URLs
            
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=url,
                disable_web_page_preview=False,
                disable_notification=True
            )
            print(f"Sent URL: {url}")
        except Exception as e:
            print(f"Failed to send URL: {str(e)}")
    
    print(f"Sent {len(courses)} course URLs to group {group_id}")

def main():
    # Create Telegram Application
    application = Application.builder().token(os.environ['TELEGRAM_TOKEN']).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("count", count))
    application.add_handler(CommandHandler("list", list_courses))
    application.add_handler(CommandHandler("search", search_courses))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # Add URL handler for group chats
    url_pattern = r'https?://(?:www\.)?udemy\.com/course/[^/]+/?'
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(url_pattern) & filters.ChatType.GROUPS,
        handle_udemy_url
    ))
    
    # Set up daily job (1 PM IST = 7:30 AM UTC)
    job_queue = application.job_queue
    job_queue.run_daily(
        send_daily_courses_to_group,
        time(hour=7, minute=30, tzinfo=timezone.utc),  # 7:30 AM UTC = 1 PM IST
        days=tuple(range(7))  # Every day of the week
    )
    
    # Start bot
    print("Bot is running with daily course delivery to group...")
    application.run_polling()

if __name__ == "__main__":
    main()
