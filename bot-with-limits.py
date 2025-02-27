import openai
import asyncio
import os
import json
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

# Replace with your own bot token and OpenAI API key
BOT_TOKEN = "7916222297:AAH8GaCr-yE5FY7T6bsCIwp2HOqifTyOHf0"
OPENAI_API_KEY = "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"
ADMIN_USER_ID = 7897984506
CHANNEL_USERNAME = "venusgpt"  # Without @

openai.api_key = OPENAI_API_KEY
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite database setup
db_path = "usersdata/users.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        messages TEXT,
        last_reset TEXT,
        message_count INTEGER
    )
""")
conn.commit()

def save_user_data(user_id, text):
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT messages, last_reset, message_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        messages, last_reset, message_count = row
        if last_reset != today:
            message_count = 0
            messages = "[]"
        messages_list = json.loads(messages)
    else:
        messages_list = []
        message_count = 0
    
    if message_count >= 20:
        return False, 0
    
    messages_list.append(text)
    messages_list = messages_list[-20:]  # Limit to last 20 messages
    
    cursor.execute("""
        INSERT INTO users (user_id, messages, last_reset, message_count)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            messages = ?,
            last_reset = ?,
            message_count = ?
    """, (user_id, json.dumps(messages_list), today, message_count + 1, json.dumps(messages_list), today, message_count + 1))
    conn.commit()
    
    return True, 20 - (message_count + 1)

def get_past_messages(user_id):
    cursor.execute("SELECT messages FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return json.loads(row[0]) if row else []

async def count_active_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    await bot.send_message(ADMIN_USER_ID, f"Active users: {users}")

async def is_user_member(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest:
        return False

@dp.message(Command("start"))
async def start(message: Message):
    if not await is_user_member(message.from_user.id):
        await message.answer(f"🚀 To use this bot, please join our channel first: [Join Here](https://t.me/{CHANNEL_USERNAME})", parse_mode="Markdown")
        return
    await message.answer("Hello! I am VenusGPT. Send me a message, and I'll reply!")

@dp.message()
async def chatgpt_reply(message: Message):
    if not await is_user_member(message.from_user.id):
        await message.answer(f"🚀 To use this bot, please join our channel first: [Join Here](https://t.me/{CHANNEL_USERNAME})", parse_mode="Markdown")
        return
    
    success, remaining = save_user_data(message.from_user.id, message.text)
    if not success:
        await message.answer("⚠️ You have reached your daily limit of 20 messages. Come back tomorrow!")
        return
    
    past_messages = get_past_messages(message.from_user.id)
    
    await message.answer("VenusGPT is typing...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": msg} for msg in past_messages]
        )
        reply_text = response["choices"][0]["message"]["content"]
        await message.answer(f"{reply_text}\n\nYou have {remaining} messages left today.")
    except Exception as e:
        await message.answer("Sorry, something went wrong. Please try again later.")

async def main():
    await count_active_users()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
