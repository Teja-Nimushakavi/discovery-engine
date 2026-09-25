"""
Semantic chunking pipeline for the Discovery Engine.

Splits cleaned text into overlapping semantic chunks optimized for
BGE embedding (512 tokens, 64 token overlap, sentence-aware splitting).

Each chunk preserves source metadata for downstream retrieval.

Usage:
    from processing.chunking.chunker import SemanticChunker
    chunker = SemanticChunker()
    chunks = chunker.chunk_text("Long text...", metadata={"source": "reddit"})
"""

import logging
import uuid
from dataclasses import dataclass, field

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a single text chunk with metadata."""

    chunk_id: str
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0
    total_chunks: int = 0
    token_count: int = 0
    is_short_chunk: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "token_count": self.token_count,
            "is_short_chunk": self.is_short_chunk,
        }


class SemanticChunker:
    """
    Sentence-aware recursive text chunker.

    Splits text at sentence boundaries with configurable chunk size
    and overlap. Designed to work with BGE embeddings (512 token context).

    Falls back to character-level splitting only when sentences
    exceed the chunk size limit.
    """

    # Sentence-ending patterns (ordered by preference)
    SENTENCE_ENDINGS = (". ", "! ", "? ", ".\n", "!\n", "?\n")

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
        min_chunk_size: int = 50,
    ):
        """
        Initialize the chunker.

        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Number of overlap tokens between consecutive chunks
            min_chunk_size: Minimum chunk size (tokens) to avoid tiny fragments
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        """
        Split text into semantic chunks with overlap.

        Args:
            text: Cleaned text to chunk
            metadata: Source metadata to attach to each chunk

        Returns:
            List of Chunk objects
        """
        metadata = metadata or {}

        if not text or not text.strip():
            return []

        # Estimate token count (rough: 1 token ≈ 4 characters for English)
        estimated_tokens = self._estimate_tokens(text)

        # If text fits in a single chunk, return it as-is
        if estimated_tokens <= self.chunk_size:
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                text=text.strip(),
                metadata=metadata.copy(),
                chunk_index=0,
                total_chunks=1,
                token_count=estimated_tokens,
                is_short_chunk=estimated_tokens < self.min_chunk_size,
            )
            return [chunk]

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        # Build chunks from sentences with overlap
        chunks = self._build_chunks_from_sentences(sentences, metadata)

        return chunks

    def chunk_batch(
        self,
        items: list[dict],
        text_field: str = "cleaned_text",
        metadata_fields: list[str] | None = None,
    ) -> list[Chunk]:
        """
        Chunk a batch of items (e.g., cleaned reviews or posts).

        Args:
            items: List of dictionaries containing text and metadata
            text_field: Key in each dict that contains the text to chunk
            metadata_fields: Keys to copy from each dict into chunk metadata

        Returns:
            Flat list of all chunks from all items
        """
        metadata_fields = metadata_fields or [
            "source_platform",
            "source_url",
            "app_referenced",
            "post_id",
            "review_id",
            "author",
            "timestamp",
        ]

        all_chunks = []
        for item in items:
            text = item.get(text_field, "")
            if not text:
                continue

            # Build metadata from specified fields
            metadata = {
                k: item[k] for k in metadata_fields if k in item
            }

            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)

        logger.info(
            "Chunked %d items into %d chunks", len(items), len(all_chunks)
        )
        return all_chunks

    # ─── Private methods ───────────────────────────────────────────────

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using punctuation-based heuristics.

        Handles common edge cases: abbreviations, decimal numbers,
        URLs, and ellipses.
        """
        sentences = []
        current = ""

        # Simple sentence splitter — handles most user-generated content
        i = 0
        while i < len(text):
            current += text[i]

            # Check if we hit a sentence ending
            if text[i] in ".!?" and i + 1 < len(text):
                next_char = text[i + 1]

                # It's a sentence break if followed by space+uppercase or newline
                if next_char in " \n":
                    # Check for abbreviations (e.g., "Mr.", "etc.")
                    last_word = current.rstrip(".!?").split()[-1] if current.rstrip(".!?").split() else ""
                    is_abbreviation = (
                        len(last_word) <= 3
                        and last_word[0].isupper()
                        and text[i] == "."
                    ) if last_word else False

                    if not is_abbreviation:
                        sentences.append(current.strip())
                        current = ""

            elif text[i] == "\n" and current.strip():
                # Newline can also be a sentence boundary
                if len(current.strip()) > 10:  # Avoid splitting on short fragments
                    sentences.append(current.strip())
                    current = ""

            i += 1

        # Add remaining text
        if current.strip():
            sentences.append(current.strip())

        return sentences

    def _build_chunks_from_sentences(
        self, sentences: list[str], metadata: dict
    ) -> list[Chunk]:
        """
        Build overlapping chunks from a list of sentences.

        Greedily adds sentences to the current chunk until the token
        limit is reached, then starts a new chunk with overlap from
        the end of the previous chunk.
        """
        chunks = []
        current_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)

            # If a single sentence exceeds chunk size, force-split it
            if sentence_tokens > self.chunk_size:
                # Flush current chunk first
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append(chunk_text)
                    current_sentences = []
                    current_tokens = 0

                # Force-split the long sentence
                sub_chunks = self._force_split(sentence)
                chunks.extend(sub_chunks)
                continue

            # Check if adding this sentence exceeds the limit
            if current_tokens + sentence_tokens > self.chunk_size:
                # Flush current chunk
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append(chunk_text)

                # Start new chunk with overlap from previous
                overlap_sentences = self._get_overlap_sentences(
                    current_sentences
                )
                current_sentences = overlap_sentences + [sentence]
                current_tokens = sum(
                    self._estimate_tokens(s) for s in current_sentences
                )
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens

        # Flush remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(chunk_text)

        # Convert to Chunk objects
        total = len(chunks)
        result = []
        for i, text in enumerate(chunks):
            token_count = self._estimate_tokens(text)
            result.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    text=text,
                    metadata=metadata.copy(),
                    chunk_index=i,
                    total_chunks=total,
                    token_count=token_count,
                    is_short_chunk=token_count < self.min_chunk_size,
                )
            )

        return result

    def _get_overlap_sentences(
        self, sentences: list[str]
    ) -> list[str]:
        """
        Get sentences from the end of the list that fit within the overlap budget.
        """
        overlap: list[str] = []
        tokens = 0

        for sentence in reversed(sentences):
            sentence_tokens = self._estimate_tokens(sentence)
            if tokens + sentence_tokens > self.chunk_overlap:
                break
            overlap.insert(0, sentence)
            tokens += sentence_tokens

        return overlap

    def _force_split(self, text: str) -> list[str]:
        """
        Force-split text that exceeds chunk size at word boundaries.
        """
        words = text.split()
        chunks = []
        current_words: list[str] = []
        current_tokens = 0

        for word in words:
            word_tokens = self._estimate_tokens(word)
            if current_tokens + word_tokens > self.chunk_size and current_words:
                chunks.append(" ".join(current_words))
                current_words = []
                current_tokens = 0
            current_words.append(word)
            current_tokens += word_tokens

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using a simple heuristic.

        Rule of thumb: ~4 characters per token for English text.
        This avoids loading a full tokenizer for estimation.
        """
        return max(1, len(text) // 4)
