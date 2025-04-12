"""
Database setup for Song Recommendation System.
This script defines the database models and creates the schema.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, 
    Text, DateTime, ForeignKey, Date, Table, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
import os
import re
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.utils.config_manager import get_db_session
from src.database.youtube import get_popular_music_videos
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Get database URL from environment variable or use a default SQLite database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///senseyourtune.db")

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create declarative base
Base = declarative_base()

# Define models
class Artist(Base):
    """Artist model representing music artists."""
    __tablename__ = 'artists'
    
    artist_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    popularity = Column(Integer)
    genre = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    songs = relationship("Song", back_populates="artist")
    
    def __repr__(self):
        return f"<Artist(artist_id={self.artist_id}, name='{self.name}')>"


class Song(Base):
    """Song model representing individual songs."""
    __tablename__ = 'songs'
    
    song_id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    artist_id = Column(Integer, ForeignKey('artists.artist_id'), nullable=False)
    youtube_id = Column(String(20), unique=True)
    release_date = Column(Date)
    # duration = Column(Integer)  # Duration in seconds
    popularity = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    artist = relationship("Artist", back_populates="songs")
    lyrics = relationship("Lyrics", back_populates="song", uselist=False)
    sentiment_analysis = relationship("SentimentAnalysis", back_populates="song", uselist=False)
    # user_history = relationship("UserHistory", back_populates="song")
    # user_preferences = relationship("UserPreference", back_populates="song")
    # tags = relationship("SongTag", back_populates="song")
    
    def __repr__(self):
        return f"<Song(song_id={self.song_id}, title='{self.title}')>"


class Lyrics(Base):
    """Lyrics model storing the text of song lyrics."""
    __tablename__ = 'lyrics'
    
    lyrics_id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False)
    lyrics_text = Column(Text, nullable=False)
    source = Column(String(50))  # Where the lyrics were obtained from
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    song = relationship("Song", back_populates="lyrics")
    
    def __repr__(self):
        return f"<Lyrics(lyrics_id={self.lyrics_id}, song_id={self.song_id})>"


class SentimentAnalysis(Base):
    """SentimentAnalysis model storing NLP analysis results of lyrics."""
    __tablename__ = 'sentiment_analysis'
    
    analysis_id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False)
    positivity = Column(Float)  # Score from 0-1
    negativity = Column(Float)  # Score from 0-1
    joy = Column(Float)
    sadness = Column(Float)
    anger = Column(Float)
    fear = Column(Float)
    surprise = Column(Float)
    dominant_mood = Column(String(20))
    word_count = Column(Integer)
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    song = relationship("Song", back_populates="sentiment_analysis")
    
    def __repr__(self):
        return f"<SentimentAnalysis(analysis_id={self.analysis_id}, song_id={self.song_id})>"


# class User(Base):
#     """User model for user authentication and management."""
#     __tablename__ = 'users'
    
#     user_id = Column(Integer, primary_key=True)
#     username = Column(String(50), unique=True)
#     email = Column(String(100), unique=True)
#     password_hash = Column(String(255))
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     last_login = Column(DateTime)
    
#     # Relationships
#     history = relationship("UserHistory", back_populates="user")
#     preferences = relationship("UserPreference", back_populates="user")
    
#     def __repr__(self):
#         return f"<User(user_id={self.user_id}, username='{self.username}')>"


# class UserHistory(Base):
#     """UserHistory model tracking user listening history."""
#     __tablename__ = 'user_history'
    
#     history_id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
#     song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False)
#     play_count = Column(Integer, default=1)
#     last_played = Column(DateTime, default=datetime.datetime.utcnow)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
#     # Relationships
#     user = relationship("User", back_populates="history")
#     song = relationship("Song", back_populates="user_history")
    
#     def __repr__(self):
#         return f"<UserHistory(history_id={self.history_id}, user_id={self.user_id}, song_id={self.song_id})>"


# class UserPreference(Base):
#     """UserPreference model storing explicit user ratings."""
#     __tablename__ = 'user_preferences'
    
#     preference_id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
#     song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False)
#     rating = Column(Integer)  # 1-5 stars
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
#     # Relationships
#     user = relationship("User", back_populates="preferences")
#     song = relationship("Song", back_populates="user_preferences")
    
#     def __repr__(self):
#         return f"<UserPreference(preference_id={self.preference_id}, user_id={self.user_id}, rating={self.rating})>"


# class SongTag(Base):
#     """SongTag model for categorizing songs by mood, theme, etc."""
#     __tablename__ = 'song_tags'
    
#     tag_id = Column(Integer, primary_key=True)
#     song_id = Column(Integer, ForeignKey('songs.song_id'), nullable=False)
#     tag_name = Column(String(50), nullable=False)
#     confidence = Column(Float)  # 0-1 confidence score
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
#     # Relationships
#     song = relationship("Song", back_populates="tags")
    
#     def __repr__(self):
#         return f"<SongTag(tag_id={self.tag_id}, song_id={self.song_id}, tag_name='{self.tag_name}')>"

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
        print(f"Error parsing date {date_str}: {e}")
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
    print(f"Fetching top {max_songs} Chinese songs from YouTube for region {region_code}...")
    
    # Get popular music videos from YouTube
    try:
        popular_videos = get_popular_music_videos(max_results=max_songs, region_code=region_code, language="zh_TW")
    except Exception as e:
        print(f"Error fetching popular videos: {e}")
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
                print(f"Song already exists in database: {song_title} by {artist_name}")
                continue
            
            # Check if artist exists, create if not
            artist = session.query(Artist).filter(Artist.name == artist_name).first()
            if not artist:
                print(f"Creating new artist: {artist_name}")
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
            print(f"Adding song: {song_title} by {artist_name}")
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
                print(f"Adding lyrics for {song_title}")
                lyrics = Lyrics(
                    song_id=song.song_id,
                    lyrics_text=lyrics_text,
                    source=lyrics_source
                )
                session.add(lyrics)
            
            songs_added += 1
        
        # Commit changes
        session.commit()
        print(f"Successfully added {songs_added} songs to the database.")
        return songs_added
    
    except Exception as e:
        print(f"Error populating database: {e}")
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
        print(f"Error fetching songs: {e}")
        return []
    
    finally:
        session.close()
        
def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(engine)
    print("Database tables created successfully!")


def drop_tables():
    """Drop all tables from the database."""
    Base.metadata.drop_all(engine)
    print("Database tables dropped successfully!")


def init_db():
    """Initialize database with any initial data if needed."""
    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add any initial data here
    # Example: session.add(User(username="admin", email="admin@example.com"))
    
    # Commit and close
    session.commit()
    session.close()
    print("Database initialized successfully!")


if __name__ == "__main__":
    # Ask user if they want to reset the database
    reset_db = input("Do you want to reset the database? (y/n): ").lower().strip() == 'y'
    
    if reset_db:
        drop_tables()
    
    create_tables()
    init_db()
    
    # Ask if user wants to populate the database with songs
    populate_db = input("Do you want to populate the database with top songs from YouTube? (y/n): ").lower().strip() == 'y'
    
    if populate_db:
        max_songs = input("How many songs do you want to fetch? (default: 50): ")
        try:
            max_songs = int(max_songs)
        except (ValueError, TypeError):
            max_songs = 50
        
        region_code = input("Enter region code (default: SG): ")
        if not region_code:
            region_code = "SG"
        
        # Call the populate function
        print(f"Populating database with {max_songs} songs...")
        songs_added = populate_top_songs(max_songs=max_songs, region_code=region_code)
        print(f"Added {songs_added} songs to the database.")
    
    print("Database setup complete!")