"""
Automated Weekly Report Generation Pipeline.

This script runs the 5 standard discovery questions across all platforms,
generates a comprehensive report, and saves it.

Can be triggered manually or via Cloud Scheduler / cron.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rag.engine import RAGEngine
from rag.comparator import CrossPlatformComparator
from reports.generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# The 5 standard discovery questions
DISCOVERY_QUESTIONS = [
    "What kinds of old photos do users struggle to retrieve?",
    "What information do people actually remember about a photo?",
    "What information have users forgotten?",
    "How do users formulate searches?",
    "What are the cascading failure loops?"
]

def run_weekly_reports():
    logger.info("Initializing RAG Engine and Comparator...")
    try:
        rag_engine = RAGEngine()
        comparator = CrossPlatformComparator(rag_engine=rag_engine)
        generator = ReportGenerator(rag_engine=rag_engine, comparator=comparator)
    except Exception as e:
        logger.error(f"Failed to initialize engines: {e}")
        return

    logger.info(f"Starting automated report generation for {len(DISCOVERY_QUESTIONS)} standard queries.")
    
    generated_files = []
    
    for query in DISCOVERY_QUESTIONS:
        logger.info(f"--- Processing: {query} ---")
        try:
            filepath = generator.generate_report(query)
            generated_files.append(filepath)
        except Exception as e:
            logger.error(f"Failed to generate report for query '{query}': {e}")
            
    logger.info(f"Automated generation complete. Created {len(generated_files)} reports.")
    for f in generated_files:
        logger.info(f" - {f}")

if __name__ == "__main__":
    run_weekly_reports()
