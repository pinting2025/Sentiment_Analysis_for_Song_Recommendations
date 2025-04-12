import sys
import os
import logging
import numpy as np
from typing import List, Dict, Optional
import chromadb
from pathlib import Path

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.utils.config_manager import get_db_session
from src.utils.settings import (
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    COLLECTION_METADATA,
    METADATA_FIELDS
)
from scripts.init_db import Song, Lyrics, Artist
from src.database.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for handling song recommendations with enhanced features."""
    
    def __init__(self):
        """Initialize the recommendation service."""
        self.collection = self._get_collection()
        self.embedding_generator = EmbeddingGenerator()
    
    def _get_collection(self):
        """Get or create ChromaDB collection."""
        chroma_path = Path(CHROMA_DB_PATH)
        chroma_path.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(path=str(chroma_path))
        try:
            collection = client.get_collection(COLLECTION_NAME)
        except ValueError:
            collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata=COLLECTION_METADATA
            )
        return collection
    
    def _get_lyrics_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for lyrics text."""
        try:
            embedding = self.embedding_generator.get_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def _get_target_embedding(self, target_song_id: int) -> Optional[np.ndarray]:
        """Get or generate embedding for target song."""
        try:
            # Try to get from ChromaDB first
            target_result = self.collection.get(ids=[str(target_song_id)])
            if target_result and target_result['ids'] and target_result['embeddings']:
                target_embedding = np.array(target_result['embeddings'][0])
                logger.info(f"Found target song {target_song_id} in ChromaDB")
                return target_embedding
            
            # If not in ChromaDB, generate and store
            session = get_db_session()
            try:
                target_song = session.query(Song, Lyrics, Artist).\
                    join(Lyrics, Song.song_id == Lyrics.song_id).\
                    join(Artist, Song.artist_id == Artist.artist_id).\
                    filter(Song.song_id == target_song_id).\
                    first()
                
                if not target_song:
                    logger.error(f"Target song {target_song_id} not found in database")
                    return None
                
                song, lyrics, artist = target_song
                if not lyrics.lyrics_text:
                    logger.error(f"No lyrics found for song {target_song_id}")
                    return None
                
                # Generate embedding
                target_embedding = self._get_lyrics_embedding(lyrics.lyrics_text)
                if target_embedding is None:
                    return None
                
                # Normalize the embedding
                target_embedding = target_embedding / np.linalg.norm(target_embedding)
                
                # Store in ChromaDB
                metadata = {
                    "title": song.title,
                    "artist": artist.name,
                    "artist_genre": artist.genre or "Unknown",
                    "artist_popularity": artist.popularity or 0,
                    "song_popularity": song.popularity or 0,
                    "release_date": str(song.release_date) if song.release_date else None,
                    "lyrics": lyrics.lyrics_text[:1000]
                }
                
                self.collection.upsert(
                    ids=[str(target_song_id)],
                    embeddings=[target_embedding.tolist()],
                    metadatas=[metadata]
                )
                logger.info(f"Stored new embedding for song {target_song_id} in ChromaDB")
                
                return target_embedding
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting target embedding: {e}")
            return None
    
    def get_recommendations(
        self,
        target_song_id: int,
        top_k: int = 5,
        artist_genre: Optional[str] = None,
        min_artist_popularity: Optional[int] = None,
        min_song_popularity: Optional[int] = None,
        similarity_weight: float = 0.7,
        popularity_weight: float = 0.3
    ) -> List[Dict]:
        """
        Get song recommendations based on lyrics similarity with genre filtering and popularity weighting.
        
        Args:
            target_song_id (int): ID of the target song
            top_k (int): Number of recommendations to return
            artist_genre (str, optional): Filter by artist genre
            min_artist_popularity (int, optional): Minimum artist popularity score
            min_song_popularity (int, optional): Minimum song popularity score
            similarity_weight (float): Weight for semantic similarity (0-1)
            popularity_weight (float): Weight for popularity (0-1)
        
        Returns:
            List[Dict]: List of recommended songs with details
        """
        try:
            # Check if collection is empty
            if self.collection.count() == 0:
                logger.warning(f"Collection {COLLECTION_NAME} is empty. Please run init_chroma.py first.")
                return []
            
            # Get target embedding
            target_embedding = self._get_target_embedding(target_song_id)
            if target_embedding is None:
                return []
            
            # Prepare where clause for filtering
            where = {}
            if artist_genre:
                where["artist_genre"] = artist_genre
            if min_artist_popularity is not None:
                where["artist_popularity"] = {"$gte": min_artist_popularity}
            if min_song_popularity is not None:
                where["song_popularity"] = {"$gte": min_song_popularity}
            
            # Get similar songs
            results = self.collection.query(
                query_embeddings=[target_embedding.tolist()],
                n_results=top_k + 1,  # +1 to exclude the target song
                where=where if where else None
            )
            
            if not results or not results['ids']:
                logger.error("No similar songs found")
                return []
            
            # Process results
            recommendations = []
            for i, (song_id, distance, metadata) in enumerate(zip(
                results['ids'][0],
                results['distances'][0],
                results['metadatas'][0]
            )):
                # Skip the target song
                if int(song_id) == target_song_id:
                    continue
                
                # Calculate scores
                similarity_score = 1 - distance
                artist_popularity_score = float(metadata['artist_popularity']) / 100
                song_popularity_score = float(metadata['song_popularity']) / 100
                popularity_score = (artist_popularity_score + song_popularity_score) / 2
                weighted_score = (
                    similarity_score * similarity_weight +
                    popularity_score * popularity_weight
                )
                
                recommendations.append({
                    'song_id': int(song_id),
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'artist_genre': metadata['artist_genre'],
                    'artist_popularity': float(metadata['artist_popularity']),
                    'song_popularity': float(metadata['song_popularity']),
                    'release_date': metadata['release_date'],
                    'similarity_score': float(similarity_score),
                    'popularity_score': float(popularity_score),
                    'weighted_score': float(weighted_score)
                })
            
            # Sort by weighted score
            recommendations.sort(key=lambda x: x['weighted_score'], reverse=True)
            return recommendations[:top_k]
            
        except Exception as e:
            logger.error(f"Error getting song recommendations: {e}")
            return [] 