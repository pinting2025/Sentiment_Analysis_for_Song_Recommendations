import sys
import os
from typing import Optional

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.service.recommendation_service import RecommendationService

def print_recommendations(recommendations: list):
    """Print recommendations in a formatted way."""
    if not recommendations:
        print("No recommendations found.")
        return
    
    print("\nRecommended Songs:")
    print("-" * 100)
    for i, song in enumerate(recommendations, 1):
        print(f"\n{i}. {song['title']} - {song['artist']}")
        print(f"   Genre: {song['artist_genre']}")
        print(f"   Artist Popularity: {song['artist_popularity']}")
        print(f"   Song Popularity: {song['song_popularity']}")
        print(f"   Release Date: {song['release_date']}")
        print(f"   Similarity Score: {song['similarity_score']:.4f}")
        print(f"   Popularity Score: {song['popularity_score']:.4f}")
        print(f"   Weighted Score: {song['weighted_score']:.4f}")
    print("-" * 100)

def main():
    """Main function to get enhanced song recommendations."""
    try:
        # Initialize recommendation service
        recommendation_service = RecommendationService()
        
        # Get song ID from user
        while True:
            try:
                song_id = int(input("Enter the song ID you're interested in: "))
                break
            except ValueError:
                print("Please enter a valid number for the song ID.")
        
        # Get number of recommendations
        while True:
            try:
                top_k = int(input("How many recommendations would you like? (default: 5): ") or "5")
                if top_k > 0:
                    break
                print("Please enter a positive number.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Get optional filters
        artist_genre = input("Filter by artist genre (optional, press Enter to skip): ").strip() or None
        min_artist_pop = None
        min_song_pop = None
        
        try:
            min_artist_pop_input = input("Minimum artist popularity (optional, press Enter to skip): ").strip()
            if min_artist_pop_input:
                min_artist_pop = int(min_artist_pop_input)
            
            min_song_pop_input = input("Minimum song popularity (optional, press Enter to skip): ").strip()
            if min_song_pop_input:
                min_song_pop = int(min_song_pop_input)
        except ValueError:
            print("Invalid popularity value. Skipping popularity filters.")
        
        # Get weights for similarity and popularity
        while True:
            try:
                similarity_weight = float(input("Weight for semantic similarity (0-1, default: 0.7): ") or "0.7")
                if 0 <= similarity_weight <= 1:
                    break
                print("Please enter a number between 0 and 1.")
            except ValueError:
                print("Please enter a valid number.")
        
        popularity_weight = 1 - similarity_weight
        
        # Get recommendations
        print("\nGetting recommendations...")
        recommendations = recommendation_service.get_recommendations(
            target_song_id=song_id,
            top_k=top_k,
            artist_genre=artist_genre,
            min_artist_popularity=min_artist_pop,
            min_song_popularity=min_song_pop,
            similarity_weight=similarity_weight,
            popularity_weight=popularity_weight
        )
        
        # Print recommendations
        print_recommendations(recommendations)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main() 