#  |-----------------------------------------------------|
#  | \                                                 / |
#  |  \/-27|09|2026-------------------------------16-\/  |
#  |   |                                             |   |
#  |   |----->___(Chrono-Weather-Bot-0-3)___ <-------|   |
#  |   |                                             |   |
#  |  /\-11:05-----------------------------------182-/\  |
#  | /                                                 \ |
#  |-----------------------------------------------------|



#1st----------> libs/modules 

#---------- import

import asyncio
import html
import sqlite3
import logging
import pytz
import aiohttp
import os
import re

#---------- from ... import ...

from datetime import datetime, timedelta
from aiogram.filters import Command, CommandObject
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError

#1fn----------> libs/modules 



#2st----------> logging for errors 

logging.basicConfig(level = logging.INFO)

#2fn----------> logging for errors 



#3st----------> bot settings  

load_dotenv(override=True)

TOKEN= os.getenv("BOT_TOKEN")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

bot = Bot(token=TOKEN)


dp = Dispatcher()


#3fn----------> bot setting



#3.1st--------> Data base work (SQLite)

DB_NAME = "users_settings.db"
def init_db():
    """Создает таблицу пользователей, если её еще нет."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                remind_at_utc TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            )
        ''')
        conn.commit()

def get_user_timezone(user_id: int) -> str:
    """Получает сохраненный часовой пояс пользователя (по умолчанию Москва)."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT timezone FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else "Europe/Moscow"

def update_user_timezone(user_id: int, timezone: str):
    """Сохраняет или обновляет часовой пояс пользователя."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, timezone) 
            VALUES (?, ?) 
            ON CONFLICT(user_id) DO UPDATE SET timezone = excluded.timezone
        ''', (user_id, timezone))
        conn.commit()
        
        
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'Europe/Moscow',
                city TEXT
            )
        ''')
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN city TEXT")
        except sqlite3.OperationalError:
            pass  # колонка уже есть
        conn.commit()

def get_user_city(user_id: int):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT city FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row else None

def update_user_city(user_id: int, city: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            INSERT INTO users (user_id, city) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET city = excluded.city
        ''', (user_id, city))

#3.1fn--------> Data base work (SQLite)



#3.2st--------> Keyboards / change tz

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏙 Сменить город", callback_data="change_city")
    builder.button(text="⚙️ Сменить часовой пояс", callback_data="change_tz")
    builder.adjust(1)
    return builder.as_markup()

def get_tz_keyboard():
    """Список доступных часовых поясов."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="МСК (UTC+3)", callback_data="set_tz:Europe/Moscow")
    builder.button(text="Калининград (UTC+2)", callback_data="set_tz:Europe/Kaliningrad")
    builder.button(text="Самара (UTC+4)", callback_data="set_tz:Europe/Samara")
    builder.button(text="Екатеринбург (UTC+5)", callback_data="set_tz:Europe/Yekaterinburg")
    builder.button(text="Ташкент (UTC+5)", callback_data="set_tz:Asia/Tashkent")
    builder.button(text="Алматы (UTC+5)", callback_data="set_tz:Asia/Almaty")
    
    builder.adjust(2) 
    return builder.as_markup()


#3.2fn--------> Keyboards / change tz



#3.3st--------> handlers

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Hello! I can show you correct time.\n"
        "Use command /time, for show time , or press button right down for settings.",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("time"))
async def cmd_time(message: types.Message):
    
    user_tz_str = get_user_timezone(message.from_user.id)
    tz = pytz.timezone(user_tz_str)
    
    
    current_time = datetime.now(tz).strftime("%H:%M:%S")
    current_date = datetime.now(tz).strftime("%d.%m.%Y")
    
    
    await message.answer(
        f"📍 Your time position: {user_tz_str}\n"
        f"📅 Date: {current_date}\n"
        f"🕒 Time: {current_time}",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "change_tz")
async def process_change_tz(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите ваш часовой пояс из списка ниже:",
        reply_markup=get_tz_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("set_tz:"))
