import asyncio
import os
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class TelegramForwardBot:
    def __init__(self):
        self.validate_environment()
        
        self.api_id = int(os.getenv('API_ID'))
        self.api_hash = os.getenv('API_HASH')
        self.bot_token = os.getenv('BOT_TOKEN')
        self.client = None
        
    def validate_environment(self):
        """Validate all required environment variables"""
        required_vars = ['API_ID', 'API_HASH', 'BOT_TOKEN']
        for var in required_vars:
            if not os.getenv(var):
                raise ValueError(f"❌ Missing required environment variable: {var}")
        logging.info("✅ Environment validation passed")
    
    async def initialize(self):
        """Initialize Telegram client"""
        try:
            self.client = TelegramClient(
                'bot_session', 
                self.api_id, 
                self.api_hash
            )
            await self.client.start(bot_token=self.bot_token)
            
            me = await self.client.get_me()
            logging.info(f"✅ Bot initialized successfully: @{me.username}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to initialize bot: {e}")
            return False

    def parse_telegram_url(self, url):
        """Parse Telegram message URL and convert to -100 format"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) >= 3 and path_parts[0] == 'c':
                channel_id = int(path_parts[1])
                message_id = int(path_parts[2])
                # Convert to -100 format for supergroups/channels
                if channel_id > 0:
                    channel_id = int(f"-100{channel_id}")
                return channel_id, message_id
            return None, None
        except Exception as e:
            logging.error(f"❌ Failed to parse URL {url}: {e}")
            return None, None

    def parse_target(self, target_input):
        """Parse target group/topic"""
        try:
            if '/' in target_input:
                group_id, topic_id = target_input.split('/')
                return int(group_id), int(topic_id)
            return int(target_input), None
        except Exception as e:
            logging.error(f"❌ Failed to parse target {target_input}: {e}")
            return None, None

    async def forward_command(self, target_input, first_url, last_url):
        """Handle forward command"""
        try:
            # Parse target
            group_id, topic_id = self.parse_target(target_input)
            if not group_id:
                return "❌ Invalid target format. Use: group_id/topic_id"

            # Parse source URLs and convert to -100 format
            source_channel_id, start_message_id = self.parse_telegram_url(first_url)
            _, end_message_id = self.parse_telegram_url(last_url)
            
            if not source_channel_id or not start_message_id or not end_message_id:
                return "❌ Failed to parse source URLs"

            logging.info(f"🎯 Starting forward command:")
            logging.info(f"   Target: Group {group_id}, Topic {topic_id}")
            logging.info(f"   Source: Channel {source_channel_id}, Messages {start_message_id}-{end_message_id}")

            # Debug: Check if we can access the channel
            try:
                channel_entity = await self.client.get_entity(source_channel_id)
                logging.info(f"✅ Successfully accessed channel: {channel_entity.title}")
            except Exception as e:
                logging.error(f"❌ Cannot access channel {source_channel_id}: {e}")
                return f"❌ Cannot access source channel. Make sure bot is admin. Error: {e}"

            # Get media messages in range with detailed logging
            media_messages = []
            min_id = min(start_message_id, end_message_id)
            max_id = max(start_message_id, end_message_id)
            
            logging.info(f"🔍 Scanning messages {min_id} to {max_id}...")
            
            total_messages = 0
            async for message in self.client.iter_messages(
                source_channel_id,
                min_id=min_id,
                max_id=max_id
            ):
                total_messages += 1
                if message.media:
                    media_type = "unknown"
                    if hasattr(message.media, 'document'):
                        media_type = "document"
                    elif hasattr(message.media, 'photo'):
                        media_type = "photo"
                    elif hasattr(message.media, 'video'):
                        media_type = "video"
                    
                    logging.info(f"📄 Found media: Message {message.id} - Type: {media_type}")
                    media_messages.append(message)

            logging.info(f"📊 Scan complete: {total_messages} total messages, {len(media_messages)} media files")

            if not media_messages:
                return f"❌ No media files found between messages {min_id} and {max_id}. Found {total_messages} total messages but no media."

            total_files = len(media_messages)
            logging.info(f"📁 Forwarding {total_files} media files")

            # Forward all media to target topic
            success_count = 0
            for index, message in enumerate(media_messages, 1):
                try:
                    await self.client.forward_messages(
                        entity=group_id,
                        messages=message.id,
                        from_peer=source_channel_id,
                        reply_to=topic_id
                    )
                    logging.info(f"✅ [{index}/{total_files}] Forwarded message {message.id}")
                    success_count += 1
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except FloodWaitError as e:
                    logging.warning(f"⏳ [{index}/{total_files}] Flood wait for {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logging.error(f"❌ [{index}/{total_files}] Failed to forward message {message.id}: {e}")

            result = f"✅ Forward completed! {success_count}/{total_files} files sent successfully"
            logging.info(result)
            return result

        except Exception as e:
            error_msg = f"❌ Forward failed: {e}"
            logging.error(error_msg)
            return error_msg

    async def handle_telegram_messages(self):
        """Handle Telegram messages"""
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            welcome_text = """
🤖 **Telegram Forward Bot**

**Commands:**
`/forward target_id first_url last_url`

**Example:**
`/forward 2952095978/5 https://t.me/c/2960040643/223 https://t.me/c/2960040643/306`

**Note:** Bot must be admin in both source channel and target group.
            """
            await event.reply(welcome_text)

        @self.client.on(events.NewMessage(pattern='/forward'))
        async def forward_handler(event):
            try:
                message_text = event.message.text
                parts = message_text.split()
                
                if len(parts) != 4:
                    await event.reply("❌ Invalid format. Use: `/forward target_id first_url last_url`")
                    return

                _, target_input, first_url, last_url = parts

                # Send processing message
                processing_msg = await event.reply("🔄 Processing your forward request...")

                # Execute forward command
                result = await self.forward_command(target_input, first_url, last_url)

                # Update with result
                await processing_msg.edit(result)

            except Exception as e:
                logging.error(f"❌ Error handling message: {e}")
                await event.reply(f"❌ Error: {str(e)}")

    async def run(self):
        """Run the bot"""
        if not await self.initialize():
            return

        # Setup message handlers
        await self.handle_telegram_messages()

        logging.info("🤖 Bot is now running! Send /start to see commands.")

        try:
            await self.client.run_until_disconnected()
        except KeyboardInterrupt:
            logging.info("🛑 Received interrupt signal")

    async def close(self):
        """Clean shutdown"""
        if self.client:
            await self.client.disconnect()
        logging.info("🔚 Bot shutdown completed")

async def main():
    bot = TelegramForwardBot()
    try:
        await bot.run()
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
