from dotenv import load_dotenv
load_dotenv()  # Load environment variables before other imports

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging before anything else
from app.core.logging_config import configure_logging, RequestContextMiddleware, get_logger

# Configure based on environment
json_logs = os.getenv("LOG_FORMAT", "console").lower() == "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(json_format=json_logs, log_level=log_level)

logger = get_logger(__name__)

app = FastAPI(title="Local Research Agent", version="0.1.0")

# Add request context middleware for logging (must be added before CORS)
app.add_middleware(RequestContextMiddleware)

# CORS configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.endpoints import chat, llm, tools, reports, status, websocket, logs

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(websocket.router, tags=["websocket"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Research Agent API")

    # Create database tables (including new graph state tables)
    from app.core.database import engine, Base
    from app.models import chat, tool, plan, graph_state  # Import all models
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    # Register built-in tools
    from app.agents.tools.registry import register_builtin_tools
    register_builtin_tools()

    # Set up WebSocket handler for execution tracking
    from app.api.endpoints.websocket import setup_websocket_handler
    setup_websocket_handler()

    logger.info("Research Agent API startup complete")


@app.get("/health")
def read_root():
    logger.debug("Health check requested")
    return {"status": "ok", "message": "Research Agent API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
