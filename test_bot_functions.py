#!/usr/bin/env python3
"""
Test bot functions without running the full bot
"""

import os
import sys
from unittest.mock import Mock

# Set required environment variables for testing
os.environ['TELEGRAM_TOKEN'] = 'test_token'
os.environ['RAPIDAPI_KEYS'] = 'test_key1,test_key2'
os.environ['BRIDGE_CHANNEL_ID'] = '-1003312906833'
os.environ['ADMIN_USER_ID'] = '900041837'

# Import bot components
from bot import UdemyBot, sanitize_html, is_admin, ADMIN_USER_ID

def test_udemy_bot():
    """Test UdemyBot class initialization"""
    print("🧪 Testing UdemyBot class...")
    
    api_keys = ['key1', 'key2']
    bot = UdemyBot(api_keys)
    
    assert bot.api_keys == api_keys
    assert bot.current_key_index == 0
    assert bot.host == "paid-udemy-course-for-free.p.rapidapi.com"
    
    print("✅ UdemyBot initialization works")

def test_sanitize_html():
    """Test HTML sanitization"""
    print("🧪 Testing HTML sanitization...")
    
    test_cases = [
        ("Hello <script>alert('xss')</script>", "Hello &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"),
        ("Test & Company", "Test & Company"),
        (None, ""),
        ("", "")
    ]
    
    for input_text, expected in test_cases:
        result = sanitize_html(input_text)
        assert result == expected, f"Expected '{expected}', got '{result}'"
    
    print("✅ HTML sanitization works")

def test_admin_check():
    """Test admin user verification"""
    print("🧪 Testing admin verification...")
    
    # Test admin user
    assert is_admin(900041837) == True
    
    # Test non-admin user
    assert is_admin(123456789) == False
    
    print(f"✅ Admin check works (Admin ID: {ADMIN_USER_ID})")

def test_imports():
    """Test that all imports work"""
    print("🧪 Testing imports...")
    
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler
        from multi_source_scraper import MultiSourceCouponScraper
        import psutil
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Testing bot components...\n")
    
    try:
        test_imports()
        test_udemy_bot()
        test_sanitize_html()
        test_admin_check()
        
        print("\n🎉 All tests passed! Bot components are working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)