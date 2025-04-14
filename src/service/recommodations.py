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

from src.database.chroma_db import ChromaManager
from src.utils.config_manager import get_db_session
from scripts.init_db import Song, Lyrics, Artist
from src.database.kkbox import KKBOXAPI

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RecommendationService:
    def __init__(self):
        self.chroma_manager = ChromaManager()

    def get_next_song_id(self) -> int:
        session = get_db_session()
        try:
            max_id = session.query(Song.song_id).order_by(Song.song_id.desc()).first()
            return (max_id[0] + 1) if max_id else 1
        finally:
            session.close()

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
            youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
            query = f"{title} {artist}" if artist != "Unknown" else title
            response = youtube.search().list(q=query, part='id,snippet', maxResults=1, type='video').execute()

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

    def get_recommendations_for_song(self, song_id: int, lyrics: Optional[str] = None) -> List[Dict]:
        try:
            from src.database.embeddings import EmbeddingGenerator
            embedding_generator = EmbeddingGenerator()
            if lyrics:
                embedding = embedding_generator.get_embedding(lyrics)
            else:
                song_data = self.chroma_manager.get_song(id=str(song_id))
                if not song_data:
                    print("Song embedding not found.")
                    return
                embedding = song_data['embedding']
        
            results = self.chroma_manager.find_songs_by_similarity(query_embedding=embedding, top_k=20)
            print("\nRecommended Songs:")
            print("-" * 100)
            print(f"{'Title':<30} {'Artist':<25} {'Similarity':<10} {'YouTube Link':<20}")
            print("-" * 100)
            
            count = 0
            for song in results:
                if song['song_id'] == song_id:
                    continue
                if count >= 5:
                    break
                similarity_score = song['similarity_score']
                video_title, video_url = self.search_youtube_video(song['title'], song['artist'])
                print(f"{song['title'][:30]:<30} {song['artist'][:25]:<25} {similarity_score:.3f} {video_url}")
                if video_url:
                    print(f"   YouTube: {video_title}\n{'-' * 100}")
                else:
                    print("   No YouTube video found\n" + "-" * 100)
                count += 1
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")

    def song_exists_in_chroma(self, song_id: str) -> bool:
        return self.chroma_manager.get_song(id=song_id) is not None
