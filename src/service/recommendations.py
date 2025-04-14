import os
import logging
import sys
from typing import Optional, Tuple, List, Dict
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.database.chroma.chroma_db import ChromaManager
from src.utils.config_manager import get_db_session
from src.database.init_db import Song, Lyrics, Artist
from src.database.kkbox import KKBOXAPI

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RecommendationService:
    def __init__(self):
        self.chroma_manager = ChromaManager()
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))

    def get_next_song_id(self) -> int:
        session = get_db_session()
        try:
            max_id = session.query(Song.song_id).order_by(Song.song_id.desc()).first()
            return (max_id[0] + 1) if max_id else 1
        finally:
            session.close()

    def get_song_preview_url(self, title: str, artist: str) -> Optional[str]:
        """
        Get YouTube video preview URL for a song from the database.
        Returns the video URL if found, None otherwise.
        """
        try:
            session = get_db_session()
            try:
                song = session.query(Song).join(Artist).filter(
                    Song.title == title,
                    Artist.name == artist
                ).first()
                
                if song and song.youtube_id:
                    return f"https://www.youtube.com/embed/{song.youtube_id}?autoplay=0&controls=1&showinfo=0&rel=0"
                return None
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error getting preview URL for {title} by {artist}: {e}")
            return None

    def fetch_lyrics(self, title: str, artist: Optional[str] = None) -> Optional[str]:
        session = get_db_session()
        try:
            video_title, video_url = self.search_youtube_video(title, artist or "Unknown Artist")
            if not video_url:
                logger.error("No YouTube video found.")
                return None

            video_id = video_url.split('v=')[1] if 'v=' in video_url else ''
            if not video_id:
                logger.error("Could not extract YouTube video ID")
                return None

            kkbox = KKBOXAPI()
            kkbox_data = kkbox.search_song(title, artist)
            if not kkbox_data:
                logger.error("No results found in KKBOX")
                return None

            song_title = kkbox_data.get('name', title)
            artist_name = kkbox_data.get('artist', {}).get('name', artist or 'Unknown Artist')
            lyrics_text = kkbox_data.get('lyrics', '')
            if not lyrics_text:
                logger.error("No lyrics found")
                return None

            artist_obj = session.query(Artist).filter_by(name=artist_name).first()
            if not artist_obj:
                artist_obj = Artist(name=artist_name)
                session.add(artist_obj)
                session.flush()

            song = session.query(Song).filter_by(title=song_title, artist_id=artist_obj.artist_id).first()
            if not song:
                song = Song(title=song_title, artist_id=artist_obj.artist_id, youtube_id=video_id)
                session.add(song)
                session.flush()

            existing_lyrics = session.query(Lyrics).filter_by(song_id=song.song_id).first()
            if existing_lyrics:
                existing_lyrics.lyrics_text = lyrics_text
                existing_lyrics.source = 'KKBOX'
            else:
                lyrics = Lyrics(song_id=song.song_id, lyrics_text=lyrics_text, source='KKBOX')
                session.add(lyrics)

            session.commit()
            logger.info(f"Lyrics updated for: {song_title} by {artist_name}")
            return lyrics_text

        except Exception as e:
            logger.error(f"Error fetching lyrics: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def search_youtube_video(self, title: str, artist: str) -> Tuple[str, str]:
        try:
            query = f"{title} {artist}" if artist != "Unknown" else title
            response = self.youtube.search().list(q=query, part='id,snippet', maxResults=1, type='video').execute()

            if not response.get('items'):
                return "No video found", ""
            video = response['items'][0]
            return video['snippet']['title'], f"https://www.youtube.com/watch?v={video['id']['videoId']}"

        except (HttpError, Exception) as e:
            logger.error(f"YouTube search error: {e}")
            return "Error", ""

    def add_song_to_chroma(self, song_id: int, title: str, artist: str, lyrics: str) -> bool:
        return self.chroma_manager.add_song_with_lyrics(
            song_id=str(song_id),
            title=title,
            artist=artist,
            lyrics=lyrics
        )

    def get_existing_song_id(self, title: str) -> Optional[int]:
        session = get_db_session()
        try:
            song = session.query(Song).join(Artist).filter(Song.title == title).first()
            return song.song_id if song else None
        finally:
            session.close()

    def get_recommendations_for_song(self, song_id: int, song_title: str, lyrics: Optional[str] = None) -> List[Dict]:
        try:
            from src.database.chroma.embeddings import EmbeddingGenerator
            embedding_generator = EmbeddingGenerator()
            if lyrics:
                embedding = embedding_generator.get_embedding(lyrics)
            else:
                song_data = self.chroma_manager.get_song(id=str(song_id))
                if not song_data:
                    print("Song embedding not found.")
                    return []
                embedding = song_data['embedding']
        
            results = self.chroma_manager.find_songs_by_similarity(query_embedding=embedding, top_k=20)
            
            # Format recommendations for the frontend
            formatted_recommendations = []
            count = 0
            for song in results:
                if song['song_id'] == song_id:
                    continue
                
                title_length = len(song_title)
                if song['title'][:title_length] == song_title:
                    continue
                
                if count >= 5:
                    break
                
                # Get preview URL from database
                preview_url = self.get_song_preview_url(song['title'], song['artist'])
                
                # Create recommendation object
                recommendation = {
                    'title': song['title'],
                    'artist': song['artist'],
                    'weighted_score': song['similarity_score'],
                    'preview_url': preview_url if preview_url else None
                }
                formatted_recommendations.append(recommendation)
                count += 1
            
            return formatted_recommendations
        
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
        
    def song_exists_in_chroma(self, song_id: str) -> bool:
        return self.chroma_manager.get_song(id=song_id) is not None
