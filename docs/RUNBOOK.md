# Discovery Engine: Operational Runbook

This document contains standard operating procedures (SOPs) for maintaining and troubleshooting the Discovery Engine pipeline and API.

## 1. Local Development Commands

**Start the PostgreSQL Database (if you have Docker locally):**
```bash
docker-compose up -d db
```
*(If you do not use Docker locally, ensure your native PostgreSQL service is running).*

**Start the FastAPI Backend:**
```bash
cd discovery-engine
uvicorn api.main:app --reload
```

**Start the React Frontend:**
```bash
cd discovery-engine/frontend
npm run dev
```

## 2. Triggering the Crawl Pipeline

To manually ingest new data from the web (Reddit, Support Forums, App Stores):
```bash
cd discovery-engine
python scripts/run_pipeline.py
```
This script will:
1. Fire off the Scrapy spiders to grab new threads.
2. Deduplicate against existing data.
3. Run the local NLP enrichment (VaderSentiment, spaCy).
4. Chunk and Embed the text into Pinecone.
5. Save the structured metadata into PostgreSQL.

## 3. Database Maintenance

### 3.1 Dropping and Recreating Tables
If you made changes to `storage/models.py` and need to reset the Postgres database:
```python
from storage.models import drop_tables, create_tables, get_engine
engine = get_engine()
drop_tables(engine)
create_tables(engine)
```

### 3.2 Clearing Pinecone Vectors
To completely wipe your Pinecone index before a fresh run:
```python
import pinecone
from config.settings import PINECONE_API_KEY, PINECONE_INDEX_NAME
pc = pinecone.Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
index.delete(deleteAll=True)
```

## 4. Key Rotation and Secrets

The application relies on secrets stored in the `.env` file (or in GitHub Secrets / Google Secret Manager for production). 

If you need to rotate a key (e.g. `GROQ_API_KEY`):
1. Generate the new key from the provider.
2. Update your local `.env` file.
3. Update the `GROQ_API_KEY` GitHub Secret in your repository settings (Settings > Secrets and variables > Actions).
4. Restart your `uvicorn` server locally.

## 5. Troubleshooting API Key Authentication

The API uses `DISCOVERY_API_KEY` for authentication.
- **In local development**: If `DISCOVERY_API_KEY` is not explicitly set in your `.env`, it defaults to `"dev_key"`, and the middleware allows traffic through (no headers required).
- **In production**: You **MUST** set `DISCOVERY_API_KEY` to a strong, secure value in your environment variables. 
- All production requests must include this header: `X-API-Key: your_secure_key`. If the header is missing, the API returns a `401 Unauthorized` error.
