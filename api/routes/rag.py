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
        # Force only google_play for RAG retrieval
        namespaces = ["google_play"]
        result = engine.query(question=req.query, namespaces=namespaces, filter_dict={"taxonomy_label": "retrieval_failure"})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare")
def compare_platforms(req: QueryRequest):
    try:
        namespaces = ["google_play"]
        result = comparator.compare(question=req.query, namespaces=namespaces)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
