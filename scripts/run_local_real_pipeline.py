"""
Script to wipe out fake reviews and fill the local database with 100% real reviews.
Uses Google Play Scraper, local SQLite, and local ChromaDB.
No API keys needed for Apify or Pinecone.
"""
import os
import sys
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage.models import get_engine, create_tables
from storage.metadata_repo import MetadataRepository
from storage.chroma_store import ChromaStore
from crawlers.google_play.scraper import GooglePlayScraper
from processing.cleaning.cleaner import TextCleaner
from processing.chunking.chunker import SemanticChunker
from embeddings.bge_embedder import BGEEmbedder
from processing.enrichment.enricher import MetadataEnricher
from processing.enrichment.ner import NERTagger
import json
from datetime import datetime, timezone

def wipe_old_data():
    print("Wiping old fake reviews...")
    db_path = Path("discovery_engine.db")
    if db_path.exists():
        db_path.unlink()
        
    chroma_path = Path("data/chroma_db")
    if chroma_path.exists():
        shutil.rmtree(chroma_path)

def run():
    wipe_old_data()
    
    print("Initializing databases...")
    engine = get_engine()
    create_tables(engine)
    repo = MetadataRepository(engine)
    vector_store = ChromaStore()
    
    print("Scraping 5000 fresh reviews from Google Play...")
    scraper = GooglePlayScraper()
    raw_reviews = scraper.scrape_reviews(
        app_id="com.google.android.apps.photos",
        app_name="Google Photos",
        max_reviews=5000
    )
        
    print("Formatting reviews...")
    reviews = []
    for r in raw_reviews:
        reviews.append({
            "text": r.get("review_text", ""),
            "source_platform": r.get("source_platform", "google_play"),
            "app_referenced": "Google Photos",
            "author": r.get("author", "unknown"),
            "timestamp": r.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })
        
    print(f"Clean & Chunk {len(reviews)} real reviews...")
    cleaner = TextCleaner()
    cleaned = []
    for r in reviews:
        c = cleaner.clean(r["text"])
        if not c["was_filtered"]:
            r["cleaned_text"] = c["cleaned_text"]
            r["original_text"] = c["original_text"]
            cleaned.append(r)
            
    chunker = SemanticChunker(chunk_size=512)
    chunks = chunker.chunk_batch(cleaned, metadata_fields=["source_platform", "app_referenced", "author", "timestamp"])
    
    print("Embedding...")
    embedder = BGEEmbedder()
    embedded = embedder.embed_chunks(chunks)
    
    print("Enriching metadata...")
    enricher = MetadataEnricher()
    ner = NERTagger()
    
    db_chunks = []
    for item in embedded:
        c = item["chunk"]
        meta = enricher.enrich(c.text, c.metadata.copy())
        ner_data = ner.extract_entities(c.text)
        
        # Update chunk metadata so it gets sent to ChromaDB
        c.metadata = meta
        
        db_chunks.append({
            "chunk_id": str(c.chunk_id),
            "vector_id": str(c.chunk_id),
            "source_platform": meta.get("source_platform", "google_play"),
            "original_text": next(r["original_text"] for r in cleaned if r["author"] == meta.get("author")),
            "chunk_text": c.text,
            "app_referenced": meta.get("app_referenced"),
            "author_id": meta.get("author"),
            "memory_anchors": ner_data.get("memory_anchors"),
            "forgotten_metadata": ner_data.get("forgotten_metadata"),
            "search_strategy": ner_data.get("inferred_search_strategy"),
            "frustration_level": meta.get("frustration_level"),
            "taxonomy_label": meta.get("taxonomy_label"),
            "sentiment_score": meta.get("sentiment_score"),
        })

    print("Saving to ChromaDB...")
    vector_store.upsert_chunks(embedded, namespace="google_play")
    
    print("Saving metadata to SQLite...")
        
    repo.bulk_insert_chunks(db_chunks)
    print("DONE! You now have 100% REAL reviews in your local dashboard.")

if __name__ == "__main__":
    run()
