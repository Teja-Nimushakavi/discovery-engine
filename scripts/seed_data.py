import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from storage.models import create_tables, get_engine, FeedbackChunk
from sqlalchemy.orm import Session

def seed():
    engine = get_engine()
    create_tables(engine)
    
    with Session(engine) as session:
        # Check if already seeded
        if session.query(FeedbackChunk).count() > 0:
            print("Database already seeded.")
            return

        print("Seeding database with sample data...")
        samples = [
            FeedbackChunk(
                chunk_id=str(uuid.uuid4()),
                vector_id="vec1",
                source_platform="google_play",
                original_text="I have 50,000 photos and I can't find the one from my sister's wedding in 2019. I remember the blue dress she wore but Google Photos only lets me search by date, which I forgot.",
                chunk_text="I have 50,000 photos and I can't find the one from my sister's wedding in 2019.",
                app_referenced="Google Photos",
                author_id="user123",
                memory_anchors={"people": ["sister"], "events": ["wedding"], "objects": ["blue dress"]},
                forgotten_metadata={"dates": ["exact date in 2019"]},
                search_strategy="visual_attribute",
                frustration_level="high",
                taxonomy_label="retrieval_failure",
                sentiment_score=-0.7,
                crawled_at=datetime.now(timezone.utc)
            ),
            FeedbackChunk(
                chunk_id=str(uuid.uuid4()),
                vector_id="vec2",
                source_platform="app_store",
                original_text="Why is it so hard to search for emotions? I want to find that really happy photo from the beach trip...",
                chunk_text="Why is it so hard to search for emotions? I want to find that really happy photo from the beach trip...",
                app_referenced="iCloud Photos",
                author_id="user456",
                memory_anchors={"emotions": ["happy"], "locations": ["beach"]},
                forgotten_metadata={"dates": ["date of trip"]},
                search_strategy="emotion",
                frustration_level="medium",
                taxonomy_label="feature_request",
                sentiment_score=-0.4,
                crawled_at=datetime.now(timezone.utc)
            ),
            FeedbackChunk(
                chunk_id=str(uuid.uuid4()),
                vector_id="vec3",
                source_platform="reddit",
                original_text="Does anyone else remember taking a photo of a specific receipt 3 years ago but can't find it?",
                chunk_text="Does anyone else remember taking a photo of a specific receipt 3 years ago but can't find it?",
                app_referenced="Google Photos",
                author_id="user789",
                memory_anchors={"objects": ["receipt"]},
                forgotten_metadata={"dates": ["exact date 3 years ago"]},
                search_strategy="document",
                frustration_level="low",
                taxonomy_label="retrieval_failure",
                sentiment_score=-0.2,
                crawled_at=datetime.now(timezone.utc)
            )
        ]
        session.add_all(samples)
        session.commit()
        print("Successfully seeded 3 records!")

if __name__ == "__main__":
    seed()
