# Discovery Engine

**AI-Powered Discovery Engine for Photo Retrieval Cognitive Gap**

A RAG-powered system that ingests, synthesizes, and semantically analyzes public user feedback to surface insights about how users recall and search for photos.

## Architecture

```
Public Platforms → Scrapy/Apify → LangChain/LlamaIndex → BGE Embeddings → Pinecone → Groq RAG → Insights
```

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- API Keys: Groq, Pinecone, Apify

### Setup (Docker - Recommended)

The easiest way to run the entire stack (Database, API, and React Frontend) is using Docker Compose:

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys (Groq)

# 2. Start the services
docker-compose up -d
```
The React Dashboard will be available at `http://localhost:8080` and the API at `http://localhost:8000`.

### Setup (Manual)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download spaCy model
python -m spacy download en_core_web_lg

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Set up PostgreSQL
psql -U postgres -f storage/migrations/001_initial_schema.sql

# 6. Run the pipeline
python scripts/run_pipeline.py
```

## Documentation

- [API Reference](docs/API.md) - Detailed guide to the REST API endpoints and data schemas.
- [Runbook](docs/RUNBOOK.md) - Operational guidelines for triggering crawlers, re-indexing, and key rotation.
- [Handoff Document](docs/HANDOFF.md) - Final system overview and architecture handoff.


### Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
discovery-engine/
├── api/                  # FastAPI REST API
├── config/               # Centralized configuration
├── crawlers/             # Data ingestion (Scrapy + Apify)
│   ├── reddit/           # Reddit spider
│   ├── google_play/      # Google Play scraper
│   └── dedup.py          # Deduplication engine
├── processing/           # Text processing pipeline
│   ├── cleaning/         # LangChain text cleaning
│   └── chunking/         # LlamaIndex semantic chunking
├── embeddings/           # BGE embedding pipeline
├── rag/                  # RAG pipeline with Groq
├── storage/              # Pinecone + PostgreSQL
│   └── migrations/       # SQL migrations
├── tests/                # Unit & integration tests
├── scripts/              # Pipeline runners
└── data/                 # Scraped & processed data (gitignored)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Crawling | Scrapy, Apify |
| Text Processing | LangChain, LlamaIndex |
| Embeddings | BGE (bge-large-en-v1.5) |
| Vector Database | ChromaDB |
| Metadata Store | PostgreSQL (or local SQLite) |
| LLM Engine | Groq (LLaMA 3.3 70B) |
| API | FastAPI |

## License

MIT
