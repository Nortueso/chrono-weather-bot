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

#---------- from ... import ...

from datetime import datetime
from aiogram.filters import Command, CommandObject
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

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
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                timezone TEXT DEFAULT 'Europe/Moscow'
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
    """Кнопка под сообщением для смены пояса."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Сменить часовой пояс", callback_data="change_tz")
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
    # 1. Получаем часовой пояс из базы данных
    user_tz_str = get_user_timezone(message.from_user.id)
    tz = pytz.timezone(user_tz_str)
    
    # 2. Вычисляем время
    current_time = datetime.now(tz).strftime("%H:%M:%S")
    current_date = datetime.now(tz).strftime("%d.%m.%Y")
    
    # 3. Отвечаем пользователю
    await message.answer(
        f"📍 Your time position: {user_tz_str}\n"
        f"📅 Date: {current_date}\n"
        f"🕒 Time: {current_time}",
        reply_markup=get_main_keyboard()
    )

# Обработка нажатия на кнопку "Сменить часовой пояс"
@dp.callback_query(F.data == "change_tz")
async def process_change_tz(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите ваш часовой пояс из списка ниже:",
        reply_markup=get_tz_keyboard()
    )
    await callback.answer() # Close animation downloading on button

# Обработка выбора конкретного часового пояса
@dp.callback_query(F.data.startswith("set_tz:"))
async def process_set_tz(callback: types.CallbackQuery):
    # finding name of tz from callback_data (example, "Europe/Moscow")
    chosen_tz = callback.data.split(":")[1]
    
    # Saving DB forever
    update_user_timezone(callback.from_user.id, chosen_tz)
    
    # Updating messages for users
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



#st----------> polling 

async def main():
    init_db() # Инициализируем базу данных перед запуском
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    

#fn----------> polling 

