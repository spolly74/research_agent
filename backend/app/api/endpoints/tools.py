"""
Tool Management API endpoints.

Provides endpoints for:
- Listing available tools
- Creating dynamic tools
- Tool execution and testing
- Tool status management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

router = APIRouter()


class ToolCreateRequest(BaseModel):
    """Request to create a new tool."""
    name: str = Field(..., description="Tool name (snake_case)")
    description: str = Field(..., description="Tool description")
    code: str = Field(..., description="Python code defining the tool function")
    category: str = Field(default="custom", description="Tool category")
    allowed_agents: Optional[list[str]] = Field(default=None, description="Agents that can use this tool")


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""
    name: str = Field(..., description="Name of the tool to execute")
    args: dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")


class ToolStatusUpdate(BaseModel):
    """Request to update tool status."""
    status: str = Field(..., description="New status: active, disabled, or error")
    error_message: Optional[str] = Field(default=None, description="Error message if status is 'error'")


@router.get("/")
def list_tools() -> dict[str, Any]:
    """
    List all registered tools.

    Returns information about all tools including:
    - Built-in and custom tools
    - Tool status and metadata
    - Execution counts
    """
    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    return registry.get_registry_status()


@router.get("/{tool_name}")
def get_tool(tool_name: str) -> dict[str, Any]:
    """
    Get details for a specific tool.
    """
    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    tool = registry.get_tool(tool_name)
    metadata = registry.get_metadata(tool_name)

    if not tool or not metadata:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return {
        "name": metadata.name,
        "description": metadata.description,
        "category": metadata.category.value,
        "is_builtin": metadata.is_builtin,
        "status": metadata.status.value,
        "created_at": metadata.created_at.isoformat(),
        "updated_at": metadata.updated_at.isoformat(),
        "execution_count": metadata.execution_count,
        "last_execution": metadata.last_execution.isoformat() if metadata.last_execution else None,
        "allowed_agents": metadata.allowed_agents,
        "source_code": metadata.source_code if not metadata.is_builtin else None,
        "error_message": metadata.error_message
    }


@router.post("/")
def create_tool(request: ToolCreateRequest) -> dict[str, Any]:
    """
    Create a new dynamic tool.

    The code must define a function with the same name as the tool.
    The function should have type hints and return a string.
    """
    from app.agents.tools.registry import get_tool_registry, ToolCategory

    registry = get_tool_registry()

    # Map category string to enum
    category_map = {
        "math": ToolCategory.MATH,
        "data": ToolCategory.DATA,
        "api": ToolCategory.API,
        "code": ToolCategory.CODE,
        "browser": ToolCategory.BROWSER,
        "file": ToolCategory.FILE,
        "custom": ToolCategory.CUSTOM,
    }
    category = category_map.get(request.category.lower(), ToolCategory.CUSTOM)

    # Check if tool already exists
    if registry.get_tool(request.name):
        raise HTTPException(status_code=409, detail=f"Tool '{request.name}' already exists")

    # Create the tool
    success, tool_instance, error = registry.create_tool_from_code(
        name=request.name,
        description=request.description,
        code=request.code,
        category=category,
        allowed_agents=request.allowed_agents
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return {
        "success": True,
        "message": f"Tool '{request.name}' created successfully",
        "tool_name": request.name
    }


@router.post("/{tool_name}/execute")
def execute_tool(tool_name: str, request: ToolExecuteRequest) -> dict[str, Any]:
    """
    Execute a tool with the given arguments.

    This is useful for testing tools.
    """
    from app.agents.tools.registry import get_tool_registry
    import time

    registry = get_tool_registry()
    tool = registry.get_tool(tool_name)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    metadata = registry.get_metadata(tool_name)
    if metadata.status.value != "active":
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' is not active")

    try:
        start_time = time.time()
        result = tool.invoke(request.args)
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Record execution
        registry.record_execution(tool_name)

        return {
            "success": True,
            "tool_name": tool_name,
            "result": result,
            "execution_time_ms": execution_time_ms
        }

    except Exception as e:
        return {
            "success": False,
            "tool_name": tool_name,
            "error": str(e)
        }


@router.patch("/{tool_name}/status")
def update_tool_status(tool_name: str, request: ToolStatusUpdate) -> dict[str, Any]:
    """
    Update the status of a tool.

    Valid statuses: active, disabled, error
    """
    from app.agents.tools.registry import get_tool_registry, ToolStatus

    registry = get_tool_registry()

    if not registry.get_tool(tool_name):
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    # Map status string to enum
    status_map = {
        "active": ToolStatus.ACTIVE,
        "disabled": ToolStatus.DISABLED,
        "error": ToolStatus.ERROR,
    }

    if request.status.lower() not in status_map:
        raise HTTPException(status_code=400, detail=f"Invalid status '{request.status}'")

    status = status_map[request.status.lower()]
    success = registry.set_tool_status(tool_name, status, request.error_message)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update tool status")

    return {
        "success": True,
        "tool_name": tool_name,
        "status": request.status
    }


@router.delete("/{tool_name}")
def delete_tool(tool_name: str) -> dict[str, Any]:
    """
    Delete a custom tool.

    Built-in tools cannot be deleted.
    """
    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()

    if not registry.get_tool(tool_name):
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    metadata = registry.get_metadata(tool_name)
    if metadata.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete built-in tools")

    success = registry.unregister(tool_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete tool")

    return {
        "success": True,
        "message": f"Tool '{tool_name}' deleted successfully"
    }


@router.get("/category/{category}")
def list_tools_by_category(category: str) -> dict[str, Any]:
    """
    List tools in a specific category.
    """
    from app.agents.tools.registry import get_tool_registry, ToolCategory

    category_map = {
        "math": ToolCategory.MATH,
        "data": ToolCategory.DATA,
        "api": ToolCategory.API,
        "code": ToolCategory.CODE,
        "browser": ToolCategory.BROWSER,
        "file": ToolCategory.FILE,
        "custom": ToolCategory.CUSTOM,
    }

    if category.lower() not in category_map:
        raise HTTPException(status_code=400, detail=f"Invalid category '{category}'")

    registry = get_tool_registry()
    tools = registry.get_tools_by_category(category_map[category.lower()])

    return {
        "category": category,
        "count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description
            }
            for t in tools
        ]
    }


@router.get("/agent/{agent_type}")
def list_tools_for_agent(agent_type: str) -> dict[str, Any]:
    """
    List tools available to a specific agent type.
    """
    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    tools = registry.get_tools_for_agent(agent_type)

    return {
        "agent_type": agent_type,
        "count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description
            }
            for t in tools
        ]
    }
