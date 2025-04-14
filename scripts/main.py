import sys
import os
from dotenv import load_dotenv

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.service.recommodations import RecommendationService
from src.database.chroma_db import ChromaManager
from src.utils.config_manager import get_db_session
from scripts.init_db import Song, Artist
from dotenv import load_dotenv
load_dotenv()


def display_recommendations(recommendations):
    if not recommendations:
        print("No recommendations found.")
        return

    print("\nRecommended Songs:\n" + "-" * 100)
    print(f"{'Title':<30} {'Artist':<25} {'Score':<10}")
    print("-" * 100)

    for rec in recommendations:
        print(f"{rec['title'][:30]:<30} {rec['artist'][:25]:<25} {rec['weighted_score']:.3f}")
    print("-" * 100)

def main():
    try:
        title = input("Enter the song title: ").strip()
        if not title:
            print("Please enter a song title.")
            return
        
        artist = input("Enter the artist name (optional, press Enter to skip): ").strip() or None

        print(f"\nFetching lyrics...")
        session = get_db_session()
        service = RecommendationService()
        try:
            existing_song = session.query(Song).join(Artist).filter(Song.title == title).first()
            if existing_song:
                print(f"\nFound existing song in SenseYourTune with ID: {existing_song.song_id}")
                song_id = str(existing_song.song_id)
                if service.song_exists_in_chroma(song_id):
                    print("Song already exists in ChromaDB. Getting recommendations...")
                    service.get_recommendations_for_song(song_id)
                    return
                else:
                    print("Song exists in SenseYourTune but not in ChromaDB. Adding to ChromaDB...")
            else:
                print("Song not found in SenseYourTune. Adding new song...")
                song_id = str(service.get_next_song_id())
        finally:
            session.close()

        lyrics = service.fetch_lyrics(title, artist)
        if not lyrics:
            print("Could not fetch lyrics for this song. Please try another song.")
            return

        print("\nLyrics fetched successfully!")
        print("\nLyrics preview:")
        print("-" * 50)
        print(lyrics[:200] + "..." if len(lyrics) > 200 else lyrics)
        print("-" * 50)

        success = service.add_song_to_chroma(song_id=song_id, title=title, artist=artist or "Unknown Artist", lyrics=lyrics)

        if success:
            print(f"\nSuccessfully added song to ChromaDB with ID: {song_id}")
            print("\nGetting recommendations for the newly added song...")
            service.get_recommendations_for_song(song_id, lyrics)
        else:
            print("\nFailed to add song to ChromaDB")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main() 