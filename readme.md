# 📚 CourseHunt Rapid API Bot

A powerful **Telegram bot** for finding and sharing online courses across multiple platforms using **Rapid API**. The bot searches courses from various platforms, provides detailed information, and offers a seamless way to discover educational content.

![CourseHunt Bot](https://img.shields.io/badge/CourseHunt-Telegram%20Bot-blue)

---

## 🚀 Features

### 🔍 Course Search
- **Multi-Platform Course Search**: Find courses across multiple e-learning platforms with a single query.
- **Detailed Course Information**: Get comprehensive details including price, ratings, instructor information, and more.
- **Filter Options**: Narrow down results by price range, platform, rating, and other criteria.

### 💬 Telegram Integration
- **User-Friendly Interface**: Simple commands and intuitive navigation.
- **Rich Media Support**: View course details with images and formatted text.
- **Quick Access**: Direct links to enroll in courses that interest you.
- **Interactive Filters**: Refine your search through interactive Telegram buttons.

### 🎓 Platform Support
- **Udemy Integration**: Access thousands of Udemy courses.
- **Coursera Coverage**: Find courses from Coursera's extensive catalog.
- **Multiple Providers**: Additional support for other major learning platforms.

### 👤 User Experience
- **Personalized Recommendations**: Get course suggestions based on your interests.
- **Search History**: Easily access your recent searches.
- **Bookmark System**: Save courses for later viewing.
- **Clean Presentation**: Well-formatted course information for easy reading.

### ⚙️ Technical Features
- **API Efficiency**: Optimized API calls to Rapid API.
- **Error Handling**: Graceful recovery from API limitations or errors.
- **Response Time**: Fast and responsive user experience.
- **Service Reliability**: Stable operation with high uptime.

---

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and get welcome information |
| `/help` | Display available commands and usage instructions |
| `/search [query]` | Search for courses with the specified query |
| `/filter` | Access filtering options for your search results |
| `/popular` | View trending and popular courses |

---

## 🛠️ Technology Stack

- Node.js
- Telegram Bot API
- Rapid API (for accessing course data)
- Heroku (deployment)

---

## 🔧 Installation and Local Development

### Prerequisites
- Node.js v14+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Rapid API subscription

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/manishgupta2026/CourseHunt-Rapid-Api-Bot.git
   cd CourseHunt-Rapid-Api-Bot
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Create a `.env` file with your API credentials:**

   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   RAPIDAPI_KEY=your_rapidapi_key
   ```

4. **Start the development server:**

   ```bash
   npm start
   ```

---

## 🚀 Deployment (Heroku)

1. Create a [Heroku](https://heroku.com) account and install the Heroku CLI.

2. **Login to Heroku:**

   ```bash
   heroku login
   ```

3. **Create a new Heroku app:**

   ```bash
   heroku create
   ```

4. **Set environment variables:**

   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token
   heroku config:set RAPIDAPI_KEY=your_rapidapi_key
   ```

5. **Deploy to Heroku:**

   ```bash
   git push heroku main
   ```

---

## 👥 Contributing

Contributions are welcome!
Please feel free to fork the project and submit a [Pull Request](https://github.com/your-username/coursehunt-bot/pulls).

---

## 📝 License

This project is licensed under the **MIT License**.
See the [LICENSE](LICENSE) file for details.

---

## 🔍 Acknowledgements

* [Telegram Bot API](https://core.telegram.org/bots/api)
* [Rapid API](https://rapidapi.com/)
* All the amazing e-learning platforms that make education accessible.

---

## 👨‍💻 Author

Created by **Manish Gupta** for CourseHunt
**Last updated:** June 18, 2025

```

---

Let me know if you’d also like a sample `.env` file or a [deploy-to-Heroku button](f) added directly in the README!
