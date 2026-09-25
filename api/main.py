from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from storage.models import get_engine, create_tables
import os

from .routes import analytics, explore, rag

app = FastAPI(title="Discovery Engine API", version="0.1.0")

import time
from collections import defaultdict

# Security: API Key Authentication
API_KEY = os.getenv("DISCOVERY_API_KEY", "dev_key")

# Rate Limiting (100 requests/min per IP/Key)
request_history = defaultdict(list)
RATE_LIMIT = 100
RATE_LIMIT_WINDOW = 60

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    # Skip auth for root or OPTIONS requests (CORS)
    if request.url.path == "/" or request.method == "OPTIONS":
        return await call_next(request)
        
    client_key = request.headers.get("X-API-Key")
    # For local development, if DISCOVERY_API_KEY is not strictly set, we allow it to proceed gracefully
    # In production, this guarantees only clients with the key can hit the API
    if API_KEY != "dev_key" and client_key != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized: Invalid or missing API Key"})
        
    # Rate Limiting
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    # Clean up old requests
    request_history[client_ip] = [req_time for req_time in request_history[client_ip] if current_time - req_time < RATE_LIMIT_WINDOW]
    
    if len(request_history[client_ip]) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests: Rate limit exceeded (100 req/min)"})
        
    request_history[client_ip].append(current_time)
        
    response = await call_next(request)
    return response

# Allow CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(explore.router, prefix="/api/explore", tags=["explore"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])

@app.on_event("startup")
def startup_event():
    # Ensure tables exist
    engine = get_engine()
    create_tables(engine)

@app.get("/")
def read_root():
    return {"message": "Discovery Engine API is running."}
