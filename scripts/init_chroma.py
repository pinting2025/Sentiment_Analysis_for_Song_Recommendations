import logging
import os
import sys
from datetime import datetime
from sqlalchemy import func
import numpy as np
import random
from pathlib import Path

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.database.embeddings import EmbeddingGenerator
from src.utils.config_manager import get_db_session
from scripts.init_db import Song, Lyrics, Artist
from src.utils.settings import COLLECTION_NAME, COLLECTION_METADATA, METADATA_FIELDS, CHROMA_DB_PATH
from src.database.chroma_db import ChromaManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure the chromadb_data directory exists
chroma_path = Path(CHROMA_DB_PATH)
chroma_path.mkdir(parents=True, exist_ok=True)
logger.info(f"Using ChromaDB storage path: {chroma_path}")

def needs_update() -> bool:
    try:
        chroma_manager = ChromaManager()
        collection = chroma_manager.collection
        last_update = datetime.fromisoformat(collection.metadata.get("last_updated", "1970-01-01"))

        session = get_db_session()
        try:
            latest_db_update = session.query(
                func.max(func.greatest(
                    Song.updated_at,
                    Lyrics.updated_at,
                    Artist.updated_at
                ))
            ).scalar()

            if latest_db_update is None:
                return True

            return latest_db_update > last_update

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error checking if update is needed: {e}")
        return True

def init_chroma_db(force: bool = False):
    try:
        chroma_manager = ChromaManager()
        client = chroma_manager.client
        collection = chroma_manager.collection
        logger.info(f"Initialized ChromaDB client with path: {chroma_path}")

        if force:
            try:
                client.delete_collection(COLLECTION_NAME)
                logger.info(f"Deleted existing collection: {COLLECTION_NAME}")
                collection = client.create_collection(name=COLLECTION_NAME, metadata=COLLECTION_METADATA)
                logger.info(f"Created new collection: {COLLECTION_NAME}")
            except Exception as e:
                logger.error(f"Failed to reset collection: {e}")
                raise

        session = get_db_session()
        try:
            songs = session.query(Song, Lyrics, Artist).\
                join(Lyrics, Song.song_id == Lyrics.song_id).\
                join(Artist, Song.artist_id == Artist.artist_id).\
                all()

            ids, embeddings, metadatas = [], [], []
            total_songs = len(songs)
            logger.info(f"Processing {total_songs} songs...")

            embedding_generator = EmbeddingGenerator()

            for idx, (song, lyrics, artist) in enumerate(songs, 1):
                if not lyrics.lyrics_text:
                    logger.warning(f"Skipping song {song.song_id} - no lyrics available")
                    continue

                embedding = embedding_generator.get_embedding(lyrics.lyrics_text)
                if embedding is not None:
                    embedding = embedding / np.linalg.norm(embedding)
                    metadata = {
                        "title": song.title,
                        "artist": artist.name,
                        "artist_genre": artist.genre or "Unknown",
                        "artist_popularity": artist.popularity or 0,
                        "song_popularity": song.popularity or 0,
                        "release_date": str(song.release_date) if song.release_date else None,
                        "lyrics": lyrics.lyrics_text[:1000]
                    }

                    for field, field_type in METADATA_FIELDS.items():
                        if field in metadata and not isinstance(metadata[field], field_type):
                            try:
                                metadata[field] = field_type(metadata[field])
                            except (ValueError, TypeError):
                                metadata[field] = field_type()

                    ids.append(str(song.song_id))
                    embeddings.append(embedding.tolist())
                    metadatas.append(metadata)

                    if idx % 10 == 0:
                        logger.info(f"Processed {idx}/{total_songs} songs")

            if ids:
                try:
                    collection.delete(ids=ids)
                    logger.info(f"Deleted existing embeddings for {len(ids)} songs")
                except Exception as e:
                    logger.debug(f"No existing embeddings to delete: {e}")

                collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
                logger.info(f"Added {len(ids)} songs to ChromaDB")

            collection.modify(metadata={
                **COLLECTION_METADATA,
                "last_updated": datetime.now().isoformat()
            })

            count = collection.count()
            logger.info(f"ChromaDB collection now contains {count} songs")

            sample_size = min(5, count)
            if sample_size > 0:
                sample_ids = random.sample(ids, sample_size)
                sample_results = collection.get(ids=sample_ids)
                logger.info(f"Verified {len(sample_results['ids'])} sample songs in collection")

        except Exception as e:
            logger.error(f"Error populating ChromaDB: {e}")
            raise

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error initializing ChromaDB: {e}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Initialize or update ChromaDB")
    parser.add_argument("--force", action="store_true", help="Force reinitialization")
    args = parser.parse_args()

    if args.force or needs_update():
        logger.info("ChromaDB needs to be updated. Starting initialization...")
        init_chroma_db(force=args.force)
    else:
        logger.info("ChromaDB is up to date. No update needed.")
