"""
ChromaDB vector store for the Discovery Engine.

Manages a local ChromaDB instance for storing and retrieving BGE embeddings.
Handles collection creation, upsert, search, and namespace management
(mapping namespaces to Chroma collections).

Usage:
    from storage.chroma_store import ChromaStore
    store = ChromaStore()
    store.upsert_vectors(vectors, namespace="reddit_threads")
    results = store.search([0.1, 0.2, ...], top_k=20, namespace="reddit_threads")
"""

import logging
import os
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from config.settings import (
    PINECONE_NAMESPACES,  # We will reuse this as a list of namespaces
)

logger = logging.getLogger(__name__)


class ChromaStore:
    """
    Chroma vector database client for the Discovery Engine.

    Provides a clean interface for upserting embeddings and performing
    semantic similarity search using a local database.
    """

    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """
        Initialize the Chroma store.

        Args:
            persist_directory: Path to store ChromaDB data locally.
        """
        self.persist_directory = persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        logger.info("Initializing ChromaDB client at %s", self.persist_directory)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

    def _get_or_create_collection(self, namespace: str):
        """Get or create a Chroma collection for the given namespace."""
        # Chroma collection names must be valid (no spaces, etc.)
        collection_name = namespace.replace(" ", "_").replace("-", "_")
        if not collection_name:
            collection_name = "default_namespace"
            
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"} # Use cosine similarity
        )

    def upsert_vectors(
        self,
        vectors: list[dict],
        namespace: str = "",
        batch_size: int = 100,
    ) -> int:
        """
        Upsert vectors into the Chroma collection.

        Args:
            vectors: List of dicts with keys:
                - "id": str (vector ID)
                - "values": list[float] (embedding vector)
                - "metadata": dict (optional metadata to store alongside)
            namespace: Collection namespace for organizing vectors
            batch_size: Number of vectors per upsert batch

        Returns:
            Total number of vectors upserted
        """
        if not vectors:
            return 0

        total = len(vectors)
        logger.info(
            "Upserting %d vectors to namespace='%s' (batch_size=%d)...",
            total,
            namespace,
            batch_size,
        )

        collection = self._get_or_create_collection(namespace)

        upserted = 0
        for i in range(0, total, batch_size):
            batch = vectors[i : i + batch_size]
            
            ids = [item["id"] for item in batch]
            embeddings = [item["values"] for item in batch]
            metadatas = [item.get("metadata", {}) for item in batch]
            
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            upserted += len(batch)
            logger.debug(
                "Upserted batch %d/%d (%d vectors)",
                i // batch_size + 1,
                (total + batch_size - 1) // batch_size,
                len(batch),
            )

        logger.info("Upserted %d vectors total.", upserted)
        return upserted

    def upsert_chunks(
        self,
        embedded_chunks: list[dict],
        namespace: str = "",
    ) -> int:
        """
        Upsert embedded chunks (from BGEEmbedder.embed_chunks) into ChromaDB.

        Args:
            embedded_chunks: List of {"chunk": Chunk, "vector": np.ndarray}
            namespace: Namespace to store chunks in

        Returns:
            Total number of vectors upserted
        """
        vectors = []
        for item in embedded_chunks:
            chunk = item["chunk"]
            vector = item["vector"]

            metadata = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text, 
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
            }
            # Copy source metadata fields
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value

            vectors.append({
                "id": chunk.chunk_id,
                "values": vector.tolist(),
                "metadata": metadata,
            })

        return self.upsert_vectors(vectors, namespace=namespace)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        namespace: str = "",
        filter_dict: Optional[dict] = None,
        include_metadata: bool = True,
    ) -> list[dict]:
        """
        Perform semantic similarity search.

        Args:
            query_vector: Query embedding vector (1024-dim)
            top_k: Number of results to return
            namespace: Namespace to search within
            filter_dict: Chroma metadata filter (e.g., {"source_platform": "reddit"})
            include_metadata: Whether to return stored metadata

        Returns:
            List of match dicts with keys: id, score, metadata
        """
        logger.debug(
            "Searching namespace='%s' with top_k=%d, filter=%s",
            namespace,
            top_k,
            filter_dict,
        )

        collection = self._get_or_create_collection(namespace)
        
        include = ["distances"]
        if include_metadata:
            include.append("metadatas")

        try:
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=filter_dict,
                include=include
            )
        except Exception as e:
            logger.error("Chroma query failed: %s", e)
            return []

        matches = []
        
        if results and results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0] * len(ids)
            metadatas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(ids)
            
            for i in range(len(ids)):
                # Chroma with cosine actually returns cosine distance (1 - cosine similarity)
                score = 1.0 - distances[i]
                
                matches.append({
                    "id": ids[i],
                    "score": score,
                    "metadata": metadatas[i],
                })

        logger.info(
            "Search returned %d matches (top score: %.4f)",
            len(matches),
            matches[0]["score"] if matches else 0,
        )
        return matches

    def search_across_namespaces(
        self,
        query_vector: list[float],
        top_k: int = 20,
        namespaces: Optional[list[str]] = None,
        filter_dict: Optional[dict] = None,
    ) -> dict[str, list[dict]]:
        """
        Search across multiple namespaces and return results per namespace.
        """
        namespaces = namespaces or PINECONE_NAMESPACES

        all_results = {}
        for ns in namespaces:
            try:
                results = self.search(
                    query_vector=query_vector,
                    top_k=top_k,
                    namespace=ns,
                    filter_dict=filter_dict,
                )
                all_results[ns] = results
            except Exception as e:
                logger.warning("Search failed for namespace '%s': %s", ns, e)
                all_results[ns] = []

        return all_results

    def delete_vectors(
        self,
        ids: list[str],
        namespace: str = "",
    ) -> None:
        """Delete vectors by their IDs."""
        collection = self._get_or_create_collection(namespace)
        collection.delete(ids=ids)
        logger.info("Deleted %d vectors from namespace='%s'", len(ids), namespace)

    def delete_namespace(self, namespace: str) -> None:
        """Delete all vectors in a namespace (deletes the collection)."""
        collection_name = namespace.replace(" ", "_").replace("-", "_")
        try:
            self.client.delete_collection(name=collection_name)
            logger.info("Deleted collection for namespace='%s'", namespace)
        except Exception as e:
            logger.warning("Failed to delete namespace '%s': %s", namespace, e)

    def get_stats(self) -> dict:
        """Get index statistics including per-namespace vector counts."""
        collections = self.client.list_collections()
        stats = {
            "namespaces": {}
        }
        total_vectors = 0
        
        for col in collections:
            count = col.count()
            stats["namespaces"][col.name] = count
            total_vectors += count
            
        stats["total_vector_count"] = total_vectors
        return stats
