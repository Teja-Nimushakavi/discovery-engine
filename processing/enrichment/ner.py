"""
NER Pipeline for the Discovery Engine.

Uses spaCy to extract specific memory anchors and forgotten metadata
from user feedback text.

Extracted entities:
- Memory anchors: emotions, people (PERSON), dates/times (DATE, TIME), locations (GPE, LOC)
- Search strategies: inferred from context
"""

import logging
from typing import Dict, List

from config.settings import SPACY_MODEL

logger = logging.getLogger(__name__)

class NERTagger:
    """
    Extracts entities and memory anchors using spaCy.
    """

    def __init__(self, model_name: str = SPACY_MODEL):
        self.model_name = model_name
        self.nlp = None
        
        # Simple heuristic dictionaries for custom entity types not natively in spaCy
        self.EMOTION_KEYWORDS = {"happy", "sad", "angry", "frustrated", "excited", "nostalgic", "funny", "hilarious", "cry", "smile"}
        self.VISUAL_KEYWORDS = {"red", "blue", "green", "yellow", "dark", "bright", "blurry", "dog", "cat", "car", "dress", "shirt", "beach", "mountain"}
        self.EVENT_KEYWORDS = {"wedding", "birthday", "party", "trip", "vacation", "concert", "graduation", "funeral", "christmas", "thanksgiving"}

    @property
    def model(self):
        """Lazy load the spaCy model."""
        if self.nlp is None:
            import spacy
            try:
                logger.info("Loading spaCy model: %s", self.model_name)
                self.nlp = spacy.load(self.model_name)
            except OSError:
                logger.warning(
                    "spaCy model '%s' not found. "
                    "Run: python -m spacy download %s", 
                    self.model_name, self.model_name
                )
                # Fallback to blank english model if large model not found
                self.nlp = spacy.blank("en")
        return self.nlp

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text and categorize them into memory anchors
        and forgotten metadata based on context.
        """
        doc = self.model(text)
        
        # Initialize categorizations
        anchors = {
            "people": set(),
            "temporal": set(),
            "spatial": set(),
            "visual": set(),
            "emotions": set(),
            "events": set()
        }
        
        forgotten = {
            "temporal": set(),
            "spatial": set(),
            "other": set()
        }
        
        # 1. Extract standard NER entities (People, Dates, Locations)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                anchors["people"].add(ent.text.lower())
            elif ent.label_ in ("DATE", "TIME"):
                # Simple heuristic: if it follows "forget", "don't know", it's forgotten
                context = text[max(0, ent.start_char - 30):ent.start_char].lower()
                if any(w in context for w in ["forget", "forgot", "don't know", "can't remember"]):
                    forgotten["temporal"].add(ent.text.lower())
                else:
                    anchors["temporal"].add(ent.text.lower())
            elif ent.label_ in ("GPE", "LOC", "FAC"):
                context = text[max(0, ent.start_char - 30):ent.start_char].lower()
                if any(w in context for w in ["forget", "forgot", "don't know", "can't remember"]):
                    forgotten["spatial"].add(ent.text.lower())
                else:
                    anchors["spatial"].add(ent.text.lower())

        # 2. Extract custom entities via keyword matching
        words = {token.text.lower() for token in doc if token.is_alpha}
        
        anchors["emotions"].update(words.intersection(self.EMOTION_KEYWORDS))
        anchors["visual"].update(words.intersection(self.VISUAL_KEYWORDS))
        anchors["events"].update(words.intersection(self.EVENT_KEYWORDS))
        
        # Determine Search Strategy
        search_strategy = self._infer_search_strategy(anchors)

        return {
            "memory_anchors": {k: list(v) for k, v in anchors.items() if v},
            "forgotten_metadata": {k: list(v) for k, v in forgotten.items() if v},
            "inferred_search_strategy": search_strategy
        }

    def _infer_search_strategy(self, anchors: Dict[str, set]) -> str:
        """Infer the likely search strategy based on present anchors."""
        if anchors["visual"]:
            return "visual_attribute"
        if anchors["people"]:
            return "people"
        if anchors["events"]:
            return "event"
        if anchors["temporal"]:
            return "temporal"
        if anchors["spatial"]:
            return "spatial"
        return "keyword_unknown"
