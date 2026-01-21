"""
Tool Registry - Central registry for all available tools.

This module provides:
- Runtime tool registration and management
- Tool metadata tracking
- Dynamic tool creation from code
- Agent-specific tool filtering
"""

import ast
import hashlib
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, Any
from threading import Lock

import structlog
from langchain_core.tools import BaseTool, tool

logger = structlog.get_logger(__name__)


class ToolCategory(str, Enum):
    """Categories for organizing tools."""
    BROWSER = "browser"
    FILE = "file"
    CODE = "code"
    DATA = "data"
    API = "api"
    MATH = "math"
    CUSTOM = "custom"


class ToolStatus(str, Enum):
    """Status of a tool in the registry."""
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ToolMetadata:
    """Metadata about a registered tool."""
    name: str
    description: str
    category: ToolCategory
    is_builtin: bool = True
    status: ToolStatus = ToolStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    code_hash: Optional[str] = None  # For dynamic tools
    source_code: Optional[str] = None  # For dynamic tools
    error_message: Optional[str] = None
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    allowed_agents: list[str] = field(default_factory=list)  # Empty = all agents


class ToolRegistry:
    """
    Central registry for all available tools.

    Manages both built-in tools and dynamically created tools.
    Supports agent-specific tool filtering and tool lifecycle management.
    """

    _instance: Optional['ToolRegistry'] = None
    _lock = Lock()

    def __new__(cls):
        """Singleton pattern for tool registry."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the tool registry."""
        if self._initialized:
            return

        self._initialized = True
        self._tools: dict[str, BaseTool] = {}
        self._metadata: dict[str, ToolMetadata] = {}
        self._tool_lock = Lock()

        logger.info("Tool Registry initialized")

    def register(
        self,
        tool_instance: BaseTool,
        category: ToolCategory = ToolCategory.CUSTOM,
        is_builtin: bool = False,
        allowed_agents: Optional[list[str]] = None,
        source_code: Optional[str] = None
    ) -> bool:
        """
        Register a tool in the registry.

        Args:
            tool_instance: The LangChain tool to register
            category: Category for organization
            is_builtin: Whether this is a built-in tool
            allowed_agents: List of agent types that can use this tool (None = all)
            source_code: Source code for dynamic tools

        Returns:
            True if registration successful, False otherwise
        """
        with self._tool_lock:
            name = tool_instance.name

            if name in self._tools:
                logger.warning("Tool already registered, updating", tool_name=name)

            # Create metadata
            code_hash = None
            if source_code:
                code_hash = hashlib.sha256(source_code.encode()).hexdigest()[:16]

            metadata = ToolMetadata(
                name=name,
                description=tool_instance.description,
                category=category,
                is_builtin=is_builtin,
                code_hash=code_hash,
                source_code=source_code,
                allowed_agents=allowed_agents or []
            )

            self._tools[name] = tool_instance
            self._metadata[name] = metadata

            logger.info(
                "Tool registered",
                tool_name=name,
                category=category.value,
                is_builtin=is_builtin
            )

            return True

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        with self._tool_lock:
            if name not in self._tools:
                logger.warning("Tool not found for unregistration", tool_name=name)
                return False

            # Don't allow removing built-in tools
            if self._metadata[name].is_builtin:
                logger.warning("Cannot unregister built-in tool", tool_name=name)
                return False

            del self._tools[name]
            del self._metadata[name]

            logger.info("Tool unregistered", tool_name=name)
            return True

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a specific tool by name."""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a specific tool."""
        return self._metadata.get(name)

    def get_all_tools(self) -> list[BaseTool]:
        """Get all active tools."""
        return [
            tool for name, tool in self._tools.items()
            if self._metadata[name].status == ToolStatus.ACTIVE
        ]

    def get_tools_for_agent(self, agent_type: str) -> list[BaseTool]:
        """
        Get tools available to a specific agent type.

        Args:
            agent_type: The type of agent (e.g., "researcher", "coder")

        Returns:
            List of tools available to this agent
        """
        tools = []
        for name, tool_instance in self._tools.items():
            metadata = self._metadata[name]

            # Skip inactive tools
            if metadata.status != ToolStatus.ACTIVE:
                continue

            # Check if agent is allowed (empty list = all agents)
            if metadata.allowed_agents and agent_type not in metadata.allowed_agents:
                continue

            tools.append(tool_instance)

        return tools

    def get_tools_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """Get all tools in a specific category."""
        return [
            tool for name, tool in self._tools.items()
            if self._metadata[name].category == category
            and self._metadata[name].status == ToolStatus.ACTIVE
        ]

    def set_tool_status(self, name: str, status: ToolStatus, error_message: Optional[str] = None) -> bool:
        """Update the status of a tool."""
        with self._tool_lock:
            if name not in self._metadata:
                return False

            self._metadata[name].status = status
            self._metadata[name].error_message = error_message
            self._metadata[name].updated_at = datetime.now()

            logger.info("Tool status updated", tool_name=name, status=status.value)
            return True

    def record_execution(self, name: str) -> None:
        """Record that a tool was executed."""
        with self._tool_lock:
            if name in self._metadata:
                self._metadata[name].execution_count += 1
                self._metadata[name].last_execution = datetime.now()

    def create_tool_from_code(
        self,
        name: str,
        description: str,
        code: str,
        category: ToolCategory = ToolCategory.CUSTOM,
        allowed_agents: Optional[list[str]] = None
    ) -> tuple[bool, Optional[BaseTool], Optional[str]]:
        """
        Dynamically create a tool from Python code.

        The code should define a function with the same name as the tool.
        The function should have type hints and a docstring.

        Args:
            name: Name of the tool (must match function name in code)
            description: Description of what the tool does
            code: Python source code defining the tool function
            category: Category for the tool
            allowed_agents: List of agents that can use this tool

        Returns:
            Tuple of (success, tool_instance, error_message)
        """
        # Validate the code first
        is_valid, error = self._validate_tool_code(name, code)
        if not is_valid:
            logger.error("Invalid tool code", tool_name=name, error=error)
            return False, None, error

        try:
            # Create a restricted namespace for execution
            namespace = self._get_safe_namespace()

            # Execute the code to define the function
            exec(code, namespace)

            # Get the function from namespace
            if name not in namespace:
                return False, None, f"Function '{name}' not found in code"

            func = namespace[name]

            # Wrap it as a LangChain tool
            tool_instance = tool(func)
            tool_instance.name = name
            tool_instance.description = description

            # Register the tool
            self.register(
                tool_instance,
                category=category,
                is_builtin=False,
                allowed_agents=allowed_agents,
                source_code=code
            )

            logger.info("Dynamic tool created", tool_name=name)
            return True, tool_instance, None

        except Exception as e:
            error_msg = f"Failed to create tool: {str(e)}\n{traceback.format_exc()}"
            logger.error("Dynamic tool creation failed", tool_name=name, error=str(e))
            return False, None, error_msg

    def _validate_tool_code(self, name: str, code: str) -> tuple[bool, Optional[str]]:
        """
        Validate tool code for safety and correctness.

        Checks:
        - Valid Python syntax
        - Contains the expected function definition
        - No dangerous operations
        """
        # Check syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # Find function definition
        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                func_def = node
                break

        if func_def is None:
            return False, f"Function '{name}' not found in code"

        # Check for dangerous operations
        dangerous_names = {
            'eval', 'exec', 'compile', '__import__', 'open',
            'os', 'subprocess', 'sys', 'importlib', 'builtins',
            'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr',
            'delattr', 'hasattr'
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in dangerous_names:
                return False, f"Dangerous operation '{node.id}' not allowed"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in {'os', 'subprocess', 'sys', 'importlib'}:
                        return False, f"Import of '{alias.name}' not allowed"
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in {'os', 'subprocess', 'sys', 'importlib'}:
                    return False, f"Import from '{node.module}' not allowed"

        return True, None

    def _get_safe_namespace(self) -> dict[str, Any]:
        """Get a restricted namespace for executing tool code."""
        import math
        import json
        import re
        from datetime import datetime, timedelta

        return {
            # Safe built-ins
            'abs': abs,
            'all': all,
            'any': any,
            'bool': bool,
            'dict': dict,
            'enumerate': enumerate,
            'filter': filter,
            'float': float,
            'format': format,
            'frozenset': frozenset,
            'int': int,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'iter': iter,
            'len': len,
            'list': list,
            'map': map,
            'max': max,
            'min': min,
            'next': next,
            'pow': pow,
            'print': print,
            'range': range,
            'reversed': reversed,
            'round': round,
            'set': set,
            'slice': slice,
            'sorted': sorted,
            'str': str,
            'sum': sum,
            'tuple': tuple,
            'type': type,
            'zip': zip,
            # Safe modules
            'math': math,
            'json': json,
            're': re,
            'datetime': datetime,
            'timedelta': timedelta,
        }

    def get_registry_status(self) -> dict[str, Any]:
        """Get current status of the registry."""
        return {
            "total_tools": len(self._tools),
            "active_tools": sum(
                1 for m in self._metadata.values()
                if m.status == ToolStatus.ACTIVE
            ),
            "builtin_tools": sum(
                1 for m in self._metadata.values()
                if m.is_builtin
            ),
            "custom_tools": sum(
                1 for m in self._metadata.values()
                if not m.is_builtin
            ),
            "tools": [
                {
                    "name": name,
                    "description": meta.description,
                    "category": meta.category.value,
                    "is_builtin": meta.is_builtin,
                    "status": meta.status.value,
                    "execution_count": meta.execution_count,
                    "allowed_agents": meta.allowed_agents
                }
                for name, meta in self._metadata.items()
            ]
        }


# Singleton instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the singleton tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_builtin_tools():
    """Register all built-in tools in the registry."""
    from app.agents.tools.browser import browser_search, visit_page
    from app.agents.tools.math_tools import calculator, statistics_calculator, unit_converter
    from app.agents.tools.http_tools import api_get, api_post, json_parser
    from app.agents.tools.executor import execute_python, analyze_code
    from app.agents.tools.filesystem import file_reader, file_writer, list_directory
    from app.agents.tools.database import database_query, database_schema
    from app.agents.tools.documents import document_parser, document_metadata

    registry = get_tool_registry()

    # Register browser tools
    registry.register(
        browser_search,
        category=ToolCategory.BROWSER,
        is_builtin=True,
        allowed_agents=["researcher"]
    )

    registry.register(
        visit_page,
        category=ToolCategory.BROWSER,
        is_builtin=True,
        allowed_agents=["researcher"]
    )

    # Register math tools
    registry.register(
        calculator,
        category=ToolCategory.MATH,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    registry.register(
        statistics_calculator,
        category=ToolCategory.MATH,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    registry.register(
        unit_converter,
        category=ToolCategory.MATH,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    # Register HTTP/API tools
    registry.register(
        api_get,
        category=ToolCategory.API,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    registry.register(
        api_post,
        category=ToolCategory.API,
        is_builtin=True,
        allowed_agents=["coder"]
    )

    registry.register(
        json_parser,
        category=ToolCategory.DATA,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    # Register code execution tools
    registry.register(
        execute_python,
        category=ToolCategory.CODE,
        is_builtin=True,
        allowed_agents=["coder"]
    )

    registry.register(
        analyze_code,
        category=ToolCategory.CODE,
        is_builtin=True,
        allowed_agents=["coder", "reviewer"]
    )

    # Register filesystem tools
    registry.register(
        file_reader,
        category=ToolCategory.FILE,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    registry.register(
        file_writer,
        category=ToolCategory.FILE,
        is_builtin=True,
        allowed_agents=["coder"]
    )

    registry.register(
        list_directory,
        category=ToolCategory.FILE,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    # Register database tools
    registry.register(
        database_query,
        category=ToolCategory.DATA,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    registry.register(
        database_schema,
        category=ToolCategory.DATA,
        is_builtin=True,
        allowed_agents=["researcher", "coder"]
    )

    # Register document tools
    registry.register(
        document_parser,
        category=ToolCategory.FILE,
        is_builtin=True,
        allowed_agents=["researcher"]
    )

    registry.register(
        document_metadata,
        category=ToolCategory.FILE,
        is_builtin=True,
        allowed_agents=["researcher"]
    )

    logger.info("Built-in tools registered", count=17)
