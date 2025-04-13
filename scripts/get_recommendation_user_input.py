import sys
import os
from typing import Optional, Tuple
import numpy as np
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.database.chroma_db import ChromaDBManager
from src.utils.config_manager import get_db_session
from scripts.init_db import Song, Lyrics, Artist
from dotenv import load_dotenv
from src.database.kkbox import KKBOXAPI
from src.utils.settings import DB_PATH

# Load environment variables
load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_next_song_id() -> int:
    """Get the next available song ID from the database."""
    session = get_db_session()
    try:
        # Get the maximum song_id from the database
        max_id = session.query(Song.song_id).order_by(Song.song_id.desc()).first()
        if max_id:
            return max_id[0] + 1
        return 1  # If no songs exist, start with 1
    finally:
        session.close()

def fetch_lyrics(title: str, artist: Optional[str] = None) -> Optional[str]:
    """
    Fetch lyrics for a song using the KKBOX API and update the database
    
    Args:
        title (str): Song title
        artist (Optional[str]): Artist name
        
    Returns:
        Optional[str]: Lyrics text if found, None otherwise
    """
    session = get_db_session()
    try:
        # First search for YouTube video to get the video ID
        video_title, video_url = search_youtube_video(title, artist or "Unknown")
        if not video_url:
            logger.error("No YouTube video found for this song")
            return None
            
        # Extract video ID from URL
        video_id = video_url.split('v=')[1] if 'v=' in video_url else ''
        if not video_id:
            logger.error("Could not extract YouTube video ID")
            return None
            
        # Initialize KKBOX API
        kkbox = KKBOXAPI()
        
        # Search for the song
        kkbox_data = kkbox.search_song(title, artist)
        
        if not kkbox_data:
            logger.error("No results found in KKBOX")
            return None
            
        # Get song details from KKBOX response
        song_title = kkbox_data.get('name', title)
        
        # Extract artist name from KKBOX response - handle nested structure
        if isinstance(kkbox_data.get('artist'), dict):
            kkbox_artist_name = kkbox_data['artist'].get('name', artist or 'Unknown Artist')
        else:
            kkbox_artist_name = artist or 'Unknown Artist'
            
        lyrics_text = kkbox_data.get('lyrics', '')
        
        if not lyrics_text:
            logger.error("No lyrics found for this song")
            return None
            
        # Check if artist exists in database
        artist_obj = session.query(Artist).filter_by(name=kkbox_artist_name).first()
        if not artist_obj:
            # If artist not found, check if there's an artist with the original name
            if artist == "Unknown Artist" and kkbox_artist_name != "Unknown Artist":
                artist_obj = session.query(Artist).filter_by(name=artist).first()
                if artist_obj:
                    # Update artist name to match KKBOX
                    artist_obj.name = kkbox_artist_name
                    logger.info(f"Updated artist name from '{artist}' to '{kkbox_artist_name}'")
            else:
                # Create new artist
                artist_obj = Artist(name=kkbox_artist_name)
                session.add(artist_obj)
            session.flush()  # Get the artist_id
        
        # Check if song exists in database
        song = session.query(Song).filter_by(
            title=song_title,
            artist_id=artist_obj.artist_id
        ).first()
        
        if not song:
            # Create new song if it doesn't exist
            song = Song(
                title=song_title,
                artist_id=artist_obj.artist_id,
                youtube_id=video_id,  # Use the YouTube video ID we found
                release_date=None  # Will be updated later with YouTube search
            )
            session.add(song)
            session.flush()  # Get the song_id
        
        # Check if lyrics already exist
        existing_lyrics = session.query(Lyrics).filter_by(song_id=song.song_id).first()
        if existing_lyrics:
            # Update existing lyrics
            existing_lyrics.lyrics_text = lyrics_text
            existing_lyrics.source = 'KKBOX'
        else:
            # Create new lyrics entry
            lyrics = Lyrics(
                song_id=song.song_id,
                lyrics_text=lyrics_text,
                source='KKBOX'
            )
            session.add(lyrics)
        
        session.commit()
        logger.info(f"Successfully updated lyrics for song: {song_title} by {kkbox_artist_name}")
        return lyrics_text
        
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
        session.rollback()
        return None
    finally:
        session.close()

def search_youtube_video(title: str, artist: str) -> Tuple[str, str]:
    """Search for a song on YouTube and return the first result's title and URL."""
    try:
        youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        
        # Create search query
        search_query = f"{title} {artist}" if artist != "Unknown" else title
        
        # Search for the video
        search_response = youtube.search().list(
            q=search_query,
            part='id,snippet',
            maxResults=1,
            type='video'
        ).execute()
        
        if not search_response.get('items'):
            return "No video found", ""
            
        video = search_response['items'][0]
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        return video_title, video_url
        
    except HttpError as e:
        print(f"An error occurred while searching YouTube: {e}")
        return "Error searching YouTube", ""
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error", ""

