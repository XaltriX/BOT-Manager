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
import psutil
import gc
import sys
import platform

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Import resource module only on non-Windows platforms
if platform.system() != 'Windows':
    import resource

def escape_markdown_v2(text):
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Constants
CUSTOM_MESSAGE = escape_markdown_v2("""
══════⊹⊱≼≽⊰⊹══════
*@NeonGhost_Networks* Search & Download Your Favourite Movies 👇👇🆓
[Link 1](https://t.me/+CUiCri9JMA45Mzk1) [Link 2](https://t.me/+CUiCri9JMA45Mzk1)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
Leak Viral Video MMS OYO P0rn 🚨👇👇🆓
[Link 1](https://t.me/+XNvgEn-PVqE1ZmU8) [Link 2](https://t.me/+XNvgEn-PVqE1ZmU8)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
TeraBox Viral Video Links🔗🍑👇👇
[Link 1](https://t.me/+vgOaudZKle0zNmE0) [Link 2](https://t.me/+vgOaudZKle0zNmE0)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
TeraBox Video Downloader Bot 🎥🍿👇👇
[Link 1](https://t.me/TeraBox_Download3r_Bot) [Link 2](https://t.me/TeraBox_Download3r_Bot)
══════⊹⊱≼≽⊰⊹══════
For More: - *@NeonGhost_Networks*
""")

NOTIFICATION_BOT_TOKEN = '6836105234:AAFYHYLpQrecJGMVIRJHraGnHTbcON3pxxU'
NOTIFICATION_CHAT_ID = '-1002177330851'
BOT_TOKENS_FILE = 'bot_tokens.txt'

# Global variables
total_messages_sent = 0
running_bots = []
recent_messages = deque(maxlen=1000)
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
rate_limiter = RateLimiter(rate=30, per=60)  # 30 messages per minute

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
            logger.info(f"Message sent by {bot_info} to {user_info}")
        except telegram.error.BadRequest as e:
            error_message = f"Error sending message: {str(e)}"
            logger.error(f"BadRequest: {error_message}")
            await send_notification(user_info, "Error", f"{bot_info}\n{error_message}")
        except AttributeError:
            error_message = "Error: Message object is None"
            logger.error(f"AttributeError: {error_message}")
            await send_notification(user_info, "Error", f"{bot_info}\n{error_message}")
        
        # Call memory management function every 1000 messages
        if total_messages_sent % 1000 == 0:
            await free_cache_memory()
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
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    stats_message = (
        f"Total messages sent: {total_messages_sent}\n"
        f"Messages sent in last 5 minutes: {messages_last_5_min}\n"
        f"Total bots running: {len(running_bots)}\n"
        f"CPU Usage: {cpu_usage}%\n"
        f"Memory Usage: {memory_usage}%"
    )
    await update.message.reply_text(stats_message)

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

async def status_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_message = "Bot Status:\n\n"
    for bot in running_bots:
        try:
            await bot['app'].bot.get_me()
            status = "Online"
        except TelegramError:
            status = "Offline"
        status_message += f"{bot['name']} (@{bot['username']}): {status}\n"
    await update.message.reply_text(status_message)

async def add_token_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document is None:
        await update.message.reply_text("Please upload a text file containing bot tokens.")
        return

    file = await context.bot.get_file(update.message.document.file_id)
    
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
            await file.download_to_memory(temp_file)
            temp_file_path = temp_file.name

        new_tokens = await load_bot_tokens(temp_file_path)

        await aiofiles.os.remove(temp_file_path)

        if not new_tokens:
            await update.message.reply_text("No valid tokens found in the file.")
            return

        added_count = 0
        for token in new_tokens:
            if token not in [bot['token'] for bot in running_bots]:
                app = await initialize_bot(token)
                if app:
                    added_count += 1

        await save_bot_tokens()
        
        await update.message.reply_text(f"Successfully added and started {added_count} new bot(s).")
    except Exception as e:
        logger.error(f"Error processing token file: {e}")
        await update.message.reply_text("An error occurred while processing the file. Please try again.")

