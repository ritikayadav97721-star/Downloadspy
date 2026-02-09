"""Configuration management"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "./downloads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB Telegram limit
    ADMIN_ID = os.getenv("ADMIN_ID")
    
    # YouTube settings
    YT_COOKIES = os.getenv("YT_COOKIES", None)  # Path to cookies file for age-restricted
    
    # Saavn API settings
    SAAVN_API_BASE = "https://saavn.dev"  # Free unofficial API
    
    # Quality presets
    VIDEO_QUALITIES = {
        "best": "Best Quality",
        "1080": "1080p",
        "720": "720p", 
        "480": "480p",
        "audio": "Audio Only (MP3)"
    }
    
    AUDIO_QUALITIES = {
        "320": "320kbps",
        "160": "160kbps",
        "96": "96kbps"
    }