def main():
    """Main function to add a new song to ChromaDB."""
    try:
        # Initialize ChromaDB manager
        chroma_manager = ChromaDBManager()
        
        # Get song title and optional artist from user
        while True:
            title = input("Enter the song title: ").strip()
            if title:
                break
            print("Please enter a song title.")
        
        artist = input("Enter the artist name (optional, press Enter to skip): ").strip() or None
        
        # Fetch lyrics and get the song ID from SenseYourTune database
        print(f"\nFetching lyrics...")
        session = get_db_session()
        try:
            # First check if song exists in SenseYourTune
            kkbox_artist_name = artist or "Unknown Artist"
            existing_song = session.query(Song).join(Artist).filter(
                Song.title == title,
                Artist.name == kkbox_artist_name
            ).first()
            
            if existing_song:
                print(f"\nFound existing song in SenseYourTune with ID: {existing_song.song_id}")
                # Check if it exists in ChromaDB
                if chroma_manager.get_song(str(existing_song.song_id)):
                    print("Song already exists in ChromaDB. Getting recommendations...")
                    song_id = str(existing_song.song_id)
                else:
                    print("Song exists in SenseYourTune but not in ChromaDB. Adding to ChromaDB...")
                    song_id = str(existing_song.song_id)
            else:
                print("Song not found in SenseYourTune. Adding new song...")
                song_id = str(get_next_song_id())
        finally:
            session.close()
        
        # Fetch lyrics (this will add/update the song in SenseYourTune)
        lyrics = fetch_lyrics(title, artist)
        
        if not lyrics:
            print("Could not fetch lyrics for this song. Please try another song.")
            return
        
        print("\nLyrics fetched successfully!")
        print("\nLyrics preview:")
        print("-" * 50)
        print(lyrics[:200] + "..." if len(lyrics) > 200 else lyrics)
        print("-" * 50)
        
        # Ask user if they want to proceed with these lyrics
        while True:
            choice = input("\nDo you want to proceed with these lyrics? (yes/no): ").lower()
            if choice in ['yes', 'no']:
                break
            print("Please enter 'yes' or 'no'.")
        
        if choice == 'no':
            print("Operation cancelled by user.")
            return
        
        # Get additional metadata
        artist_genre = input("Enter artist genre (optional, press Enter to skip): ").strip() or "Unknown"
        artist_popularity = input("Enter artist popularity (0-100, optional, press Enter to skip): ").strip()
        song_popularity = input("Enter song popularity (0-100, optional, press Enter to skip): ").strip()
        release_date = input("Enter release date (YYYY-MM-DD, optional, press Enter to skip): ").strip()
        
        # Convert popularity scores to integers
        try:
            artist_popularity = int(artist_popularity) if artist_popularity else 0
            song_popularity = int(song_popularity) if song_popularity else 0
        except ValueError:
            print("Invalid popularity score. Using default value of 0.")
            artist_popularity = 0
            song_popularity = 0
        
        # Add song to ChromaDB
        success = chroma_manager.add_song_with_lyrics(
            song_id=song_id,
            title=title,
            artist=artist or "Unknown",
            lyrics=lyrics
        )
        
        if success:
            print(f"\nSuccessfully added song to ChromaDB with ID: {song_id}")
            
            # Get recommendations for the newly added song
            print("\nGetting recommendations for the newly added song...")
            
            try:
                # Generate embedding for lyrics
                from src.database.embeddings import EmbeddingGenerator
                embedding_generator = EmbeddingGenerator()
                embedding = embedding_generator.get_embedding(lyrics)
                
                if embedding is None:
                    print("Failed to generate embedding for recommendations")
                    return
                
                # Normalize embedding
                embedding = embedding / np.linalg.norm(embedding)
                
                # Find similar songs
                results = chroma_manager.find_similar_songs(
                    query_embedding=embedding.tolist(),
                    n_results=6  # Get 5 recommendations + the target song
                )
                
                if results and results.get('ids') and results.get('metadatas'):
                    # Process and display results
                    print("\nRecommended Songs:")
                    print("-" * 100)
                    print(f"{'Title':<30} {'Artist':<25} {'Genre':<15} {'Similarity':<10} {'YouTube Link':<20}")
                    print("-" * 100)
                    
                    for i, (result_id, distance, metadata) in enumerate(zip(
                        results['ids'][0],
                        results['distances'][0],
                        results['metadatas'][0]
                    )):
                        # Skip the target song itself
                        if result_id == song_id:
                            continue
                            
                        similarity_score = 1 - distance
                        # Search for YouTube video
                        video_title, video_url = search_youtube_video(
                            metadata['title'],
                            metadata['artist']
                        )
                        
                        print(f"{metadata['title'][:30]:<30} {metadata['artist'][:25]:<25} "
                              f"{metadata['artist_genre'][:15]:<15} {similarity_score:.3f} {video_url}")
                        
                        if video_url:
                            print(f"   YouTube: {video_title}")
                            print("-" * 100)
                        else:
                            print("   No YouTube video found")
                            print("-" * 100)
                else:
                    print("No similar songs found in the database.")
                    
            except Exception as e:
                print(f"Error getting recommendations: {e}")
        else:
            print("\nFailed to add song to ChromaDB")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main() 