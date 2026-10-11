# 🌦 Chrono Weather Bot 1.0

A Telegram bot that shows **weather**, **local time** and sends **reminders** that survive restarts. Each user has their own saved city and time zone.

Built with Python, [aiogram 3](https://docs.aiogram.dev/), `aiohttp`, SQLite and the [OpenWeather](https://openweathermap.org/api) API.

---

## ✨ Features

- 🌍 **Current weather** for any city: temperature, "feels like", conditions, wind, humidity
- 🏙 **Saved city**: type `/weather` with no arguments and get your own city
- 🕒 **Local time** in your time zone, switchable with inline buttons
- ⏰ **Reminders** in several formats (relative time, time of day, exact date)
- 💾 **Persistent storage**: cities, time zones and reminders live in SQLite
- 🛡 **Friendly errors**: unknown city, invalid API key, timeouts and bad input never crash the bot

---

## 💬 Commands

| Command | Description |
|---|---|
| `/start` | Greeting and list of commands |
| `/weather [city]` | Weather for the given city, or for your saved city |
| `/setcity` | Change your saved city |
| `/time` | Current date and time in your time zone |
| `/remind <when> <text>` | Create a reminder |
| `/reminders` | List your active reminders |
| `/delremind <number>` | Delete a reminder by its number |
| `/cancel` | Cancel the current action |

### Reminder formats

```text
/remind 30m drink water          → in 30 minutes   (m = minutes)
/remind 2h call mom              → in 2 hours      (h = hours)
/remind 1d pay rent              → in 1 day        (d = days)
/remind 18:30 workout            → today at 18:30 (tomorrow if it has passed)
/remind 25.12 09:00 congratulate → on 25 December at 09:00 (DD.MM)
```

All times are interpreted in **your** time zone (change it with the ⚙️ button under any message).

---

## 🧠 How it works

```text
Telegram ──polling──▶ aiogram Dispatcher ──▶ handlers ──▶ SQLite
                                                │
                                                └──▶ OpenWeather API (aiohttp)

reminder_loop (background task, every 20 s) ──▶ SQLite ──▶ send due reminders
```

- **Polling**: the bot repeatedly asks Telegram for new updates. No public URL is required.
- **Async everywhere**: handlers and API calls use `async`/`await`, so one slow request doesn't block other users.
- **Weather**: the city name is first resolved to coordinates (OpenWeather Geocoding API), then the weather is requested by coordinates. This is more reliable than querying by name.
- **FSM**: after "Change city" the bot enters a `waiting_for_city` state, so the next message is treated as a city name.
- **Reminders**: stored in **UTC** in SQLite. A background task checks the database every 20 seconds and sends everything that is due, so reminders are not lost if the bot restarts.

---

## 🚀 Quick start

### 1. Requirements

- Python 3.10+
- A bot token from [@BotFather](https://t.me/BotFather)
- A free API key from [OpenWeather](https://openweathermap.org/api)
  (a new key can take from several minutes to a couple of hours to activate)

### 2. Install

```bash
git clone https://github.com/<your-username>/chrono-weather-bot.git
cd chrono-weather-bot

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure

Create a `.env` file next to `main.py` (no quotes, no spaces around `=`):

```dotenv
BOT_TOKEN=your_telegram_bot_token
WEATHER_API_KEY=your_openweather_api_key
```

### 4. Run

```bash
python main.py
```

You should see `Start polling` in the log. Open your bot in Telegram and send `/start`.

---

## 📦 `requirements.txt`

```text
aiogram>=3.0
aiohttp
pytz
python-dotenv
```

---

## 🗂 Project structure

```text
chrono-weather-bot/
├── main.py            # the whole bot, split into numbered sections
├── requirements.txt
├── .env               # secrets (never commit this!)
├── .gitignore
└── users_settings.db  # created automatically on first run
```

`main.py` sections: settings → database → keyboards → weather → reminder parser → handlers → background scheduler → entry point.

Recommended `.gitignore`:

```text
.env
.venv/
*.db
__pycache__/
```

---

## ☁️ Deployment notes

- **VPS** (recommended): run with `systemd`, `tmux` or Docker. The SQLite file stays on disk.
- **Render / similar PaaS**:
  - A *Background Worker* needs no port. A *Web Service* requires the app to listen on `$PORT`, otherwise the deploy times out.
  - Free tiers usually have an **ephemeral disk**: `users_settings.db` is wiped on every restart, so saved cities, time zones and reminders disappear. Use a persistent disk or an external database (e.g. PostgreSQL).
  - Set `BOT_TOKEN` and `WEATHER_API_KEY` in the service's *Environment* settings, **without quotes**.
- Only **one** running instance may use a given bot token. A second one causes `Conflict: terminated by other getUpdates request`.

---

## 🛠 Troubleshooting

| Problem | Likely cause |
|---|---|
| `Unauthorized` on start | Wrong, truncated or revoked bot token. A valid token is usually 46 characters |
| `BOT_TOKEN not found` | `.env` missing, in the wrong folder, or the variable is misspelled |
| Weather says the API key was rejected | The key is wrong or not activated yet, wait a while |
| `/remind` doesn't fire | Check the log for errors from `reminder_loop`; make sure the bot process is running |
| Time is off by some hours | Pick your time zone with ⚙️ **Change time zone** |

---

## 🗺 Roadmap

- [ ] Choose between several cities with the same name
- [ ] Daily morning weather digest
- [ ] Repeating reminders (daily / weekly)
- [ ] Weather forecast for the next days
- [ ] Detect time zone from a shared location
- [ ] Move to PostgreSQL / `aiosqlite`
- [ ] Split `main.py` into modules and add tests

---

## 📄 License

MIT. Use it, learn from it, improve it.
