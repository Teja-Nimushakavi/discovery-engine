"""
Standalone script to fetch >500 reviews using Google Play Scraper
and ingest them directly into SQLite for the qualitative PM dashboard.
"""
import sys
import os
import logging
from datetime import datetime, timezone

# Add project root to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlers.google_play.scraper import GooglePlayScraper
from processing.cleaning.cleaner import TextCleaner
from processing.chunking.chunker import SemanticChunker
from processing.enrichment.enricher import MetadataEnricher
from storage.metadata_repo import MetadataRepository
from storage.models import get_engine, create_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing SQLite database...")
    db_engine = get_engine()
    create_tables(db_engine)
    repo = MetadataRepository(db_engine)

    logger.info("Scraping up to 1500 reviews for Google Photos from Google Play...")
    scraper = GooglePlayScraper()
    raw_reviews = scraper.scrape_reviews(
        app_id="com.google.android.apps.photos",
        app_name="Google Photos",
        max_reviews=1500
    )
    logger.info(f"Successfully scraped {len(raw_reviews)} reviews.")

    if not raw_reviews:
        logger.error("No reviews scraped. Exiting.")
        return

    logger.info("Cleaning reviews...")
    cleaner = TextCleaner()
    cleaned_items = []
    
    # Map the scraper schema (review_text) to the expected schema (text)
    for r in raw_reviews:
        r["text"] = r["review_text"]
        res = cleaner.clean(r["text"])
        if not res["was_filtered"]:
            r["cleaned_text"] = res["cleaned_text"]
            r["original_text"] = res["original_text"]
            cleaned_items.append(r)
            
    logger.info(f"Cleaned {len(cleaned_items)} reviews.")

    logger.info("Chunking reviews...")
    chunker = SemanticChunker(chunk_size=512)
    chunks = chunker.chunk_batch(
        cleaned_items,
        metadata_fields=["source_platform", "app_name", "author", "timestamp", "rating"]
    )
    logger.info(f"Generated {len(chunks)} chunks.")

    logger.info("Enriching metadata and building DB records...")
    enricher = MetadataEnricher()
    
    db_chunks = []
    for c in chunks:
        # Base metadata
        meta = c.metadata.copy()
        
        # We rename app_name back to app_referenced for the enricher and DB
        meta["app_referenced"] = meta.get("app_name", "Google Photos")
        
        # Enrich with VADER sentiment and taxonomy regex
        meta = enricher.enrich(c.text, meta)
        
        db_chunks.append({
            "chunk_id": str(c.chunk_id),
            "vector_id": str(c.chunk_id), # Mock vector_id
            "source_platform": meta.get("source_platform", "unknown"),
            "original_text": next(r["original_text"] for r in cleaned_items if r["author"] == meta.get("author")),
            "chunk_text": c.text,
            "app_referenced": meta.get("app_referenced"),
            "author_id": meta.get("author"),
            "memory_anchors": {},
            "forgotten_metadata": {},
            "search_strategy": "keyword_unknown",
            "frustration_level": meta.get("frustration_level", "low"),
            "taxonomy_label": meta.get("taxonomy_label", "unrelated"),
            "sentiment_score": meta.get("sentiment_score", 0.0),
            "crawled_at": datetime.now(timezone.utc),
        })

    logger.info("Inserting into PostgreSQL / SQLite...")
    inserted_count = repo.bulk_insert_chunks(db_chunks)
    logger.info(f"Successfully inserted {inserted_count} chunks into the database!")
    logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()
