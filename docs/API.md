# Discovery Engine: API Reference

The Discovery Engine API is built using **FastAPI** and conforms to the OpenAPI specification. 

## Interactive Documentation

Because we use FastAPI, you do not need to read static documentation! The API automatically generates interactive documentation where you can test the endpoints directly from your browser.

When the server is running (`uvicorn api.main:app --reload`), visit:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Core Endpoints

### `POST /api/rag/`
Submits a natural language discovery question to the RAG engine.
- **Request Body:** `{"query": "string", "namespaces": ["string"]}`
- **Response:** `{"answer": "string", "retrieved_chunks": [...]}`

### `POST /api/rag/compare`
Submits a query to the Cross-Platform Comparator to analyze differences between apps.
- **Request Body:** `{"query": "string", "namespaces": ["string"]}`
- **Response:** `{"comparison": {"similarities": [...], "differences": [...]}, "platform_answers": {...}}`

### `GET /api/analytics/summary`
Retrieves aggregated statistics from PostgreSQL for the dashboard charts.
- **Response:** `{"total_chunks": int, "taxonomy": [...], "frustration": [...]}`

### `GET /api/explore/`
Paginated endpoint to explore the raw user feedback.
- **Query Params:** `page` (int), `limit` (int), `app` (string), `taxonomy` (string)

## Security
If deployed in production with the `DISCOVERY_API_KEY` environment variable set, all requests (except to the `/` healthcheck) must include the following header:
```
X-API-Key: <your_secret_key>
```
