import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters

# Get environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

print("🔧 Starting bot...")
print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH[:10]}..." if API_HASH else "No API_HASH")
print(f"BOT_TOKEN: {BOT_TOKEN[:10]}..." if BOT_TOKEN else "No BOT_TOKEN")

# Create client
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Web server for Render
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")

# Simple command handler
@app.on_message(filters.command("start"))
async def start_command(client, message):
    print(f"📩 Received start from user {message.from_user.id}")
    await message.reply_text("🤖 **Hello! I'm alive!**\n\nSend me any media file or use /help")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply_text("🆘 **Help**\n\nJust forward any file to me and I'll copy it instantly!")

@app.on_message(filters.text & filters.private)
async def text_handler(client, message):
    if not message.text.startswith('/'):
        await message.reply_text("👋 Hi! I can copy files instantly.\n\nUse /start or /help")

@app.on_message(filters.media & filters.private)
async def media_handler(client, message):
    try:
        user_id = message.from_user.id
        await message.reply_text("📥 Processing your file...")
        
        if message.photo:
            await client.send_photo(user_id, message.photo.file_id, caption="✅ Copied photo!")
        elif message.video:
            await client.send_video(user_id, message.video.file_id, caption="✅ Copied video!")
        elif message.document:
            await client.send_document(user_id, message.document.file_id, caption="✅ Copied document!")
        elif message.audio:
            await client.send_audio(user_id, message.audio.file_id, caption="✅ Copied audio!")
        else:
            await message.reply_text("❌ Unsupported media type")
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

async def main():
    print("🚀 Starting bot services...")
    
    # Start web server
    await start_web_server()
    
    # Start Telegram bot
    await app.start()
    print("✅ Bot started successfully!")
    print("🎯 Bot is now ready and listening...")
    
    # Get bot info
    me = await app.get_me()
    print(f"🤖 Bot username: @{me.username}")
    
    # Keep running forever
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Bot crashed: {e}")
