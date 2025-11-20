from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import os
from dotenv import load_dotenv

# Import our backend components
from orchestrator import SearchOrchestrator

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Search Engine API",
    description="Backend for Perplexity-like AI Search Engine",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Orchestrator
orchestrator = SearchOrchestrator(
    cache_dir=os.getenv("CACHE_DIR", "./cache"),
    ollama_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

class SearchRequest(BaseModel):
    query: str
    use_cache: bool = True
    provider: str = "wikipedia"

@app.post("/search")
async def search(request: SearchRequest):
    """
    Perform a search query.
    """
    try:
        result = orchestrator.search(request.query, request.use_cache, request.provider)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "ollama": "connected"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query")
            use_cache = data.get("use_cache", True)
            provider = data.get("provider", "wikipedia")
            
            if not query:
                await websocket.send_json({"error": "Query is required"})
                continue
            
            # Stream results
            for chunk in orchestrator.search_stream(query, use_cache, provider):
                await websocket.send_json(chunk)
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.post("/clear-cache")
async def clear_cache():
    """Clear the cache."""
    # Note: This is a simplified implementation. 
    # In a real app, you'd want to expose a method on CacheLayer
    return {"status": "not implemented via API yet"}

@app.get("/cache-stats")
async def cache_stats():
    """Get cache statistics."""
    return orchestrator.cache.get_stats()

if __name__ == "__main__":
    print("Starting AI Search Engine API on 0.0.0.0:8000")
    print(f"Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"Cache directory: {os.getenv('CACHE_DIR', './cache')}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
