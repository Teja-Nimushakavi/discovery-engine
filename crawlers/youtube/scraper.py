"""
YouTube comments scraper using `youtube-comment-downloader`.

Fetches comments for target photo management query videos. Outputs normalized 
JSONL matching the same schema used by other crawlers.

Usage:
    from crawlers.youtube.scraper import YouTubeScraper
    scraper = YouTubeScraper()
    reviews = scraper.scrape_video_comments("VIDEO_ID")
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR

from config.settings import TARGET_APPS
from crawlers.dedup import DedupEngine

logger = logging.getLogger(__name__)


class YouTubeScraper:
    """
    Scrapes YouTube video comments using youtube-comment-downloader.

    Each comment is normalized into the shared JSONL schema and
    deduplicated before output.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw/youtube",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dedup = DedupEngine()
        self.downloader = YoutubeCommentDownloader()

    def scrape_all_apps(self) -> list[dict]:
        """Scrape comments for configured target apps/queries."""
        # For youtube, target apps in settings might contain a list of video IDs
        all_comments = []
        for app in TARGET_APPS:
            if app.get("platform") != "youtube":
                continue
            
            video_ids = app.get("video_ids", [])
            for video_id in video_ids:
                logger.info("Scraping comments for video %s (%s)", video_id, app["name"])
                try:
                    comments = self.scrape_video_comments(
                        video_id=video_id,
                        app_name=app["name"],
                    )
                    all_comments.extend(comments)
                    logger.info(
                        "Scraped %d comments for video %s", len(comments), video_id
                    )
                except Exception as e:
                    logger.error(
                        "Failed to scrape video %s: %s", video_id, str(e)
                    )
                    continue
        return all_comments

    def scrape_video_comments(
        self,
        video_id: str,
        app_name: str = "Google Photos",
        max_comments: int = 200,
    ) -> list[dict]:
        """
        Scrape comments for a single YouTube video.

        Args:
            video_id: YouTube video ID
            app_name: Human-readable app name for metadata
            max_comments: Maximum number of comments to fetch

        Returns:
            List of normalized comment dictionaries
        """
        logger.info("Fetching comments for video %s...", video_id)
        
        generator = self.downloader.get_comments_from_url(
            f"https://www.youtube.com/watch?v={video_id}", 
            sort_by=SORT_BY_POPULAR
        )
        
        results = []
        for i, comment in enumerate(generator):
            if i >= max_comments:
                break
            results.append(comment)

        # Normalize and deduplicate
        normalized = []
        for item in results:
            review = self._normalize_review(item, video_id, app_name)
            if review is None:
                continue

            dedup_key = (
                f"youtube|{review['author']}|"
                f"{review['timestamp']}|{review['review_text'][:200]}"
            )
            if self.dedup.is_duplicate(dedup_key):
                continue

            normalized.append(review)

        # Save to JSONL
        self._save_reviews(normalized, video_id)
        return normalized

    def _normalize_review(
        self, raw: dict, video_id: str, app_name: str
    ) -> dict | None:
        """
        Normalize a raw youtube comment into the shared schema.
        """
        review_text = raw.get("text", "").strip()
        if not review_text:
            return None

        # Author name
        author = raw.get("author", "anonymous")
        
        # ID
        review_id = raw.get("cid", "")
        
        # Timestamp (youtube-comment-downloader returns "3 years ago" string in time, but no exact ISO)
        # We will use the crawling time as a fallback or leave the fuzzy time string
        fuzzy_time = raw.get("time", "")

        return {
            "source_platform": "youtube",
            "review_id": review_id,
            "app_id": video_id,
            "app_name": app_name,
            "rating": 0, # N/A for youtube
            "review_text": review_text,
            "title": "", 
            "author": author,
            "timestamp": fuzzy_time, 
            "version": "",
            "device": "", 
            "thumbs_up": raw.get("votes", 0),
            "url": f"https://www.youtube.com/watch?v={video_id}&lc={review_id}",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_reviews(self, review_items: list[dict], video_id: str) -> None:
        """Save normalized reviews to a JSONL file."""
        if not review_items:
            return
            
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{video_id}_{timestamp}.jsonl"

        with open(filename, "w", encoding="utf-8") as f:
            for review in review_items:
                f.write(json.dumps(review, ensure_ascii=False) + "\n")

        logger.info("Saved %d reviews to %s", len(review_items), filename)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
