"""
Apple App Store scraper using iTunes RSS feed.

Fetches app reviews for target photo management apps. Outputs normalized 
JSONL matching the same schema used by other crawlers.

Usage:
    from crawlers.apple_app_store.scraper import AppleAppStoreScraper
    scraper = AppleAppStoreScraper()
    reviews = scraper.scrape_reviews("962118360") # Google Photos iOS app ID
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config.settings import TARGET_APPS
from crawlers.dedup import DedupEngine

logger = logging.getLogger(__name__)


class AppleAppStoreScraper:
    """
    Scrapes Apple App Store reviews using iTunes RSS feeds.

    Each review is normalized into the shared JSONL schema and
    deduplicated before output.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw/apple_app_store",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dedup = DedupEngine()
        self.client = httpx.Client(timeout=30.0)

    def scrape_all_apps(self) -> list[dict]:
        """Scrape reviews for all configured target apps."""
        all_reviews = []
        for app in TARGET_APPS:
            if app.get("platform") != "apple_app_store":
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
        max_pages: int = 10,
    ) -> list[dict]:
        """
        Scrape reviews for a single app from the Apple App Store via iTunes RSS.

        Args:
            app_id: Apple App ID (e.g., "962118360" for Google Photos)
            app_name: Human-readable app name for metadata
            max_pages: Maximum number of pages to fetch (max 10 allowed by iTunes)

        Returns:
            List of normalized review dictionaries
        """
        logger.info("Fetching reviews for %s using iTunes RSS...", app_id)
        
        results = []
        # iTunes RSS feed supports pages 1 through 10
        for page in range(1, min(max_pages + 1, 11)):
            url = f"https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
            response = self.client.get(url)
            
            if response.status_code != 200:
                logger.warning("Failed to fetch page %d: %s", page, response.status_code)
                break
                
            data = response.json()
            feed = data.get("feed", {})
            entries = feed.get("entry", [])
            
            # If the entry is a dict, it's just one item, if list, multiple
            if isinstance(entries, dict):
                entries = [entries]
                
            if not entries:
                break
                
            for entry in entries:
                # The first entry in page 1 is often the app metadata itself, skip if it doesn't have an author
                if "author" not in entry:
                    continue
                results.append(entry)

        # Normalize and deduplicate
        normalized = []
        for item in results:
            review = self._normalize_review(item, app_id, app_name)
            if review is None:
                continue

            dedup_key = (
                f"apple_app_store|{review['author']}|"
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
        Normalize a raw iTunes review into the shared schema.
        """
        review_text = raw.get("content", {}).get("label", "").strip()
        if not review_text:
            return None

        # iTunes returns rating in 'im:rating'
        rating_str = raw.get("im:rating", {}).get("label", "0")
        try:
            rating = int(rating_str)
        except ValueError:
            rating = 0

        # Author name
        author = raw.get("author", {}).get("name", {}).get("label", "anonymous")
        
        # ID
        review_id = raw.get("id", {}).get("label", "")
        
        # Title
        title = raw.get("title", {}).get("label", "")
        
        # Version
        version = raw.get("im:version", {}).get("label", "")

        return {
            "source_platform": "apple_app_store",
            "review_id": review_id,
            "app_id": app_id,
            "app_name": app_name,
            "rating": rating,
            "review_text": review_text,
            "title": title,
            "author": author,
            "timestamp": "", # iTunes RSS doesn't provide exact timestamp reliably in JSON
            "version": version,
            "device": "iOS", 
            "thumbs_up": 0,
            "url": f"https://apps.apple.com/app/id{app_id}",
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
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
