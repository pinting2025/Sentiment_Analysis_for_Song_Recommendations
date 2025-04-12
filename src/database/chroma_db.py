import os
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
import numpy as np
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.utils.settings import (
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    COLLECTION_METADATA,
    METADATA_FIELDS
)

class ChromaDBManager:
    """Manager class for ChromaDB operations."""
    
    def __init__(self):
        """Initialize ChromaDB client and ensure data directory exists."""
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get existing collection or create a new one."""
        try:
            collection = self.client.get_collection(COLLECTION_NAME)
            print(f"Using existing collection: {COLLECTION_NAME}")
        except ValueError:
            collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata=COLLECTION_METADATA
            )
            print(f"Created new collection: {COLLECTION_NAME}")
        return collection
    
    def add_song(
        self,
        song_id: str,
        embedding: List[float],
        metadata: Dict
    ) -> bool:
        """
        Add a single song to the ChromaDB collection.
        
        Args:
            song_id (str): Unique identifier for the song
            embedding (List[float]): Normalized embedding vector
            metadata (Dict): Song metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.collection.upsert(
                ids=[song_id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            print(f"Error adding song to ChromaDB: {e}")
            return False
    
    def add_song_with_lyrics(
        self,
        song_id: str,
        title: str,
        artist: str,
        lyrics: str,
        artist_genre: str = "Unknown",
        artist_popularity: int = 0,
        song_popularity: int = 0,
        release_date: Optional[str] = None
    ) -> bool:
        """
        Add a single song with lyrics to the ChromaDB collection.
        
        Args:
            song_id (str): Unique identifier for the song
            title (str): Song title
            artist (str): Artist name
            lyrics (str): Song lyrics
            artist_genre (str): Artist genre
            artist_popularity (int): Artist popularity score (0-100)
            song_popularity (int): Song popularity score (0-100)
            release_date (Optional[str]): Song release date
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate embedding for lyrics
            from src.database.embeddings import EmbeddingGenerator
            embedding_generator = EmbeddingGenerator()
            embedding = embedding_generator.get_embedding(lyrics)
            
            if embedding is None:
                print("Failed to generate embedding for lyrics")
                return False
            
            # Normalize embedding
            embedding = embedding / np.linalg.norm(embedding)
            
            # Prepare metadata
            metadata = {
                "title": str(title),
                "artist": str(artist),
                "artist_genre": str(artist_genre),
                "artist_popularity": int(artist_popularity),
                "song_popularity": int(song_popularity),
                "release_date": str(release_date) if release_date else "Unknown",
                "lyrics": str(lyrics[:1000])  # Store first 1000 chars for reference
            }
            
            # Add to collection
            return self.add_song(
                song_id=song_id,
                embedding=embedding.tolist(),
                metadata=metadata
            )
            
        except Exception as e:
            print(f"Error adding song to ChromaDB: {e}")
            return False
    
    def get_song(self, song_id: str) -> Optional[Dict]:
        """Get a song's embedding and metadata from ChromaDB."""
        try:
            # Get the song from the collection
            result = self.collection.get(ids=[song_id])
            
            # Check if we got any results
            if not result or not result.get('ids') or not result.get('embeddings') or not result.get('metadatas'):
                print(f"Song {song_id} not found in ChromaDB")
                return None
                
            # Return the song data
            return {
                'embedding': result['embeddings'][0],
                'metadata': result['metadatas'][0]
            }
            
        except Exception as e:
            print(f"Error getting song {song_id} from ChromaDB: {e}")
            return None
    
    def find_similar_songs(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """Find similar songs using vector similarity search."""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            print(f"Error finding similar songs: {e}")
            raise
    
    def delete_songs(self, ids: List[str]):
        """Delete songs from the collection."""
        try:
            self.collection.delete(ids=ids)
            print(f"Deleted {len(ids)} songs from ChromaDB")
        except Exception as e:
            print(f"Error deleting songs from ChromaDB: {e}")
            raise
    
    def get_collection_stats(self) -> Dict:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            return {
                "total_songs": count,
                "collection_name": COLLECTION_NAME
            }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            raise

def find_similar_songs(
    target_song_id: int,
    top_k: int = 5,
    artist_genre: Optional[str] = None,
    min_artist_popularity: Optional[int] = None,
    min_song_popularity: Optional[int] = None
) -> List[Dict]:
    """
    Find similar songs based on a target song ID and optional filters.
    
    Args:
        target_song_id (int): ID of the target song
        top_k (int): Number of similar songs to return
        artist_genre (str, optional): Filter by artist genre
        min_artist_popularity (int, optional): Minimum artist popularity
        min_song_popularity (int, optional): Minimum song popularity
    
    Returns:
        List[Dict]: List of similar songs with their details
    """
    try:
        # Initialize ChromaDB manager
        chroma_manager = ChromaDBManager()
        
        # Get the target song's embedding
        target_song = chroma_manager.get_song(str(target_song_id))
        if not target_song:
            print(f"Target song {target_song_id} not found in ChromaDB")
            return []
        
        # Build where clause for filtering
        where = {}
        if artist_genre:
            where["artist_genre"] = artist_genre
        if min_artist_popularity is not None:
            where["artist_popularity"] = {"$gte": min_artist_popularity}
        if min_song_popularity is not None:
            where["song_popularity"] = {"$gte": min_song_popularity}
        
        # Find similar songs
        results = chroma_manager.find_similar_songs(
            query_embedding=target_song['embedding'],
            n_results=top_k + 1,  # +1 because the target song will be in results
            where=where if where else None
        )
        
        # Process results
        similar_songs = []
        for i, song_id in enumerate(results['ids'][0]):
            # Skip the target song itself
            if int(song_id) == target_song_id:
                continue
            
            metadata = results['metadatas'][0][i]
            similar_songs.append({
                "song_id": int(song_id),
                "title": metadata["title"],
                "artist": metadata["artist"],
                "artist_genre": metadata["artist_genre"],
                "artist_popularity": metadata["artist_popularity"],
                "song_popularity": metadata["song_popularity"],
                "release_date": metadata["release_date"],
                "similarity_score": float(results['distances'][0][i])
            })
        
        return similar_songs
        
    except Exception as e:
        print(f"Error finding similar songs: {e}")
        return [] 