import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
import api.main

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def override_repo():
    # Use a dummy class that implements the required methods for testing
    class DummyRepo:
        def get_stats(self):
            return {
                "total_chunks": 100,
                "by_platform": {"reddit": 100},
                "by_taxonomy": {},
                "by_frustration": {}
            }
            
        def get_chunks_by_platform(self, platform, limit=50):
            return []

    # Save original
    original_repo = api.main._repo
    api.main._repo = DummyRepo()
    
    yield
    
    # Restore original
    api.main._repo = original_repo
