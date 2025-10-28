import os
import re
import asyncio
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Read from Render environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Debug: Check if variables are loaded
logger.info("🔧 Loading environment variables...")
logger.info(f"API_ID: {API_ID}")
logger.info(f"API_HASH: {API_HASH}")
logger.info(f"BOT_TOKEN: {BOT_TOKEN}")

# Validate credentials
if not all([API_ID, API_HASH, BOT_TOKEN]):
    error_msg = "Missing API credentials. Please check your Render environment variables"
    logger.error(error_msg)
    raise ValueError(error_msg)

try:
    API_ID = int(API_ID)
except ValueError:
    error_msg = "API_ID must be a number"
    logger.error(error_msg)
    raise ValueError(error_msg)

app = Client(
    "fast_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    sleep_threshold=60,
    in_memory=True
)

# Simple storage
user_data = {}

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    try:
        logger.info(f"📩 Received start command from {message.from_user.id}")
        await message.reply_text(
            "🚀 **Fast File Bot**\n\n"
            "I instantly copy files using Telegram's file ID system!\n\n"
            "**Commands:**\n"
            "/setcaption TEXT - Add custom caption\n"
            "/replace OLD NEW - Replace words in caption\n"
            "/target CHAT_ID - Set destination chat\n"
            "/info - Show current settings\n\n"
            "**Just forward any media file or send a public channel link!**",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info("✅ Start command replied successfully")
    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")

@app.on_message(filters.command("test"))
async def test_command(client, message: Message):
    """Test if bot is responding"""
    try:
        logger.info(f"📩 Received test command from {message.from_user.id}")
        await message.reply_text("✅ Bot is working and responding!")
        logger.info("✅ Test command responded successfully")
    except Exception as e:
        logger.error(f"❌ Test command failed: {e}")

@app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    """Simple ping command"""
    try:
        import time
        start_time = time.time()
        msg = await message.reply_text("🏓 Pong!")
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        await msg.edit_text(f"🏓 Pong! Response time: {response_time}ms")
        logger.info(f"✅ Ping command responded in {response_time}ms")
    except Exception as e:
        logger.error(f"❌ Ping command failed: {e}")

@app.on_message(filters.command("setcaption"))
async def set_caption_command(client, message: Message):
    try:
        user_id = message.from_user.id
        if len(message.command) > 1:
            caption = ' '.join(message.command[1:])
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['caption'] = caption
            await message.reply_text(f"✅ Caption set: `{caption}`", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Caption set for user {user_id}")
        else:
            await message.reply_text("❌ Usage: `/setcaption Your text`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"❌ Error in setcaption: {e}")

@app.on_message(filters.command("replace"))
async def set_replace_command(client, message: Message):
    try:
        user_id = message.from_user.id
        if len(message.command) > 2:
            old, new = message.command[1], message.command[2]
            if user_id not in user_data:
                user_data[user_id] = {'replace': {}}
            if 'replace' not in user_data[user_id]:
                user_data[user_id]['replace'] = {}
            user_data[user_id]['replace'][old] = new
            await message.reply_text(f"✅ Replacement: `{old}` → `{new}`", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Replacement set for user {user_id}")
        else:
            await message.reply_text("❌ Usage: `/replace OLD_WORD NEW_WORD`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"❌ Error in replace: {e}")

@app.on_message(filters.command("target"))
async def set_target_command(client, message: Message):
    try:
        user_id = message.from_user.id
        if len(message.command) > 1:
            target = message.command[1]
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['target'] = target
            await message.reply_text(f"✅ Target: `{target}`", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Target set for user {user_id}")
        else:
            await message.reply_text("❌ Usage: `/target CHAT_ID` or `/target me`", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"❌ Error in target: {e}")

@app.on_message(filters.command("info"))
async def show_info_command(client, message: Message):
    try:
        user_id = message.from_user.id
        user = user_data.get(user_id, {})
        
        caption = user.get('caption', 'Not set')
        target = user.get('target', 'Current chat')
        replaces = user.get('replace', {})
        
        text = f"**Your Settings:**\n\n**Caption:** `{caption}`\n**Target:** `{target}`\n**Replacements:** {len(replaces)}"
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"✅ Info sent to user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error in info: {e}")

@app.on_message(filters.media & filters.private)
async def handle_media_message(client, message: Message):
    try:
        user_id = message.from_user.id
        user = user_data.get(user_id, {})
        target = user.get('target', user_id)
        
        # Process caption
        original = message.caption or ""
        final = original
        
        # Apply replacements
        for old, new in user.get('replace', {}).items():
            final = final.replace(old, new)
        
        # Add custom caption
        if user.get('caption'):
            final = f"{final}\n\n{user['caption']}".strip()
        
        logger.info(f"📨 Processing media from user {user_id} to target {target}")
        
        if message.photo:
            await app.send_photo(target, message.photo.file_id, caption=final or None)
        elif message.video:
            await app.send_video(target, message.video.file_id, caption=final or None)
        elif message.document:
            await app.send_document(target, message.document.file_id, caption=final or None)
        elif message.audio:
            await app.send_audio(target, message.audio.file_id, caption=final or None)
        else:
            await message.reply_text("❌ Media type not supported")
            return
        
        await message.reply_text("✅ File sent!")
        logger.info(f"✅ Media sent successfully for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error handling media: {e}")
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.regex(r'https?://t\.me/\w+/\d+') & filters.private)
async def handle_link_message(client, message: Message):
    try:
        user_id = message.from_user.id
        link = message.text
        
        logger.info(f"🔗 Processing link from user {user_id}: {link}")
        
        parts = link.split('/')
        chat, msg_id = parts[-2], int(parts[-1])
        
        status = await message.reply_text("🔗 Processing...")
        source_msg = await app.get_messages(chat, msg_id)
        
        if not source_msg or not source_msg.media:
            await status.edit_text("❌ No media found")
            return
        
        # Forward the media using file ID
        user = user_data.get(user_id, {})
        target = user.get('target', user_id)
        
        original = source_msg.caption or ""
        final = original
        
        for old, new in user.get('replace', {}).items():
            final = final.replace(old, new)
        
        if user.get('caption'):
            final = f"{final}\n\n{user['caption']}".strip()
        
        if source_msg.photo:
            await app.send_photo(target, source_msg.photo.file_id, caption=final or None)
        elif source_msg.video:
            await app.send_video(target, source_msg.video.file_id, caption=final or None)
        elif source_msg.document:
            await app.send_document(target, source_msg.document.file_id, caption=final or None)
        elif source_msg.audio:
            await app.send_audio(target, source_msg.audio.file_id, caption=final or None)
        else:
            await status.edit_text("❌ Media type not supported")
            return
        
        await status.edit_text("✅ File copied!")
        logger.info(f"✅ Link processed successfully for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing link: {e}")
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.text & filters.private)
async def handle_all_text(client, message: Message):
    try:
        logger.info(f"📩 Received text from {message.from_user.id}: {message.text}")
        # If it's not a command and not a Telegram link, show help
        if not message.text.startswith('/') and not re.match(r'https?://t\.me/\w+/\d+', message.text):
            await message.reply_text(
                "🤔 **How to use:**\n\n"
                "1. **Forward any media file** to me\n"
                "2. **Send a public channel link:**\n"
                "   `https://t.me/channel/123`\n\n"
                "Use `/start` for full instructions",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"❌ Error in text handler: {e}")

async def main():
    """Start the Telegram bot"""
    logger.info("🚀 Starting Fast File Bot...")
    
    try:
        # Start Telegram bot
        await app.start()
        logger.info("✅ Bot started successfully!")
        
        # Get bot info to verify it's working
        me = await app.get_me()
        logger.info(f"🤖 Bot @{me.username} is now active!")
        
        # Send a startup notification (optional)
        try:
            await app.send_message(me.id, "🤖 Bot started successfully!")
        except:
            pass
        
        # Keep the bot running
        logger.info("📱 Bot is now listening for messages...")
        await idle()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        # Stop the bot when needed
        await app.stop()
        logger.info("🛑 Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
