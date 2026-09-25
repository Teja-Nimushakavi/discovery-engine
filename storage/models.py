"""
PostgreSQL metadata models for the Discovery Engine.

SQLAlchemy ORM models for the feedback_chunks table and related
metadata storage. Provides a structured store alongside the
Pinecone vector database.

Usage:
    from storage.models import FeedbackChunk, get_engine, create_tables
    engine = get_engine()
    create_tables(engine)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Index,
    String,
    Text,
    JSON,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
import os

# Fallback to SQLite if Postgres URL is not correctly configured
POSTGRES_URL = os.getenv("DATABASE_URL", "sqlite:///./discovery_engine.db")

class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class FeedbackChunk(Base):
    """
    Represents a single processed chunk of user feedback.

    Maps to the feedback_chunks table. Each row stores
    the chunk text, its vector ID (linking to Pinecone), and enriched
    metadata for filtering and analysis.
    """

    __tablename__ = "feedback_chunks"

    chunk_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique identifier for this chunk",
    )
    vector_id = Column(
        String(64),
        nullable=False,
        doc="Reference to the vector in Pinecone",
    )
    source_platform = Column(
        String(32),
        nullable=False,
        doc="Origin platform: reddit, google_play, app_store, support_forums, youtube",
    )
    source_url = Column(
        Text,
        nullable=True,
        doc="URL of the original source content",
    )
    author_id = Column(
        String(128),
        nullable=True,
        doc="SHA-256 hashed author identifier (PII protection)",
    )
    original_text = Column(
        Text,
        nullable=False,
        doc="Original unprocessed text (preserved for citation)",
    )
    chunk_text = Column(
        Text,
        nullable=False,
        doc="Cleaned and chunked text used for embedding",
    )
    app_referenced = Column(
        String(64),
        nullable=True,
        doc="Photo app being discussed (Google Photos, iCloud, etc.)",
    )
    memory_anchors = Column(
        JSON,
        nullable=True,
        doc="What users DO remember: emotions, people, events, clothing, etc.",
    )
    forgotten_metadata = Column(
        JSON,
        nullable=True,
        doc="What users have FORGOTTEN: exact dates, locations, album names",
    )
    search_strategy = Column(
        String(64),
        nullable=True,
        doc="How the user tried to search: visual_attribute, temporal, people, event",
    )
    frustration_level = Column(
        String(16),
        nullable=True,
        doc="Sentiment-derived frustration level: low, medium, high",
    )
    taxonomy_label = Column(
        String(64),
        nullable=True,
        doc="Content classification: retrieval_failure, feature_request, workaround, praise",
    )
    sentiment_score = Column(
        Float,
        nullable=True,
        doc="Numerical sentiment score (-1.0 to 1.0)",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        doc="When this record was created",
    )
    crawled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the source content was originally crawled",
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_source_platform", "source_platform"),
        Index("idx_taxonomy_label", "taxonomy_label"),
        Index("idx_app_referenced", "app_referenced"),
        Index("idx_frustration_level", "frustration_level"),
        Index("idx_search_strategy", "search_strategy"),
    )

    def __repr__(self) -> str:
        return (
            f"<FeedbackChunk(chunk_id={self.chunk_id}, "
            f"source={self.source_platform}, "
            f"taxonomy={self.taxonomy_label})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": str(self.chunk_id),
            "vector_id": self.vector_id,
            "source_platform": self.source_platform,
            "source_url": self.source_url,
            "author_id": self.author_id,
            "original_text": self.original_text,
            "chunk_text": self.chunk_text,
            "app_referenced": self.app_referenced,
            "memory_anchors": self.memory_anchors,
            "forgotten_metadata": self.forgotten_metadata,
            "search_strategy": self.search_strategy,
            "frustration_level": self.frustration_level,
            "taxonomy_label": self.taxonomy_label,
            "sentiment_score": self.sentiment_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
        }


# ─── Database Helpers ────────────────────────────────────────────────────────


def get_engine(url: str = POSTGRES_URL, echo: bool = False):
    """
    Create a SQLAlchemy engine.

    Args:
        url: PostgreSQL connection URL
        echo: If True, log all SQL statements

    Returns:
        SQLAlchemy Engine instance
    """
    return create_engine(url, echo=echo, pool_pre_ping=True)


def get_session_factory(engine=None):
    """
    Create a session factory bound to the given engine.

    Args:
        engine: SQLAlchemy Engine. Uses default if None.

    Returns:
        sessionmaker instance
    """
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)


def create_tables(engine=None):
    """
    Create all tables defined in the ORM models.

    Args:
        engine: SQLAlchemy Engine. Uses default if None.
    """
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def drop_tables(engine=None):
    """
    Drop all tables (use with caution!).

    Args:
        engine: SQLAlchemy Engine. Uses default if None.
    """
    if engine is None:
        engine = get_engine()
    Base.metadata.drop_all(engine)
