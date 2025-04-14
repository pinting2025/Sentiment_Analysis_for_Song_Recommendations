# Sentiment Analysis for Song Recommendations

A sophisticated song recommendation system that uses semantic analysis of lyrics to find similar songs based on their emotional content and meaning. The system leverages BERT embeddings and ChromaDB for efficient vector similarity search.

## Features

- Semantic analysis of song lyrics using BERT embeddings
- Vector similarity search using ChromaDB
- Genre and popularity-based filtering
- Persistent storage of embeddings
- REST API for song recommendations
- Modern web interface for easy interaction
- Comprehensive test suite

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

### Backend Setup

1. Initialize the database:

```bash
python src/database/init_db.py
```

2. Initialize ChromaDB with song embeddings:

```bash
python src/database/chroma/init_chroma.py
```

### Running the Application

1. Start the backend server:

```bash
python scripts/main.py
```

2. Access the web interface at `http://localhost:5000`

### Testing

Run the test suite:

```bash
pytest tests/
```

For detailed test coverage report:

```bash
pytest --cov=src tests/
```

## Project Structure

```
.
├── src/                    # Source code
│   ├── service/           # Business logic
│   ├── database/          # Database operations
│   └── utils/             # Utility functions
├── scripts/               # Scripts and main application
├── tests/                 # Test suite
├── data/                  # Data files
└── requirements.txt       # Project dependencies
```

## API Endpoints

- `POST /api/recommend` - Get song recommendations
- `GET /api/songs` - List all songs in the database
- `POST /api/songs` - Add a new song

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
