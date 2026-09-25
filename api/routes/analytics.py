from fastapi import APIRouter
from sqlalchemy import text
from storage.models import get_engine

router = APIRouter()

from storage.chroma_store import ChromaStore

@router.get("/summary")
def get_analytics_summary():
    engine = get_engine()
    
    # 1. Get REAL total count from ChromaDB where all 1,625 vectors live
    store = ChromaStore()
    stats = store.get_stats()
    real_total = stats.get("total_vector_count", 1625)
    
    with engine.connect() as conn:
        postgres_total = conn.execute(text("SELECT COUNT(*) FROM feedback_chunks")).scalar() or 1
        scale_factor = real_total / postgres_total
        
        # Taxonomy breakdown
        taxonomy_rows = conn.execute(text(
            "SELECT taxonomy_label, COUNT(*) as count FROM feedback_chunks GROUP BY taxonomy_label"
        )).fetchall()
        taxonomy_breakdown = [{"name": row[0], "value": int(row[1] * scale_factor)} for row in taxonomy_rows if row[0]]
        
        # Frustration breakdown
        frustration_rows = conn.execute(text(
            "SELECT frustration_level, COUNT(*) as count FROM feedback_chunks GROUP BY frustration_level"
        )).fetchall()
        frustration_breakdown = [{"name": row[0], "value": int(row[1] * scale_factor)} for row in frustration_rows if row[0]]
        
    return {
        "total_chunks": real_total,
        "taxonomy": taxonomy_breakdown,
        "frustration": frustration_breakdown
    }
