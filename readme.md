# 📚 CourseHunt - Free Udemy Course Bot

A powerful **Python Telegram bot** that automatically finds and shares **100% free Udemy courses** from multiple sources. The bot scrapes coupon sites, validates that coupons are truly 100% off via the Udemy API, and sends verified free courses to your Telegram channel.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Features

### 🔍 Multi-Source Course Scraping
- **RapidAPI Integration**: Fetches courses from the Udemy coupon API
- **Real.discount**: Scrapes free courses from Real.discount
- **Discudemy**: Scrapes discounted courses from Discudemy
- **CourseVania**: Fetches course deals from CourseVania
- **UdemyFreebies**: Scrapes free courses from UdemyFreebies

### ✅ 100% Off Coupon Validation
- **Udemy API Validation**: Every coupon is verified via Udemy's API
- **Only Free Courses**: Only courses with `discount_percent == 100` are sent
- **No Expired Coupons**: Validates before sending to ensure coupons work

### 📡 Automatic Channel Updates
- **Scheduled Fetching**: Automatically checks for new courses every 2 hours
- **Duplicate Prevention**: Maintains cache to avoid sending same course twice
- **Clean URLs**: Sends only the course URL without extra metadata

### 🔧 Admin Controls
- **Pause/Resume**: Control automatic fetching without stopping the bot
- **Manual Trigger**: Force run a fetch cycle on demand
- **Statistics**: View detailed bot performance metrics
- **Cache Management**: Clear cache to resend all courses

---

## 📋 Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and get welcome message |
| `/help` | Display available commands |
| `/list` | Browse courses with pagination |
| `/search [query]` | Search for specific courses (e.g., `/search python`) |
| `/count` | Show total available courses |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/stats` | Detailed bot statistics (uptime, courses sent, etc.) |
| `/status` | Quick bot status overview |
| `/forcerun` | Manually trigger course fetch cycle |
| `/pause` | Pause automatic course fetching |
| `/resume` | Resume automatic course fetching |
| `/clearcache` | Clear sent course IDs cache |
| `/restart` | Restart the bot process |
| `/stop` | Stop the bot completely |
| `/restart_heroku` | Restart Heroku dyno |
| `/adminhelp` | Show all admin commands |

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| Bot Framework | python-telegram-bot 20.3 |
| HTTP Client | requests, cloudscraper |
| HTML Parser | BeautifulSoup4, lxml |
| Scheduling | APScheduler (via python-telegram-bot job-queue) |
| Deployment | Heroku |

---

## 📁 Project Structure

```
CourseHunt-Rapid-Api-Bot/
├── bot.py                    # Main Telegram bot with commands and scheduling
├── multi_source_scraper.py   # Multi-source scraper with coupon validation
├── requirements.txt          # Python dependencies
├── runtime.txt               # Python version for Heroku
├── Procfile                  # Heroku process configuration
└── readme.md                 # This file
```

---

## 🔧 Installation

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- RapidAPI Key (from [RapidAPI](https://rapidapi.com/))
- Telegram Channel/Group ID

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/manishgupta2026/CourseHunt-Rapid-Api-Bot.git
   cd CourseHunt-Rapid-Api-Bot
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   ```bash
   export TELEGRAM_TOKEN=your_bot_token
   export RAPIDAPI_KEYS=key1,key2,key3
   export BRIDGE_CHANNEL_ID=your_channel_id
   export ADMIN_USER_ID=your_telegram_user_id
   ```

5. **Run the bot:**
   ```bash
   python bot.py
   ```

---

## 🚀 Heroku Deployment

1. **Create Heroku app:**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables:**
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_bot_token
   heroku config:set RAPIDAPI_KEYS=key1,key2,key3
   heroku config:set BRIDGE_CHANNEL_ID=your_channel_id
   heroku config:set ADMIN_USER_ID=your_telegram_user_id
   ```

3. **Deploy:**
   ```bash
   git push heroku main
   ```

4. **Scale worker dyno:**
   ```bash
   heroku ps:scale worker=1
   ```

5. **View logs:**
   ```bash
   heroku logs --tail
   ```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_TOKEN` | ✅ | Bot token from @BotFather |
| `RAPIDAPI_KEYS` | ✅ | Comma-separated RapidAPI keys |
| `BRIDGE_CHANNEL_ID` | ✅ | Telegram channel ID for course posts |
| `ADMIN_USER_ID` | ✅ | Your Telegram user ID for admin commands |
| `TARGET_GROUP_ID` | ❌ | Fallback channel ID |
| `HEROKU_API_TOKEN` | ❌ | For `/restart_heroku` command |
| `HEROKU_APP_NAME` | ❌ | Your Heroku app name |

---

## 📊 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    COURSE PIPELINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. FETCH FROM SOURCES (Every 2 hours)                      │
│     ├── RapidAPI (3 pages)                                  │
│     ├── Real.discount                                       │
│     ├── Discudemy                                           │
│     ├── CourseVania                                         │
│     └── UdemyFreebies                                       │
│                    │                                        │
│                    ▼                                        │
│  2. VALIDATE 100% OFF                                       │
│     └── Udemy API: Check discount_percent == 100            │
│                    │                                        │
│                    ▼                                        │
│  3. DEDUPLICATE                                             │
│     └── Remove duplicate URLs                               │
│                    │                                        │
│                    ▼                                        │
│  4. FILTER ALREADY SENT                                     │
│     └── Check against cache (last 2000 URLs)                │
│                    │                                        │
│                    ▼                                        │
│  5. SEND TO TELEGRAM                                        │
│     └── Post clean URL to bridge channel                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Fetch Interval | Every 2 hours (12 times/day) |
| RapidAPI Usage | ~36 requests/day (within free tier) |
| Expected Courses | 50-200+ validated courses per cycle |
| Cache Size | Last 2000 course URLs |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [RapidAPI](https://rapidapi.com/)
- [Real.discount](https://www.real.discount/)
- [Discudemy](https://www.discudemy.com/)
- [CourseVania](https://coursevania.com/)
- [UdemyFreebies](https://www.udemyfreebies.com/)

---

## 👨‍💻 Author

Created by **Manish Gupta**

**Last updated:** December 10, 2025
