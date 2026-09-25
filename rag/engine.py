"""
RAG Engine for the Discovery Engine.

Orchestrates the retrieval and generation process:
1. Receives natural language query
2. Parses/routes the query to the right prompt template
3. Retrieves relevant chunks from Pinecone using BGE embeddings
4. Synthesizes an answer using the Groq LLM API
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import groq
import cohere

from config.settings import (
    GROQ_API_KEY,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    PINECONE_NAMESPACES,
    RAG_TOP_K,
    RAG_RERANK_TOP_K,
    COHERE_API_KEY,
)
from embeddings.bge_embedder import BGEEmbedder
from rag.prompts import build_rag_prompt
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from storage.chroma_store import ChromaStore
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Retrieval-Augmented Generation (RAG) engine.

    Integrates the BGE Embedder, Pinecone Vector Store, and Groq LLM
    to answer discovery questions based on scraped user feedback.
    """

    def __init__(
        self,
        embedder: Optional[BGEEmbedder] = None,
        vector_store: Optional[ChromaStore] = None,
        groq_api_key: str = GROQ_API_KEY,
        cohere_api_key: str = COHERE_API_KEY,
        model: str = GROQ_MODEL,
        temperature: float = GROQ_TEMPERATURE,
        max_tokens: int = GROQ_MAX_TOKENS,
    ):
        self.embedder = embedder or BGEEmbedder()
        if vector_store is None:
            from storage.chroma_store import ChromaStore
            self.vector_store = ChromaStore()
        else:
            self.vector_store = vector_store
        
        if not groq_api_key:
            logger.warning("GROQ_API_KEY is not set. LLM synthesis will fail.")
            
        self.client = groq.Groq(api_key=groq_api_key)
        
        if cohere_api_key:
            self.cohere_client = cohere.ClientV2(api_key=cohere_api_key)
        else:
            logger.warning("COHERE_API_KEY is not set. Re-ranking will be skipped.")
            self.cohere_client = None
            
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Query Router
        from rag.router import QueryRouter
        self.router = QueryRouter(api_key=groq_api_key, model=model)

    def query(
        self,
        question: str,
        namespaces: Optional[list[str]] = None,
        top_k: int = RAG_TOP_K,
        discovery_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Execute a full RAG query.

        Args:
            question: The natural language question to ask
            namespaces: List of Chroma namespaces to search (default: all)
            top_k: Number of chunks to retrieve per namespace
            discovery_key: Optional key to use a specialized prompt template

        Returns:
            Dictionary with 'answer', 'retrieved_chunks', and 'usage' stats
        """
        namespaces = namespaces or PINECONE_NAMESPACES
        
        # 0. Route query if no discovery_key is provided
        if not discovery_key:
            discovery_key = self.router.route_query(question)
            
        logger.info("Running RAG query across %d namespaces (Intent: %s)...", len(namespaces), discovery_key or "general")

        # 1. Embed the query
        logger.debug("Embedding query...")
        query_vector = self.embedder.embed_query(question)

        # 2. Retrieve from ChromaDB
        logger.debug("Retrieving relevant chunks...")
        all_results = self.vector_store.search_across_namespaces(
            query_vector=query_vector.tolist(),
            top_k=top_k,
            namespaces=namespaces,
        )

        # Flatten and sort results by score (descending)
        flattened_results = []
        for ns, matches in all_results.items():
            for match in matches:
                # Add namespace to metadata if not present
                if "source_platform" not in match["metadata"]:
                    match["metadata"]["source_platform"] = ns
                flattened_results.append(match)

        flattened_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Take the top_k across all namespaces combined for the context window
        context_chunks = flattened_results[:top_k]
        
        logger.info("Retrieved %d total relevant chunks from ChromaDB", len(context_chunks))

        # Optional: Re-rank using Cohere
        if self.cohere_client and context_chunks:
            logger.info("Re-ranking top %d chunks with Cohere...", len(context_chunks))
            try:
                documents = [chunk["metadata"]["text"] for chunk in context_chunks]
                # Assuming v2 client usage:
                response = self.cohere_client.rerank(
                    model="rerank-english-v3.0",
                    query=question,
                    documents=documents,
                    top_n=RAG_RERANK_TOP_K,
                )
                
                # Re-order and slice based on Cohere results
                reranked_chunks = []
                for result in response.results:
                    # result.index points to the original index in the documents array
                    original_chunk = context_chunks[result.index]
                    # Update score to reflect re-ranking confidence
                    original_chunk["score"] = result.relevance_score
                    reranked_chunks.append(original_chunk)
                    
                context_chunks = reranked_chunks
                logger.info("Successfully re-ranked down to top %d chunks", len(context_chunks))
            except Exception as e:
                logger.error("Cohere re-ranking failed: %s. Falling back to original ordering.", str(e))
                # Fall back to original top 8
                context_chunks = context_chunks[:RAG_RERANK_TOP_K]
        else:
            # If no Cohere, just take the top rerank K from ChromaDB
            context_chunks = context_chunks[:RAG_RERANK_TOP_K]

        # 3. Build Prompt
        messages = build_rag_prompt(
            query=question,
            context_chunks=context_chunks,
            sources=namespaces,
            discovery_key=discovery_key,
        )

        # 4. Synthesize Answer via Groq
        if not context_chunks:
            return {
                "answer": "I don't have enough relevant user feedback data to answer this question.",
                "retrieved_chunks": [],
                "usage": None,
            }

        logger.info("Synthesizing answer with Groq (%s)...", self.model)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            answer = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            
            return {
                "answer": answer,
                "retrieved_chunks": context_chunks,
                "usage": usage,
            }
            
        except Exception as e:
            logger.error("Failed to synthesize answer: %s", str(e))
            raise