async def process_set_tz(callback: types.CallbackQuery):
    
    chosen_tz = callback.data.split(":")[1]
    
    
    update_user_timezone(callback.from_user.id, chosen_tz)
    
    
    await callback.message.edit_text(
        f"✅ Часовой пояс успешно изменен на: **{chosen_tz}**\n"
        f"Теперь команда /time будет показывать актуальное для вас время.",
        parse_mode="Markdown"
    )
    await callback.answer(f"Сохранено: {chosen_tz}")
    
    
class WeatherStates(StatesGroup):
    waiting_for_city = State()

async def send_weather(message: types.Message, city: str):
    try:
        text = await get_weather(city)
    except WeatherError as e:
        await message.answer(f"⚠️ {e}")
        return
    update_user_city(message.from_user.id, city)  # запоминаем только удачный город
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())

@dp.message(Command("weather"))
async def cmd_weather(message: types.Message, command: CommandObject, state: FSMContext):
    city = command.args or get_user_city(message.from_user.id)
    if not city:
        await state.set_state(WeatherStates.waiting_for_city)
        await message.answer("Напиши название города.")
        return
    await send_weather(message, city)

@dp.message(WeatherStates.waiting_for_city, F.text, ~F.text.startswith("/"))
async def process_city(message: types.Message, state: FSMContext):
    await state.clear()
    await send_weather(message, message.text.strip())

#3.3fn--------> handlers



#3.4st--------> change city

async def ask_city(message: types.Message, state: FSMContext):
    await state.set_state(WeatherStates.waiting_for_city)
    await message.answer("Напиши название нового города.")

@dp.message(Command("setcity"))
async def cmd_setcity(message: types.Message, state: FSMContext):
    await ask_city(message, state)

@dp.callback_query(F.data == "change_city")
async def process_change_city(callback: types.CallbackQuery, state: FSMContext):
    await ask_city(callback.message, state)
    await callback.answer()

#3.4fn--------> change city



#3.5st--------> Data base work (reminders)

DB_TIME_FMT = "%Y-%m-%d %H:%M:%S"

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

#3.5fn--------> Data base work (reminders)



#3.6st--------> reminder handlers

REMIND_HELP = (
    "⏰ <b>Как создать напоминание:</b>\n"
    "<code>/remind 30m выпить воды</code> (через 30 минут)\n"
    "<code>/remind 2h позвонить</code> (через 2 часа)\n"
    "<code>/remind 18:30 тренировка</code> (в 18:30)\n"
    "<code>/remind 25.12 09:00 поздравить</code> (в дату)\n\n"
    "/reminders: список, /delremind номер: удалить"
)

