import logging
import hashlib
from typing import List, Optional

from storage.models import get_engine
from storage.metadata_repo import MetadataRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def hash_pii(data: str, salt: str = "discovery_engine_salt") -> str:
    """Hashes PII using SHA-256 with a salt."""
    if not data:
        return data
    payload = f"{salt}_{data}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def audit_and_hash_author_ids():
    """
    Audits the PostgreSQL database for raw author IDs that haven't been hashed 
    (assuming they might contain PII like email addresses or real names) 
    and hashes them in place.
    """
    logger.info("Starting security audit for PII in Author IDs...")
    engine = get_engine()
    repo = MetadataRepository(engine)
    
    # In a real scenario, this would paginate through the DB and update records
    # For now, we simulate the audit process
    with repo.Session() as session:
        # Example logic: Find records where author_id doesn't look like a 64-char hex string
        # This is a basic heuristic; a production system might have a dedicated flag.
        from storage.models import FeedbackChunk
        
        # We fetch all (or a batch)
        # Note: If database is large, use yield_per or limit/offset
        records = session.query(FeedbackChunk).filter(
            FeedbackChunk.author_id.isnot(None)
        ).all()
        
        updated_count = 0
        for record in records:
            # Simple heuristic: if it's exactly 64 chars and hex, it's likely already hashed
            if len(record.author_id) == 64 and all(c in '0123456789abcdefABCDEF' for c in record.author_id):
                continue
                
            # Otherwise, hash it
            original = record.author_id
            hashed = hash_pii(original)
            record.author_id = hashed
            updated_count += 1
            
        if updated_count > 0:
            session.commit()
            logger.info(f"Successfully audited and hashed {updated_count} author IDs.")
        else:
            logger.info("No unhashed author IDs found. Audit passed.")

def verify_secrets_manager():
    """
    Placeholder for verifying that secrets are loaded from GCP Secret Manager 
    rather than .env files in production.
    """
    logger.info("Verifying Secrets Management configuration...")
    import os
    if os.environ.get("ENVIRONMENT") == "production":
        # Check if critical secrets exist in environment
        critical_vars = ["GROQ_API_KEY", "PINECONE_API_KEY", "DATABASE_URL"]
        missing = [v for v in critical_vars if not os.environ.get(v)]
        
        if missing:
            logger.error(f"SECURITY ALERT: Missing critical environment variables in production: {missing}")
            return False
            
        logger.info("All critical secrets are present in the environment.")
    else:
        logger.info("Non-production environment. Skipping strict secrets check.")
    return True

if __name__ == "__main__":
    audit_and_hash_author_ids()
    verify_secrets_manager()
    logger.info("Security audit completed.")
