import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.service.recommendations import RecommendationService
from src.database.chroma.chroma_db import ChromaManager
from src.utils.config_manager import get_db_session
from src.database.kkbox import KKBOXAPI
from src.database.init_db import Artist, Song, Base

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

@pytest.fixture
def recommendation_service(db_session):
    service = RecommendationService()
    service.db_session = db_session
    return service

@pytest.fixture
def mock_youtube_search():
    with patch('src.database.youtube.search_song') as mock:
        mock.return_value = [{
            'video_id': 'test_video_id',
            'title': 'Test Song',
            'channel_title': 'Test Artist',
            'published_at': '2024-01-01T00:00:00Z',
            'view_count': 1000,
            'like_count': 100,
            'thumbnail': 'http://example.com/thumbnail.jpg'
        }]
        yield mock

@pytest.fixture
def mock_kkbox_api():
    with patch('src.database.kkbox.KKBOXAPI') as mock:
        instance = mock.return_value
        instance.search_song.return_value = {
            'name': 'Test Song',
            'artist': {'name': 'Test Artist'},
            'lyrics': 'Test lyrics\nfor the song\nwith multiple lines'
        }
        yield instance

@pytest.fixture
def mock_chroma_manager():
    with patch('src.database.chroma.chroma_db.ChromaManager') as mock:
        instance = mock.return_value
        instance.find_songs_by_similarity.return_value = [
            {
                "song_id": "1",
                "title": "Test Song 1",
                "artist": "Test Artist 1",
                "similarity_score": 0.9,
                "metadata": {"title": "Test Song 1", "artist": "Test Artist 1"}
            }
        ]
        instance.add_song_with_lyrics.return_value = True
        instance.song_exists.return_value = False
        yield instance

def test_fetch_lyrics_api_error(recommendation_service, mock_youtube_search):
    # Test when KKBOX API fails
    with patch('src.database.kkbox.KKBOXAPI') as mock:
        instance = mock.return_value
        instance.search_song.return_value = {}
        lyrics = recommendation_service.fetch_lyrics("Test Song", "Test Artist")
        assert lyrics is None

@patch('src.service.recommendations.ChromaManager.find_songs_by_similarity')
@patch('src.database.youtube.search_song')
def test_get_recommendations_for_song(mock_youtube_search, mock_find_similar, recommendation_service):
    # Mock the similar songs response
    mock_similar_songs = [
        {
            "song_id": "1",
            "title": "Test Song 1",
            "artist": "Test Artist 1",
            "similarity_score": 0.9,
            "metadata": {"title": "Test Song 1", "artist": "Test Artist 1"}
        },
        {
            "song_id": "2",
            "title": "Test Song 2",
            "artist": "Test Artist 2",
            "similarity_score": 0.8,
            "metadata": {"title": "Test Song 2", "artist": "Test Artist 2"}
        }
    ]
    mock_find_similar.return_value = mock_similar_songs
    
    # Mock YouTube search response
    mock_youtube_search.return_value = [{
        'video_id': 'test_video_id',
        'title': 'Test Song',
        'channel_title': 'Test Artist',
        'published_at': '2024-01-01T00:00:00Z',
        'view_count': 1000,
        'like_count': 100,
        'thumbnail': 'http://example.com/thumbnail.jpg'
    }]

    # Test with a known song ID
    recommendations = recommendation_service.get_recommendations_for_song("1")
    assert recommendations is not None

def test_get_recommendations_with_lyrics(recommendation_service, mock_chroma_manager):
    # Test getting recommendations with lyrics
    recommendations = recommendation_service.get_recommendations_for_song(song_id="1", lyrics="Test lyrics")
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
    assert all(isinstance(rec, dict) for rec in recommendations)

@patch('src.database.chroma.chroma_db.ChromaManager.add_song_with_lyrics')
def test_add_song_to_chroma(mock_add_song, recommendation_service):
    # Mock the add_song_with_lyrics method
    mock_add_song.return_value = True

    # Test adding a song
    success = recommendation_service.add_song_to_chroma(
        song_id="test_1",
        title="Test Song",
        artist="Test Artist",
        lyrics="Test lyrics for the song"
    )
    assert success is True
    mock_add_song.assert_called_once()

def test_get_next_song_id(recommendation_service, db_session):
    # Test getting next song ID
    next_id = recommendation_service.get_next_song_id()
    assert isinstance(next_id, int)
    assert next_id > 0

def test_get_existing_song_id(recommendation_service, db_session):
    # Test getting existing song ID
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.commit()
    
    song = Song(title="Test Song", artist_id=artist.artist_id)
    db_session.add(song)
    db_session.commit()
    
    song_id = recommendation_service.get_existing_song_id("Test Song")
    assert song_id is None

@patch('src.database.youtube.search_song')
def test_search_youtube_video(mock_search_song):
    # Test YouTube video search
    # Mock search_song to return an empty list
    mock_search_song.return_value = []
    
    service = RecommendationService()
    title = "Non Existent Song"
    artist = "Non Existent Artist"
    video, url = service.search_youtube_video(title=title, artist=artist)
    
    assert video is not None
    assert url is not None
    
@patch('src.database.youtube.search_song')
def test_search_youtube_video_no_results(mock_search_song):
    # Mock search_song to return an empty list
    mock_search_song.return_value = []

    service = RecommendationService()
    title = "Non Existent Song"
    artist = "Non Existent Artist"
    video, url = service.search_youtube_video(title=title, artist=artist)

    assert video == "Error"
    assert url == ""