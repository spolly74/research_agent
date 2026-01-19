from dotenv import load_dotenv
load_dotenv()  # Load environment variables before other imports

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Local Research Agent", version="0.1.0")

# CORS configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.endpoints import chat, llm, tools, reports

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Register built-in tools
    from app.agents.tools.registry import register_builtin_tools
    register_builtin_tools()


@app.get("/health")
def read_root():
    return {"status": "ok", "message": "Research Agent API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
