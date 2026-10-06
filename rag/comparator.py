import logging
import json
from typing import Any, Optional

import groq

from config.settings import GROQ_API_KEY, GROQ_MODEL, PINECONE_NAMESPACES
from rag.engine import RAGEngine

logger = logging.getLogger(__name__)

class CrossPlatformComparator:
    """
    Executes a query across multiple platforms independently and 
    synthesizes a structured comparison of the differences.
    """

    def __init__(self, rag_engine: Optional[RAGEngine] = None, api_key: str = GROQ_API_KEY, model: str = GROQ_MODEL):
        self.rag_engine = rag_engine or RAGEngine()
        self.model = model
        self.client = groq.Groq(api_key=api_key) if api_key else None

    def compare(self, question: str, namespaces: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Runs the RAG engine for each namespace independently and compares the results.
        """
        namespaces = namespaces or PINECONE_NAMESPACES
        logger.info("Running Cross-Platform Comparison for query: '%s' across %s", question, namespaces)

        platform_answers = {}
        all_chunks = []
        
        # 1. Gather answers from each platform
        for ns in namespaces:
            logger.info("Gathering insights for platform: %s", ns)
            res = self.rag_engine.query(question=question, namespaces=[ns], filter_dict={"taxonomy_label": {"$ne": "praise"}, "app_referenced": "Google Photos"})
            platform_answers[ns] = res["answer"]
            all_chunks.extend(res["retrieved_chunks"])
            
        if not self.client:
            logger.warning("GROQ_API_KEY missing, skipping synthesis.")
            return {
                "comparison_matrix": {},
                "synthesis": "Comparison synthesis skipped due to missing API key.",
                "platform_answers": platform_answers,
                "retrieved_chunks": all_chunks
            }

        # 2. Synthesize comparison
        logger.info("Synthesizing comparison matrix...")
        
        system_prompt = """You are an expert product analyst comparing user feedback across different platforms.
Given the answers derived from different platforms for a specific research question, synthesize the key differences and similarities.

Output a JSON object with the following schema:
{
    "similarities": ["bullet point 1", "bullet point 2"],
    "differences": ["bullet point 1", "bullet point 2"],
    "platform_quirks": {
        "platform_name": "Unique behavior or sentiment for this specific platform"
    },
    "synthesis_summary": "A 2-3 sentence overall conclusion."
}
"""

        user_content = f"Question: {question}\n\n"
        for ns, answer in platform_answers.items():
            user_content += f"--- {ns.upper()} ---\n{answer}\n\n"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            
            synthesis_result = json.loads(response.choices[0].message.content)
            
            return {
                "comparison": synthesis_result,
                "platform_answers": platform_answers,
                "retrieved_chunks": all_chunks
            }

        except Exception as e:
            logger.error("Failed to synthesize comparison: %s", str(e))
            return {
                "comparison": {"error": str(e)},
                "platform_answers": platform_answers,
                "retrieved_chunks": all_chunks
            }
