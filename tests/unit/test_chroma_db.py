import pytest
import os
import sys
import numpy as np

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, project_root)
from src.database.chroma.chroma_db import ChromaManager

@pytest.fixture
def chroma_manager():
    return ChromaManager()

def test_collection_initialization(chroma_manager):
    # Test collection initialization
    collection = chroma_manager.collection
    assert collection is not None
    assert collection.name == "song_embeddings"

def test_add_song(chroma_manager):
    # Test adding a song to ChromaDB
    song_id = "test_1"
    title = "Test Song"
    artist = "Test Artist"
    lyrics = "This is a test song with some lyrics"
    
    # Generate a random embedding for testing
    embedding = np.random.rand(768).tolist()  # BERT embeddings are typically 768-dimensional
    
    metadata = {
        "title": title,
        "artist": artist,
        "lyrics": lyrics[:1000],
        "song_popularity": 0
    }
    
    success = chroma_manager.add_song(song_id, embedding, metadata)
    assert success is True

def test_find_similar_songs(chroma_manager):
    # Test finding similar songs
    # Generate a random query embedding
    query_embedding = np.random.rand(768).tolist()
    
    similar_songs = chroma_manager.find_songs_by_similarity(query_embedding, top_k=5)
    assert isinstance(similar_songs, list)
    if similar_songs:  # If there are similar songs
        assert all(isinstance(song, dict) for song in similar_songs)
        assert all("song_id" in song for song in similar_songs)
        assert all("similarity_score" in song for song in similar_songs) 