#  |-----------------------------------------------------|
#  | \                                                 / |
#  |  \/-27|09|2026-------------------------------16-\/  |
#  |   |                                             |   |
#  |   |----->___(Chrono-Weather-Bot-1-0)___ <-------|   |
#  |   |                                             |   |
#  |  /\-11:05-----------------------------------182-/\  |
#  | /                                                 \ |
#  |-----------------------------------------------------|



#1st----------> libs/modules

import asyncio
import html
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta

import aiohttp
import pytz
from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

#1fn----------> libs/modules



#2st----------> logging

logging.basicConfig(level=logging.INFO)

#2fn----------> logging



#3st----------> bot settings

load_dotenv(override=True)

TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not found. Add it to the .env file.")
if not WEATHER_API_KEY:
    raise RuntimeError("WEATHER_API_KEY not found. Add it to the .env file.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

#3fn----------> bot settings



#4st----------> database (SQLite)

DB_NAME = "users_settings.db"
DB_TIME_FMT = "%Y-%m-%d %H:%M:%S"  # reminders are stored in UTC in this format
DEFAULT_TZ = "UTC"


def init_db():
    """Creates all tables. Safe to call on every start."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT '{DEFAULT_TZ}',
                city TEXT
            )
        ''')
        # CREATE TABLE IF NOT EXISTS does not change an existing table,
        # so for an old database we add the missing column ourselves.
        columns = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
        if "city" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN city TEXT")

        conn.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                remind_at_utc TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            )
        ''')


def get_user_timezone(user_id: int) -> str:
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT timezone FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row[0] if row and row[0] else DEFAULT_TZ


def update_user_timezone(user_id: int, timezone: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT INTO users (user_id, timezone) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET timezone = excluded.timezone
        ''', (user_id, timezone))


def get_user_city(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute(
            "SELECT city FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row[0] if row else None


def update_user_city(user_id: int, city: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT INTO users (user_id, timezone, city) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET city = excluded.city
        ''', (user_id, DEFAULT_TZ, city))


def add_reminder(user_id: int, text: str, when_utc: datetime) -> int:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "INSERT INTO reminders (user_id, text, remind_at_utc) VALUES (?, ?, ?)",
            (user_id, text, when_utc.strftime(DB_TIME_FMT)),
        )
        return cur.lastrowid


def get_due_reminders() -> list:
    now = datetime.now(pytz.utc).strftime(DB_TIME_FMT)
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute(
            "SELECT id, user_id, text FROM reminders WHERE sent = 0 AND remind_at_utc <= ?",
            (now,),
        ).fetchall()


def mark_reminder_sent(reminder_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))


def get_user_reminders(user_id: int) -> list:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute(
            "SELECT id, text, remind_at_utc FROM reminders "
            "WHERE user_id = ? AND sent = 0 ORDER BY remind_at_utc",
            (user_id,),
        ).fetchall()


def delete_reminder(reminder_id: int, user_id: int) -> bool:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ? AND sent = 0",
            (reminder_id, user_id),
        )
        return cur.rowcount > 0

#4fn----------> database (SQLite)



#5st----------> keyboards

TIMEZONES = [
    ("Kaliningrad (UTC+2)", "Europe/Kaliningrad"),
    ("Moscow (UTC+3)", "Europe/Moscow"),
    ("Samara (UTC+4)", "Europe/Samara"),
    ("Baku (UTC+4)", "Asia/Baku"),
    ("Yekaterinburg (UTC+5)", "Asia/Yekaterinburg"),
    ("Tashkent (UTC+5)", "Asia/Tashkent"),
    ("Dushanbe (UTC+5)", "Asia/Dushanbe"),
    ("Almaty (UTC+5)", "Asia/Almaty"),
    ("Bishkek (UTC+6)", "Asia/Bishkek"),
    ("UTC", "UTC"),
]
VALID_TZ = {tz_name for _, tz_name in TIMEZONES}


def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏙 Change city", callback_data="change_city")
    builder.button(text="⚙️ Change time zone", callback_data="change_tz")
    builder.adjust(1)
    return builder.as_markup()


def get_tz_keyboard():
    builder = InlineKeyboardBuilder()
    for label, tz_name in TIMEZONES:
        builder.button(text=label, callback_data=f"set_tz:{tz_name}")
    builder.adjust(2)
    return builder.as_markup()

#5fn----------> keyboards



#6st----------> weather (OpenWeather)

GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherError(Exception):
    """An error whose text is safe and clear enough to show to the user (HTML)."""


async def geocode_city(session: aiohttp.ClientSession, city: str) -> dict:
    """City name -> coordinates. Returns an empty list from the API if not found."""
    params = {"q": city, "limit": 1, "appid": WEATHER_API_KEY}
    async with session.get(GEO_URL, params=params) as resp:
        if resp.status == 401:
            raise WeatherError("Weather API key was rejected (a new key can take a while to activate).")
        if resp.status != 200:
            raise WeatherError(f"Geocoding service returned error {resp.status}.")
        data = await resp.json()
    if not data:
        raise WeatherError(f"City «{html.escape(city)}» not found. Check the spelling.")
    return data[0]


async def get_weather(city: str) -> str:
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            place = await geocode_city(session, city)
            params = {
                "lat": place["lat"],
                "lon": place["lon"],
                "appid": WEATHER_API_KEY,
                "units": "metric",
                "lang": "en",
            }
            async with session.get(WEATHER_URL, params=params) as resp:
                if resp.status == 401:
                    raise WeatherError("Weather API key was rejected (a new key can take a while to activate).")
                if resp.status != 200:
                    raise WeatherError(f"Weather service returned error {resp.status}.")
                data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise WeatherError("Weather service is not responding, try again later.") from exc

    try:
        main = data["main"]
        description = data["weather"][0]["description"].capitalize()
        wind = data.get("wind", {}).get("speed", 0)
        return (
            f"🌍 {html.escape(place['name'])}, {html.escape(place.get('country', ''))}\n"
            f"🌡 {main['temp']:.0f}°C (feels like {main['feels_like']:.0f}°C)\n"
            f"☁️ {html.escape(description)}\n"
            f"💨 Wind: {wind} m/s\n"
            f"💧 Humidity: {main['humidity']}%"
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise WeatherError("Weather service returned an unexpected answer.") from exc

#6fn----------> weather (OpenWeather)



#7st----------> reminder time parser

UNITS = {"m": "minutes", "h": "hours", "d": "days"}
MAX_REMINDER_TEXT = 500


def parse_reminder(args: str, tz) -> tuple:
    """Returns (time in UTC, text). Raises ValueError / OverflowError on bad input."""
    args = args.strip()
    now = datetime.now(tz)

    # Variant 1: in N minutes/hours/days  ->  30m, 2h, 1d
    m = re.match(r"^(\d+)([mhd])\s+(.+)$", args, re.S | re.I)
    if m:
        amount, unit, text = int(m[1]), UNITS[m[2].lower()], m[3]
        target = now + timedelta(**{unit: amount})  # OverflowError if the number is absurd
        return target.astimezone(pytz.utc), text

    # Variant 2: today (or tomorrow if already passed) at HH:MM  ->  18:30
    m = re.match(r"^(\d{1,2}):(\d{2})\s+(.+)$", args, re.S)
    if m:
        hour, minute, text = int(m[1]), int(m[2]), m[3]
        naive = datetime(now.year, now.month, now.day, hour, minute)  # ValueError for 25:99
        target = tz.localize(naive)
        if target <= now:
            target = tz.localize(naive + timedelta(days=1))
        return target.astimezone(pytz.utc), text

    # Variant 3: exact date DD.MM HH:MM  ->  25.12 09:00
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})\s+(.+)$", args, re.S)
    if m:
        day, month, hour, minute, text = (int(m[1]), int(m[2]), int(m[3]), int(m[4]), m[5])
        target = tz.localize(datetime(now.year, month, day, hour, minute))
        if target <= now:
            target = tz.localize(datetime(now.year + 1, month, day, hour, minute))
        return target.astimezone(pytz.utc), text

    raise ValueError("bad format")

#7fn----------> reminder time parser



#8st----------> handlers: start / time / time zone

class WeatherStates(StatesGroup):
    waiting_for_city = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Hello! I show weather and time, and I can remind you of things.\n\n"
        "/weather [city] - current weather\n"
        "/setcity - change your saved city\n"
        "/time - your local time\n"
        "/remind - create a reminder\n"
        "/reminders - list reminders\n"
        "/cancel - cancel the current action",
        reply_markup=get_main_keyboard(),
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.", reply_markup=get_main_keyboard())


@dp.message(Command("time"))
async def cmd_time(message: types.Message):
    tz = pytz.timezone(get_user_timezone(message.from_user.id))
    now = datetime.now(tz)  # one call, so date and time always match
    await message.answer(
        f"📍 Time zone: {tz.zone}\n"
        f"📅 Date: {now:%d.%m.%Y}\n"
        f"🕒 Time: {now:%H:%M:%S}",
        reply_markup=get_main_keyboard(),
    )


@dp.callback_query(F.data == "change_tz")
async def process_change_tz(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Choose your time zone:", reply_markup=get_tz_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("set_tz:"))
async def process_set_tz(callback: types.CallbackQuery):
    chosen_tz = callback.data.split(":", 1)[1]
    if chosen_tz not in VALID_TZ:
        await callback.answer("Unknown time zone.", show_alert=True)
        return
    update_user_timezone(callback.from_user.id, chosen_tz)
    await callback.message.edit_text(
        f"✅ Time zone changed to: <b>{html.escape(chosen_tz)}</b>\n"
        "/time and your reminders now use it.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )
    await callback.answer(f"Saved: {chosen_tz}")

#8fn----------> handlers: start / time / time zone



#9st----------> handlers: weather / city

async def send_weather(message: types.Message, city: str):
    try:
        text = await get_weather(city)
    except WeatherError as e:
        await message.answer(f"⚠️ {e}", parse_mode="HTML")  # error text may contain escaped HTML
        return
    update_user_city(message.from_user.id, city)  # remember only a city that worked
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())


async def ask_city(message: types.Message, state: FSMContext):
    await state.set_state(WeatherStates.waiting_for_city)
    await message.answer("Send me the city name (or /cancel).")


@dp.message(Command("weather"))
async def cmd_weather(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    city = command.args or get_user_city(message.from_user.id)
    if not city:
        await ask_city(message, state)
        return
    await send_weather(message, city.strip())


@dp.message(Command("setcity"))
async def cmd_setcity(message: types.Message, state: FSMContext):
    await ask_city(message, state)


@dp.callback_query(F.data == "change_city")
async def process_change_city(callback: types.CallbackQuery, state: FSMContext):
    await ask_city(callback.message, state)
    await callback.answer()


@dp.message(WeatherStates.waiting_for_city, F.text, ~F.text.startswith("/"))
async def process_city(message: types.Message, state: FSMContext):
    await state.clear()
    await send_weather(message, message.text.strip())

#9fn----------> handlers: weather / city



#10st---------> handlers: reminders

REMIND_HELP = (
    "⏰ <b>How to create a reminder:</b>\n"
    "<code>/remind 30m drink water</code> (in 30 minutes)\n"
    "<code>/remind 2h call mom</code> (in 2 hours)\n"
    "<code>/remind 18:30 workout</code> (at 18:30)\n"
    "<code>/remind 25.12 09:00 congratulate</code> (on a date, DD.MM)\n\n"
    "/reminders - list, /delremind number - delete"
)


@dp.message(Command("remind"))
async def cmd_remind(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer(REMIND_HELP, parse_mode="HTML")
        return

    tz = pytz.timezone(get_user_timezone(message.from_user.id))
    try:
        when_utc, text = parse_reminder(command.args, tz)
    except (ValueError, OverflowError):
        await message.answer("⚠️ I didn't understand the time.\n\n" + REMIND_HELP, parse_mode="HTML")
        return

    if len(text) > MAX_REMINDER_TEXT:
        await message.answer(f"⚠️ Text is too long (max {MAX_REMINDER_TEXT} characters).")
        return

    rid = add_reminder(message.from_user.id, text, when_utc)
    local = when_utc.astimezone(tz).strftime("%d.%m.%Y %H:%M")
    await message.answer(
        f"✅ Reminder <b>#{rid}</b> set for {local} ({tz.zone}):\n{html.escape(text)}",
        parse_mode="HTML",
    )


@dp.message(Command("reminders"))
async def cmd_reminders(message: types.Message):
    rows = get_user_reminders(message.from_user.id)
    if not rows:
        await message.answer("No active reminders. Create one with /remind")
        return
    tz = pytz.timezone(get_user_timezone(message.from_user.id))
    lines = []
    for rid, text, when in rows:
        local = (
            datetime.strptime(when, DB_TIME_FMT)
            .replace(tzinfo=pytz.utc)
            .astimezone(tz)
            .strftime("%d.%m %H:%M")
        )
        lines.append(f"<b>#{rid}</b> · {local} · {html.escape(text)}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("delremind"))
async def cmd_delremind(message: types.Message, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Give me a number: /delremind 3")
        return
    ok = delete_reminder(int(command.args.strip()), message.from_user.id)
    await message.answer("🗑 Deleted." if ok else "No such reminder.")

#10fn---------> handlers: reminders



#11st---------> reminder scheduler (background task)

async def reminder_loop():
    while True:
        try:
            for rid, user_id, text in get_due_reminders():
                try:
                    await bot.send_message(
                        user_id,
                        f"⏰ <b>Reminder:</b>\n{html.escape(text)}",
                        parse_mode="HTML",
                    )
                    mark_reminder_sent(rid)
                except TelegramForbiddenError:
                    mark_reminder_sent(rid) 
                except Exception:
                    logging.exception("Could not send reminder %s", rid)
        except Exception:
            logging.exception("Error in reminder_loop")
        await asyncio.sleep(20)

#11fn---------> reminder scheduler



#12st---------> run

async def main():
    init_db()
    task = asyncio.create_task(reminder_loop())
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())

#12fn---------> run
