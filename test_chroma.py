import logging
from config.settings import PINECONE_NAMESPACES
from storage.chroma_store import ChromaStore
from embeddings.bge_embedder import BGEEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    store = ChromaStore()
    stats = store.get_stats()
    print("Stats:", stats)
    
    print("Namespaces in config:", PINECONE_NAMESPACES)
    
    embedder = BGEEmbedder()
    query_vector = embedder.embed_query("What do users forget?")
    
    print(f"Searching google_play...")
    results = store.search(query_vector.tolist(), top_k=5, namespace="google_play")
    print("google_play results:", len(results))
    if results:
        print("Sample:", results[0])

    print("Searching across all...")
    all_res = store.search_across_namespaces(query_vector.tolist(), top_k=5)
    total = sum(len(r) for r in all_res.values())
    print("Total results across all namespaces:", total)

if __name__ == "__main__":
    main()
