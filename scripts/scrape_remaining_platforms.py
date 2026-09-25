"""
Script to orchestrate the scraping of the remaining data sources:
- Apple App Store
- YouTube Comments
- Support Forums (Google / Apple)
"""
import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlers.apple_app_store.scraper import AppleAppStoreScraper
from crawlers.youtube.scraper import YouTubeScraper
# We will use subprocess to run the Scrapy spiders to avoid Twisted reactor issues
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_apple_app_store():
    logger.info("=== Starting Apple App Store Scraper ===")
    try:
        with AppleAppStoreScraper() as scraper:
            # Scrape up to 10 pages for each app (max allowed by iTunes RSS)
            reviews = scraper.scrape_all_apps()
            logger.info(f"Finished scraping {len(reviews)} reviews from Apple App Store.")
    except Exception as e:
        logger.error(f"Error scraping Apple App Store: {e}")

def scrape_youtube():
    logger.info("=== Starting YouTube Scraper ===")
    try:
        with YouTubeScraper() as scraper:
            # The TARGET_APPS config defines the video_ids to scrape
            comments = scraper.scrape_all_apps()
            logger.info(f"Finished scraping {len(comments)} comments from YouTube.")
    except Exception as e:
        logger.error(f"Error scraping YouTube: {e}")

def scrape_support_forums():
    logger.info("=== Starting Support Forums Scraper ===")
    try:
        # Run the Scrapy process as a module so imports resolve correctly
        subprocess.run([sys.executable, "-m", "crawlers.support_forums.spider"], check=True)
        logger.info("Finished scraping Support Forums.")
    except Exception as e:
        logger.error(f"Error scraping Support Forums: {e}")

def main():
    logger.info("Starting multi-platform scraping pipeline...")
    
    # 1. Apple App Store
    scrape_apple_app_store()
    
    # 2. YouTube Comments
    scrape_youtube()
    
    # 3. Support Forums
    scrape_support_forums()
    
    logger.info("Multi-platform scraping pipeline complete!")

if __name__ == "__main__":
    main()
