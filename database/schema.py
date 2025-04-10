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
from dotenv import load_dotenv

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