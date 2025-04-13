import os
import requests
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class KKBOXAPI:
    def __init__(self):
        self.client_id = os.getenv("KKBOX_CLIENT_ID")
        self.client_secret = os.getenv("KKBOX_CLIENT_SECRET")
        self.access_token = None
        self.base_url = "https://api.kkbox.com/v1.1"
        self.web_base_url = "https://www.kkbox.com/tw/tc/song"
        
        if not self.client_id or not self.client_secret:
            raise ValueError("KKBOX_CLIENT_ID and KKBOX_CLIENT_SECRET must be set in .env file")
        
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with KKBOX API and get access token"""
        auth_url = "https://account.kkbox.com/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "account.kkbox.com"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("Successfully authenticated with KKBOX API")
        except Exception as e:
            logger.error(f"Failed to authenticate with KKBOX API: {e}")
            raise
    
    def search_song(self, title: str, artist: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for a song on KKBOX
        
        Args:
            title (str): Song title
            artist (str, optional): Artist name
            
        Returns:
            Dict containing song information including lyrics if available
        """
        if not self.access_token:
            self._authenticate()
            
        search_url = f"{self.base_url}/search"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Host": "api.kkbox.com"
        }
        
        query = title
        if artist:
            query = f"{title} {artist}"
            
        params = {
            "q": query,
            "type": "track",
            "territory": "TW",
            "limit": 1
        }
        
        try:
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("tracks", {}).get("data"):
                logger.warning(f"No results found for query: {query}")
                return {}
                
            track = data["tracks"]["data"][0]
            track_id = track["id"]
            
            # Get lyrics using web scraping
            lyrics = self._get_lyrics_from_web(track_id)
            track["lyrics"] = lyrics
            
            return track
            
        except Exception as e:
            logger.error(f"Error searching for song: {e}")
            return {}
    
    def _get_lyrics_from_web(self, track_id: str) -> str:
        """
        Get lyrics by scraping KKBOX's website
        
        Args:
            track_id (str): KKBOX track ID
            
        Returns:
            str: Lyrics text or empty string if not available
        """
        try:
            # Construct the song URL
            song_url = f"{self.web_base_url}/{track_id}"
            
            # Make request to the song page
            response = requests.get(song_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all script tags with type="application/ld+json"
            scripts = soup.find_all('script', type='application/ld+json')
            
            for script in scripts:
                try:
                    # Parse JSON-LD
                    json_data = json.loads(script.string)
                    
                    # Check if this is a MusicRecording with lyrics
                    if json_data.get('@type') == 'MusicRecording' and 'recordingOf' in json_data:
                        # Extract lyrics from the nested structure
                        lyrics = json_data['recordingOf'].get('lyrics', {}).get('text', '')
                        if lyrics:
                            # Clean up the lyrics text
                            lyrics = lyrics.replace('\\n', '\n').strip()
                            return lyrics
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Error parsing JSON-LD: {e}")
                    continue
                    
            logger.warning(f"No lyrics found for track {track_id}")
            return ""
            
        except Exception as e:
            logger.error(f"Error scraping lyrics: {e}")
            return "" 