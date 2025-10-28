import os
import re
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# Configuration
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

# Validate environment variables
if not all([API_ID, API_HASH, BOT_TOKEN]):
    missing = []
    if not API_ID: missing.append("API_ID")
    if not API_HASH: missing.append("API_HASH")
    if not BOT_TOKEN: missing.append("BOT_TOKEN")
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# Convert API_ID to integer
try:
    API_ID = int(API_ID)
except ValueError:
    raise ValueError("API_ID must be a valid integer")

print("✅ Environment variables loaded successfully")

# Initialize Client
app = Client(
    "fast_file_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# User data storage
user_data = {}

# Web server for Render
async def handle_request(request):
    return web.Response(text="Bot is running!")

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    print(f"📩 Received start command from {message.from_user.id}")
    await message.reply_text(
        "🤖 **Fast File Bot**\n\n"
        "I can instantly copy files using Telegram's file ID system!\n\n"
        "**Available Commands:**\n"
        "• /setcaption <text> - Set custom caption\n"
        "• /replace <old> <new> - Replace words in caption\n"
        "• /target <chat_id> - Set destination chat\n"
        "• /info - Show your settings\n\n"
        "**How to use:**\n"
        "1. Forward any media file to me\n"
        "2. Send a public channel link\n"
        "3. I'll instantly copy it with your settings!",
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("setcaption"))
async def set_caption_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/setcaption Your caption text`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    caption = ' '.join(message.command[1:])
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['caption'] = caption
    await message.reply_text(f"✅ Custom caption set:\n`{caption}`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("replace"))
async def replace_handler(client, message: Message):
    if len(message.command) < 3:
        await message.reply_text("❌ Usage: `/replace OLD_WORD NEW_WORD`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    old_word = message.command[1]
    new_word = message.command[2]
    
    if user_id not in user_data:
        user_data[user_id] = {'replacements': {}}
    elif 'replacements' not in user_data[user_id]:
        user_data[user_id]['replacements'] = {}
    
    user_data[user_id]['replacements'][old_word] = new_word
    await message.reply_text(f"✅ Replacement set:\n`{old_word}` → `{new_word}`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("target"))
async def target_handler(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/target CHAT_ID`\nExample: `/target me` or `/target -1001234567890`", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_id = message.from_user.id
    target_chat = message.command[1]
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['target'] = target_chat
    await message.reply_text(f"✅ Target chat set to: `{target_chat}`", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("info"))
async def info_handler(client, message: Message):
    user_id = message.from_user.id
    user_settings = user_data.get(user_id, {})
    
    caption = user_settings.get('caption', 'Not set')
    target = user_settings.get('target', 'Current chat')
    replacements = user_settings.get('replacements', {})
    
    response = [
        "**Your Current Settings:**",
        f"**Custom Caption:** `{caption}`",
        f"**Target Chat:** `{target}`",
        f"**Replacements:** {len(replacements)} rules"
    ]
    
    if replacements:
        response.append("\n**Active Replacements:**")
        for old, new in list(replacements.items())[:5]:
            response.append(f"• `{old}` → `{new}`")
    
    await message.reply_text('\n'.join(response), parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.media & filters.private)
async def media_handler(client, message: Message):
    user_id = message.from_user.id
    user_settings = user_data.get(user_id, {})
    
    # Get target chat
    target_chat = user_settings.get('target', user_id)
    if target_chat == 'me':
        target_chat = user_id
    
    # Process caption
    original_caption = message.caption or ""
    processed_caption = original_caption
    
    # Apply replacements
    replacements = user_settings.get('replacements', {})
    for old_word, new_word in replacements.items():
        processed_caption = processed_caption.replace(old_word, new_word)
    
    # Add custom caption
    custom_caption = user_settings.get('caption', '')
    if custom_caption:
        if processed_caption:
            processed_caption = f"{processed_caption}\n\n{custom_caption}"
        else:
            processed_caption = custom_caption
    
    try:
        # Send based on media type
        if message.photo:
            await client.send_photo(
                target_chat,
                message.photo.file_id,
                caption=processed_caption or None
            )
        elif message.video:
            await client.send_video(
                target_chat,
                message.video.file_id,
                caption=processed_caption or None
            )
        elif message.document:
            await client.send_document(
                target_chat,
                message.document.file_id,
                caption=processed_caption or None
            )
        elif message.audio:
            await client.send_audio(
                target_chat,
                message.audio.file_id,
                caption=processed_caption or None
            )
        else:
            await message.reply_text("❌ This media type is not supported")
            return
        
        await message.reply_text("✅ File copied successfully!")
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@app.on_message(filters.text & filters.private)
async def text_handler(client, message: Message):
    # Check if it's a Telegram link
    if re.match(r'https?://t\.me/\w+/\d+', message.text):
        await handle_telegram_link(client, message)
        return
    
    # If it's not a command, show help
    if not message.text.startswith('/'):
        await message.reply_text(
            "🤔 **How to use this bot:**\n\n"
            "1. **Forward any media file** to me\n"
            "2. **Send a public channel link** like:\n"
            "   `https://t.me/channel/123`\n\n"
            "Use `/start` to see all commands and features.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_telegram_link(client, message: Message):
    user_id = message.from_user.id
    link = message.text.strip()
    
    try:
        # Extract chat and message ID
        match = re.match(r'https?://t\.me/(\w+)/(\d+)', link)
        if not match:
            await message.reply_text("❌ Invalid link format")
            return
        
        chat_username = match.group(1)
        message_id = int(match.group(2))
        
        status_msg = await message.reply_text("🔗 Processing link...")
        
        # Get the source message
        source_message = await client.get_messages(chat_username, message_id)
        if not source_message or not source_message.media:
            await status_msg.edit_text("❌ No media found in this message")
            return
        
        # Get user settings
        user_settings = user_data.get(user_id, {})
        target_chat = user_settings.get('target', user_id)
        if target_chat == 'me':
            target_chat = user_id
        
        # Process caption
        original_caption = source_message.caption or ""
        processed_caption = original_caption
        
        # Apply replacements
        replacements = user_settings.get('replacements', {})
        for old_word, new_word in replacements.items():
            processed_caption = processed_caption.replace(old_word, new_word)
        
        # Add custom caption
        custom_caption = user_settings.get('caption', '')
        if custom_caption:
            if processed_caption:
                processed_caption = f"{processed_caption}\n\n{custom_caption}"
            else:
                processed_caption = custom_caption
        
        # Send based on media type
        if source_message.photo:
            await client.send_photo(
                target_chat,
                source_message.photo.file_id,
                caption=processed_caption or None
            )
        elif source_message.video:
            await client.send_video(
                target_chat,
                source_message.video.file_id,
                caption=processed_caption or None
            )
        elif source_message.document:
            await client.send_document(
                target_chat,
                source_message.document.file_id,
                caption=processed_caption or None
            )
        elif source_message.audio:
            await client.send_audio(
                target_chat,
                source_message.audio.file_id,
                caption=processed_caption or None
            )
        else:
            await status_msg.edit_text("❌ Media type not supported")
            return
        
        await status_msg.edit_text("✅ File copied successfully!")
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        if "chat not found" in str(e).lower():
            error_msg = "❌ Channel not found or not accessible"
        elif "private" in str(e).lower():
            error_msg = "❌ This appears to be a private channel"
        
        await message.reply_text(error_msg)

async def start_web_server():
    """Start web server for Render"""
    web_app = web.Application()
    web_app.router.add_get('/', handle_request)
    web_app.router.add_get('/health', handle_request)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Web server started on port {PORT}")

async def main():
    """Main function to start everything"""
    print("🚀 Starting Fast File Bot...")
    
    # Start web server
    await start_web_server()
    
    # Start Telegram client
    await app.start()
    print("✅ Bot started successfully!")
    print("🤖 Bot is now listening for messages...")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)  # Sleep for 1 hour

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
