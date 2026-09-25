import logging
from typing import Optional

import groq
from pydantic import BaseModel, Field

from config.settings import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

class QueryIntent(BaseModel):
    intent: str = Field(
        description="The classified intent of the user's research question.",
        enum=["photo_types", "what_users_remember", "what_users_forget", "search_strategies", "failure_cascades", "general"]
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Brief reasoning for the classification")

class QueryRouter:
    """
    Intelligent router that classifies incoming natural language queries
    to determine which specialized discovery prompt template to use.
    """

    def __init__(self, api_key: str = GROQ_API_KEY, model: str = "llama-3.3-70b-specdec"): # Using specdec or versatile
        # Fast model for routing
        self.model = GROQ_MODEL
        if not api_key:
            logger.warning("GROQ_API_KEY is not set. Query routing will fallback to 'general'.")
            self.client = None
        else:
            self.client = groq.Groq(api_key=api_key)

    def route_query(self, query: str) -> str:
        """
        Classifies the query and returns the matching discovery_key.
        Falls back to 'general' if unknown.
        """
        if not self.client:
            return "general"

        system_prompt = """You are a specialized query router for a Photo Retrieval UX research tool.
Your job is to analyze the user's natural language question and map it to one of the following research intents:

- "photo_types": Questions about what kinds of old photos users are looking for (e.g. "What type of photos do they struggle to find?")
- "what_users_remember": Questions about the memory anchors users rely on (e.g. "What details do they actually remember?")
- "what_users_forget": Questions about metadata users forget (e.g. "Do they remember exact dates?")
- "search_strategies": Questions about how users formulate searches (e.g. "How do iOS users search for photos?")
- "failure_cascades": Questions about what happens when searches fail (e.g. "What do they do after a search fails?")
- "general": Any other question that doesn't fit the above categories.

Output a JSON object matching the requested schema.
"""

        try:
            logger.info("Routing query: %s", query)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify this query: '{query}'"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            
            # Since Groq JSON mode just guarantees JSON, we parse it
            import json
            result = json.loads(response.choices[0].message.content)
            
            intent = result.get("intent", "general")
            valid_intents = ["photo_types", "what_users_remember", "what_users_forget", "search_strategies", "failure_cascades", "general"]
            
            if intent not in valid_intents:
                intent = "general"
                
            logger.info("Routed query to intent: %s (Reasoning: %s)", intent, result.get("reasoning", ""))
            return intent if intent != "general" else None

        except Exception as e:
            logger.error("Query routing failed: %s", str(e))
            return None
