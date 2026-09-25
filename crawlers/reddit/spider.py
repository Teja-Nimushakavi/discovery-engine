"""
Reddit Spider for the Discovery Engine.

Crawls target subreddits for photo-retrieval-related posts and comments.
Outputs JSONL files with structured post + comment data.

Usage:
    scrapy runspider crawlers/reddit/spider.py -o data/raw/reddit/output.jsonl
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import scrapy

from crawlers.dedup import DedupEngine

logger = logging.getLogger(__name__)


class RedditSearchSpider(scrapy.Spider):
    """
    Spider that searches Reddit for photo-retrieval-related posts.

    Uses Reddit's public JSON API (appending .json to URLs) to avoid
    authentication requirements. Respects rate limits with configurable delay.
    """

    name = "reddit_photo_search"
    allowed_domains = ["www.reddit.com", "old.reddit.com"]

    # Default settings (can be overridden via Scrapy settings)
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "ROBOTSTXT_OBEY": False,
        "USER_AGENT": (
            "DiscoveryEngine/0.1 (Research Project; "
            "photo retrieval UX analysis)"
        ),
        "CONCURRENT_REQUESTS": 1,
        "FEEDS": {
            "data/raw/reddit/%(time)s.jsonl": {
                "format": "jsonlines",
                "encoding": "utf-8",
                "overwrite": False,
            }
        },
        "LOG_LEVEL": "INFO",
    }

    def __init__(
        self,
        subreddits: list[str] | None = None,
        keywords: list[str] | None = None,
        max_pages: int = 5,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.subreddits = subreddits or [
            "googlephotos",
            "photography",
            "iphone",
        ]
        self.keywords = keywords or [
            "can't find photo",
            "search not working",
            "find old photos",
            "photo search",
            "looking for a picture",
        ]
        self.max_pages = int(max_pages)
        self.dedup = DedupEngine()
        self._output_dir = Path("data/raw/reddit")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def start_requests(self):
        """Generate search URLs for each subreddit + keyword combination."""
        for subreddit in self.subreddits:
            # Fetch subreddit's recent posts
            url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
            yield scrapy.Request(
                url=url,
                callback=self.parse_listing,
                meta={"subreddit": subreddit, "page": 1},
                headers={"Accept": "application/json"},
            )

            # Search within subreddit for each keyword
            for keyword in self.keywords:
                search_url = (
                    f"https://www.reddit.com/r/{subreddit}/search.json"
                    f"?q={keyword}&restrict_sr=on&sort=relevance&t=all&limit=100"
                )
                yield scrapy.Request(
                    url=search_url,
                    callback=self.parse_listing,
                    meta={
                        "subreddit": subreddit,
                        "keyword": keyword,
                        "page": 1,
                    },
                    headers={"Accept": "application/json"},
                )

    def parse_listing(self, response):
        """Parse a subreddit listing page and follow links to individual posts."""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from %s", response.url)
            return

        listing = data.get("data", {})
        children = listing.get("children", [])

        if not children:
            logger.info("No posts found at %s", response.url)
            return

        for child in children:
            post_data = child.get("data", {})
            post_id = post_data.get("id", "")
            permalink = post_data.get("permalink", "")

            if not permalink:
                continue

            # Fetch full post with comments
            post_url = f"https://www.reddit.com{permalink}.json?limit=500"
            yield scrapy.Request(
                url=post_url,
                callback=self.parse_post,
                meta={
                    "subreddit": response.meta.get("subreddit"),
                    "post_id": post_id,
                },
                headers={"Accept": "application/json"},
            )

        # Pagination — follow "after" cursor
        after = listing.get("after")
        current_page = response.meta.get("page", 1)
        if after and current_page < self.max_pages:
            next_url = response.url.split("&after=")[0] + f"&after={after}"
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_listing,
                meta={
                    **response.meta,
                    "page": current_page + 1,
                },
                headers={"Accept": "application/json"},
            )

    def parse_post(self, response):
        """Parse a single Reddit post with its comment tree."""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logger.error("Failed to parse post JSON from %s", response.url)
            return

        if not isinstance(data, list) or len(data) < 1:
            return

        # First element is the post, second is comments
        post_listing = data[0].get("data", {}).get("children", [])
        if not post_listing:
            return

        post_data = post_listing[0].get("data", {})
        post_id = post_data.get("id", "")
        author = post_data.get("author", "[deleted]")
        created_utc = post_data.get("created_utc", 0)
        title = post_data.get("title", "")
        selftext = post_data.get("selftext", "")
        subreddit = post_data.get("subreddit", response.meta.get("subreddit", ""))
        permalink = post_data.get("permalink", "")
        score = post_data.get("score", 0)
        num_comments = post_data.get("num_comments", 0)

        # Extract comments
        comments = []
        if len(data) > 1:
            comment_listing = data[1].get("data", {}).get("children", [])
            comments = self._extract_comments(comment_listing, max_depth=5)

        # Build the full text for dedup check
        full_text = f"{title} {selftext}"
        content_snippet = full_text[:200] if full_text else ""

        # Check for duplicates
        dedup_key = f"reddit|{author}|{created_utc}|{content_snippet}"
        if self.dedup.is_duplicate(dedup_key):
            logger.debug("Skipping duplicate post: %s", post_id)
            return

        # Yield structured item
        yield {
            "source_platform": "reddit",
            "post_id": post_id,
            "subreddit": subreddit,
            "title": title,
            "body": selftext,
            "author": author,
            "timestamp": datetime.fromtimestamp(
                created_utc, tz=timezone.utc
            ).isoformat(),
            "url": f"https://www.reddit.com{permalink}",
            "score": score,
            "num_comments": num_comments,
            "comments": comments,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_comments(
        self, children: list, max_depth: int = 5, current_depth: int = 0
    ) -> list[dict]:
        """
        Recursively extract comments from Reddit's nested comment tree.

        Caps recursion at max_depth to prevent excessive nesting.
        """
        if current_depth >= max_depth:
            return []

        comments = []
        for child in children:
            if child.get("kind") != "t1":  # t1 = comment
                continue

            comment_data = child.get("data", {})
            author = comment_data.get("author", "[deleted]")
            body = comment_data.get("body", "")
            created_utc = comment_data.get("created_utc", 0)
            score = comment_data.get("score", 0)
            comment_id = comment_data.get("id", "")

            # Skip deleted/removed comments with no content
            if body in ("[deleted]", "[removed]", ""):
                continue

            comment = {
                "comment_id": comment_id,
                "author": author,
                "body": body,
                "timestamp": datetime.fromtimestamp(
                    created_utc, tz=timezone.utc
                ).isoformat(),
                "score": score,
                "replies": [],
            }

            # Recursively extract replies
            replies_data = comment_data.get("replies", "")
            if isinstance(replies_data, dict):
                reply_children = (
                    replies_data.get("data", {}).get("children", [])
                )
                comment["replies"] = self._extract_comments(
                    reply_children, max_depth, current_depth + 1
                )

            comments.append(comment)

        return comments
