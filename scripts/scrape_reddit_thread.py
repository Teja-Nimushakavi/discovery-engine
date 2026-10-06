import json
import logging
from datetime import datetime, timezone
import requests
import os
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_reddit_thread(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) (Research Project)"}
    json_url = url.rstrip('/') + '.json'
    
    logger.info(f"Fetching from {json_url}")
    response = requests.get(json_url, headers=headers)
    
    if response.status_code != 200:
        logger.error(f"Failed: {response.status_code} - {response.text}")
        return
        
    data = response.json()
    
    # data is a list: [0] = post, [1] = comments
    post_data = data[0]['data']['children'][0]['data']
    comments_data = data[1]['data']['children']
    
    output_dir = "data/raw/reddit_threads"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/thread_data.jsonl"
    count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        # Write post
        post_item = {
            "source_platform": "reddit_threads",
            "post_id": post_data.get("id", ""),
            "author": post_data.get("author", ""),
            "timestamp": datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc).isoformat(),
            "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
            "score": post_data.get("score", 0),
            "cleaned_text": f"Title: {post_data.get('title', '')}\n\n{post_data.get('selftext', '')}"
        }
        f.write(json.dumps(post_item) + "\n")
        count += 1
        
        # Write comments
        for child in comments_data:
            if child['kind'] == 't1':  # t1 = comment
                comment = child['data']
                if not comment.get('body'):
                    continue
                comment_item = {
                    "source_platform": "reddit_threads",
                    "post_id": comment.get("id", ""),
                    "author": comment.get("author", ""),
                    "timestamp": datetime.fromtimestamp(comment.get("created_utc", 0), tz=timezone.utc).isoformat(),
                    "url": f"https://www.reddit.com{comment.get('permalink', '')}",
                    "score": comment.get("score", 0),
                    "cleaned_text": comment.get('body', '')
                }
                f.write(json.dumps(comment_item) + "\n")
                count += 1
            
    logger.info(f"Successfully wrote {count} items (post + comments) to {output_file}")
    return output_file

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://www.reddit.com/r/GooglePixel/comments/1qbdo8i/google_photos_removing_search_and_replacing_it/"
    fetch_reddit_thread(url)
