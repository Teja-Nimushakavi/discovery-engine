import logging
import os
import sys
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from embeddings.bge_embedder import BGEEmbedder
from processing.chunking.chunker import SemanticChunker
from processing.cleaning.cleaner import TextCleaner
from processing.enrichment.enricher import MetadataEnricher
from processing.enrichment.ner import NERTagger
from rag.engine import RAGEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# --- Mock Vector Store for Local Test ---
class MockPineconeStore:
    def __init__(self, embedded_chunks):
        self.embedded_chunks = embedded_chunks
        
    def search_across_namespaces(self, query_vector, top_k, namespaces=None):
        logger.info("MockPineconeStore: Returning all chunks without vector similarity matching.")
        # Just return the chunks with a fake score
        matches = []
        for i, c in enumerate(self.embedded_chunks):
            matches.append({
                "id": str(c["chunk"].chunk_id),
                "score": 0.9 - (i * 0.05),
                "metadata": {
                    "text": c["chunk"].text,
                    "source_platform": c["chunk"].metadata.get("source_platform", "unknown"),
                    "app_referenced": c["chunk"].metadata.get("app_referenced", "unknown")
                }
            })
        return {"test_namespace": matches[:top_k]}

def main():
    logger.info("=== Discovery Engine: Local Mocked Integration Test ===")
    
    import json
    
    # Check if --real flag is passed
    use_real_data = "--real" in sys.argv
    sample_reviews = []
    
    if use_real_data:
        logger.info("Loading real reviews from data/raw/google_play/real_data.jsonl...")
        try:
            with open("data/raw/google_play/real_data.jsonl", "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    sample_reviews.append({
                        "text": data.get("body", "") + " " + data.get("title", ""),
                        "source_platform": data.get("source_platform", "google_play"),
                        "app_referenced": "Google Photos", # Defaulting for this test
                        "author": data.get("author", "unknown"),
                        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    })
        except FileNotFoundError:
            logger.error("Real data file not found! Please run the scraper first.")
            sys.exit(1)
    else:
        logger.info("Using synthetic mock reviews...")
        # Sample Data
        sample_reviews = [
            {
                "text": "I have 50,000 photos and I can't find the one from my sister's wedding in 2019. I remember the blue dress she wore but Google Photos only lets me search by date, which I forgot.",
                "source_platform": "google_play",
                "app_referenced": "Google Photos",
                "author": "user123",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "text": "Why is it so hard to search for emotions? I want to find that really happy photo from the beach trip, but typing 'happy' just shows me pictures of signs with the word happy on them. Apple photos needs to fix this.",
                "source_platform": "app_store",
                "app_referenced": "iCloud Photos",
                "author": "user456",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

    logger.info("1. Cleaning sample data...")
    cleaner = TextCleaner()
    cleaned_items = []
    for item in sample_reviews:
        res = cleaner.clean(item["text"])
        if not res["was_filtered"]:
            item["cleaned_text"] = res["cleaned_text"]
            cleaned_items.append(item)

    logger.info("2. Chunking sample data...")
    chunker = SemanticChunker(chunk_size=512)
    chunks = chunker.chunk_batch(
        cleaned_items, 
        metadata_fields=["source_platform", "app_referenced", "author", "timestamp"]
    )

    logger.info("3. Embedding chunks (BGE)...")
    embedder = BGEEmbedder()
    embedded_chunks = embedder.embed_chunks(chunks)

    logger.info("4. Enriching Metadata (spaCy NER)...")
    enricher = MetadataEnricher()
    ner = NERTagger()
    
    for item in embedded_chunks:
        c = item["chunk"]
        meta = enricher.enrich(c.text, c.metadata.copy())
        ner_data = ner.extract_entities(c.text)
        logger.info(f"NER Extracted for chunk: {ner_data}")
        # Attach back to chunk for RAG
        c.metadata = meta

    logger.info("5. Testing RAG Engine (with Mock Vector Store)...")
    mock_store = MockPineconeStore(embedded_chunks)
    rag = RAGEngine(embedder=embedder, vector_store=mock_store)
    
    question = "What are users currently complaining about regarding the photo search functionality?"
    logger.info(f"Question: {question}")
    
    result = rag.query(
        question=question,
        namespaces=["test_namespace"],
        top_k=5,
        discovery_key="search_complaints"
    )
    
    logger.info("=== RAG Response (from Groq) ===")
    output_path = "data/rag_output.txt"
    os.makedirs("data", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["answer"])
    
    logger.info(f"Response written successfully to {output_path}")
    
    logger.info("Local integration test complete.")

if __name__ == "__main__":
    main()
