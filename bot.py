#!/usr/bin/env python3
"""
YouTube & Saavn Music Downloader Telegram Bot
Supports video/audio downloads from YouTube and high-quality MP3 from JioSaavn
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from bot.config import Config
from bot.handlers import (
    start_command,
    help_command,
    youtube_handler,
    saavn_handler,
    quality_callback,
    format_selection
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot"""
    # Create download directory if not exists
    os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
    
    # Build application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("yt", youtube_handler))
    application.add_handler(CommandHandler("saavn", saavn_handler))
    
    # Callback handlers for inline buttons
    application.add_handler(CallbackQueryHandler(quality_callback, pattern="^quality_"))
    application.add_handler(CallbackQueryHandler(format_selection, pattern="^format_"))
    
    # Message handler for direct URLs
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    logger.info("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-detect URL type and route accordingly"""
    url = update.message.text
    
    if "youtube.com" in url or "youtu.be" in url:
        await youtube_handler(update, context, url)
    elif "jiosaavn.com" in url or "saavn.com" in url:
        await saavn_handler(update, context, url)
    else:
        await update.message.reply_text(
            "❌ Unsupported URL!\n\n"
            "I can download from:\n"
            "• YouTube (videos/shorts/playlists)\n"
            "• JioSaavn (songs/albums/playlists)\n\n"
            "Use /help for more info."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates"""
    logger.error(f"Update {update} caused error {context.error}")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again later."
        )

if __name__ == '__main__':
    main()
