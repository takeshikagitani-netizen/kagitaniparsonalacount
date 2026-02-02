"""FastAPI main application."""
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_db
from .routers import receipts_router, journals_router
from .config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    # Ensure directories exist
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    # Initialize database
    init_db()

    yield

    # Shutdown (if needed)


app = FastAPI(
    title="Receipt Accounting MVP",
    description="領収書/請求書から仕訳を自動生成するシステム",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS settings for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(receipts_router, prefix="/api")
app.include_router(journals_router, prefix="/api")


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# Serve frontend
frontend_path = Path(__file__).parent.parent.parent / "frontend"


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML."""
    return FileResponse(frontend_path / "index.html")


# Serve static files (if any)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
