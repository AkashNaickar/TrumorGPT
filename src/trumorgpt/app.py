"""
FastAPI Server Entry Point for TrumorGPT Backend Core & Web UI Frontend
Exposes REST API endpoints:
- POST /api/v1/fact-check
- POST /api/v1/seed-graph
- GET /health
- GET / (Serves Static Web UI)
"""

import os

from dotenv import load_dotenv

# Load .env file (GEMINI_API_KEY, etc.) from project root
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_project_root, ".env"))


from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from trumorgpt.pipeline import TrumorGPTPipeline

app = FastAPI(
    title="TrumorGPT REST API & Web UI",
    description="Topic-Enhanced TextRank & GraphRAG Health Fact-Checking Pipeline",
    version="1.0.0"
)

# Global Pipeline Instance
pipeline = TrumorGPTPipeline()

# Mount Static Assets Directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class FactCheckRequest(BaseModel):
    query: str


class TripleItem(BaseModel):
    head: str
    relation: str
    tail: str


class SeedGraphRequest(BaseModel):
    graph_id: str
    source: str
    topic: str
    triples: list[TripleItem]


@app.on_event("startup")
def startup_event():
    """Initializes LDA, TextRank, and GraphRAG Knowledge Base on startup."""
    pipeline.initialize()


@app.get("/", response_class=FileResponse)
def serve_homepage():
    """Serves the main TrumorGPT Cognee landing homepage."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "TrumorGPT Web UI index.html not found"}


@app.get("/app", response_class=FileResponse)
def serve_app_page():
    """Serves the dedicated TrumorGPT Fact-Checking Application workspace."""
    app_path = os.path.join(STATIC_DIR, "app.html")
    if os.path.exists(app_path):
        return FileResponse(app_path)
    return {"message": "TrumorGPT Web UI app.html not found"}



@app.get("/health")
def health_check():
    """Health check status endpoint."""
    return {
        "status": "healthy",
        "pipeline_initialized": pipeline.is_initialized,
        "knowledge_graphs_indexed": len(pipeline.graph_rag_engine.knowledge_base)
    }


@app.post("/api/v1/fact-check")
def fact_check_endpoint(request: FactCheckRequest):
    """Executes full 5-component paper pipeline on a health query."""
    if not request.query or len(request.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    result = pipeline.fact_check(request.query.strip())
    return result


@app.post("/api/v1/seed-graph")
def seed_graph_endpoint(request: SeedGraphRequest):
    """Dynamically seeds a new verified Knowledge Graph into the GraphRAG index."""
    graph_dict = {
        "graph_id": request.graph_id,
        "source": request.source,
        "topic": request.topic,
        "triples": [t.model_dump() for t in request.triples]
    }
    pipeline.graph_rag_engine.add_knowledge_graph(graph_dict)
    return {
        "status": "success",
        "message": f"Seeded Knowledge Graph '{request.topic}' successfully.",
        "total_graphs": len(pipeline.graph_rag_engine.knowledge_base)
    }
