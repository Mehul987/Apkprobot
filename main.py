# main.py

import os
import json
import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, Message,
    CallbackQuery, ChatMember
)
from pyrogram.errors import UserNotParticipant
from pyrogram.errors.exceptions.bad_request_400 import ChatAdminRequired, PeerIdInvalid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_ID = "YOUR_API_ID"
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_USERNAME = "YOUR_CHANNEL_USERNAME"
CHANNEL_ID = -1001234567890
LOG_FILE = "user_searches.json"

app = Client("ProAPKBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def is_user_member(user_id: int) -> bool:
    try:
        member = await app.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in (enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED)
    except UserNotParticipant:
        return False
    except (ChatAdminRequired, PeerIdInvalid) as e:
        logger.error(f"Error checking membership: {e}")
        return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

def log_search(user_id, username, query, success):
    try:
        log_entry = {
            "user_id": user_id,
            "username": username,
            "query": query,
            "success": success,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
        logs.append(log_entry)
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Logging error: {e}")

async def search_channel(query: str):
    try:
        messages = []
        async for message in app.search_messages(CHANNEL_ID, query=query):
            if message.caption or message.text:
                content = message.caption or message.text
                if query.lower() in content.lower():
                    messages.append(message)
                    if len(messages) >= 5:
                        break
        return messages
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    is_member = await is_user_member(user_id)
    if is_member:
        await message.reply("👋 Welcome! Send an app name to get the premium version.")
    else:
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
        ])
        await message.reply("Join the channel to continue.", reply_markup=join_button)

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    await message.reply("Send any app name. Make sure you're a member of the channel.")

@app.on_message(~filters.command(["start", "help"]) & filters.private & filters.text)
async def search_apk(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    query = message.text.strip()
    is_member = await is_user_member(user_id)
    if not is_member:
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
        ])
        await message.reply("Join the channel first.", reply_markup=join_button)
        return
    await message.reply_chat_action(enums.ChatAction.TYPING)
    results = await search_channel(query)
    if results:
        log_search(user_id, username, query, True)
        result = results[0]
        content = result.caption or result.text
        lines = content.split('\n')
        title = lines[0] if lines else f"{query.title()} – Premium Version"
        description = "\n".join(lines[1:4]) if len(lines) > 1 else "Premium version unlocked!"
        download_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Download Now", url=f"https://t.me/{CHANNEL_USERNAME}/{result.id}")]
        ])
        if result.photo:
            await message.reply_photo(result.photo.file_id, caption=f"**{title}**\n\n{description}", reply_markup=download_button)
        else:
            await message.reply(f"**{title}**\n\n{description}", reply_markup=download_button)
    else:
        log_search(user_id, username, query, False)
        await message.reply("App not found. Try another.")

@app.on_callback_query(filters.regex("^check_membership$"))
async def callback_check_membership(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    is_member = await is_user_member(user_id)
    if is_member:
        await callback_query.answer("Thanks for joining!", show_alert=True)
        await callback_query.message.edit("✅ You're now a member. Send the app name again.")
    else:
        await callback_query.answer("Join the channel first!", show_alert=True)
        join_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ Check Membership", callback_data="check_membership")]
        ])
        await callback_query.message.edit("Join the channel first.", reply_markup=join_button)

async def idle():
    while True:
        try:
            await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            break

async def main():
    await app.start()
    logger.info("Bot started")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")