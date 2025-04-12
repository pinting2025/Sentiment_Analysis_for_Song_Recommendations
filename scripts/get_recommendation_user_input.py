import sys
import os
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple
import numpy as np
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.database.chroma_db import ChromaDBManager
from src.utils.config_manager import get_db_session
from scripts.init_db import Song
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Genius API token
GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
if not GENIUS_TOKEN:
    print("Error: Genius API token not found in environment variables.")
    print("Please set GENIUS_TOKEN in your .env file.")
    sys.exit(1)

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
    """Fetch lyrics for a song using the Genius API."""
    try:
        # Search for the song
        search_url = "https://api.genius.com/search"
        headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
        
        if artist:
            query = f"{title} {artist}"
        else:
            query = title
            
        params = {"q": query}
        
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Genius API search failed: {response.status_code}")
            return None
            
        search_results = response.json()["response"]["hits"]
        if not search_results:
            print("No results found in Genius API")
            return None
            
        # Get the first result's URL
        song_url = search_results[0]["result"]["url"]
        
        # Scrape the lyrics from the song page
        page = requests.get(song_url)
        if page.status_code != 200:
            print(f"Failed to fetch song page: {page.status_code}")
            return None
            
        soup = BeautifulSoup(page.text, "html.parser")
        
        # Find the lyrics container
        lyrics_div = soup.find("div", {"data-lyrics-container": "true"})
        if not lyrics_div:
            print("Could not find lyrics container")
            return None
            
        # Extract and clean the lyrics
        lyrics = lyrics_div.get_text("\n")
        lyrics = re.sub(r'\[.*?\]', '', lyrics)  # Remove [Verse 1] etc.
        lyrics = re.sub(r'\n\s*\n', '\n', lyrics)  # Remove extra newlines
        lyrics = lyrics.strip()
        
        return lyrics
        
    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return None

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
        
        # Fetch lyrics
        print(f"\nFetching lyrics...")
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
        
        # Get the next available song ID
        song_id = str(get_next_song_id())
        
        # Add song to ChromaDB
        success = chroma_manager.add_song_with_lyrics(
            song_id=song_id,
            title=title,
            artist=artist or "Unknown",
            lyrics=lyrics,
            artist_genre=artist_genre,
            artist_popularity=artist_popularity,
            song_popularity=song_popularity,
            release_date=release_date if release_date else None
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