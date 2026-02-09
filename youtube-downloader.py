"""YouTube download functionality using yt-dlp"""
import os
import logging
import yt_dlp
from typing import Optional, Dict, Any
from bot.config import Config

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self):
        self.download_path = Config.DOWNLOAD_PATH
        
    def get_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract video info without downloading"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        if Config.YT_COOKIES and os.path.exists(Config.YT_COOKIES):
            ydl_opts['cookiefile'] = Config.YT_COOKIES
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'thumbnail': info.get('thumbnail'),
                    'formats': self._parse_formats(info.get('formats', [])),
                    'url': url
                }
        except Exception as e:
            logger.error(f"Error extracting info: {e}")
            return None
    
    def _parse_formats(self, formats: list) -> Dict:
        """Parse available formats"""
        parsed = {
            'video': [],
            'audio': []
        }
        
        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                # Progressive video (video+audio)
                parsed['video'].append({
                    'format_id': f['format_id'],
                    'ext': f['ext'],
                    'quality': f.get('quality_label', 'unknown'),
                    'filesize': f.get('filesize', 0)
                })
            elif f.get('acodec') != 'none':
                # Audio only
                parsed['audio'].append({
                    'format_id': f['format_id'],
                    'ext': f['ext'],
                    'abr': f.get('abr', 0),
                    'filesize': f.get('filesize', 0)
                })
                
        return parsed
    
    def download(self, url: str, quality: str = "best", audio_only: bool = False) -> Optional[str]:
        """
        Download video/audio from YouTube
        Returns file path or None if failed
        """
        output_path = os.path.join(self.download_path, '%(title)s.%(ext)s')
        
        if audio_only or quality == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'max_filesize': Config.MAX_FILE_SIZE,
            }
        else:
            format_spec = {
                "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
                "720": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
                "480": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]"
            }.get(quality, "best[ext=mp4]")
            
            ydl_opts = {
                'format': format_spec,
                'outtmpl': output_path,
                'merge_output_format': 'mp4',
                'max_filesize': Config.MAX_FILE_SIZE,
            }
        
        if Config.YT_COOKIES and os.path.exists(Config.YT_COOKIES):
            ydl_opts['cookiefile'] = Config.YT_COOKIES
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Adjust extension for audio files
                if audio_only or quality == "audio":
                    base, _ = os.path.splitext(filename)
                    filename = base + '.mp3'
                    
                return filename if os.path.exists(filename) else None
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    def clean_up(self, file_path: str):
        """Remove downloaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
