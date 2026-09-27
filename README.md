# ⏱️ ChronoWeather Bot

> Modern asynchronous Telegram bot for real-time weather forecasts, world time tracking with timezone support, and customizable reminders.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://github.com/aiogram/aiogram)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

---

## 🌟 Key Features

- 🌤 **Real-Time Weather:** Live weather data (temperature, feels-like, wind speed, humidity) fetched via OpenWeatherMap API.
- 🕒 **World Time & Timezones:** Displays current local time and converts timestamps across different global timezones.
- 🔔 **Scheduled Reminders:** Asynchronous notifications and task scheduling using `asyncio`.
- 💾 **Persistent Data Storage:** Saves user preferences, chosen cities, and active reminders in a local SQLite database.
- ⚡ **Asynchronous & Fast:** Built on top of `aiogram 3.x` framework for non-blocking message processing.

---

## 🛠 Tech Stack

- **Language:** Python 3.11+
- **Framework:** [aiogram 3.x](https://docs.aiogram.dev/)
- **Database:** SQLite / aiosqlite (Async CRUD)
- **Networking:** [aiohttp](https://docs.aiohttp.org/) / [httpx](https://www.python-httpx.org/)
- **External API:** OpenWeatherMap API

---

## 🚀 Getting Started

### 1. Clone the repository

``` Bash
git clone https://github.com/Nortueso/chrono-weather-bot.git

cd chrono-weather-bot
```
### 2. Create and activate a virtual environment
``` Bash

python3 -m venv .venv

source .venv/bin/activate
```
### 3. Install dependencies
``` Bash
pip install -r requirements.txt
```
### 4. Setup Environment Variables
Create a `.env` file in the root folder based on `.env.example`:
```env

BOT_TOKEN=your_telegram_bot_token

WEATHER_API_KEY=your_openweathermap_api_key
```
### 5. Run the bot
```bash
python3 botmain01.py
```
---

## 📂 Project Architecture
```text

chrono-weather-bot/
├── src/
│   ├── handlers/       # Command & message routers (/start, /weather, /time)
│   ├── keyboards/      # Inline and reply keyboard layouts
│   ├── services/       # External Weather API & Timezone utilities
│   ├── database/
       # Database connection & models
│   └── config.py       # Configuration settings (.env parser)
├── .env.example        # Environment template
├── .gitignore          # Ignored files (venv, .env, pycache)
├── requirements.txt    # Project dependencies
├── README.md           # Documentation
└── main.py             # Entrypoint

---

## 📌 Usage Commands

* `/start` — Launch the bot and show the main navigation menu
* `/weather [city]` — Get current weather report for a specified city
* `/time [city/timezone]` — Get precise local time
* `/remind [HH:MM] [text]` — Schedule a personal reminder notification
* `/help` — Display list of commands and features

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
https://github.com/Nortueso/chrono-weather-bot.git
