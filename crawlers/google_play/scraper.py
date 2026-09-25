"""
Google Play Store scraper using `google-play-scraper`.

Fetches app reviews for target photo management apps. Outputs normalized 
JSONL matching the same schema used by other crawlers.

Usage:
    from crawlers.google_play.scraper import GooglePlayScraper
    scraper = GooglePlayScraper()
    reviews = scraper.scrape_reviews("com.google.android.apps.photos")
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews

from config.settings import TARGET_APPS
from crawlers.dedup import DedupEngine

logger = logging.getLogger(__name__)


class GooglePlayScraper:
    """
    Scrapes Google Play Store reviews using google-play-scraper.

    Each review is normalized into the shared JSONL schema and
    deduplicated before output.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw/google_play",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dedup = DedupEngine()

    def scrape_all_apps(self) -> list[dict]:
        """Scrape reviews for all configured target apps."""
        all_reviews = []
        for app in TARGET_APPS:
            if app.get("platform") != "google_play":
                continue
            logger.info("Scraping reviews for %s (%s)", app["name"], app["id"])
            try:
                app_reviews = self.scrape_reviews(
                    app_id=app["id"],
                    app_name=app["name"],
                )
                all_reviews.extend(app_reviews)
                logger.info(
                    "Scraped %d reviews for %s", len(app_reviews), app["name"]
                )
            except Exception as e:
                logger.error(
                    "Failed to scrape %s: %s", app["name"], str(e)
                )
                continue
        return all_reviews

    def scrape_reviews(
        self,
        app_id: str,
        app_name: str = "",
        max_reviews: int = 1000,
        sort: Sort = Sort.NEWEST,
    ) -> list[dict]:
        """
        Scrape reviews for a single app from Google Play Store.

        Args:
            app_id: Google Play app package ID (e.g., "com.google.android.apps.photos")
            app_name: Human-readable app name for metadata
            max_reviews: Maximum number of reviews to fetch
            sort: Sort order (from google_play_scraper.Sort)

        Returns:
            List of normalized review dictionaries
        """
        logger.info("Fetching reviews for %s using google-play-scraper...", app_id)
        
        result, _ = reviews(
            app_id,
            lang='en', # defaults to 'en'
            country='us', # defaults to 'us'
            sort=sort, # defaults to Sort.NEWEST
            count=max_reviews
        )

        # Normalize and deduplicate
        normalized = []
        for item in result:
            review = self._normalize_review(item, app_id, app_name)
            if review is None:
                continue

            dedup_key = (
                f"google_play|{review['author']}|"
                f"{review['timestamp']}|{review['review_text'][:200]}"
            )
            if self.dedup.is_duplicate(dedup_key):
                continue

            normalized.append(review)

        # Save to JSONL
        self._save_reviews(normalized, app_id)
        return normalized

    def _normalize_review(
        self, raw: dict, app_id: str, app_name: str
    ) -> dict | None:
        """
        Normalize a raw google-play-scraper review into the shared schema.

        Returns None if the review is empty or invalid.
        """
        review_text = raw.get("content", "").strip()
        if not review_text:
            return None

        # Convert datetime to ISO format string
        timestamp_obj = raw.get("at")
        timestamp = timestamp_obj.isoformat() if timestamp_obj else ""

        return {
            "source_platform": "google_play",
            "review_id": raw.get("reviewId", ""),
            "app_id": app_id,
            "app_name": app_name,
            "rating": raw.get("score"),
            "review_text": review_text,
            "title": "", # google-play-scraper doesn't return title for Android reviews
            "author": raw.get("userName", "anonymous"),
            "timestamp": timestamp,
            "version": raw.get("reviewCreatedVersion", ""),
            "device": "", # google-play-scraper doesn't return device
            "thumbs_up": raw.get("thumbsUpCount", 0),
            "url": f"https://play.google.com/store/apps/details?id={app_id}",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_reviews(self, review_items: list[dict], app_id: str) -> None:
        """Save normalized reviews to a JSONL file."""
        if not review_items:
            return
            
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{app_id}_{timestamp}.jsonl"

        with open(filename, "w", encoding="utf-8") as f:
            for review in review_items:
                f.write(json.dumps(review, ensure_ascii=False) + "\n")

        logger.info("Saved %d reviews to %s", len(review_items), filename)

    def close(self):
        """Mock method to maintain compatibility with context managers."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
