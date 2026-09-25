-- ============================================================================
-- Discovery Engine — Initial Schema Migration
-- ============================================================================
-- Creates the feedback_chunks table and related indexes.
-- Run with: psql -U discovery -d discovery_engine -f 001_initial_schema.sql
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Main table ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS feedback_chunks (
    chunk_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vector_id         VARCHAR(64) NOT NULL,
    source_platform   VARCHAR(32) NOT NULL,
    source_url        TEXT,
    author_id         VARCHAR(128),
    original_text     TEXT NOT NULL,
    chunk_text        TEXT NOT NULL,
    app_referenced    VARCHAR(64),
    memory_anchors    JSONB,
    forgotten_metadata JSONB,
    search_strategy   VARCHAR(64),
    frustration_level VARCHAR(16),
    taxonomy_label    VARCHAR(64),
    sentiment_score   FLOAT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    crawled_at        TIMESTAMP WITH TIME ZONE NOT NULL
);

-- ── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_source_platform
    ON feedback_chunks(source_platform);

CREATE INDEX IF NOT EXISTS idx_taxonomy_label
    ON feedback_chunks(taxonomy_label);

CREATE INDEX IF NOT EXISTS idx_app_referenced
    ON feedback_chunks(app_referenced);

CREATE INDEX IF NOT EXISTS idx_frustration_level
    ON feedback_chunks(frustration_level);

CREATE INDEX IF NOT EXISTS idx_search_strategy
    ON feedback_chunks(search_strategy);

CREATE INDEX IF NOT EXISTS idx_created_at
    ON feedback_chunks(created_at DESC);

-- GIN index on JSONB columns for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_memory_anchors_gin
    ON feedback_chunks USING GIN (memory_anchors);

CREATE INDEX IF NOT EXISTS idx_forgotten_metadata_gin
    ON feedback_chunks USING GIN (forgotten_metadata);

-- ── Comments ────────────────────────────────────────────────────────────────

COMMENT ON TABLE feedback_chunks IS
    'Processed user feedback chunks with embeddings metadata and enrichment';

COMMENT ON COLUMN feedback_chunks.vector_id IS
    'Reference to the corresponding vector in Pinecone';

COMMENT ON COLUMN feedback_chunks.memory_anchors IS
    'JSONB: what users DO remember (emotions, people, events, clothing)';

COMMENT ON COLUMN feedback_chunks.forgotten_metadata IS
    'JSONB: what users have FORGOTTEN (exact dates, locations, album names)';

COMMENT ON COLUMN feedback_chunks.author_id IS
    'SHA-256 hashed author identifier for PII protection';
