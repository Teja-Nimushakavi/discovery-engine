"""
Pinecone vector store for the Discovery Engine.

Manages the Pinecone index for storing and retrieving BGE embeddings.
Handles index creation, upsert, search, and namespace management.

Usage:
    from storage.pinecone_store import PineconeStore
    store = PineconeStore()
    store.upsert_vectors(vectors, namespace="reddit_threads")
    results = store.search("photo search query", top_k=20)
"""

import logging
import time
import uuid
from typing import Optional

from config.settings import (
    PINECONE_API_KEY,
    PINECONE_DIMENSIONS,
    PINECONE_INDEX_NAME,
    PINECONE_METRIC,
    PINECONE_NAMESPACES,
)

logger = logging.getLogger(__name__)


class PineconeStore:
    """
    Pinecone vector database client for the Discovery Engine.

    Wraps the Pinecone Python SDK to provide a clean interface for
    upserting embeddings and performing semantic similarity search.
    """

    def __init__(
        self,
        api_key: str = PINECONE_API_KEY,
        index_name: str = PINECONE_INDEX_NAME,
        metric: str = PINECONE_METRIC,
        dimensions: int = PINECONE_DIMENSIONS,
    ):
        """
        Initialize the Pinecone store.

        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            metric: Distance metric (cosine, dotproduct, euclidean)
            dimensions: Vector dimensionality (1024 for BGE-large)
        """
        self.api_key = api_key
        self.index_name = index_name
        self.metric = metric
        self.dimensions = dimensions
        self._pc = None
        self._index = None

    @property
    def client(self):
        """Lazy-initialize the Pinecone client."""
        if self._pc is None:
            self._connect()
        return self._pc

    @property
    def index(self):
        """Lazy-initialize the index connection."""
        if self._index is None:
            self._connect()
        return self._index

    def _connect(self):
        """Connect to Pinecone and get or create the index."""
        from pinecone import Pinecone, ServerlessSpec

        logger.info("Connecting to Pinecone...")
        self._pc = Pinecone(api_key=self.api_key)

        # Check if index exists
        existing_indexes = [idx.name for idx in self._pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(
                "Creating index '%s' (dims=%d, metric=%s)...",
                self.index_name,
                self.dimensions,
                self.metric,
            )
            self._pc.create_index(
                name=self.index_name,
                dimension=self.dimensions,
                metric=self.metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1",
                ),
            )
            # Wait for index to be ready
            self._wait_for_index()
        else:
            logger.info("Index '%s' already exists.", self.index_name)

        self._index = self._pc.Index(self.index_name)
        logger.info("Connected to Pinecone index: %s", self.index_name)

    def _wait_for_index(self, timeout: int = 120):
        """Wait until the index is ready for operations."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                desc = self._pc.describe_index(self.index_name)
                if desc.status.get("ready", False):
                    logger.info("Index '%s' is ready.", self.index_name)
                    return
            except Exception:
                pass
            time.sleep(2)
        raise TimeoutError(
            f"Index '{self.index_name}' not ready after {timeout}s"
        )

    def upsert_vectors(
        self,
        vectors: list[dict],
        namespace: str = "",
        batch_size: int = 100,
    ) -> int:
        """
        Upsert vectors into the Pinecone index.

        Args:
            vectors: List of dicts with keys:
                - "id": str (vector ID)
                - "values": list[float] (embedding vector)
                - "metadata": dict (optional metadata to store alongside)
            namespace: Pinecone namespace for organizing vectors
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

        upserted = 0
        for i in range(0, total, batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(
                vectors=batch,
                namespace=namespace,
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
        Upsert embedded chunks (from BGEEmbedder.embed_chunks) into Pinecone.

        Converts Chunk objects + vectors into the format expected by upsert_vectors.

        Args:
            embedded_chunks: List of {"chunk": Chunk, "vector": np.ndarray}
            namespace: Pinecone namespace

        Returns:
            Total number of vectors upserted
        """
        vectors = []
        for item in embedded_chunks:
            chunk = item["chunk"]
            vector = item["vector"]

            # Build metadata for filtering (Pinecone metadata)
            metadata = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text[:1000],  # Pinecone metadata size limit
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
            filter_dict: Pinecone metadata filter (e.g., {"source_platform": "reddit"})
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

        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict,
            include_metadata=include_metadata,
        )

        matches = []
        for match in results.get("matches", []):
            matches.append({
                "id": match["id"],
                "score": match["score"],
                "metadata": match.get("metadata", {}),
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

        Args:
            query_vector: Query embedding vector
            top_k: Number of results per namespace
            namespaces: List of namespaces to search. Defaults to all configured.
            filter_dict: Optional metadata filter

        Returns:
            Dictionary mapping namespace name to list of matches
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
        self.index.delete(ids=ids, namespace=namespace)
        logger.info("Deleted %d vectors from namespace='%s'", len(ids), namespace)

    def delete_namespace(self, namespace: str) -> None:
        """Delete all vectors in a namespace."""
        self.index.delete(delete_all=True, namespace=namespace)
        logger.info("Deleted all vectors in namespace='%s'", namespace)

    def get_stats(self) -> dict:
        """Get index statistics including per-namespace vector counts."""
        stats = self.index.describe_index_stats()
        return {
            "total_vector_count": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 0),
            "namespaces": {
                ns: info.get("vector_count", 0)
                for ns, info in stats.get("namespaces", {}).items()
            },
        }
