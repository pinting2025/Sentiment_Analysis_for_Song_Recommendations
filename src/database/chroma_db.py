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
    COLLECTION_METADATA
)
import logging
# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChromaManager:
    """Manager class for ChromaDB operations."""
    
    def __init__(self):
        """
        Initialize the ChromaDB manager.
        
        Args:
            db_path (str): Path to ChromaDB storage
            collection_name (str): Name of the collection to use
            collection_metadata (Dict, optional): Metadata for the collection
        """
        self.db_path = CHROMA_DB_PATH
        self.collection_name = COLLECTION_NAME
        self.collection_metadata = COLLECTION_METADATA or {}
        
        # Ensure the directory exists
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        
        # Initialize client
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
        
    def _get_or_create_collection(self):
        """Get existing collection or create a new one."""
        try:
            collection = self.client.get_collection(self.collection_name)
            logger.info(f"Using existing collection: {self.collection_name}")
        except ValueError:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata=self.collection_metadata
            )
            logger.info(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def add_song(
        self, 
        id: str, 
        embedding: List[float], 
        metadata: Dict
    ) -> bool:
        """
        Add a single embedding to the collection.
        
        Args:
            id (str): Unique identifier
            embedding (List[float]): Vector embedding
            metadata (Dict): Associated metadata
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate the embedding
            if not embedding or len(embedding) == 0:
                logger.error(f"Invalid embedding for ID {id}")
                return False
            
            # Add the document
            self.collection.upsert(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully added embedding for ID {id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding embedding: {e}")
            return False
    
    def get_song(self, id: str) -> Optional[Dict]:
        """
        Get an embedding by ID.
        
        Args:
            id (str): Document ID
            
        Returns:
            Optional[Dict]: Document data including embedding and metadata, or None if not found
        """
        try:
            result = self.collection.get(
                ids=[id],
                include=["embeddings", "metadatas"]
            )
            
            if not result or not result["ids"]:
                logger.warning(f"ID {id} not found in collection")
                return None
                
            return {
                "id": result["ids"][0],
                "embedding": result["embeddings"][0],
                "metadata": result["metadatas"][0]
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    def delete_song(self, id: str) -> bool:
        """
        Delete an embedding by ID.
        
        Args:
            id (str): Document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[id])
            logger.info(f"Deleted embedding for ID {id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting embedding: {e}")
            return False
    
    def get_all_ids(self) -> List[str]:
        """
        Get all document IDs in the collection.
        
        Returns:
            List[str]: List of all IDs
        """
        try:
            # Get a limited number of results but only retrieve IDs
            results = self.collection.get(include=["documents"])
            return results.get("ids", [])
        except Exception as e:
            logger.error(f"Error getting all IDs: {e}")
            return []
    
    def collection_stats(self) -> Dict:
        """
        Get statistics about the collection.
        
        Returns:
            Dict: Collection statistics
        """
        try:
            count = self.collection.count()
            metadata = self.collection.metadata
            
            return {
                "count": count,
                "name": self.collection_name,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def find_similar(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None,
        include: Optional[List[str]] = None
    ) -> Dict:
        """
        Find similar embeddings using vector search.
        
        Args:
            query_embedding (List[float]): Query vector
            n_results (int): Number of results to return
            where (Dict, optional): Filter based on metadata
            where_document (Dict, optional): Filter based on document content
            include (List[str], optional): What to include in results
            
        Returns:
            Dict: Search results
        """
        try:
            include = include or ["metadatas", "distances"]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar embeddings: {e}")
            raise

    def find_songs_by_similarity(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Find similar songs based on embedding similarity.
        
        Args:
            query_embedding (List[float]): Query embedding
            top_k (int): Number of results to return
            filters (Dict, optional): Metadata filters
            
        Returns:
            List[Dict]: List of similar songs with metadata and scores
        """
        try:
            # Build where clause if filters provided
            where = {}
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict) and ("$gte" in value or "$lte" in value):
                        # Handle range filters
                        where[key] = value
                    elif value is not None:
                        where[key] = value
            
            # Query the collection
            results = self.find_similar(
                query_embedding=query_embedding,
                n_results=top_k,
                where=where if where else None,
                include=["metadatas", "distances", "embeddings"]
            )
            
            # Process results
            songs = []
            for i, result_id in enumerate(results["ids"][0]):
                # Get metadata and distance
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Calculate similarity score (1 - distance)
                similarity_score = 1.0 - float(distance)
                
                # Add to results
                songs.append({
                    "song_id": result_id,
                    "title": metadata.get("title", "Unknown"),
                    "artist": metadata.get("artist", "Unknown"),
                    "similarity_score": similarity_score,
                    "metadata": metadata
                })
            
            # Sort by similarity score (highest first)
            songs.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return songs
            
        except Exception as e:
            logger.error(f"Error finding similar songs: {e}")
            return []
    
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
            song_popularity (int): Song popularity score (0-100)
            
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
                "song_popularity": int(song_popularity),
                "lyrics": str(lyrics[:1000])  # Store first 1000 chars for reference
            }
            
            # Add to collection
            return self.add_song(
                id=song_id,
                embedding=embedding.tolist(),
                metadata=metadata
            )
            
        except Exception as e:
            print(f"Error adding song to ChromaDB: {e}")
            return False