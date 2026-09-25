def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Discovery Engine API is running"}

def test_get_stats(client):
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_chunks"] == 100
    assert "reddit" in data["by_platform"]

def test_get_sources(client):
    response = client.get("/api/v1/sources?platform=reddit&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
