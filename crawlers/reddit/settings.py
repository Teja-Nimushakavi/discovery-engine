"""
Scrapy settings for the Reddit spider.

These settings are loaded by Scrapy when running the spider.
They enforce respectful crawling behavior.
"""

BOT_NAME = "discovery_engine"

SPIDER_MODULES = ["crawlers.reddit"]
NEWSPIDER_MODULE = "crawlers.reddit"

# Crawl responsibly — identify yourself and respect robots.txt
ROBOTSTXT_OBEY = True
USER_AGENT = (
    "DiscoveryEngine/0.1 (Research Project; photo retrieval UX analysis)"
)

# Rate limiting — be respectful to Reddit's servers
DOWNLOAD_DELAY = 2.0
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

# HTTP cache (for development — avoids re-fetching during testing)
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = "httpcache"

# Output
FEED_EXPORT_ENCODING = "utf-8"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# Auto-throttle (adaptive rate limiting)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
