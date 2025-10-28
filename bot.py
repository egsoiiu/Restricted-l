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
    handlers=[
        logging.StreamHandler()
    ]
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
                'forward_bot_session', 
                self.api_id, 
                self.api_hash
            )
            await self.client.start(bot_token=self.bot_token)
            
            # Get bot info
            me = await self.client.get_me()
            logging.info(f"✅ Bot initialized successfully: @{me.username}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to initialize bot: {e}")
            return False

    def parse_telegram_url(self, url):
        """Parse Telegram message URL to extract channel and message ID"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            channel_id = None
            message_id = None
            
            if len(path_parts) >= 3 and path_parts[0] == 'c':
                channel_id = int(path_parts[1])
                message_id = int(path_parts[2])
            elif len(path_parts) >= 2:
                channel_username = path_parts[0]
                message_id = int(path_parts[1])
                channel_id = channel_username
            
            return channel_id, message_id
        except Exception as e:
            logging.error(f"❌ Failed to parse URL {url}: {e}")
            return None, None

    def parse_target(self, target_input):
        """Parse target group/topic format: group_id/topic_id"""
        try:
            if '/' in target_input:
                group_id, topic_id = target_input.split('/')
                return int(group_id), int(topic_id)
            else:
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

            # Parse source URLs
            source_channel, start_message_id = self.parse_telegram_url(first_url)
            _, end_message_id = self.parse_telegram_url(last_url)
            
            if not source_channel or not start_message_id or not end_message_id:
                return "❌ Failed to parse source URLs"

            logging.info(f"🎯 Starting forward command:")
            logging.info(f"   Target: Group {group_id}, Topic {topic_id}")
            logging.info(f"   Source: Channel {source_channel}, Messages {start_message_id}-{end_message_id}")

            # Get media messages in range
            media_messages = await self.get_media_messages_in_range(
                source_channel, start_message_id, end_message_id
            )

            if not media_messages:
                return "❌ No media files found in the specified range"

            total_files = len(media_messages)
            logging.info(f"📁 Found {total_files} media files to forward")

            # Forward all media to target topic
            success_count = await self.forward_media_to_topic(
                group_id, topic_id, source_channel, media_messages
            )

            result = f"✅ Forward completed! {success_count}/{total_files} files sent successfully"
            logging.info(result)
            return result

        except Exception as e:
            error_msg = f"❌ Forward failed: {e}"
            logging.error(error_msg)
            return error_msg

    async def get_media_messages_in_range(self, source_channel, start_id, end_id):
        """Get media messages between start and end message IDs"""
        media_messages = []
        try:
            min_id = min(start_id, end_id)
            max_id = max(start_id, end_id)
            
            logging.info(f"🔍 Fetching media from message {min_id} to {max_id}")

            async for message in self.client.iter_messages(
                source_channel, 
                min_id=min_id, 
                max_id=max_id
            ):
                if message.media and not message.media.webpage:
                    media_messages.append(message)

            # Sort by message ID to maintain order
            media_messages.sort(key=lambda x: x.id)
            logging.info(f"✅ Found {len(media_messages)} media messages")
            return media_messages

        except Exception as e:
            logging.error(f"❌ Error fetching media messages: {e}")
            return []

    async def forward_media_to_topic(self, group_id, topic_id, source_channel, media_messages):
        """Forward all media messages to the target topic"""
        success_count = 0
        total_files = len(media_messages)
        
        for index, message in enumerate(media_messages, 1):
            if await self.forward_single_message(group_id, topic_id, source_channel, message, index, total_files):
                success_count += 1

            # Rate limiting
            await asyncio.sleep(1)
        
        return success_count

    async def forward_single_message(self, group_id, topic_id, source_channel, message, current, total):
        """Forward single message to topic"""
        try:
            await self.client.forward_messages(
                entity=group_id,
                messages=message.id,
                from_peer=source_channel,
                reply_to=topic_id
            )
            
            logging.info(f"✅ [{current}/{total}] Forwarded message {message.id}")
            return True
            
        except FloodWaitError as e:
            logging.warning(f"⏳ [{current}/{total}] Flood wait for {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return False
        except Exception as e:
            logging.error(f"❌ [{current}/{total}] Failed to forward message {message.id}: {e}")
            return False

    async def handle_telegram_messages(self):
        """Handle Telegram messages"""
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Handle /start command"""
            welcome_text = """
🤖 **Telegram Forward Bot**

**Commands:**
`/forward target_id first_url last_url`

**Example:**
`/forward 3187801487/38 https://t.me/c/2387726302/7 https://t.me/c/2387726302/77`

**Format:**
- `target_id`: GroupID/TopicID (e.g., 3187801487/38)
- `first_url`: First message URL
- `last_url`: Last message URL

The bot will forward all media files between the first and last URLs to the specified topic.
            """
            await event.reply(welcome_text)

        @self.client.on(events.NewMessage(pattern='/forward'))
        async def forward_handler(event):
            """Handle /forward command"""
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

        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            """Handle /help command"""
            help_text = """
🆘 **Help Guide**

**Commands:**
• `/start` - Start the bot and see instructions
• `/forward target first last` - Forward media between URLs
• `/help` - Show this help message

**URL Format:**
- Source URLs: `https://t.me/c/channel_id/message_id`
- Target: `group_id/topic_id`

**Requirements:**
- Bot must be admin in both source channel and target group
- Target group must have topics enabled
            """
            await event.reply(help_text)

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
