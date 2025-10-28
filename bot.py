import os
import re
import asyncio
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# Read from environment variables
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", 8080))

# Validate credentials
if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Missing API credentials. Check your environment variables")

app = Client(
    "fast_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    sleep_threshold=60
)

# Simple storage
user_data = {}

# Web server for Render health checks
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Start a simple web server for Render"""
    web_app = web.Application()
    web_app.router.add_get('/', health_check)
    web_app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
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

@app.on_message(filters.command("setcaption"))
async def set_caption_command(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) > 1:
        caption = ' '.join(message.command[1:])
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['caption'] = caption
        await message.reply_text(f"✅ Caption set: `{caption}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ Usage: `/setcaption Your text`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("replace"))
async def set_replace_command(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) > 2:
        old, new = message.command[1], message.command[2]
        if user_id not in user_data:
            user_data[user_id] = {'replace': {}}
        if 'replace' not in user_data[user_id]:
            user_data[user_id]['replace'] = {}
        user_data[user_id]['replace'][old] = new
        await message.reply_text(f"✅ Replacement: `{old}` → `{new}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ Usage: `/replace OLD_WORD NEW_WORD`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("target"))
async def set_target_command(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) > 1:
        target = message.command[1]
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['target'] = target
        await message.reply_text(f"✅ Target: `{target}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text("❌ Usage: `/target CHAT_ID` or `/target me`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("info"))
async def show_info_command(client, message: Message):
    user_id = message.from_user.id
    user = user_data.get(user_id, {})
    
    caption = user.get('caption', 'Not set')
    target = user.get('target', 'Current chat')
    replaces = user.get('replace', {})
    
    text = f"**Your Settings:**\n\n**Caption:** `{caption}`\n**Target:** `{target}`\n**Replacements:** {len(replaces)}"
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.media & filters.private)
async def handle_media_message(client, message: Message):
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
    
    try:
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
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.regex(r'https?://t\.me/\w+/\d+') & filters.private)
async def handle_link_message(client, message: Message):
    user_id = message.from_user.id
    link = message.text
    
    try:
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
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Handle all text messages to catch any issues
@app.on_message(filters.text & filters.private)
async def handle_all_text(client, message: Message):
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

async def main():
    """Start both web server and Telegram bot"""
    print("🚀 Starting Fast File Bot...")
    
    # Start web server for Render
    await start_web_server()
    
    # Start Telegram bot
    await app.start()
    print("✅ Bot started successfully!")
    
    # Keep the bot running
    print("🤖 Bot is now active and listening...")
    await idle()
    
    # Stop the bot when needed
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
