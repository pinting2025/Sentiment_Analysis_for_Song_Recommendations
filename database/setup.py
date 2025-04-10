"""
Script to populate the database with top songs from YouTube.
"""

import logging
import datetime
from config import get_db_session
from schema import Artist, Song, Lyrics
from youtube_api import get_popular_music_videos
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_artist_from_title(title, channel_title):
    """
    Extract artist name from video title or channel title.
    
    Args:
        title (str): Video title
        channel_title (str): Channel title
    
    Returns:
        str: Best guess at artist name
    """
    # Common patterns for artist - title formats
    patterns = [
        r'^(.+?)\s*[-–]\s*(.+)$',  # Artist - Title
        r'^(.+?)\s*["|\']\s*(.+)\s*["|\']$',  # Artist "Title"
        r'^(.+?)\s*:\s*(.+)$',  # Artist: Title
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            # The first group should be the artist name in most cases
            potential_artist = match.group(1).strip()
            # If it looks reasonable (not too long), return it
            if 2 <= len(potential_artist) <= 50:
                return potential_artist
    
    # If no pattern matched, use the channel title as fallback
    # Remove common suffixes like "VEVO", "Official", etc.
    channel_clean = re.sub(r'\s*(VEVO|Official|Music|Records|Channel)$', '', channel_title, flags=re.IGNORECASE)
    return channel_clean.strip()

def extract_title_from_video(title):
    """
    Extract song title from video title.
    
    Args:
        title (str): Video title
    
    Returns:
        str: Best guess at song title
    """
    # Common patterns for artist - title formats
    patterns = [
        r'^.+?\s*[-–]\s*(.+)$',  # Artist - Title
        r'^.+?\s*["|\']\s*(.+)\s*["|\']$',  # Artist "Title"
        r'^.+?\s*:\s*(.+)$',  # Artist: Title
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            # The second group should be the song title
            return match.group(1).strip()
    
    # If no pattern matched, remove common suffixes
    clean_title = re.sub(r'\s*(Official Video|Official Music Video|Official Audio|Audio|Video|MV|M/V|Lyrics|Lyric Video)$', '', title, flags=re.IGNORECASE)
    return clean_title.strip()

def convert_youtube_date(date_str):
    """
    Convert YouTube date string to datetime.date object.
    
    Args:
        date_str (str): Date string in YouTube format (e.g., '2021-09-30T15:30:15Z')
    
    Returns:
        datetime.date: Date object
    """
    try:
        # YouTube dates are in ISO format
        date_obj = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.date()
    except Exception as e:
        logger.warning(f"Error parsing date {date_str}: {e}")
        return None

def populate_top_songs(max_songs=10, region_code="SG"):
    """
    Fetch top songs from YouTube and populate the database.
    
    Args:
        max_songs (int, optional): Maximum number of songs to fetch. Defaults to 10.
        region_code (str, optional): Region code for localized results. Defaults to "SG".
    
    Returns:
        int: Number of songs added to database
    """
    logger.info(f"Fetching top {max_songs} Chinese songs from YouTube for region {region_code}...")
    
    # Get popular music videos from YouTube
    try:
        popular_videos = get_popular_music_videos(max_results=max_songs, region_code=region_code, language="zh_TW")
    except Exception as e:
        logger.error(f"Error fetching popular videos: {e}")
        return 0
    
    # Get database session
    session = get_db_session()
    
    try:
        songs_added = 0
        
        for video in popular_videos:
            # Extract information
            video_id = video['video_id']
            song_title = video['title']
            artist_name = video['artist_name']
            # artist_popularity = video['artist_popularity']
            # artist_genre = video['artist_genre']
            lyrics_text = video['lyrics_text']
            lyrics_source = video['lyrics_source']
            
            # Check if song already exists
            existing_song = session.query(Song).filter(Song.youtube_id == video_id).first()
            if existing_song:
                logger.info(f"Song already exists in database: {song_title} by {artist_name}")
                continue
            
            # Check if artist exists, create if not
            artist = session.query(Artist).filter(Artist.name == artist_name).first()
            if not artist:
                logger.info(f"Creating new artist: {artist_name}")
                artist = Artist(
                    name=artist_name,
                    # popularity=artist_popularity,
                    # genre=artist_genre
                )
                session.add(artist)
                session.flush()
            
            # Parse published date
            release_date = convert_youtube_date(video['published_at'])
            
            # Calculate popularity based on view count and like count
            view_count = video['view_count']
            like_count = video['like_count']
            
            # Calculate popularity score (0-100)
            popularity = min(100, int(
                (view_count / 1000000) * 0.7 +  # 0.7 points per million views
                (like_count / 10000) * 0.3      # 0.3 points per 10,000 likes
            ))
            
            # Create new song
            logger.info(f"Adding song: {song_title} by {artist_name}")
            song = Song(
                title=song_title,
                artist_id=artist.artist_id,
                youtube_id=video_id,
                release_date=release_date,
                popularity=popularity
            )
            session.add(song)
            session.flush()  # Flush to get song_id
            
            # Add lyrics if available
            if lyrics_text:
                logger.info(f"Adding lyrics for {song_title}")
                lyrics = Lyrics(
                    song_id=song.song_id,
                    lyrics_text=lyrics_text,
                    source=lyrics_source
                )
                session.add(lyrics)
            
            songs_added += 1
        
        # Commit changes
        session.commit()
        logger.info(f"Successfully added {songs_added} songs to the database.")
        return songs_added
    
    except Exception as e:
        logger.error(f"Error populating database: {e}")
        session.rollback()
        return 0
    
    finally:
        session.close()

def get_all_songs():
    """
    Get all songs from the database.
    
    Returns:
        list: List of songs with artist information
    """
    session = get_db_session()
    
    try:
        songs = session.query(Song, Artist).join(Artist).all()
        
        results = []
        for song, artist in songs:
            results.append({
                'song_id': song.song_id,
                'title': song.title,
                'artist_name': artist.name,
                'youtube_id': song.youtube_id,
                'release_date': song.release_date.isoformat() if song.release_date else None,
                'popularity': song.popularity
            })
        
        return results
    
    except Exception as e:
        logger.error(f"Error fetching songs: {e}")
        return []
    
    finally:
        session.close()

if __name__ == "__main__":
    # Populate database with top songs
    num_songs = populate_top_songs(max_songs=500)
    print(f"Added {num_songs} new songs to the database.")