@dp.message(Command("remind"))
async def cmd_remind(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer(REMIND_HELP, parse_mode="HTML")
        return

    tz = pytz.timezone(get_user_timezone(message.from_user.id))
    try:
        when_utc, text = parse_reminder(command.args, tz)
    except ValueError:
        await message.answer("⚠️ Не понял время.\n\n" + REMIND_HELP, parse_mode="HTML")
        return

    add_reminder(message.from_user.id, text, when_utc)
    local = when_utc.astimezone(tz).strftime("%d.%m.%Y %H:%M")
    await message.answer(
        f"✅ Напомню {local} ({tz.zone}):\n{html.escape(text)}",
        parse_mode="HTML",
    )

@dp.message(Command("reminders"))
async def cmd_reminders(message: types.Message):
    rows = get_user_reminders(message.from_user.id)
    if not rows:
        await message.answer("Активных напоминаний нет. Создай через /remind")
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
        await message.answer("Укажи номер: /delremind 3")
        return
    ok = delete_reminder(int(command.args.strip()), message.from_user.id)
    await message.answer("🗑 Удалено." if ok else "Такого напоминания нет.")

#3.6fn--------> reminder handlers



#6st----------> OpenWeatherAPI

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

class WeatherError(Exception):
    """Ошибка с понятным пользователю текстом."""

async def get_weather(city: str) -> str:
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            place = await geocode_city(session, city)

            params = {
                "lat": place["lat"], "lon": place["lon"],
                "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru",
            }
            async with session.get(WEATHER_URL, params=params) as resp:
                if resp.status == 401:
                    raise WeatherError("Ключ погоды не принят (возможно, ещё не активирован).")
                if resp.status != 200:
                    raise WeatherError(f"Сервис погоды ответил ошибкой {resp.status}.")
                data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise WeatherError("Сервис погоды не отвечает, попробуй позже.")

    name = place.get("local_names", {}).get("ru", place["name"])
    return (
        f"🌍 {html.escape(name)}, {place['country']}\n"
        f"🌡 {data['main']['temp']:.0f}°C (ощущается {data['main']['feels_like']:.0f}°C)\n"
        f"☁️ {data['weather'][0]['description'].capitalize()}\n"
        f"💨 Ветер: {data['wind']['speed']} м/с\n"
        f"💧 Влажность: {data['main']['humidity']}%"
    )


#6fn----------> OpenWeatherAPI



#6.1st---------> Reminder time parser

UNITS = {"m": "minutes", "м": "minutes", "h": "hours", "ч": "hours", "d": "days", "д": "days"}

def parse_reminder(args: str, tz) -> tuple[datetime, str]:
    """Возвращает (время в UTC, текст). Если формат неверный, кидает ValueError."""
    args = args.strip()
    now = datetime.now(tz)

    # Вариант 1: через N минут/часов/дней  ->  30m, 2h, 1d
    m = re.match(r"^(\d+)([mhdмчд])\s+(.+)$", args, re.S | re.I)
    if m:
        amount, unit, text = int(m[1]), UNITS[m[2].lower()], m[3]
        target = now + timedelta(**{unit: amount})
        return target.astimezone(pytz.utc), text

    # Вариант 2: сегодня или завтра в ЧЧ:ММ  ->  18:30
    m = re.match(r"^(\d{1,2}):(\d{2})\s+(.+)$", args, re.S)
    if m:
        hour, minute, text = int(m[1]), int(m[2]), m[3]
        naive = datetime(now.year, now.month, now.day, hour, minute)  # ValueError, если 25:99
        target = tz.localize(naive)
        if target <= now:
            target = tz.localize(naive + timedelta(days=1))
        return target.astimezone(pytz.utc), text

    # Вариант 3: конкретная дата  ->  25.12 09:00
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})\s+(.+)$", args, re.S)
    if m:
        day, month, hour, minute, text = int(m[1]), int(m[2]), int(m[3]), int(m[4]), m[5]
        target = tz.localize(datetime(now.year, month, day, hour, minute))
        if target <= now:
            target = tz.localize(datetime(now.year + 1, month, day, hour, minute))
        return target.astimezone(pytz.utc), text

    raise ValueError("формат")

#6.1fn---------> Reminder time parser



#7st---------> Geo Error Fixing

GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"

async def geocode_city(session: aiohttp.ClientSession, city: str) -> dict:
    params = {"q": city, "limit": 1, "appid": WEATHER_API_KEY}
    async with session.get(GEO_URL, params=params) as resp:
        if resp.status == 401:
            raise WeatherError("Ключ погоды не принят (возможно, ещё не активирован).")
        if resp.status != 200:
            raise WeatherError(f"Геосервис ответил ошибкой {resp.status}.")
        data = await resp.json()
    if not data:
        raise WeatherError(f"Город «{html.escape(city)}» не найден. Проверь написание.")
    return data[0]


#7fn---------> Geo Error Fixing



#9st----------> Reminder scheduler

async def reminder_loop():
    while True:
        try:
            for rid, user_id, text in get_due_reminders():
                try:
                    await bot.send_message(
                        user_id, f"⏰ <b>Напоминание:</b>\n{html.escape(text)}", parse_mode="HTML"
                    )
                    mark_reminder_sent(rid)
                except TelegramForbiddenError:
                    mark_reminder_sent(rid)  # человек заблокировал бота, повторять бессмысленно
                except Exception:
                    logging.exception("Не удалось отправить напоминание %s", rid)  # попробуем в следующий цикл
        except Exception:
            logging.exception("Ошибка в reminder_loop")
        await asyncio.sleep(20)

#9fn----------> Reminder scheduler



#st----------> polling 

async def main():
    init_db()
    task = asyncio.create_task(reminder_loop())
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
    

#fn----------> polling 

