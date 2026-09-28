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
import aiogram
import asyncio
import sqlite3
import logging
import pytz
import aiohttp

#---------- from ... import ...

from datetime import datetime
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

TOKEN=""

WEATHER_API_KEY = ""

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
    # Кнопки: Текст на кнопке и callback_data (что отправится боту при нажатии)
    builder.button(text="МСК (UTC+3)", callback_data="set_tz:Europe/Moscow")
    builder.button(text="Калининград (UTC+2)", callback_data="set_tz:Europe/Kaliningrad")
    builder.button(text="Самара (UTC+4)", callback_data="set_tz:Europe/Samara")
    builder.button(text="Екатеринбург (UTC+5)", callback_data="set_tz:Europe/Yekaterinburg")
    builder.button(text="Ташкент (UTC+5)", callback_data="set_tz:Asia/Tashkent")
    builder.button(text="Алматы (UTC+6)", callback_data="set_tz:Asia/Almaty")
    
    builder.adjust(2) # Располагаем по 2 кнопки в ряд
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

#3.3fn--------> handlers



#4st----------> command /start 

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(" WSP ")

#4fn----------> command /start 



#5st----------> command /time

@dp.message(Command("time"))
async def cmd_time(message: types.Message):
    # Используем F-строку и вызываем datetime.now()
    current_time = datetime.now().strftime("%H:%M:%S")
    await message.answer(f"time: {current_time}")

#5fn----------> command /time



#6st----------> OpenWeatherAPI



#6fn----------> OpenWeatherAPI



#7st---------> Geo Error Fixing



#7fn---------> Geo Error Fixing



#st----------> polling 

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db() # Инициализируем базу данных перед запуском
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

#fn----------> polling 


