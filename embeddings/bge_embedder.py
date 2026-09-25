"""
BGE Embedding Pipeline for the Discovery Engine.

Generates 1024-dimensional embeddings using the BGE-large-en-v1.5 model
from BAAI via the sentence-transformers library.

Features:
    - Batch embedding with configurable batch size
    - L2 normalization (recommended by BGE authors)
    - Automatic GPU/CPU detection
    - Throughput benchmarking

Usage:
    from embeddings.bge_embedder import BGEEmbedder
    embedder = BGEEmbedder()
    vectors = embedder.embed_texts(["Hello world", "Photo search"])
"""

import logging
import time
from typing import Optional

import numpy as np

from config.settings import BGE_BATCH_SIZE, BGE_MAX_SEQ_LENGTH, BGE_MODEL_NAME

logger = logging.getLogger(__name__)


class BGEEmbedder:
    """
    Batch embedding pipeline using BGE-large-en-v1.5.

    Produces 1024-dimensional vectors with L2 normalization for
    cosine similarity search in Pinecone.
    """

    def __init__(
        self,
        model_name: str = BGE_MODEL_NAME,
        batch_size: int = BGE_BATCH_SIZE,
        max_seq_length: int = BGE_MAX_SEQ_LENGTH,
        device: Optional[str] = None,
        normalize: bool = True,
    ):
        """
        Initialize the BGE embedder.

        Args:
            model_name: HuggingFace model ID for the BGE model
            batch_size: Number of texts to embed per batch
            max_seq_length: Maximum token sequence length (truncation limit)
            device: Force device ('cuda', 'cpu', or 'mps'). Auto-detects if None.
            normalize: Apply L2 normalization to output vectors
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.normalize = normalize
        self._model = None
        self._device = device

    @property
    def model(self):
        """Lazy-load the model on first use."""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def dimensions(self) -> int:
        """Return the embedding dimensionality."""
        return 1024  # BGE-large-en-v1.5

    def _load_model(self):
        """Load the sentence-transformers model."""
        from sentence_transformers import SentenceTransformer

        logger.info("Loading BGE model: %s ...", self.model_name)
        start = time.time()

        self._model = SentenceTransformer(
            self.model_name,
            device=self._device,
        )
        self._model.max_seq_length = self.max_seq_length

        elapsed = time.time() - start
        device = self._model.device
        logger.info(
            "Model loaded in %.1fs on device: %s", elapsed, device
        )

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed a list of texts into vectors.

        BGE recommends prepending "Represent this sentence: " for
        retrieval tasks. We add this prefix automatically.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of shape (len(texts), 1024)
        """
        if not texts:
            return np.array([])

        # BGE instruction prefix for retrieval
        prefixed = [f"Represent this sentence: {t}" for t in texts]

        logger.info(
            "Embedding %d texts (batch_size=%d) ...",
            len(prefixed),
            self.batch_size,
        )
        start = time.time()

        embeddings = self.model.encode(
            prefixed,
            batch_size=self.batch_size,
            show_progress_bar=len(prefixed) > 100,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )

        elapsed = time.time() - start
        throughput = len(texts) / elapsed if elapsed > 0 else 0
        logger.info(
            "Embedded %d texts in %.2fs (%.1f texts/sec)",
            len(texts),
            elapsed,
            throughput,
        )

        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a single query string for retrieval.

        BGE recommends a different prefix for queries vs. documents.

        Args:
            query: The search query to embed

        Returns:
            1D numpy array of shape (1024,)
        """
        prefixed = f"Represent this sentence for searching relevant passages: {query}"

        embedding = self.model.encode(
            [prefixed],
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )

        return embedding[0]

    def embed_chunks(self, chunks: list) -> list[dict]:
        """
        Embed a list of Chunk objects and return them with vectors attached.

        Args:
            chunks: List of Chunk objects (from processing.chunking.chunker)

        Returns:
            List of dicts: {"chunk": Chunk, "vector": np.ndarray}
        """
        texts = [c.text for c in chunks]
        vectors = self.embed_texts(texts)

        results = []
        for chunk, vector in zip(chunks, vectors):
            results.append({
                "chunk": chunk,
                "vector": vector,
            })

        return results

    def benchmark(self, n_samples: int = 100) -> dict:
        """
        Run a throughput benchmark with synthetic data.

        Args:
            n_samples: Number of sample texts to embed

        Returns:
            Dictionary with benchmark results
        """
        sample_texts = [
            f"This is sample text number {i} for benchmarking the BGE "
            f"embedding pipeline. It contains enough words to simulate "
            f"a typical user review or forum post about photo search."
            for i in range(n_samples)
        ]

        start = time.time()
        embeddings = self.embed_texts(sample_texts)
        elapsed = time.time() - start

        return {
            "model": self.model_name,
            "device": str(self.model.device),
            "n_samples": n_samples,
            "batch_size": self.batch_size,
            "dimensions": embeddings.shape[1] if len(embeddings.shape) > 1 else 0,
            "total_time_seconds": round(elapsed, 3),
            "throughput_texts_per_sec": round(n_samples / elapsed, 1),
            "avg_ms_per_text": round((elapsed / n_samples) * 1000, 2),
        }
