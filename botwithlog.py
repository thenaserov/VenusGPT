import openai
import json
import os
import time
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

# Replace with your bot token and OpenAI API key
BOT_TOKEN = "YOUR_BOT_TOKEN"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
CHANNEL_USERNAME = "venusgpt"  # Without @

openai.api_key = OPENAI_API_KEY  # Set OpenAI API key

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Directory to store user messages
USER_DATA_DIR = "usersdata"
os.makedirs(USER_DATA_DIR, exist_ok=True)  # Create directory if not exists

def get_user_file(user_id):
    """Generate a JSON file path for each user"""
    return os.path.join(USER_DATA_DIR, f"{user_id}.json")

def save_message(user_id, message_text):
    """Save only user messages in a JSON file"""
    user_file = get_user_file(user_id)

    # Load existing messages or create an empty list
    if os.path.exists(user_file):
        try:
            with open(user_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    # Add new message
    data.append({
        "message": message_text,
        "timestamp": time.time()
    })

    # Remove messages older than 30 days
    one_month_ago = time.time() - (30 * 24 * 60 * 60)
    data = [msg for msg in data if msg["timestamp"] > one_month_ago]

    # Save updated data
    with open(user_file, "w") as f:
        json.dump(data, f, indent=4)

# Function to check if the user is a member of the channel
async def is_user_member(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        print(f"User {user_id} membership status: {chat_member.status}")  # Debugging line
        return chat_member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest as e:
        print(f"Error while checking membership for user {user_id}: {e}")
        return False

# Handle start command
@dp.message(Command("start"))
async def start(message: Message):
    if not await is_user_member(message.from_user.id):
        await message.answer(
            f"🚀 To use this bot, please join our channel first: [Join Here](https://t.me/{CHANNEL_USERNAME})",
            parse_mode="Markdown"
        )
        return

    await message.answer("Hello! I am VenusGPT. Send me a message, and I'll reply!")

# Handle user messages
@dp.message()
async def chatgpt_reply(message: Message):
    if not await is_user_member(message.from_user.id):
        await message.answer(
            f"🚀 To use this bot, please join our channel first: [Join Here](https://t.me/{CHANNEL_USERNAME})",
            parse_mode="Markdown"
        )
        return

    save_message(message.from_user.id, message.text)  # Save user message

    print(f"Received message: {message.text}")  # Debugging message
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message.text}]
        )
        reply_text = response["choices"][0]["message"]["content"]
        await message.answer(reply_text)
    except Exception as e:
        print(f"Error: {e}")
        await message.answer("Sorry, something went wrong. Please try again later.")

async def main():
    print("Bot is starting...")  # Debug message
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
