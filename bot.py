import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# === CONFIG - EDIT THESE ===
API_ID = 12345678  # From https://my.telegram.org
API_HASH = "your_api_hash_here"  # From https://my.telegram.org
BOT_TOKEN = "your_bot_token_here"  # From @BotFather
# === END CONFIG ===

app = Client("fast_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Simple storage
user_data = {}

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply(
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
async def set_caption(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) > 1:
        caption = ' '.join(message.command[1:])
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['caption'] = caption
        await message.reply(f"✅ Caption set: `{caption}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("❌ Usage: `/setcaption Your text`")

@app.on_message(filters.command("replace"))
async def set_replace(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) > 2:
        old, new = message.command[1], message.command[2]
        if user_id not in user_data:
            user_data[user_id] = {'replace': {}}
        if 'replace' not in user_data[user_id]:
            user_data[user_id]['replace'] = {}
        user_data[user_id]['replace'][old] = new
        await message.reply(f"✅ Replacement: `{old}` → `{new}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("❌ Usage: `/replace OLD_WORD NEW_WORD`")

@app.on_message(filters.command("target"))
async def set_target(client, message: Message):
    user_id = message.from_user.id
    if len(message.command) > 1:
        target = message.command[1]
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['target'] = target
        await message.reply(f"✅ Target: `{target}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply("❌ Usage: `/target CHAT_ID` or `/target me`")

@app.on_message(filters.command("info"))
async def show_info(client, message: Message):
    user_id = message.from_user.id
    user = user_data.get(user_id, {})
    
    caption = user.get('caption', 'Not set')
    target = user.get('target', 'Current chat')
    replaces = user.get('replace', {})
    
    text = f"**Your Settings:**\n\n**Caption:** `{caption}`\n**Target:** `{target}`\n**Replacements:** {len(replaces)}"
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.media & filters.private)
async def handle_media(client, message: Message):
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
            await message.reply("❌ Media type not supported")
            return
        
        await message.reply("✅ File sent!")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.regex(r'https?://t\.me/\w+/\d+') & filters.private)
async def handle_link(client, message: Message):
    user_id = message.from_user.id
    link = message.text
    
    try:
        parts = link.split('/')
        chat, msg_id = parts[-2], int(parts[-1])
        
        status = await message.reply("🔗 Processing...")
        source_msg = await app.get_messages(chat, msg_id)
        
        if not source_msg or not source_msg.media:
            await status.edit("❌ No media found")
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
            await status.edit("❌ Media type not supported")
            return
        
        await status.edit("✅ File copied!")
        
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

print("🚀 Fast File Bot Starting...")
app.run()
