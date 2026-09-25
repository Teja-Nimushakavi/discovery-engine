from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from rag.engine import RAGEngine
from rag.comparator import CrossPlatformComparator

router = APIRouter()
engine = RAGEngine()
comparator = CrossPlatformComparator(rag_engine=engine)

class QueryRequest(BaseModel):
    query: str
    namespaces: list[str] | None = None

@router.post("/")
def ask_question(req: QueryRequest):
    try:
        result = engine.query(question=req.query, namespaces=req.namespaces)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
def compare_platforms(req: QueryRequest):
    try:
        result = comparator.compare(question=req.query, namespaces=req.namespaces)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
