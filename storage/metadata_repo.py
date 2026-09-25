"""
PostgreSQL metadata repository for the Discovery Engine.

Provides CRUD operations for the feedback_chunks table, including
bulk insert, filtered queries, and aggregation helpers.

Usage:
    from storage.metadata_repo import MetadataRepository
    repo = MetadataRepository()
    repo.bulk_insert_chunks(chunks)
    results = repo.get_chunks_by_platform("reddit")
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from storage.models import FeedbackChunk, get_engine, get_session_factory

logger = logging.getLogger(__name__)


class MetadataRepository:
    """
    Repository pattern for FeedbackChunk metadata operations.

    Encapsulates all database access so the rest of the application
    doesn't need to know about SQLAlchemy internals.
    """

    def __init__(self, engine=None):
        """
        Initialize the repository.

        Args:
            engine: SQLAlchemy engine. Uses default if None.
        """
        self._engine = engine or get_engine()
        self._session_factory = get_session_factory(self._engine)

    def _get_session(self) -> Session:
        """Create a new database session."""
        return self._session_factory()

    def insert_chunk(
        self,
        chunk_id: str,
        vector_id: str,
        source_platform: str,
        original_text: str,
        chunk_text: str,
        crawled_at: datetime,
        source_url: Optional[str] = None,
        author_id: Optional[str] = None,
        app_referenced: Optional[str] = None,
        memory_anchors: Optional[dict] = None,
        forgotten_metadata: Optional[dict] = None,
        search_strategy: Optional[str] = None,
        frustration_level: Optional[str] = None,
        taxonomy_label: Optional[str] = None,
        sentiment_score: Optional[float] = None,
    ) -> FeedbackChunk:
        """
        Insert a single feedback chunk into the database.

        The author_id is automatically SHA-256 hashed for PII protection.
        """
        # Hash author ID for PII protection
        hashed_author = None
        if author_id:
            hashed_author = hashlib.sha256(
                author_id.encode("utf-8")
            ).hexdigest()[:32]

        record = FeedbackChunk(
            chunk_id=str(chunk_id),
            vector_id=vector_id,
            source_platform=source_platform,
            source_url=source_url,
            author_id=hashed_author,
            original_text=original_text,
            chunk_text=chunk_text,
            app_referenced=app_referenced,
            memory_anchors=memory_anchors,
            forgotten_metadata=forgotten_metadata,
            search_strategy=search_strategy,
            frustration_level=frustration_level,
            taxonomy_label=taxonomy_label,
            sentiment_score=sentiment_score,
            crawled_at=crawled_at,
        )

        with self._get_session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def bulk_insert_chunks(self, chunks: list[dict]) -> int:
        """
        Bulk insert multiple feedback chunks.

        Args:
            chunks: List of dicts with FeedbackChunk fields

        Returns:
            Number of chunks inserted
        """
        records = []
        for c in chunks:
            # Hash author ID
            author_id = c.get("author_id")
            hashed_author = None
            if author_id:
                hashed_author = hashlib.sha256(
                    author_id.encode("utf-8")
                ).hexdigest()[:32]

            records.append(FeedbackChunk(
                chunk_id=str(c["chunk_id"]),
                vector_id=str(c.get("vector_id", c["chunk_id"])),
                source_platform=c["source_platform"],
                source_url=c.get("source_url"),
                author_id=hashed_author,
                original_text=c["original_text"],
                chunk_text=c["chunk_text"],
                app_referenced=c.get("app_referenced"),
                memory_anchors=c.get("memory_anchors"),
                forgotten_metadata=c.get("forgotten_metadata"),
                search_strategy=c.get("search_strategy"),
                frustration_level=c.get("frustration_level"),
                taxonomy_label=c.get("taxonomy_label"),
                sentiment_score=c.get("sentiment_score"),
                crawled_at=c.get(
                    "crawled_at", datetime.now(timezone.utc)
                ),
            ))

        with self._get_session() as session:
            session.add_all(records)
            session.commit()

        logger.info("Bulk inserted %d chunks", len(records))
        return len(records)

    def get_chunk_by_id(self, chunk_id: str) -> Optional[FeedbackChunk]:
        """Fetch a single chunk by its ID."""
        with self._get_session() as session:
            return session.get(FeedbackChunk, uuid.UUID(chunk_id))

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[FeedbackChunk]:
        """Fetch multiple chunks by their IDs."""
        uuids = [uuid.UUID(cid) for cid in chunk_ids]
        with self._get_session() as session:
            stmt = select(FeedbackChunk).where(
                FeedbackChunk.chunk_id.in_(uuids)
            )
            return list(session.scalars(stmt).all())

    def get_chunks_by_platform(
        self,
        platform: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeedbackChunk]:
        """Fetch chunks filtered by source platform."""
        with self._get_session() as session:
            stmt = (
                select(FeedbackChunk)
                .where(FeedbackChunk.source_platform == platform)
                .order_by(FeedbackChunk.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(session.scalars(stmt).all())

    def get_chunks_by_taxonomy(
        self,
        taxonomy: str,
        limit: int = 100,
    ) -> list[FeedbackChunk]:
        """Fetch chunks filtered by taxonomy label."""
        with self._get_session() as session:
            stmt = (
                select(FeedbackChunk)
                .where(FeedbackChunk.taxonomy_label == taxonomy)
                .order_by(FeedbackChunk.created_at.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def get_chunks_by_app(
        self,
        app_name: str,
        limit: int = 100,
    ) -> list[FeedbackChunk]:
        """Fetch chunks filtered by referenced app."""
        with self._get_session() as session:
            stmt = (
                select(FeedbackChunk)
                .where(FeedbackChunk.app_referenced == app_name)
                .order_by(FeedbackChunk.created_at.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def get_stats(self) -> dict:
        """Get corpus statistics: total chunks, per-platform counts, etc."""
        with self._get_session() as session:
            total = session.scalar(
                select(func.count()).select_from(FeedbackChunk)
            )
            platform_counts = session.execute(
                select(
                    FeedbackChunk.source_platform,
                    func.count().label("count"),
                )
                .group_by(FeedbackChunk.source_platform)
            ).all()
            taxonomy_counts = session.execute(
                select(
                    FeedbackChunk.taxonomy_label,
                    func.count().label("count"),
                )
                .where(FeedbackChunk.taxonomy_label.isnot(None))
                .group_by(FeedbackChunk.taxonomy_label)
            ).all()
            frustration_counts = session.execute(
                select(
                    FeedbackChunk.frustration_level,
                    func.count().label("count"),
                )
                .where(FeedbackChunk.frustration_level.isnot(None))
                .group_by(FeedbackChunk.frustration_level)
            ).all()

        return {
            "total_chunks": total or 0,
            "by_platform": {row[0]: row[1] for row in platform_counts},
            "by_taxonomy": {row[0]: row[1] for row in taxonomy_counts},
            "by_frustration": {row[0]: row[1] for row in frustration_counts},
        }
