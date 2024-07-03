import re
import asyncio
import os
import logging
import time
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.constants import ParseMode
import telegram
from collections import deque

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CUSTOM_MESSAGE = r"""
══════⊹⊱≼≽⊰⊹══════
*@NeonGhost\_Networks* `Search & Download Your Favourite Movies` 👇👇🆓
[Link 1](https://t\.me/\+6YAYymxzoqk5YmNl) [Link 2](https://t\.me/\+6YAYymxzoqk5YmNl)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
`Leak Viral Video MMS OYO` 🚨👇👇🆓
[Link 1](https://t\.me/\+XNvgEn\-PVqE1ZmU8) [Link 2](https://t\.me/\+XNvgEn\-PVqE1ZmU8)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
`TeraBox Viral Video Links`🔗🍑👇👇
[Link 1](https://t\.me/\+vgOaudZKle0zNmE0) [Link 2](https://t\.me/\+vgOaudZKle0zNmE0)
══════⊹⊱≼≽⊰⊹══════
══════⊹⊱≼≽⊰⊹══════
TeraBox Video Downloader Bot` 🎥🍿👇👇
[Link 1]( https://t.me/TeraBox_Download3r_Bot) [Link 2]( https://t.me/TeraBox_Download3r_Bot)
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

async def handle_user_interaction(update: Update, context):
    global total_messages_sent, user_interaction_cache
    
    try:
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
async def start(update: Update, context):
    await handle_user_interaction(update, context)
    user_info = f"{update.effective_user.first_name} {update.effective_user.last_name or ''} (@{update.effective_user.username or 'No username'}) (ID: {update.effective_user.id})"
    bot_info = f"{context.bot.first_name} (@{context.bot.username})"
    await send_notification(user_info, "Start command", bot_info)

async def echo(update: Update, context):
    await handle_user_interaction(update, context)

async def stats_command(update: Update, context):
    current_time = time.time()
    messages_last_5_min = sum(1 for msg_time in recent_messages if current_time - msg_time <= 300)
    stats_message = (
        f"Total messages sent: {total_messages_sent}\n"
        f"Messages sent in last 5 minutes: {messages_last_5_min}\n"
        f"Total bots running: {len(running_bots)}"
    )
    await update.message.reply_text(stats_message)

async def add_token_file(update: Update, context):
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Please reply to a document message containing the bot tokens.")
        return
    file_id = update.message.reply_to_message.document.file_id
    file = await context.bot.get_file(file_id)
    try:
        downloaded_file = await file.download_as_bytearray()
        tokens = re.findall(r'Bot token: (\d+:[A-Za-z0-9_-]+)', downloaded_file.decode('utf-8'))
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
        
        save_bot_tokens()
        await status_message.edit_text(f"Finished! Successfully added {new_bots} new bots from the file.")
    except Exception as e:
        await update.message.reply_text(f"Failed to add tokens from the file: {str(e)}")

async def list_running_bots(update: Update, context):
    if not running_bots:
        await update.message.reply_text("No bots are currently running.")
        return
    
    bot_list = "Running bots:\n\n"
    for bot in running_bots:
        bot_list += f"Name: {bot['name']}\n"
        bot_list += f"Username: @{bot['username']}\n"
        bot_list += f"Token: {bot['token'][:10]}...\n\n"
    
    await update.message.reply_text(bot_list)

# Utility functions
def load_bot_tokens():
    if os.path.exists(BOT_TOKENS_FILE):
        try:
            with open(BOT_TOKENS_FILE, 'r', encoding='utf-8') as f:
                tokens = []
                for line in f:
                    parts = line.strip().split(', ')
                    if parts and parts[0].startswith('Bot token:'):
                        token = parts[0].split(': ', 1)[1]
                        tokens.append(token)
                return tokens
        except UnicodeDecodeError:
            # If UTF-8 fails, try with 'latin-1' encoding
            with open(BOT_TOKENS_FILE, 'r', encoding='latin-1') as f:
                tokens = []
                for line in f:
                    parts = line.strip().split(', ')
                    if parts and parts[0].startswith('Bot token:'):
                        token = parts[0].split(': ', 1)[1]
                        tokens.append(token)
                return tokens
        except Exception as e:
            logger.error(f"Error loading bot tokens: {e}")
            return []
    return []

def save_bot_tokens():
    try:
        with open(BOT_TOKENS_FILE, 'w', encoding='utf-8') as f:
            for bot in running_bots:
                f.write(f"Bot token: {bot['token']}, Name: {bot['name']}, Username: {bot['username']}\n")
    except Exception as e:
        logger.error(f"Error saving bot tokens: {e}")

async def check_bot_token(token):
    try:
        bot = Bot(token)
        await bot.get_me()
        return True
    except telegram.error.InvalidToken:
        logger.error(f"Invalid token: {token[:10]}...")
        return False
    except Exception as e:
        logger.error(f"Error checking token {token[:10]}...: {str(e)}")
        return False

async def initialize_bot(token):
    global running_bots
    try:
        if not await check_bot_token(token):
            return None

        for bot in running_bots:
            if bot['token'] == token:
                logger.info(f"Bot with token {token[:10]}... is already running.")
                return None
        
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        app.add_error_handler(global_error_handler)
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        bot_info = await app.bot.get_me()
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
async def global_error_handler(update: Update, context: CallbackContext) -> None:
    error = context.error
    try:
        raise error
    except telegram.error.Unauthorized:
        logger.error(f"Unauthorized error: {error}")
    except telegram.error.BadRequest:
        logger.error(f"Bad request: {error}")
    except telegram.error.TimedOut:
        logger.error(f"Timed out: {error}")
    except telegram.error.NetworkError:
        logger.error(f"Network error: {error}")
    except AttributeError:
        logger.error(f"Attribute error: {error}")
    except Exception as e:
        logger.error(f"Unexpected error: {error}")
    
    # Notify about the error
    await send_notification("System", f"Global error: {str(error)}")

# File handler
async def file_handler(update: Update, context):
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
        await asyncio.sleep(1)  # Wait a bit between batches

# Main function
async def main():
    global running_bots
    tokens = load_bot_tokens()
    
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
        await personal_app.updater.start_polling()
    except Exception as e:
        logger.error(f"Error starting personal bot: {e}")
        return

    try:
        await asyncio.Event().wait()
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
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Critical error in main function: {e}")
            logger.info("Restarting main function in 60 seconds...")
            time.sleep(60)
