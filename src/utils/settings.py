import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database settings
DB_PATH = PROJECT_ROOT / "data" / "songs.db"
CHROMA_DB_PATH = PROJECT_ROOT / "data" / "chromadb_data"

# ChromaDB settings
COLLECTION_NAME = "song_embeddings"
COLLECTION_METADATA = {
    "description": "Song embeddings for semantic search",
    "embedding_model": "bert-base-chinese",
}

# Metadata field types
METADATA_FIELDS = {
    "title": str,
    "artist": str,
    "artist_genre": str,
    "artist_popularity": int,
    "song_popularity": int,
    "release_date": str,
    "lyrics": str,
}

# Model settings
MODEL_NAME = "bert-base-chinese"
MAX_SEQUENCE_LENGTH = 512
DEVICE = "cuda" if os.environ.get("USE_CUDA", "false").lower() == "true" else "cpu"

# Recommendation settings
DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_WEIGHT = 0.7
DEFAULT_POPULARITY_WEIGHT = 0.3 