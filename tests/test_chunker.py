import pytest
from processing.chunking.chunker import SemanticChunker, Chunk

def test_chunker_basic():
    chunker = SemanticChunker(chunk_size=50, chunk_overlap=10)
    text = "This is a simple sentence. This is another one. And a third one."
    chunks = chunker.chunk_text(text)
    
    # Should fit in one chunk since chunk_size is 50 tokens (~200 chars)
    assert len(chunks) == 1
    assert chunks[0].text == text

def test_chunker_long_text():
    chunker = SemanticChunker(chunk_size=10, chunk_overlap=2)
    # Each ~4 chars is 1 token. "A short sentence. " is ~18 chars = 4 tokens.
    text = "A short sentence. Another sentence here. Third sentence follows. Fourth one now."
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1
    # Check that metadata can be attached
    meta_chunks = chunker.chunk_text(text, metadata={"source": "test"})
    assert meta_chunks[0].metadata["source"] == "test"

def test_chunk_batch():
    chunker = SemanticChunker(chunk_size=50, chunk_overlap=10)
    items = [
        {"cleaned_text": "First item text.", "source_platform": "reddit"},
        {"cleaned_text": "Second item text.", "source_platform": "app_store"}
    ]
    chunks = chunker.chunk_batch(items, metadata_fields=["source_platform"])
    
    assert len(chunks) == 2
    assert chunks[0].metadata["source_platform"] == "reddit"
    assert chunks[1].metadata["source_platform"] == "app_store"
