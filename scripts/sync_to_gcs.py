"""
Sync local raw data to Google Cloud Storage.

Usage:
    python scripts/sync_to_gcs.py
"""

import os
import glob
import logging
from pathlib import Path
from google.cloud import storage

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "discovery-engine-raw")

def sync_directory_to_gcs(local_dir: str, gcs_prefix: str):
    """Syncs a local directory of JSONL files to a GCS prefix."""
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
    except Exception as e:
        logger.warning(f"Could not initialize GCS client (ensure google-cloud-storage is installed and auth is configured): {e}")
        return

    local_path = Path(local_dir)
    if not local_path.exists():
        logger.warning(f"Local directory {local_dir} does not exist. Skipping.")
        return

    for file_path in local_path.glob("*.jsonl"):
        blob_name = f"{gcs_prefix}/{file_path.name}"
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            logger.info(f"Uploading {file_path} to gs://{GCS_BUCKET_NAME}/{blob_name}")
            blob.upload_from_filename(str(file_path))
        else:
            logger.debug(f"File {blob_name} already exists in GCS. Skipping.")

def main():
    logger.info("Starting GCS sync...")
    
    # Define mappings of local directory to GCS prefix
    sync_mappings = [
        ("data/raw/reddit", "reddit"),
        ("data/raw/google_play", "google_play"),
        ("data/raw/apple_app_store", "apple_app_store"),
        ("data/raw/support_forums", "support_forums"),
        ("data/raw/youtube", "youtube_comments"),
    ]
    
    for local_dir, gcs_prefix in sync_mappings:
        sync_directory_to_gcs(local_dir, gcs_prefix)
        
    logger.info("GCS sync completed.")

if __name__ == "__main__":
    main()
