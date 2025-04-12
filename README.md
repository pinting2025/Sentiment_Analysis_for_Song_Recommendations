# Song Recommender System

A song recommendation system that uses semantic analysis of lyrics to find similar songs based on their emotional content and meaning.

## Features

- Semantic analysis of song lyrics using BERT embeddings
- Vector similarity search using ChromaDB
- Genre and popularity-based filtering
- Persistent storage of embeddings
- REST API for song recommendations

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/Sentiment_Analysis_for_Song_Recommendations.git
cd Sentiment_Analysis_for_Song_Recommendations
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -e .
```

## Usage

1. Initialize the database:

```bash
python scripts/init_db.py
```

2. Initialize ChromaDB with song embeddings:

```bash
python scripts/init_chroma.py
```

3. Get song recommendations:

```bash
python scripts/get_recommendation.py
```

## Project Structure

```
src/song_recommender/
├── config/          # Configuration files
├── database/        # Database models and operations
├── utils/           # Utility functions
└── api/             # API endpoints
```

## Development

1. Install development dependencies:

```bash
pip install -e ".[dev]"
```

2. Run tests:

```bash
pytest
```

3. Format code:

```bash
black .
isort .
```

## License

MIT License - see LICENSE file for details
