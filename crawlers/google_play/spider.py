import json
import logging
from datetime import datetime, timezone
import os
from google_play_scraper import reviews, Sort

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_google_play_data():
    app_id = 'com.google.android.apps.photos'
    
    logger.info(f"Fetching reviews for {app_id}...")
    
    result, continuation_token = reviews(
        app_id,
        lang='en',
        country='us',
        sort=Sort.NEWEST,
        count=1000
    )
    
    logger.info(f"Fetched {len(result)} total reviews.")
    
    # Filter for retrieval-related keywords
    keywords = ["search", "find", "lost", "missing", "remember", "forget", "can't find", "couldn't find", "where is", "retrieval"]
    filtered_reviews = []
    
    for r in result:
        content = r.get("content", "").lower()
        if any(kw in content for kw in keywords):
            filtered_reviews.append(r)
            
    logger.info(f"Filtered down to {len(filtered_reviews)} reviews focused on photo retrieval issues.")
    
    output_dir = "data/raw/google_play"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/real_data.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for r in filtered_reviews:
            item = {
                "source_platform": "google_play",
                "post_id": r.get("reviewId", ""),
                "subreddit": "", # Not applicable
                "title": "", # Play store reviews don't have titles
                "body": r.get("content", ""),
                "author": r.get("userName", "Anonymous"),
                "timestamp": r.get("at", datetime.now()).isoformat() if not isinstance(r.get("at"), datetime) else r.get("at").isoformat(),
                "url": f"https://play.google.com/store/apps/details?id={app_id}&reviewId={r.get('reviewId')}",
                "score": r.get("score", 0),
                "num_comments": 0,
                "comments": [],
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(item) + "\n")
            
    logger.info(f"Successfully wrote {len(filtered_reviews)} retrieval-focused reviews to {output_file}")

if __name__ == "__main__":
    fetch_google_play_data()
