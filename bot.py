import re
import asyncio
import os
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
import telegram
from collections import deque
from time import time

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
`Kalki 2898 AD Full Movie` 🎥🍿👇👇
[Link 1](https://t\.me/\+VD5n7M6FIWFmYTg1) [Link 2](https://t\.me/\+VD5n7M6FIWFmYTg1)
══════⊹⊱≼≽⊰⊹══════
For More: \- *@NeonGhost\_Networks*
"""

NOTIFICATION_BOT_TOKEN = '6836105234:AAFYHYLpQrecJGMVIRJHraGnHTbcON3pxxU'
NOTIFICATION_CHAT_ID = '-1002177330851'

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
        print(f"Error sending notification: {e}")

async def handle_user_interaction(update: Update, context):
    global total_messages_sent, user_interaction_cache
    
    user = update.effective_user
    chat = update.effective_chat
    bot = context.bot
    
    user_info = f"{user.first_name} {user.last_name or ''} (@{user.username or 'No username'}) (ID: {user.id})"
    bot_info = f"{bot.first_name} (@{bot.username})"
    
    interaction_key = f"{user.id}_{bot.id}_{chat.id}"
    
    if interaction_key not in user_interaction_cache:
        user_interaction_cache.add(interaction_key)
        await send_notification(user_info, "New user interaction", bot_info)
    
    try:
        await update.message.reply_text(CUSTOM_MESSAGE, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
        total_messages_sent += 1
        recent_messages.append(time())
        await send_notification(user_info, "Custom message sent", bot_info)
    except telegram.error.TelegramError as e:
        error_message = f"Error sending message: {str(e)}"
        await send_notification(user_info, "Error", f"{bot_info}\n{error_message}")

# Command handlers
async def start(update: Update, context):
    await handle_user_interaction(update, context)
    user_info = f"{update.effective_user.first_name} {update.effective_user.last_name or ''} (@{update.effective_user.username or 'No username'}) (ID: {update.effective_user.id})"
    bot_info = f"{context.bot.first_name} (@{context.bot.username})"
    await send_notification(user_info, "Start command", bot_info)

async def echo(update: Update, context):
    await handle_user_interaction(update, context)

async def stats_command(update: Update, context):
    current_time = time()
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
        new_bots = 0
        for token in tokens:
            bot = await initialize_bot(token)
            if bot:
                new_bots += 1
        await update.message.reply_text(f"Successfully added {new_bots} new bots from the file.")
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
def read_tokens(file_path):
    token_pattern = r'Bot token: (\d+:[A-Za-z0-9_-]+)'
    tokens = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            tokens = re.findall(token_pattern, content)
    except FileNotFoundError:
        print(f"Token file not found: {file_path}")
    except Exception as e:
        print(f"Error reading token file: {str(e)}")
    return tokens

async def initialize_bot(token):
    global running_bots
    try:
        for bot in running_bots:
            if bot['token'] == token:
                print(f"Bot with token {token[:10]}... is already running.")
                return None
        
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
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
        print(f"Bot with token {token[:10]}... successfully started.")
        return app
    except telegram.error.InvalidToken:
        print(f"Invalid token: {token[:10]}... Skipping this bot.")
    except Exception as e:
        print(f"Error initializing bot with token {token[:10]}...: {str(e)}")
    
    await asyncio.sleep(0.5)  # Reduced delay to 0.5 seconds
    return None

# Error handler
async def error_handler(update: Update, context):
    error_message = f"An error occurred: {context.error}"
    print(error_message)
    await send_notification("System", "Error", error_message)

# File handler
async def file_handler(update: Update, context):
    if update.message.document:
        file_id = update.message.document.file_id
        new_file = await context.bot.get_file(file_id)
        file_path = os.path.join("uploaded_files", update.message.document.file_name)
        await new_file.download(file_path)
        uploaded_files[update.message.message_id] = file_path
        await update.message.reply_text(f"File {update.message.document.file_name} uploaded. Reply with /add_token_file to add tokens from this file.")

# Main function
async def main():
    global running_bots
    token_file = 'bot_tokens.txt'
    tokens = read_tokens(token_file)
    
    # Use asyncio.gather to start bots concurrently
    await asyncio.gather(*[initialize_bot(token) for token in tokens])
    
    if not running_bots:
        print("No bots were successfully initialized. Exiting.")
        return
    print(f"Successfully started {len(running_bots)} bot(s).")

    personal_app = Application.builder().token(NOTIFICATION_BOT_TOKEN).build()
    personal_app.add_handler(CommandHandler("stats", stats_command))
    personal_app.add_handler(CommandHandler("add_token_file", add_token_file))
    personal_app.add_handler(CommandHandler("list_bots", list_running_bots))
    personal_app.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    personal_app.add_error_handler(error_handler)
    await personal_app.initialize()
    await personal_app.start()
    await personal_app.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        for bot in running_bots:
            await bot['app'].stop()
            await bot['app'].shutdown()
        await personal_app.stop()
        await personal_app.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