# Utility functions
async def load_bot_tokens(file_path=BOT_TOKENS_FILE):
    if await aiofiles.os.path.exists(file_path):
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                # Use regex to find patterns that look like bot tokens
                token_pattern = r'\b(?:\d+:[\w-]{35})\b'
                tokens = re.findall(token_pattern, content)
                return list(set(tokens))  # Remove duplicates
        except Exception as e:
            logger.error(f"Error loading bot tokens: {e}")
    return []

async def save_bot_tokens():
    try:
        async with aiofiles.open(BOT_TOKENS_FILE, 'w', encoding='utf-8') as f:
            for bot in running_bots:
                await f.write(f"{bot['token']}\n")
        logger.info(f"Saved {len(running_bots)} bot tokens to {BOT_TOKENS_FILE}")
    except Exception as e:
        logger.error(f"Error saving bot tokens: {e}")

async def check_bot_token(token):
    try:
        bot = Bot(token)
        bot_info = await bot.get_me()
        return True, bot_info
    except TelegramError as e:
        logger.error(f"Error checking token {token[:10]}...: {str(e)}")
        return False, None

async def initialize_bot(token):
    global running_bots, bot_applications
    try:
        if token in bot_applications:
            logger.info(f"Bot with token {token[:10]}... is already running.")
            return bot_applications[token]

        is_valid, bot_info = await check_bot_token(token)
        if not is_valid:
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
        await asyncio.sleep(30)  # Check every 30 seconds

async def check_and_reconnect_bot(bot):
    try:
        await bot['app'].bot.get_me()
    except (NetworkError, TelegramError) as e:
        logger.warning(f"Bot {bot['username']} seems to be disconnected. Error: {e}. Attempting to reconnect...")
        await reconnect_bot(bot)
    except Exception as e:
        logger.error(f"Error checking bot {bot['username']}: {e}")

def global_exception_handler(loop, context):
    exception = context.get('exception', context['message'])
    logger.error(f"Unhandled exception: {exception}")
    logger.error(f"Exception context: {context}")

async def free_cache_memory():
    collected = gc.collect()
    logger.info(f"Garbage collector: collected {collected} objects.")
    
    try:
        import ctypes
        if platform.system() == 'Windows':
            ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1)
            logger.info("Called SetProcessWorkingSetSize to release memory to the system.")
        else:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.info("Called malloc_trim(0) to release memory to the system.")
    except Exception as e:
        logger.warning(f"Failed to call memory release function: {e}")
    
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        logger.info(f"Current memory usage: {memory_info.rss / (1024 * 1024):.2f} MB")
    except Exception as e:
        logger.warning(f"Failed to get memory usage: {e}")

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
    personal_app.add_handler(CommandHandler("list_bots", list_running_bots))
    personal_app.add_handler(CommandHandler("status", status_check))
    personal_app.add_handler(CommandHandler("add_token_file", add_token_file))
    personal_app.add_error_handler(global_error_handler)
    
    try:
        await personal_app.initialize()
        await personal_app.start()
        await personal_app.updater.start_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error starting personal bot: {e}")
        return

    # Set up the global exception handler
    asyncio.get_event_loop().set_exception_handler(global_exception_handler)

    # Start the bot checking and reconnection task
    check_task = asyncio.create_task(check_and_reconnect_bots())

    try:
        while True:
            await asyncio.sleep(60)
            if not check_task.done():
                logger.info("Bot checking task is running")
            else:
                logger.error("Bot checking task has stopped unexpectedly")
                check_task = asyncio.create_task(check_and_reconnect_bots())
            
            # Periodically free cache memory
            await free_cache_memory()
    except asyncio.CancelledError:
        logger.info("Main loop was cancelled")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        check_task.cancel()
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
