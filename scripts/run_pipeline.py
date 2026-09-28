"""
End-to-End Pipeline Integration Script for Phase 1.

Runs the full data pipeline on a small sample to verify end-to-end functionality:
1. Initialize PostgreSQL & Pinecone
2. Clean and Chunk a sample raw dataset
3. Embed and store the chunks
4. Run a RAG query
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from embeddings.bge_embedder import BGEEmbedder
from processing.chunking.chunker import SemanticChunker
from processing.cleaning.cleaner import TextCleaner
from processing.enrichment.enricher import MetadataEnricher
from processing.enrichment.ner import NERTagger
from rag.engine import RAGEngine
from storage.metadata_repo import MetadataRepository
from storage.models import create_tables, get_engine
from storage.pinecone_store import PineconeStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Discovery Engine: Phase 1 Integration Test ===")

    # 1. Initialize databases
    logger.info("Initializing PostgreSQL tables...")
    db_engine = get_engine()
    create_tables(db_engine)
    repo = MetadataRepository(db_engine)

    logger.info("Initializing Pinecone store...")
    vector_store = PineconeStore()
    
    # 2. Scrape Real Data
    logger.info("Running scrapers to fetch real data...")
    from crawlers.google_play.scraper import GooglePlayScraper
    from scripts.scrape_remaining_platforms import main as run_other_scrapers
    
    try:
        logger.info("Scraping Google Play...")
        with GooglePlayScraper() as scraper:
            scraper.scrape_all_apps()
            
        logger.info("Scraping other platforms...")
        run_other_scrapers()
    except Exception as e:
        logger.error(f"Scraping encountered an error, continuing with existing data: {e}")

    # 3. Load all scraped data
    logger.info("Loading real reviews from data/raw/...")
    sample_reviews = []
    import json
    from pathlib import Path
    
    for jsonl_file in Path("data/raw").rglob("*.jsonl"):
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    
                    text = data.get("review_text", "")
                    if not text:
                        text = data.get("body", "") + " " + data.get("title", "")
                    if not text.strip(): continue
                        
                    sample_reviews.append({
                        "text": text,
                        "source_platform": data.get("source_platform", "unknown"),
                        "app_referenced": data.get("app_name", data.get("app_referenced", "unknown")),
                        "author": data.get("author", "unknown"),
                        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    })
        except Exception as e:
            logger.error(f"Failed to read {jsonl_file}: {e}")

    logger.info(f"Loaded {len(sample_reviews)} real reviews.")
    logger.info("Cleaning sample data...")
    cleaner = TextCleaner()
    cleaned_items = []
    for item in sample_reviews:
        res = cleaner.clean(item["text"])
        if not res["was_filtered"]:
            item["cleaned_text"] = res["cleaned_text"]
            item["original_text"] = res["original_text"]
            cleaned_items.append(item)

    logger.info("Chunking sample data...")
    chunker = SemanticChunker(chunk_size=512)
    chunks = chunker.chunk_batch(
        cleaned_items, 
        metadata_fields=["source_platform", "app_referenced", "author", "timestamp"]
    )

    # 3. Embedding and Storage
    logger.info("Embedding chunks...")
    embedder = BGEEmbedder()
    embedded_chunks = embedder.embed_chunks(chunks)

    logger.info("Upserting chunks to Pinecone...")
    vector_store.upsert_chunks(embedded_chunks, namespace="test_namespace")

    logger.info("Enriching and Saving metadata to PostgreSQL...")
    enricher = MetadataEnricher()
    ner = NERTagger()
    
    db_chunks = []
    for item in embedded_chunks:
        c = item["chunk"]
        
        # Base metadata
        meta = c.metadata.copy()
        
        # 1. Enrich with sentiment, taxonomy, app ident
        meta = enricher.enrich(c.text, meta)
        
        # 2. Extract NER memory anchors
        ner_data = ner.extract_entities(c.text)
        
        # Merge NER data
        memory_anchors = ner_data.get("memory_anchors")
        forgotten_metadata = ner_data.get("forgotten_metadata")
        search_strategy = ner_data.get("inferred_search_strategy")
        
        db_chunks.append({
            "chunk_id": str(c.chunk_id),
            "vector_id": str(c.chunk_id),
            "source_platform": meta.get("source_platform", "unknown"),
            "original_text": next(r["original_text"] for r in cleaned_items if r["author"] == meta.get("author")),
            "chunk_text": c.text,
            "app_referenced": meta.get("app_referenced"),
            "author_id": meta.get("author"),
            "memory_anchors": memory_anchors,
            "forgotten_metadata": forgotten_metadata,
            "search_strategy": search_strategy,
            "frustration_level": meta.get("frustration_level"),
            "taxonomy_label": meta.get("taxonomy_label"),
            "sentiment_score": meta.get("sentiment_score"),
        })
    repo.bulk_insert_chunks(db_chunks)

    # 4. Cleanup
    logger.info("Integration and storage pipeline complete.")


if __name__ == "__main__":
    main()
