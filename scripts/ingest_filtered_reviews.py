import os
import sys
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
import re

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from storage.models import get_engine, create_tables
from storage.metadata_repo import MetadataRepository
from processing.chunking.chunker import SemanticChunker
from embeddings.bge_embedder import BGEEmbedder
from storage.chroma_store import ChromaStore
from processing.enrichment.enricher import MetadataEnricher
from processing.enrichment.ner import NERTagger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ingest_filtered_reviews():
    file_path = r"C:\Users\Teja\.gemini\antigravity-ide\brain\95620dcd-17a1-4343-bdc8-c5afff97638a\filtered_reddit_reviews.md"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    items = []
    # Parse the markdown to extract individual reviews
    # Reviews start with "- **author**:" or similar
    lines = content.split('\n')
    for line in lines:
        if line.startswith("- **") and "**: " in line:
            author_part = line.split("**: ")[0]
            text_part = line.split("**: ", 1)[1].strip().strip('"')
            author = author_part.replace("- **", "").replace("**", "").strip()
            
            items.append({
                "cleaned_text": text_part,
                "original_text": text_part,
                "author": author,
                "source_platform": "reddit_threads",
                "app_referenced": "Google Photos",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "post_id": "1qbdo8i",
                "url": "https://www.reddit.com/r/GooglePixel/comments/1qbdo8i/google_photos_removing_search_and_replacing_it/"
            })
            
    logger.info(f"Parsed {len(items)} reviews from markdown.")
    
    # 1. Chunking
    chunker = SemanticChunker(chunk_size=512)
    chunks = chunker.chunk_batch(
        items=items,
        text_field="cleaned_text",
        metadata_fields=["source_platform", "url", "post_id", "author", "timestamp", "app_referenced"]
    )
    
    # 2. Embedding
    embedder = BGEEmbedder()
    embedded_chunks = embedder.embed_chunks(chunks)
    
    # 3. ChromaDB
    chroma_store = ChromaStore()
    upserted_count = chroma_store.upsert_chunks(embedded_chunks, namespace="reddit_threads")
    logger.info(f"Upserted {upserted_count} vectors to ChromaDB (reddit_threads).")
    
    # 4. SQLite DB
    db_engine = get_engine()
    create_tables(db_engine)
    repo = MetadataRepository(db_engine)
    
    enricher = MetadataEnricher()
    ner = NERTagger()
    
    db_chunks = []
    for item in embedded_chunks:
        c = item["chunk"]
        meta = c.metadata.copy()
        
        meta = enricher.enrich(c.text, meta)
        ner_data = ner.extract_entities(c.text)
        
        db_chunks.append({
            "chunk_id": str(c.chunk_id),
            "vector_id": str(c.chunk_id),
            "source_platform": meta.get("source_platform", "reddit_threads"),
            "original_text": c.text,
            "chunk_text": c.text,
            "app_referenced": meta.get("app_referenced", "Google Photos"),
            "author_id": meta.get("author", "unknown"),
            "memory_anchors": ner_data.get("memory_anchors", {}),
            "forgotten_metadata": ner_data.get("forgotten_metadata", {}),
            "search_strategy": ner_data.get("inferred_search_strategy", "keyword_unknown"),
            "frustration_level": meta.get("frustration_level", "low"),
            "taxonomy_label": meta.get("taxonomy_label", "retrieval_failure"),
            "sentiment_score": meta.get("sentiment_score", 0.0),
            "crawled_at": datetime.now(timezone.utc),
        })
        
    inserted_count = repo.bulk_insert_chunks(db_chunks)
    logger.info(f"Inserted {inserted_count} chunks into SQLite.")

if __name__ == "__main__":
    ingest_filtered_reviews()
