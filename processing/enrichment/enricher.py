"""
Metadata Enrichment Pipeline for the Discovery Engine.

Runs post-chunking to enrich chunks with:
- Sentiment scoring and frustration detection (via VADER)
- Taxonomy classification (Rule-based Regex)
- Feature extraction (via spaCy and rule-based matching)
- App identification
"""

import logging
import re
from typing import Dict, Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import spacy

logger = logging.getLogger(__name__)

class MetadataEnricher:
    """
    Enriches semantic chunks with additional metadata properties using Local NLP.
    """

    # Basic keyword rules for taxonomy classification
    TAXONOMY_RULES = {
        "retrieval_failure": [
            r"can'?t find", r"lost", r"missing", r"where is", 
            r"searching for", r"couldn'?t find", r"disappeared",
            r"search not working", r"forgot where", r"long back"
        ],
        "feature_request": [
            r"wish", r"should add", r"please add", r"would be nice",
            r"needs to", r"hope they", r"bring back"
        ],
        "workaround": [
            r"i usually", r"my trick", r"instead i", r"had to",
            r"ended up", r"figured out a way", r"workaround"
        ],
        "praise": [
            r"love", r"great", r"amazing", r"best feature",
            r"finally", r"so easy", r"awesome"
        ]
    }

    # Common Google Photos features for extraction
    KNOWN_FEATURES = {
        "search bar", "map view", "face grouping", "faces", "timeline", 
        "album", "tags", "filter", "sort", "backup", "memories", "magic eraser",
        "search", "date", "location", "people"
    }

    def __init__(self):
        # Compile regex rules
        self.compiled_rules = {
            label: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for label, patterns in self.TAXONOMY_RULES.items()
        }
        
        # Initialize VADER
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize spaCy (load small English model)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("Spacy model 'en_core_web_sm' not found. Features extraction will be limited.")
            self.nlp = None

    def enrich(self, text: str, existing_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a chunk's metadata based on its text content.
        """
        metadata = existing_metadata.copy()

        # 1. App Identification (if not already present)
        if not metadata.get("app_referenced"):
            lower_text = text.lower()
            if "google photos" in lower_text:
                metadata["app_referenced"] = "Google Photos"
            elif "icloud" in lower_text or "apple photos" in lower_text:
                metadata["app_referenced"] = "iCloud Photos"
            elif "amazon photos" in lower_text:
                metadata["app_referenced"] = "Amazon Photos"

        # 2. Taxonomy Classification
        metadata["taxonomy_label"] = self._classify_taxonomy(text)

        # 3. Sentiment & Frustration (VADER)
        sentiment, frustration = self._score_sentiment(text)
        metadata["sentiment_score"] = sentiment
        metadata["frustration_level"] = frustration
        
        # 4. Feature Extraction (spaCy + Known Features)
        metadata["features_mentioned"] = self._extract_features(text)

        return metadata

    def _classify_taxonomy(self, text: str) -> str:
        """Rule-based taxonomy classifier. Defaults to 'unrelated' if no match."""
        for label, patterns in self.compiled_rules.items():
            for pattern in patterns:
                if pattern.search(text):
                    return label
        return "unrelated"

    def _score_sentiment(self, text: str) -> tuple[float, str]:
        """
        Sentiment scoring returning (score, frustration_level).
        Uses vaderSentiment for a compound score between -1.0 and 1.0.
        """
        scores = self.sentiment_analyzer.polarity_scores(text)
        compound = scores.get('compound', 0.0)
        
        if compound <= -0.5:
            frustration = "high"
        elif compound < 0.0:
            frustration = "medium"
        else:
            frustration = "low"
            
        return compound, frustration

    def _extract_features(self, text: str) -> list[str]:
        """
        Extract features mentioned using known feature lists and spaCy noun chunks.
        """
        features = set()
        text_lower = text.lower()
        
        # 1. Exact match against known features
        for feature in self.KNOWN_FEATURES:
            if feature in text_lower:
                # Basic boundary check to avoid substring matches like 'date' in 'update'
                if re.search(rf"\b{re.escape(feature)}\b", text_lower):
                    features.add(feature)
                
        # 2. Heuristic noun extraction with spaCy
        if self.nlp:
            doc = self.nlp(text)
            for chunk in doc.noun_chunks:
                chunk_text = chunk.text.lower()
                # If chunk contains key photos terms but isn't generic
                if ("photo" in chunk_text or "picture" in chunk_text) and chunk_text not in {"photos", "the photos", "my photos", "pictures"}:
                    # Only add if it's a small descriptive noun chunk (e.g. "old photos", "blurry pictures")
                    if len(chunk_text.split()) <= 3:
                        features.add(chunk_text)
                        
        return list(features)
