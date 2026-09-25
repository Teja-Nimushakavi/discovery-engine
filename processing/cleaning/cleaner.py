"""
Text cleaning pipeline for the Discovery Engine.

Takes raw scraped text (Reddit posts, app reviews, forum threads) and
produces clean, normalized text ready for semantic chunking.

Pipeline stages:
    1. Strip HTML tags and markdown formatting
    2. Normalize Unicode (NFKC)
    3. Collapse excessive punctuation and whitespace
    4. Filter non-English content
    5. Remove short/spam content
    6. Preserve original text in metadata for citation

Usage:
    from processing.cleaning.cleaner import TextCleaner
    cleaner = TextCleaner()
    result = cleaner.clean("Some <b>raw</b> text!!!")
"""

import logging
import re
import unicodedata

from config.settings import MIN_ENGLISH_RATIO, MIN_TEXT_LENGTH, RETRIEVAL_KEYWORDS

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Multi-stage text cleaning pipeline.

    Each stage can be toggled on/off. The default pipeline is optimized
    for user-generated content from app stores, Reddit, and forums.
    """

    # Regex patterns compiled once at class level
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _MARKDOWN_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
    _MARKDOWN_ITALIC_RE = re.compile(r"\*(.+?)\*")
    _MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    _MARKDOWN_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
    _MARKDOWN_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
    _MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
    _MARKDOWN_BLOCKQUOTE_RE = re.compile(r"^>\s?", re.MULTILINE)
    _URL_RE = re.compile(r"https?://\S+|www\.\S+")
    _REPEATED_PUNCT_RE = re.compile(r"([!?.])\1{2,}")
    _MULTI_SPACE_RE = re.compile(r"\s{2,}")
    _MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

    def __init__(
        self,
        strip_html: bool = True,
        strip_markdown: bool = True,
        strip_urls: bool = True,
        normalize_unicode: bool = True,
        collapse_punctuation: bool = True,
        filter_language: bool = True,
        filter_retrieval_issues: bool = True,
        min_length: int = MIN_TEXT_LENGTH,
        min_english_ratio: float = MIN_ENGLISH_RATIO,
    ):
        self.strip_html = strip_html
        self.strip_markdown = strip_markdown
        self.strip_urls = strip_urls
        self.normalize_unicode = normalize_unicode
        self.collapse_punctuation = collapse_punctuation
        self.filter_language = filter_language
        self.filter_retrieval_issues = filter_retrieval_issues
        self.min_length = min_length
        self.min_english_ratio = min_english_ratio

    def clean(self, text: str) -> dict:
        """
        Run the full cleaning pipeline on a text string.

        Args:
            text: Raw input text

        Returns:
            Dictionary with:
                - "cleaned_text": The cleaned text (empty string if filtered)
                - "original_text": The original text (preserved for citation)
                - "was_filtered": True if the text was discarded
                - "filter_reason": Reason for filtering (if applicable)
                - "urls_extracted": List of URLs found and stripped
                - "char_count_before": Character count before cleaning
                - "char_count_after": Character count after cleaning
        """
        original = text
        urls_extracted = []
        char_count_before = len(text)

        # Stage 1: Strip HTML tags
        if self.strip_html:
            text = self._strip_html(text)

        # Stage 2: Strip markdown formatting
        if self.strip_markdown:
            text = self._strip_markdown(text)

        # Stage 3: Extract and strip URLs
        if self.strip_urls:
            text, urls_extracted = self._strip_urls(text)

        # Stage 4: Normalize Unicode
        if self.normalize_unicode:
            text = self._normalize_unicode(text)

        # Stage 5: Collapse excessive punctuation
        if self.collapse_punctuation:
            text = self._collapse_punctuation(text)

        # Stage 6: Normalize whitespace
        text = self._normalize_whitespace(text)

        char_count_after = len(text)

        # Stage 7: Check minimum length
        if len(text.strip()) < self.min_length:
            return {
                "cleaned_text": "",
                "original_text": original,
                "was_filtered": True,
                "filter_reason": f"Too short ({len(text.strip())} < {self.min_length} chars)",
                "urls_extracted": urls_extracted,
                "char_count_before": char_count_before,
                "char_count_after": char_count_after,
            }

        # Stage 8: Language filter
        if self.filter_language and not self._is_english(text):
            return {
                "cleaned_text": "",
                "original_text": original,
                "was_filtered": True,
                "filter_reason": "Non-English content detected",
                "urls_extracted": urls_extracted,
                "char_count_before": char_count_before,
                "char_count_after": char_count_after,
            }

        # Stage 9: Strict Retrieval Issues Filter
        if self.filter_retrieval_issues and not self._is_retrieval_related(text):
            return {
                "cleaned_text": "",
                "original_text": original,
                "was_filtered": True,
                "filter_reason": "Not related to retrieval issues",
                "urls_extracted": urls_extracted,
                "char_count_before": char_count_before,
                "char_count_after": char_count_after,
            }

        return {
            "cleaned_text": text.strip(),
            "original_text": original,
            "was_filtered": False,
            "filter_reason": None,
            "urls_extracted": urls_extracted,
            "char_count_before": char_count_before,
            "char_count_after": char_count_after,
        }

    def clean_batch(self, texts: list[str]) -> list[dict]:
        """
        Clean a batch of texts.

        Args:
            texts: List of raw text strings

        Returns:
            List of cleaning result dictionaries
        """
        results = []
        filtered_count = 0
        for text in texts:
            result = self.clean(text)
            results.append(result)
            if result["was_filtered"]:
                filtered_count += 1

        logger.info(
            "Cleaned %d texts: %d kept, %d filtered",
            len(texts),
            len(texts) - filtered_count,
            filtered_count,
        )
        return results

    # ─── Private pipeline stages ───────────────────────────────────────

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        return self._HTML_TAG_RE.sub("", text)

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown formatting while preserving text content."""
        # Remove code blocks first (they may contain special chars)
        text = self._MARKDOWN_CODE_BLOCK_RE.sub("", text)
        # Bold: **text** → text
        text = self._MARKDOWN_BOLD_RE.sub(r"\1", text)
        # Italic: *text* → text
        text = self._MARKDOWN_ITALIC_RE.sub(r"\1", text)
        # Links: [text](url) → text
        text = self._MARKDOWN_LINK_RE.sub(r"\1", text)
        # Headers: ## text → text
        text = self._MARKDOWN_HEADER_RE.sub("", text)
        # Inline code: `text` → text
        text = self._MARKDOWN_INLINE_CODE_RE.sub(r"\1", text)
        # Blockquotes: > text → text
        text = self._MARKDOWN_BLOCKQUOTE_RE.sub("", text)
        return text

    def _strip_urls(self, text: str) -> tuple[str, list[str]]:
        """Extract URLs from text and replace them with empty string."""
        urls = self._URL_RE.findall(text)
        cleaned = self._URL_RE.sub("", text)
        return cleaned, urls

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode to NFKC form (canonical decomposition + compatibility)."""
        return unicodedata.normalize("NFKC", text)

    def _collapse_punctuation(self, text: str) -> str:
        """Collapse repeated punctuation (e.g., !!! → !)."""
        return self._REPEATED_PUNCT_RE.sub(r"\1", text)

    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces and newlines."""
        text = self._MULTI_SPACE_RE.sub(" ", text)
        text = self._MULTI_NEWLINE_RE.sub("\n\n", text)
        return text

    def _is_english(self, text: str) -> bool:
        """
        Check if text is predominantly English.

        Uses a character-ratio heuristic: checks what fraction of
        alphabetic characters are in the ASCII range. Falls back to
        langdetect for ambiguous cases.
        """
        if not text.strip():
            return False

        # Character-ratio heuristic (fast)
        alpha_chars = [c for c in text if c.isalpha()]
        if not alpha_chars:
            return True  # No alphabetic chars (e.g., just numbers/emojis)

        ascii_alpha = sum(1 for c in alpha_chars if ord(c) < 128)
        ratio = ascii_alpha / len(alpha_chars)

        if ratio >= self.min_english_ratio:
            return True

        # Fallback to langdetect for borderline cases
        try:
            from langdetect import detect

            lang = detect(text)
            return lang == "en"
        except Exception:
            # If langdetect fails, accept if ratio is above 0.5
            return ratio > 0.5

    def _is_retrieval_related(self, text: str) -> bool:
        """
        Check if text contains keywords related to retrieval issues.
        """
        text_lower = text.lower()
        for keyword in RETRIEVAL_KEYWORDS:
            if keyword in text_lower:
                return True
        return False
