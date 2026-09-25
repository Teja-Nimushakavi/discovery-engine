# Discovery Engine: Project Handoff

Welcome to the **Discovery Engine**, an AI-powered UX research tool designed to analyze the "Photo Retrieval Cognitive Gap." This document provides a high-level overview of the completed system architecture, key design decisions, and guidance for ongoing maintenance.

## 1. System Overview

The Discovery Engine ingests thousands of public user feedback posts (from Reddit, App Store, Google Play, Support Forums, and YouTube) and uses a Retrieval-Augmented Generation (RAG) pipeline to extract insights about how users recall and search for old photos.

The system is broken down into three major components:
1. **The Ingestion Pipeline:** Crawls data, cleans it, performs Named Entity Recognition (NER) to extract memory anchors, and embeddings via `BGE`.
2. **The API & Storage:** Stores dense embeddings in **Pinecone/ChromaDB** and rich structured metadata in **PostgreSQL**. A **FastAPI** application serves this data securely.
3. **The Web Dashboard:** A premium, bespoke **Vite + React** single-page application featuring a Dark Mode Glassmorphism aesthetic.

## 2. Key Architectural Decisions

### 2.1 100% Local NLP Pipeline
Instead of relying on expensive LLM calls (like OpenAI or Groq) to categorize every single scraped review, we implemented a completely free, lightning-fast Local NLP pipeline.
- **Frustration Scoring:** Uses `vaderSentiment` to automatically detect if a user is mildly annoyed or completely abandoning the app.
- **Entity Extraction:** Uses `spaCy` to extract Noun Chunks (representing features the user is mentioning) and Memory Anchors (who, what, where).
- **Taxonomy:** Uses a robust Regex mapping dictionary (`TAXONOMY_RULES`) to categorize feedback.

### 2.2 Groq-Powered Intelligence
We exclusively utilize Groq (with Llama 3) for the final "intelligence" steps because of its unmatched inference speed:
- **Query Routing:** The system dynamically categorizes your natural language questions to use the most optimal prompt template.
- **Synthesis:** The final RAG synthesis is generated almost instantly by Groq.
- **Cross-Platform Comparison:** We use Groq to summarize and compare the synthesized answers from Apple Users vs. Google Users.

### 2.3 Cloud-Ready Deployment (GitHub Actions)
The final architecture completely removes the need to run Docker locally. 
- You can develop entirely using `npm run dev` and `uvicorn`. 
- When you push to the `main` branch, **GitHub Actions** will automatically build the `discovery-api` and `discovery-frontend` Docker images.

## 3. Future Enhancements & Roadmap Ideas

While the MVP is complete and production-ready, here are ways to expand the system:

1. **Automated Report Emails:** Hook the `reports/generator.py` into a Cloud Scheduler job and integrate SendGrid to automatically email a weekly UX digest to stakeholders.
2. **More Data Sources:** Add crawlers for X (Twitter) or specialized photography forums like DPReview.
3. **User Authentication:** Add NextAuth or Firebase Auth to the React dashboard if you wish to expose it outside the internal network.

## 4. Operational Runbook

For daily operations, error handling, and manual overrides, please refer to the [Runbook (RUNBOOK.md)](RUNBOOK.md).
