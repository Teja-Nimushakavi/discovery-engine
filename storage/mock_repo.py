import json
from pathlib import Path

class MockRepository:
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        
    def get_stats(self):
        """Mock stats directly from the scraped jsonl files."""
        stats = {
            "total_chunks": 0,
            "by_platform": {},
            "by_taxonomy": {
                "retrieval_failure": 45,
                "feature_request": 12,
                "workaround": 8,
                "praise": 5
            },
            "by_frustration": {
                "high": 35,
                "medium": 20,
                "low": 15
            }
        }
        
        # Read from google play
        gp_file = self.data_dir / "google_play" / "real_data.jsonl"
        if gp_file.exists():
            with open(gp_file, "r", encoding="utf-8") as f:
                lines = [line for line in f if line.strip()]
                stats["by_platform"]["google_play"] = len(lines)
                stats["total_chunks"] += len(lines)
                
        # Read from reddit
        rd_file = self.data_dir / "reddit" / "real_data.jsonl"
        if rd_file.exists():
            with open(rd_file, "r", encoding="utf-8") as f:
                lines = [line for line in f if line.strip()]
                stats["by_platform"]["reddit"] = len(lines)
                stats["total_chunks"] += len(lines)
                
        # Fallback dummy data if nothing is scraped yet
        if stats["total_chunks"] == 0:
            stats["total_chunks"] = 1500
            stats["by_platform"] = {
                "google_play": 800,
                "apple_app_store": 400,
                "reddit_threads": 200,
                "support_forums": 100
            }
            
        return stats
