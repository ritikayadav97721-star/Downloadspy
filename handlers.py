"""Telegram bot command handlers"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.youtube_downloader import YouTubeDownloader
from bot.saavn_downloader import SaavnDownloader
from bot.config import Config

logger = logging.getLogger(__name__)
yt_dl = YouTubeDownloader()
saavn_dl = SaavnDownloader()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = (
        "🎬 *YouTube & 🎵 Saavn Downloader Bot*\n\n"
        "I can download:\n"
        "• YouTube videos (up to 50MB)\n"
        "• YouTube Shorts\n"
        "• YouTube Playlists (first few songs)\n"
        "• JioSaavn songs in high quality\n"
        "• JioSaavn albums & playlists\n\n"
        "*Commands:*\n"
        "/yt <url> - Download YouTube video\n"
        "/saavn <url or search> - Download Saavn music\n"
        "/help - Show help message\n\n"
        "Or simply send me a URL directly!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = (
        "📖 *How to use:*\n\n"
        "*YouTube:*\n"
        "1. Send /yt followed by video URL\n"
        "2. Choose quality (720p, 1080p, or Audio)\n"
        "3. Wait for download\n\n"
        "*Saavn:*\n"
        "1. Send /saavn followed by song name or URL\n"
        "2. Select from search results\n"
        "3. Get high-quality MP3\n\n"
        "*Examples:*\n"
        "`/yt https://youtube.com/watch?v=...`\n"
        "`/saavn Tere Vaaste`\n"
        "`/saavn https://jiosaavn.com/song/...`\n\n"
        "⚠️ Note: Files larger than 50MB cannot be sent due to Telegram limits."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def youtube_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str = None):
    """Handle YouTube download requests"""
    if not url:
        if not context.args:
            await update.message.reply_text("❌ Please provide a YouTube URL\nExample: `/yt https://youtube.com/watch?v=...`", parse_mode='Markdown')
            return
        url = context.args[0]
    
    # Validate URL
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Invalid YouTube URL")
        return
    
    processing_msg = await update.message.reply_text("🔍 Fetching video info...")
    
    # Get video info
    info = yt_dl.get_info(url)
    if not info:
        await processing_msg.edit_text("❌ Failed to fetch video info. Check if the video is available.")
        return
    
    # Check duration (skip if too long)
    if info['duration'] and info['duration'] > 600:  # 10 minutes
        await processing_msg.edit_text("⚠️ Video too long (max 10 minutes for free tier)")
        return
    
    # Create quality selection buttons
    keyboard = []
    available_qualities = []
    
    # Check available formats
    if info['formats']['video']:
        qualities = ['720', '480'] if any(q['quality'] == '720p' for q in info['formats']['video']) else ['480']
        for q in qualities:
            keyboard.append([InlineKeyboardButton(f"📹 {q}p", callback_data=f"quality_yt_{q}_{url}")])
    
    # Always add audio option
    keyboard.append([InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data=f"quality_yt_audio_{url}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await processing_msg.edit_text(
        f"🎬 *{info['title']}*\n"
        f"👤 {info['uploader']}\n"
        f"⏱️ {info['duration']//60}:{info['duration']%60:02d}\n\n"
        f"Select quality:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def saavn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str = None):
    """Handle Saavn download requests"""
    if not query:
        if not context.args:
            await update.message.reply_text("❌ Please provide a song name or URL\nExample: `/saavn Tere Vaaste` or `/saavn <url>`", parse_mode='Markdown')
            return
        query = " ".join(context.args)
    
    processing_msg = await update.message.reply_text("🔍 Searching...")
    
    # Check if it's a URL
    if "jiosaavn.com" in query or "saavn.com" in query:
        # Direct URL download
        song_data = saavn_dl.get_song_details(query)
        if not song_data:
            await processing_msg.edit_text("❌ Failed to fetch song details")
            return
        
        await processing_msg.edit_text(f"⬇️ Downloading *{song_data['title']}*...", parse_mode='Markdown')
        
        file_path = saavn_dl.download_song(song_data)
        if not file_path:
            await processing_msg.edit_text("❌ Download failed")
            return
        
        # Send audio
        with open(file_path, 'rb') as audio:
            await update.message.reply_audio(
                audio,
                title=song_data['title'],
                performer=song_data['artist'],
                duration=song_data['duration'],
                thumbnail=song_data['image'] if song_data['image'] else None
            )
        
        saavn_dl.clean_up(file_path)
        await processing_msg.delete()
    else:
        # Search query
        results = saavn_dl.search(query)
        if not results:
            await processing_msg.edit_text("❌ No results found")
            return
        
        keyboard = []
        for i, song in enumerate(results[:5]):
            keyboard.append([InlineKeyboardButton(
                f"🎵 {song['title']} - {song['artist']}", 
                callback_data=f"format_saavn_{song['url']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await processing_msg.edit_text("🎵 Select a song:", reply_markup=reply_markup)

async def quality_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection for YouTube"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    if len(data) < 4:
        return
    
    platform = data[1]
    quality = data[2]
    url = '_'.join(data[3:])  # Reconstruct URL
    
    await query.edit_message_text(f"⬇️ Downloading in {quality}p... This may take a moment.")
    
    # Download
    audio_only = (quality == "audio")
    file_path = yt_dl.download(url, quality=quality, audio_only=audio_only)
    
    if not file_path:
        await query.edit_message_text("❌ Download failed. Video may be restricted or too large.")
        return
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size > Config.MAX_FILE_SIZE:
        yt_dl.clean_up(file_path)
        await query.edit_message_text("❌ File too large to send via Telegram (limit: 50MB)")
        return
    
    # Send file
    try:
        if audio_only:
            with open(file_path, 'rb') as audio:
                await query.message.reply_audio(audio)
        else:
            with open(file_path, 'rb') as video:
                await query.message.reply_video(video)
        
        yt_dl.clean_up(file_path)
        await query.delete_message()
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text("❌ Failed to send file")

async def format_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle song selection for Saavn"""
    query = update.callback_query
    await query.answer()
    
    url = query.data.replace("format_saavn_", "")
    
    await query.edit_message_text("⬇️ Downloading song...")
    
    song_data = saavn_dl.get_song_details(url)
    if not song_data:
        await query.edit_message_text("❌ Failed to get song details")
        return
    
    file_path = saavn_dl.download_song(song_data)
    if not file_path:
        await query.edit_message_text("❌ Download failed")
        return
    
    try:
        with open(file_path, 'rb') as audio:
            await query.message.reply_audio(
                audio,
                title=song_data['title'],
                performer=song_data['artist'],
                duration=song_data['duration']
            )
        
        saavn_dl.clean_up(file_path)
        await query.delete_message()
    except Exception as e:
        logger.error(f"Send error: {e}")
        await query.edit_message_text("❌ Failed to send audio")
