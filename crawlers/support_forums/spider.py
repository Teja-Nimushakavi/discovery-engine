"""
Support Forums Spiders for the Discovery Engine.

Crawls Google Support Community and Apple Discussions for threads
related to photo retrieval. Outputs JSONL files with structured
thread data (original post + replies).
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import scrapy
from scrapy.crawler import CrawlerProcess

from crawlers.dedup import DedupEngine
from config.settings import RETRIEVAL_KEYWORDS

logger = logging.getLogger(__name__)


class GoogleSupportSpider(scrapy.Spider):
    """
    Spider that searches Google Support Community for photo-retrieval threads.
    """
    
    name = "google_support"
    allowed_domains = ["support.google.com"]
    
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "ROBOTSTXT_OBEY": False, # Sometimes blocks search
        "USER_AGENT": "DiscoveryEngine/0.1 (Research Project)",
        "CONCURRENT_REQUESTS": 2,
        "LOG_LEVEL": "INFO",
    }

    def __init__(
        self,
        max_pages: int = 5,
        output_dir: str = "data/raw/support_forums",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.keywords = RETRIEVAL_KEYWORDS[:5] # Use top 5 keywords to avoid too many searches
        self.max_pages = int(max_pages)
        self.dedup = DedupEngine()
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._out_file = None

    def open_spider(self, spider):
        filename = self._output_dir / f"google_support_{self._timestamp}.jsonl"
        self._out_file = open(filename, "w", encoding="utf-8")
        logger.info(f"Writing Google Support threads to {filename}")

    def close_spider(self, spider):
        if self._out_file:
            self._out_file.close()

    def start_requests(self):
        """Generate search URLs for each keyword."""
        for keyword in self.keywords:
            url = (
                f"https://support.google.com/photos/search"
                f"?q={keyword}&from_promoted_search=true"
            )
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={"keyword": keyword, "page": 1},
            )

    def parse_search_results(self, response):
        """Parse search results page and follow links to community threads."""
        thread_links = response.css("a.thread-list-thread::attr(href)").getall()
        if not thread_links:
            # Fallback if class changes
            thread_links = response.css("a[href*='/thread/']::attr(href)").getall()
            
        for link in thread_links:
            url = response.urljoin(link)
            yield scrapy.Request(
                url=url,
                callback=self.parse_thread,
                meta={"keyword": response.meta.get("keyword")},
            )
            
        # Pagination
        current_page = response.meta.get("page", 1)
        next_page_link = response.css("a.next-page::attr(href)").get()
        if next_page_link and current_page < self.max_pages:
            yield scrapy.Request(
                url=response.urljoin(next_page_link),
                callback=self.parse_search_results,
                meta={
                    "keyword": response.meta.get("keyword"),
                    "page": current_page + 1,
                },
            )

    def parse_thread(self, response):
        """Parse a single support thread with its original post and replies."""
        title = response.css("h1::text").get("").strip()
        body_parts = response.css(".thread-body p::text").getall()
        body = "\n".join([p.strip() for p in body_parts if p.strip()])
        author = response.css(".author-name::text").get("anonymous").strip()
        
        if not body and not title:
            # Try alternative selectors
            title = response.css("title::text").get("").strip()
            body = " ".join(response.css("div.post-content ::text").getall()).strip()
            
        if not body and not title:
            return
            
        full_text = f"{title}\n{body}"
        content_snippet = full_text[:200]
        
        dedup_key = f"support_forums|google|{author}|{content_snippet}"
        if self.dedup.is_duplicate(dedup_key):
            return
            
        # Extract replies
        replies = []
        for reply_block in response.css(".reply-block, .message-block"):
            reply_author = reply_block.css(".author-name::text").get("anonymous").strip()
            reply_body_parts = reply_block.css(".reply-body p::text, .message-content ::text").getall()
            reply_body = "\n".join([p.strip() for p in reply_body_parts if p.strip()])
            
            if reply_body:
                replies.append({
                    "author": reply_author,
                    "body": reply_body,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
        item = {
            "source_platform": "support_forums",
            "app_referenced": "Google Photos",
            "thread_id": response.url.split("/")[-1].split("?")[0],
            "title": title,
            "body": body,
            "author": author,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "url": response.url,
            "replies": replies,
            "resolved_status": bool(response.css(".resolved-badge")),
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if self._out_file:
            self._out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        yield item


class AppleSupportSpider(scrapy.Spider):
    """
    Spider that searches Apple Discussions for iCloud Photos retrieval threads.
    """
    
    name = "apple_support"
    allowed_domains = ["discussions.apple.com"]
    
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "ROBOTSTXT_OBEY": False,
        "USER_AGENT": "DiscoveryEngine/0.1 (Research Project)",
        "CONCURRENT_REQUESTS": 2,
        "LOG_LEVEL": "INFO",
    }

    def __init__(
        self,
        max_pages: int = 5,
        output_dir: str = "data/raw/support_forums",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.keywords = RETRIEVAL_KEYWORDS[:5]
        self.max_pages = int(max_pages)
        self.dedup = DedupEngine()
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._out_file = None

    def open_spider(self, spider):
        filename = self._output_dir / f"apple_support_{self._timestamp}.jsonl"
        self._out_file = open(filename, "w", encoding="utf-8")
        logger.info(f"Writing Apple Support threads to {filename}")

    def close_spider(self, spider):
        if self._out_file:
            self._out_file.close()

    def start_requests(self):
        """Generate search URLs for each keyword."""
        for keyword in self.keywords:
            # Search within photos community
            url = f"https://discussions.apple.com/search?q={keyword}&community=1008"
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={"keyword": keyword, "page": 1},
            )

    def parse_search_results(self, response):
        """Parse Apple Discussions search results."""
        thread_links = response.css("a[href*='/thread/']::attr(href)").getall()
            
        for link in thread_links:
            url = response.urljoin(link)
            yield scrapy.Request(
                url=url,
                callback=self.parse_thread,
                meta={"keyword": response.meta.get("keyword")},
            )
            
        current_page = response.meta.get("page", 1)
        next_page = response.css("a.pagination-next::attr(href)").get()
        if next_page and current_page < self.max_pages:
            yield scrapy.Request(
                url=response.urljoin(next_page),
                callback=self.parse_search_results,
                meta={
                    "keyword": response.meta.get("keyword"),
                    "page": current_page + 1,
                },
            )

    def parse_thread(self, response):
        """Parse Apple Discussions thread."""
        title = response.css("h1::text").get("").strip()
        body = " ".join(response.css(".post-content ::text").getall()).strip()
        author = response.css(".author-name::text").get("anonymous").strip()
        
        if not body and not title:
            return
            
        dedup_key = f"support_forums|apple|{author}|{body[:200]}"
        if self.dedup.is_duplicate(dedup_key):
            return
            
        # Extract replies
        replies = []
        for reply_block in response.css(".reply, .comment"):
            reply_author = reply_block.css(".author-name::text").get("anonymous").strip()
            reply_body = " ".join(reply_block.css(".post-content ::text").getall()).strip()
            
            if reply_body:
                replies.append({
                    "author": reply_author,
                    "body": reply_body,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
        item = {
            "source_platform": "support_forums",
            "app_referenced": "Apple Photos",
            "thread_id": response.url.split("/")[-1].split("?")[0],
            "title": title,
            "body": body,
            "author": author,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "url": response.url,
            "replies": replies,
            "resolved_status": bool(response.css(".solved, .helpful")),
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if self._out_file:
            self._out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        yield item


def run_spiders():
    """Run both support forum spiders sequentially."""
    import logging
    logging.getLogger('scrapy').setLevel(logging.DEBUG)
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "DEBUG"
    })
    process.crawl(GoogleSupportSpider)
    process.crawl(AppleSupportSpider)
    process.start()

if __name__ == "__main__":
    run_spiders()
