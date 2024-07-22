import asyncio
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError
import aiofiles
import re
import psutil
import os

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CAPTION = "@NeonGhost_Networks"
BUTTONS = [
    ("Movies", "movies"),
    ("Viral Videos", "viral"),
    ("TeraBox Links", "terabox"),
    ("TeraBox Downloader", "downloader")
]
BUTTON_URLS = {
    "movies": "https://t.me/+CUiCri9JMA45Mzk1",
    "viral": "https://t.me/+XNvgEn-PVqE1ZmU8",
    "terabox": "https://t.me/+vgOaudZKle0zNmE0",
    "downloader": "https://t.me/TeraBox_Download3r_Bot"
}
NOTIFICATION_BOT_TOKEN = '6836105234:AAFYHYLpQrecJGMVIRJHraGnHTbcON3pxxU'
NOTIFICATION_CHAT_ID = '-1002177330851'
BOT_TOKENS_FILE = 'bot_tokens.txt'

# Global variables
total_messages_sent = 0
running_bots = []

async def handle_user_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_messages_sent
    
    try:
        keyboard = [
            [InlineKeyboardButton(text, callback_data=data)] for text, data in BUTTONS
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            CAPTION,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        total_messages_sent += 1
        logger.info(f"Message sent to user {update.effective_user.id}")
        
        # Notify about new user interaction
        await send_notification(f"New user interaction from: {update.effective_user.id}")
    except TelegramError as e:
        logger.error(f"Error sending message: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    button_data = query.data
    if button_data in BUTTON_URLS:
        url = BUTTON_URLS[button_data]
        await query.edit_message_text(
            text=f"{CAPTION}\n\n{url}",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"User {query.from_user.id} clicked button: {button_data}")
        await send_notification(f"User {query.from_user.id} clicked button: {button_data}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_user_interaction(update, context)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_user_interaction(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / 1024 / 1024  # in MB
    cpu_usage = process.cpu_percent(interval=1)
    disk_usage = psutil.disk_usage('/').percent
    
    stats_message = (
        f"📊 Bot Network Stats 📊\n\n"
        f"🤖 Total running bots: {len(running_bots)}\n"
        f"💬 Total messages sent: {total_messages_sent}\n"
        f"🧠 Memory usage: {memory_usage:.2f} MB\n"
        f"⚙️ CPU usage: {cpu_usage:.2f}%\n"
        f"💾 Disk usage: {disk_usage:.2f}%"
    )
    
    await update.message.reply_text(stats_message)

async def send_notification(message):
    try:
        bot = Bot(NOTIFICATION_BOT_TOKEN)
        await bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=message)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

async def load_bot_tokens(file_path=BOT_TOKENS_FILE):
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            token_pattern = r'\b(?:\d+:[\w-]{35})\b'
            return list(set(re.findall(token_pattern, content)))
    except Exception as e:
        logger.error(f"Error loading bot tokens: {e}")
        return []

async def initialize_bot(token):
    try:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CallbackQueryHandler(button_callback))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
        bot_info = await app.bot.get_me()
        running_bots.append({
            'token': token,
            'name': bot_info.first_name,
            'username': bot_info.username,
            'app': app
        })
        logger.info(f"Bot @{bot_info.username} successfully started.")
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")

async def main():
    while True:
        try:
            tokens = await load_bot_tokens()
            
            for token in tokens:
                if token not in [bot['token'] for bot in running_bots]:
                    await initialize_bot(token)
            
            if not running_bots:
                logger.warning("No bots were successfully initialized.")
            else:
                logger.info(f"Successfully started {len(running_bots)} bot(s).")
            
            await send_notification(f"Bot manager started with {len(running_bots)} bots.")
            
            while True:
                await asyncio.sleep(300)  # Check for new tokens every 5 minutes
                new_tokens = await load_bot_tokens()
                for token in new_tokens:
                    if token not in [bot['token'] for bot in running_bots]:
                        await initialize_bot(token)
                        await send_notification(f"New bot added: @{running_bots[-1]['username']}")
        
        except Exception as e:
            logger.error(f"An error occurred in the main loop: {e}")
            await send_notification(f"Bot manager crashed. Restarting in 60 seconds. Error: {str(e)}")
            await asyncio.sleep(60)
        
        finally:
            for bot in running_bots:
                try:
                    await bot['app'].stop()
                    await bot['app'].shutdown()
                except Exception as e:
                    logger.error(f"Error stopping bot {bot['username']}: {e}")
            
            running_bots.clear()

if __name__ == '__main__':
    asyncio.run(main())
