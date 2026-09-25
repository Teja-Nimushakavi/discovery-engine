import json
import logging
from datetime import datetime, timezone
import requests
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_reddit_data():
    headers = {"User-Agent": "DiscoveryEngine/0.1 (Research Project)"}
    # Search r/googlephotos for "can't find photo"
    url = "https://www.reddit.com/r/googlephotos/search.json?q=can't find photo&restrict_sr=on&sort=relevance&t=all&limit=10"
    
    logger.info(f"Fetching from {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed: {response.status_code} - {response.text}")
        return
        
    data = response.json()
    children = data.get("data", {}).get("children", [])
    
    output_dir = "data/raw/reddit"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/real_data.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for child in children:
            post_data = child.get("data", {})
            
            # Create the structured object we expect
            item = {
                "source_platform": "reddit",
                "post_id": post_data.get("id", ""),
                "subreddit": post_data.get("subreddit", ""),
                "title": post_data.get("title", ""),
                "body": post_data.get("selftext", ""),
                "author": post_data.get("author", ""),
                "timestamp": datetime.fromtimestamp(
                    post_data.get("created_utc", 0), tz=timezone.utc
                ).isoformat(),
                "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "comments": [], # Skipping deep comments for this quick test
                "crawled_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(item) + "\n")
            
    logger.info(f"Successfully wrote {len(children)} real posts to {output_file}")

if __name__ == "__main__":
    fetch_reddit_data()
