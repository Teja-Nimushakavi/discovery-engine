"""
Script to ingest raw JSONL data from all platforms into ChromaDB.
"""
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from processing.chunking.chunker import SemanticChunker
from embeddings.bge_embedder import BGEEmbedder
from storage.chroma_store import ChromaStore
from config.settings import PINECONE_NAMESPACES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_file(data_file: Path, chunker: SemanticChunker, embedder: BGEEmbedder, store: ChromaStore):
    # Infer namespace from the parent directory name
    namespace = data_file.parent.name
    if namespace not in PINECONE_NAMESPACES:
        logger.warning(f"Namespace '{namespace}' not in PINECONE_NAMESPACES. Proceeding anyway.")

    logger.info(f"Reading data from {data_file}...")
    items = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    logger.info(f"Loaded {len(items)} items from {data_file}")
    if not items:
        return

    # Standardize the text field
    for item in items:
        # YouTube returns 'review_text', Apple returns 'review_text', Support Forums returns 'body'
        # Fallback cascade to find the text content
        if 'cleaned_text' not in item:
            item['cleaned_text'] = item.get('cleaned_text') or item.get('body') or item.get('review_text') or item.get('text') or ''

    # 1. Chunking
    logger.info(f"Chunking text for {namespace}...")
    chunks = chunker.chunk_batch(
        items=items,
        text_field="cleaned_text",
        metadata_fields=["source_platform", "url", "post_id", "author", "timestamp", "score", "app_referenced"]
    )
    
    logger.info(f"Generated {len(chunks)} chunks.")

    if not chunks:
        logger.warning(f"No chunks generated for {data_file}.")
        return

    # 2. Embedding
    logger.info("Generating embeddings...")
    embedded_chunks = embedder.embed_chunks(chunks)
    logger.info(f"Successfully embedded {len(embedded_chunks)} chunks.")

    # 3. Upserting
    logger.info(f"Upserting to ChromaDB namespace: {namespace}...")
    upserted_count = store.upsert_chunks(embedded_chunks, namespace=namespace)
    logger.info(f"Successfully upserted {upserted_count} vectors to {namespace}.")


def main():
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        logger.error(f"Raw data directory not found: {raw_dir}")
        sys.exit(1)

    logger.info("Initializing components...")
    chunker = SemanticChunker()
    embedder = BGEEmbedder()
    store = ChromaStore()

    # Find all JSONL files in all subdirectories of data/raw
    jsonl_files = list(raw_dir.glob("*/*.jsonl"))
    
    if not jsonl_files:
        logger.warning("No JSONL files found in data/raw/*/")
        sys.exit(0)
        
    for data_file in jsonl_files:
        logger.info(f"=== Processing {data_file.name} ===")
        try:
            process_file(data_file, chunker, embedder, store)
        except Exception as e:
            logger.error(f"Failed to process {data_file}: {e}")

    logger.info("Done! All files processed.")
    stats = store.get_stats()
    logger.info(f"ChromaDB Final Stats: {stats}")

if __name__ == "__main__":
    main()
