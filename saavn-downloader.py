"""JioSaavn music download functionality"""
import os
import logging
import requests
from typing import Optional, Dict, List, Any
from bot.config import Config

logger = logging.getLogger(__name__)

class SaavnDownloader:
    def __init__(self):
        self.api_base = Config.SAAVN_API_BASE
        self.download_path = Config.DOWNLOAD_PATH
        
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for songs on Saavn"""
        try:
            response = requests.get(
                f"{self.api_base}/api/search/songs",
                params={"query": query, "limit": limit},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            if data.get("data") and data["data"].get("results"):
                for song in data["data"]["results"]:
                    results.append({
                        'id': song.get('id'),
                        'title': song.get('name'),
                        'artist': ", ".join([a['name'] for a in song.get('primaryArtists', [])]),
                        'album': song.get('album', {}).get('name', 'Unknown'),
                        'year': song.get('year'),
                        'duration': song.get('duration'),
                        'image': song.get('image', [{}])[-1].get('url') if song.get('image') else None,
                        'url': song.get('url')
                    })
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_song_details(self, song_url: str) -> Optional[Dict]:
        """Get song details by URL"""
        try:
            # Extract song ID from URL or use as-is
            response = requests.get(
                f"{self.api_base}/api/songs",
                params={"link": song_url},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("data") and len(data["data"]) > 0:
                song = data["data"][0]
                return {
                    'id': song.get('id'),
                    'title': song.get('name'),
                    'artist': ", ".join([a['name'] for a in song.get('primaryArtists', [])]),
                    'album': song.get('album', {}).get('name', 'Unknown'),
                    'duration': song.get('duration'),
                    'image': song.get('image', [{}])[-1].get('url') if song.get('image') else None,
                    'download_url': song.get('downloadUrl', [{}])[-1].get('url') if song.get('downloadUrl') else None,
                    'quality': song.get('downloadUrl', [{}])[-1].get('quality') if song.get('downloadUrl') else 'unknown'
                }
            return None
        except Exception as e:
            logger.error(f"Details error: {e}")
            return None
    
    def download_song(self, song_data: Dict, quality: str = "320") -> Optional[str]:
        """
        Download song from Saavn
        Returns file path or None
        """
        download_url = song_data.get('download_url')
        if not download_url:
            logger.error("No download URL found")
            return None
            
        # Clean filename
        safe_title = "".join([c for c in song_data['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        safe_artist = "".join([c for c in song_data['artist'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{safe_title} - {safe_artist}.mp3"
        filepath = os.path.join(self.download_path, filename)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Stream download with progress
            response = requests.get(download_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check file size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > Config.MAX_FILE_SIZE:
                logger.warning(f"File too large: {content_length}")
                return None
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Add metadata (optional enhancement)
            self._add_metadata(filepath, song_data)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return None
    
    def _add_metadata(self, filepath: str, song_data: Dict):
        """Add ID3 tags to MP3 (requires mutagen)"""
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB
            
            audio = MP3(filepath)
            if audio.tags is None:
                audio.add_tags()
            
            audio.tags['TIT2'] = TIT2(encoding=3, text=song_data['title'])
            audio.tags['TPE1'] = TPE1(encoding=3, text=song_data['artist'])
            audio.tags['TALB'] = TALB(encoding=3, text=song_data['album'])
            audio.save()
        except Exception as e:
            logger.warning(f"Metadata error: {e}")
    
    def get_playlist(self, playlist_url: str) -> List[Dict]:
        """Get all songs from a playlist"""
        try:
            response = requests.get(
                f"{self.api_base}/api/playlists",
                params={"link": playlist_url},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            songs = []
            if data.get("data") and data["data"].get("songs"):
                for song in data["data"]["songs"]:
                    songs.append({
                        'id': song.get('id'),
                        'title': song.get('name'),
                        'artist': ", ".join([a['name'] for a in song.get('primaryArtists', [])]),
                        'album': song.get('album', {}).get('name', 'Unknown'),
                        'url': song.get('url')
                    })
            return songs
        except Exception as e:
            logger.error(f"Playlist error: {e}")
            return []
    
    def clean_up(self, file_path: str):
        """Remove downloaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
