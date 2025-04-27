import openai
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime

# Replace with your own bot token and OpenAI API key
BOT_TOKEN = "7916222297:AAH8GaCr-yE5FY7T6bsCIwp2HOqifTyOHf0"
OPENAI_API_KEY = "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"
CHANNEL_USERNAME = "venusgpt"  # Without @

openai.api_key = OPENAI_API_KEY  # Set OpenAI API key
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Initialize SQLite database
conn = sqlite3.connect("chat_history.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        user_id INTEGER,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_count (
        user_id INTEGER PRIMARY KEY,
        count INTEGER DEFAULT 0,
        last_reset DATE
    )
""")
conn.commit()

def reset_daily_limit(user_id: int):
    today = datetime.utcnow().date()
    cursor.execute("SELECT last_reset FROM message_count WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result or result[0] != str(today):
        cursor.execute("REPLACE INTO message_count (user_id, count, last_reset) VALUES (?, 0, ?)", (user_id, today))
        conn.commit()

def increment_message_count(user_id: int):
    reset_daily_limit(user_id)
    cursor.execute("UPDATE message_count SET count = count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_remaining_messages(user_id: int):
    reset_daily_limit(user_id)
    cursor.execute("SELECT count FROM message_count WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return 20 - (result[0] if result else 0)

def save_message(user_id: int, message: str):
    cursor.execute("INSERT INTO messages (user_id, message) VALUES (?, ?)", (user_id, message))
    conn.commit()
    
    cursor.execute("""
        DELETE FROM messages
        WHERE user_id = ? AND rowid NOT IN (
            SELECT rowid FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20
        )
    """, (user_id, user_id))
    conn.commit()

def get_user_messages(user_id: int):
    cursor.execute("SELECT message FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20", (user_id,))
    messages = cursor.fetchall()
    return [msg[0] for msg in messages][::-1]

async def is_user_member(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest:
        return False

@dp.message(Command("start"))
async def start(message: Message):
    if not await is_user_member(message.from_user.id):
        await message.answer(
            f"🚀 To use this bot, please join our channel first: [Join Here](https://t.me/{CHANNEL_USERNAME})",
            parse_mode="Markdown"
        )
        return
    await message.answer("Hello! I am VenusGPT. Ask me anything...")

@dp.message()
async def chatgpt_reply(message: Message):
    if not await is_user_member(message.from_user.id):
        await message.answer(
            f"🚀 To use this bot, please join our channel first: [Join Here](https://t.me/{CHANNEL_USERNAME})",
            parse_mode="Markdown"
        )
        return
    
    remaining_messages = get_remaining_messages(message.from_user.id)
    if remaining_messages <= 0:
        await message.answer("❌ You have reached your daily limit of 20 messages. Please try again tomorrow!")
        return
    
    user_messages = get_user_messages(message.from_user.id)
    user_messages.append(message.text)
    save_message(message.from_user.id, message.text)
    increment_message_count(message.from_user.id)
    
    chat_history = [{"role": "user", "content": msg} for msg in user_messages]
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat_history
        )
        reply_text = response["choices"][0]["message"]["content"]
        save_message(message.from_user.id, reply_text)
        remaining_messages -= 1
        await message.answer(f"{reply_text}\n\n📝 Remaining messages for today: {remaining_messages}")
    except Exception as e:
        print(f"Error: {e}")
        await message.answer("Sorry, something went wrong. Please try again later.")

async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
