from fastapi import APIRouter, Query
from sqlalchemy import text
from storage.models import get_engine

router = APIRouter()

@router.get("/")
def explore_chunks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    app: str = Query(None),
    taxonomy: str = Query(None),
):
    engine = get_engine()
    
    offset = (page - 1) * limit
    
    with engine.connect() as conn:
        query = "SELECT source_platform, original_text, taxonomy_label, frustration_level, app_referenced FROM feedback_chunks WHERE 1=1"
        params = {}
        
        if app:
            query += " AND app_referenced = :app"
            params["app"] = app
            
        if taxonomy:
            query += " AND taxonomy_label = :taxonomy"
            params["taxonomy"] = taxonomy
            
        query += " ORDER BY crawled_at DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        
        rows = conn.execute(text(query), params).fetchall()
        
        # Count total
        count_query = "SELECT COUNT(*) FROM feedback_chunks WHERE 1=1"
        if app:
            count_query += " AND app_referenced = :app"
        if taxonomy:
            count_query += " AND taxonomy_label = :taxonomy"
            
        total = conn.execute(text(count_query), params).scalar()
        
    return {
        "items": [
            {
                "platform": row[0],
                "text": row[1],
                "taxonomy": row[2],
                "frustration": row[3],
                "app": row[4]
            } for row in rows
        ],
        "total": total,
        "page": page,
        "limit": limit
    }
