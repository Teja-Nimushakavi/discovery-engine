"""
Centralized configuration for the Discovery Engine.

Loads settings from environment variables (.env file) with sensible defaults.
All components import their configuration from this module.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


# =============================================================================
# Cohere (Re-ranking)
# =============================================================================
COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")

# =============================================================================
# Groq (LLM Engine)
# =============================================================================
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = "qwen/qwen3.8-27b"
GROQ_TEMPERATURE: float = float(os.getenv("RAG_TEMPERATURE", "0.3"))
GROQ_MAX_TOKENS: int = int(os.getenv("RAG_MAX_TOKENS", "500"))

# =============================================================================
# Pinecone (Vector Database)
# =============================================================================
PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "photo-retrieval-feedback")
PINECONE_METRIC: str = "cosine"
PINECONE_DIMENSIONS: int = 1024  # BGE-large-en-v1.5 output dimensions

PINECONE_NAMESPACES: list[str] = [
    "google_play",
    "apple_app_store",
    "app_store_reviews",
    "reddit_threads",
    "support_forums",
    "youtube_comments",
]

# =============================================================================
# PostgreSQL (Metadata Store)
# =============================================================================
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "discovery_engine")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "discovery")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")

POSTGRES_URL: str = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# =============================================================================
# Apify (Google Play Crawler)
# =============================================================================
APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
APIFY_GOOGLE_PLAY_ACTOR: str = "nFJndFXA5OrgE5r5t"  # Google Play Scraper actor ID

# Target apps for review scraping
TARGET_APPS: list[dict] = [
    # Google Play
    {"id": "com.google.android.apps.photos", "name": "Google Photos (Android)", "platform": "google_play"},
    # Apple App Store
    {"id": "962164605", "name": "Google Photos (iOS)", "platform": "apple_app_store"},
]

# =============================================================================
# Apify (Additional Actors)
# =============================================================================
APIFY_APPLE_APP_STORE_ACTOR: str = os.getenv("APIFY_APPLE_APP_STORE_ACTOR", "ds-api/apple-app-store-scraper")
APIFY_YOUTUBE_ACTOR: str = os.getenv("APIFY_YOUTUBE_ACTOR", "ysmnv/youtube-comments-scraper")

# =============================================================================
# BGE Embedding Model
# =============================================================================
BGE_MODEL_NAME: str = os.getenv("BGE_MODEL_NAME", "BAAI/bge-large-en-v1.5")
BGE_BATCH_SIZE: int = int(os.getenv("BGE_BATCH_SIZE", "64"))
BGE_MAX_SEQ_LENGTH: int = 512

# =============================================================================
# RAG Configuration
# =============================================================================
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "20"))
RAG_RERANK_TOP_K: int = int(os.getenv("RAG_RERANK_TOP_K", "8"))

# =============================================================================
# Crawling
# =============================================================================
CRAWL_DELAY_SECONDS: float = float(os.getenv("CRAWL_DELAY_SECONDS", "2.0"))

# Data directories
DATA_DIR: Path = _PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = Path(os.getenv("RAW_DATA_DIR", str(DATA_DIR / "raw")))
PROCESSED_DATA_DIR: Path = Path(os.getenv("PROCESSED_DATA_DIR", str(DATA_DIR / "processed")))

# Ensure data directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Reddit crawl targets
REDDIT_SUBREDDITS: list[str] = [
    "googlephotos",
    "photography",
    "iphone",
]

REDDIT_SEARCH_KEYWORDS: list[str] = [
    "can't find photo",
    "search not working",
    "find old photos",
    "photo search",
    "looking for a picture",
    "retrieve photo",
    "remember photo",
]

RETRIEVAL_KEYWORDS: list[str] = [
    "search", "find", "look for", "retrieve", "remember", "forget", "forgot",
    "missing", "lost", "where is", "can't locate", "sort", "filter", 
    "can't find", "disappeared", "searching", "long back", "old photo",
    "years ago", "scroll", "scrolling"
]

# =============================================================================
# Chunking Configuration
# =============================================================================
CHUNK_SIZE: int = 512  # tokens
CHUNK_OVERLAP: int = 64  # tokens
MIN_TEXT_LENGTH: int = 20  # characters — discard shorter texts

# =============================================================================
# Processing
# =============================================================================
SUPPORTED_LANGUAGES: list[str] = ["en"]
MIN_ENGLISH_RATIO: float = 0.7  # Minimum ratio of English characters for code-mixed text

# =============================================================================
# Enrichment & NER
# =============================================================================
SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_lg")
