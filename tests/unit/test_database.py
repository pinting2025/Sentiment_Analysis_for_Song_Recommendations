import pytest
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.database.init_db import Base, Artist, Song, Lyrics, create_tables, drop_tables, init_db
from src.utils.settings import DB_PATH

@pytest.fixture
def db_engine():
    # Create an in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

def test_artist_model(db_session):
    # Test Artist model creation and relationships
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    
    assert artist.artist_id is not None
    assert artist.name == "Test Artist"
    assert isinstance(artist.created_at, datetime)
    assert isinstance(artist.updated_at, datetime)
    assert len(artist.songs) == 0

def test_song_model(db_session):
    # Test Song model creation and relationships
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    
    song = Song(
        title="Test Song",
        artist_id=artist.artist_id,
        youtube_id="test123",
        popularity=100
    )
    db_session.add(song)
    db_session.commit()
    
    assert song.song_id is not None
    assert song.title == "Test Song"
    assert song.artist_id == artist.artist_id
    assert song.youtube_id == "test123"
    assert song.popularity == 100
    assert isinstance(song.created_at, datetime)
    assert isinstance(song.updated_at, datetime)
    assert song.artist == artist

def test_lyrics_model(db_session):
    # Test Lyrics model creation and relationships
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    
    song = Song(
        title="Test Song",
        artist_id=artist.artist_id
    )
    db_session.add(song)
    db_session.commit()
    
    lyrics = Lyrics(
        song_id=song.song_id,
        lyrics_text="Test lyrics text",
        source="Test Source"
    )
    db_session.add(lyrics)
    db_session.commit()
    
    assert lyrics.lyrics_id is not None
    assert lyrics.song_id == song.song_id
    assert lyrics.lyrics_text == "Test lyrics text"
    assert lyrics.source == "Test Source"
    assert isinstance(lyrics.created_at, datetime)
    assert isinstance(lyrics.updated_at, datetime)
    assert lyrics.song == song

def test_artist_song_relationship(db_session):
    # Test the relationship between Artist and Song
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    
    song1 = Song(title="Song 1", artist_id=artist.artist_id)
    song2 = Song(title="Song 2", artist_id=artist.artist_id)
    db_session.add_all([song1, song2])
    db_session.commit()
    
    assert len(artist.songs) == 2
    assert song1 in artist.songs
    assert song2 in artist.songs
    assert song1.artist == artist
    assert song2.artist == artist

def test_song_lyrics_relationship(db_session):
    # Test the relationship between Song and Lyrics
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    
    song = Song(title="Test Song", artist_id=artist.artist_id)
    db_session.add(song)
    db_session.commit()
    
    lyrics = Lyrics(song_id=song.song_id, lyrics_text="Test lyrics")
    db_session.add(lyrics)
    db_session.commit()
    
    assert song.lyrics == lyrics
    assert lyrics.song == song

def test_database_initialization(db_engine):
    # Test database initialization functions
    # First drop any existing tables
    Base.metadata.drop_all(db_engine)
    
    # Create tables
    Base.metadata.create_all(db_engine)
    
    # Verify tables exist
    inspector = inspect(db_engine)
    tables = inspector.get_table_names()
    
    assert 'artists' in tables
    assert 'songs' in tables
    assert 'lyrics' in tables
    
    # Test dropping tables
    Base.metadata.drop_all(db_engine)
    inspector = inspect(db_engine)  # refresh!
    tables = inspector.get_table_names()
    assert len(tables) == 0