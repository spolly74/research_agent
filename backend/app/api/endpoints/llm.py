"""
LLM Management API endpoints.

Provides endpoints for:
- Checking LLM provider status
- Health checks
- Configuration viewing
"""

from fastapi import APIRouter
from typing import Any

router = APIRouter()


@router.get("/status")
def get_llm_status() -> dict[str, Any]:
    """
    Get current status of all LLM providers.

    Returns information about:
    - Ollama endpoints and their health
    - Claude API availability
    - Current routing configuration
    """
    from app.core.llm_manager import get_llm_manager

    manager = get_llm_manager()
    return manager.get_status()


@router.post("/health-check")
async def run_health_check() -> dict[str, Any]:
    """
    Trigger a health check on all Ollama endpoints.

    Returns updated status for all endpoints.
    """
    from app.core.llm_manager import get_llm_manager

    manager = get_llm_manager()
    results = await manager.check_all_endpoints()

    return {
        "checked": len(results),
        "healthy": sum(1 for s in results.values() if s.is_healthy),
        "endpoints": {
            url: {
                "is_healthy": status.is_healthy,
                "response_time_ms": status.response_time_ms,
                "available_models": status.available_models,
                "last_error": status.last_error
            }
            for url, status in results.items()
        }
    }


@router.get("/analyze-complexity")
def analyze_complexity(prompt: str) -> dict[str, Any]:
    """
    Analyze the complexity of a prompt.

    This is useful for understanding how the routing system
    will categorize a given task.

    Args:
        prompt: The text to analyze

    Returns:
        Complexity score and routing recommendation
    """
    from app.core.complexity_analyzer import analyze_complexity as analyze

    result = analyze(prompt)

    return {
        "score": result.score,
        "recommendation": result.recommendation,
        "reasoning": result.reasoning,
        "factors": result.factors
    }
