import os
import http.client
import json
from html import escape
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import time, timezone

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
/testbot - Send a test message to the target bot
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
    url_list = "🔗 <b>Raw URLs:</b>\n"
    
    for i, course in enumerate(courses, 1):
        title = sanitize_html(course.get('title', 'Untitled Course'))
        coupon = course.get('coupon', '#')
        rating = course.get('rating', 'N/A')
        duration = course.get('duration', 'N/A')
        category = sanitize_html(course.get('category', 'Unknown'))
        
        response += f"<b>{i}. {title}</b>\n"
        response += f"⭐ Rating: {rating} | 🕒 Duration: {duration}h\n"
        response += f"🏷️ Category: {category}\n\n"
        
        url_list += f"{i}. <code>{coupon}</code>\n"
    
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"list:{page-1}"))
    if page < total_pages - 1:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"list:{page+1}"))
    
    try:
        # Send main course info
        await update.message.reply_html(
            response,
            reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None,
            disable_web_page_preview=True
        )
        
        # Send raw URLs separately
        await update.message.reply_html(
            url_list,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Failed to send message: {str(e)}")
        # Fallback implementation
        plain_response = f"Page {page+1}/{total_pages}\n\n"
        for i, course in enumerate(courses, 1):
            plain_response += f"{i}. {course.get('title', 'Untitled Course')}\n"
            plain_response += f"Rating: {course.get('rating', 'N/A')} | Duration: {course.get('duration', 'N/A')}h\n"
            plain_response += f"Category: {course.get('category', 'Unknown')}\n"
            plain_response += f"URL: {course.get('coupon', 'Not available')}\n\n"
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
    url_list = "🔗 <b>Raw URLs:</b>\n"
    
    for i, course in enumerate(courses, 1):
        title = sanitize_html(course.get('title', 'Untitled Course'))
        coupon = course.get('coupon', '#')
        rating = course.get('rating', 'N/A')
        duration = course.get('duration', 'N/A')
        
        response += f"<b>{i}. {title}</b>\n"
        response += f"⭐ Rating: {rating} | 🕒 Duration: {duration}h\n\n"
        
        url_list += f"{i}. <code>{coupon}</code>\n"
    
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search:{query}:{page-1}"))
    keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"search:{query}:{page+1}"))
    
    try:
        # Send main course info
        await update.message.reply_html(
            response,
            reply_markup=InlineKeyboardMarkup([keyboard]),
            disable_web_page_preview=True
        )
        
        # Send raw URLs separately
        await update.message.reply_html(
            url_list,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Failed to send message: {str(e)}")
        plain_response = f"Results for '{query}' (Page {page+1})\n\n"
        for i, course in enumerate(courses, 1):
            plain_response += f"{i}. {course.get('title', 'Untitled Course')}\n"
            plain_response += f"Rating: {course.get('rating', 'N/A')} | Duration: {course.get('duration', 'N/A')}h\n"
            plain_response += f"URL: {course.get('coupon', 'Not available')}\n\n"
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

async def initialize_bot_chat(context: ContextTypes.DEFAULT_TYPE):
    """Force-create a chat session between bots"""
    target_bot_id = 7826136340
    try:
        # Send a dummy message to establish chat
        await context.bot.send_message(
            chat_id=target_bot_id,
            text="🤖 Chat session initialized",
            disable_notification=True
        )
        print("Bot chat session established successfully")
    except Exception as e:
        print(f"Initialization failed: {str(e)}")

async def send_daily_courses(context: ContextTypes.DEFAULT_TYPE):
    target_bot_id = 7826136340
    urls = "\n".join(get_top_20_courses())  # Your course fetching logic
    
    try:
        # Attempt to send URLs
        await context.bot.send_message(
            chat_id=target_bot_id,
            text=urls,
            disable_notification=True,
            disable_web_page_preview=True
        )
        print(f"Successfully sent to bot {target_bot_id}")
    except Exception as e:
        print(f"Failed to send: {str(e)}\nReinitializing chat...")
        await initialize_bot_chat(context)  # Auto-recover chat session

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

def main():
    # Create Telegram Application
    application = Application.builder().token(os.environ['TELEGRAM_TOKEN']).build()

    application.job_queue.run_once(initialize_bot_chat, when=0)
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("count", count))
    application.add_handler(CommandHandler("list", list_courses))
    application.add_handler(CommandHandler("search", search_courses))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("testbot", test_bot_message))

    # Daily 1AM IST (7:30PM UTC) delivery
    application.job_queue.run_daily(
        send_daily_courses,
        time(hour=19, minute=30, tzinfo=timezone.utc),
        days=tuple(range(7))
    )

    # Start bot
    print("Bot is running with daily course delivery to target bot...")
    application.run_polling()
    
    # Start bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()