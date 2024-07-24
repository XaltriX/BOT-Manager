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
    ("𝐕𝐢𝐫𝐚𝐥 𝐕𝐢𝐝𝐞𝐨𝐬 𝐏𝟎𝐫𝐧 𝐌𝐌𝐒", "movies"),
    ("𝐕𝐢𝐫𝐚𝐥 𝐕𝐢𝐝𝐞𝐨𝐬 𝐏𝟎𝐫𝐧 𝐌𝐌𝐒", "viral"),
    ("𝗧𝗲𝗿𝗮𝗕𝗼𝘅 𝗠𝗠𝗦 𝗟𝗶𝗻𝗸𝘀", "terabox"),
    ("𝗧𝗲𝗿𝗮𝗕𝗼𝘅 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗿 𝗕𝗼𝘁", "downloader")
]
BUTTON_URLS = {
    "movies": "https://t.me/+CUiCri9JMA45Mzk1",
    "viral": "https://t.me/+XNvgEn-PVqE1ZmU8",
    "terabox": "https://t.me/+vgOaudZKle0zNmE0",
    "downloader": "https://t.me/TeraBox_Download3r_Bot"
}
MAIN_BOT_TOKEN = '6836105234:AAFYHYLpQrecJGMVIRJHraGnHTbcON3pxxU'
NOTIFICATION_CHAT_ID = '-1002177330851'
BOT_TOKENS_FILE = 'bot_tokens.txt'

class SharedState:
    def __init__(self):
        self.total_messages_sent = 0
        self.running_bots = {}
        self.main_bot = None

shared_state = SharedState()

async def handle_user_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        shared_state.total_messages_sent += 1
        logger.info(f"Message sent to user {update.effective_user.id}")
        
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
        f"🤖 Total running bots: {len(shared_state.running_bots)}\n"
        f"💬 Total messages sent: {shared_state.total_messages_sent}\n"
        f"🧠 Memory usage: {memory_usage:.2f} MB\n"
        f"⚙️ CPU usage: {cpu_usage:.2f}%\n"
        f"💾 Disk usage: {disk_usage:.2f}%"
    )
    
    await update.message.reply_text(stats_message)

async def list_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not shared_state.running_bots:
        await update.message.reply_text("No bots are currently running.")
        return

    bot_list = "Running Bots:\n\n"
    for token, bot_data in shared_state.running_bots.items():
        bot_list += f"Name: {bot_data['name']}\nUsername: @{bot_data['username']}\n\n"

    await update.message.reply_text(bot_list)

async def send_notification(message):
    try:
        if shared_state.main_bot:
            await shared_state.main_bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=message)
        else:
            logger.error("Main bot not initialized for sending notifications")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

async def add_token_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document.file_name.endswith('.txt'):
        file = await context.bot.get_file(update.message.document.file_id)
        file_content = await file.download_as_bytearray()
        
        content = file_content.decode('utf-8')
        new_tokens = extract_tokens(content)
        
        if new_tokens:
            await update_token_file(new_tokens)
            await update.message.reply_text(f"Added {len(new_tokens)} new tokens to the bot network.")
            for token in new_tokens:
                if token != MAIN_BOT_TOKEN and token not in shared_state.running_bots:
                    await initialize_bot(token)
        else:
            await update.message.reply_text("No valid bot tokens found in the uploaded file.")
    else:
        await update.message.reply_text("Please upload a .txt file containing bot tokens.")

def extract_tokens(content):
    token_pattern = r'\b(?:\d+:[\w-]{35})\b'
    return list(set(re.findall(token_pattern, content)))

async def update_token_file(new_tokens):
    async with aiofiles.open(BOT_TOKENS_FILE, 'a') as f:
        await f.write('\n' + '\n'.join(new_tokens))

async def load_bot_tokens(file_path=BOT_TOKENS_FILE):
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            return extract_tokens(content)
    except Exception as e:
        logger.error(f"Error loading bot tokens: {e}")
        return []

async def initialize_bot(token, is_main_bot=False):
    if token in shared_state.running_bots:
        logger.info(f"Bot with token {token[:10]}... is already running.")
        return

    try:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        app.add_handler(CallbackQueryHandler(button_callback))
        
        if is_main_bot:
            app.add_handler(CommandHandler("stats", stats))
            app.add_handler(CommandHandler("add_token_file", add_token_file))
            app.add_handler(CommandHandler("list_bots", list_bots))
            shared_state.main_bot = app.bot
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
        bot_info = await app.bot.get_me()
        shared_state.running_bots[token] = {
            'name': bot_info.first_name,
            'username': bot_info.username,
            'app': app
        }
        logger.info(f"Bot @{bot_info.username} successfully started.")
        if not is_main_bot:
            await send_notification(f"New bot added: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")

async def main():
    # Initialize the main bot
    await initialize_bot(MAIN_BOT_TOKEN, is_main_bot=True)

    while True:
        try:
            tokens = await load_bot_tokens()
            
            for token in tokens:
                if token != MAIN_BOT_TOKEN and token not in shared_state.running_bots:
                    await initialize_bot(token)
            
            if len(shared_state.running_bots) <= 1:
                logger.warning("Only the main bot is running. Check your bot tokens.")
            else:
                logger.info(f"Successfully running {len(shared_state.running_bots)} bot(s).")
            
            while True:
                await asyncio.sleep(300)  # Check for new tokens every 5 minutes
                new_tokens = await load_bot_tokens()
                for token in new_tokens:
                    if token != MAIN_BOT_TOKEN and token not in shared_state.running_bots:
                        await initialize_bot(token)
        
        except Exception as e:
            logger.error(f"An error occurred in the main loop: {e}")
            await send_notification(f"Bot manager crashed. Restarting in 60 seconds. Error: {str(e)}")
            await asyncio.sleep(60)
        
        finally:
            for bot_data in shared_state.running_bots.values():
                try:
                    await bot_data['app'].stop()
                    await bot_data['app'].shutdown()
                except Exception as e:
                    logger.error(f"Error stopping bot {bot_data['username']}: {e}")
            
            shared_state.running_bots.clear()
            shared_state.main_bot = None

if __name__ == '__main__':
    asyncio.run(main())
