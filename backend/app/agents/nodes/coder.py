"""
Enhanced Coder Agent - Can analyze, write, and register tools dynamically.

This agent can:
1. Analyze if custom code/tools are needed
2. Generate Python code for new tools
3. Register tools dynamically in the registry
4. Execute code safely in sandbox
"""

import json
import re
from typing import Optional
from langchain_core.messages import SystemMessage, AIMessage
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType
from app.agents.tools.registry import get_tool_registry, ToolCategory
from app.agents.tools.executor import execute_python, analyze_code

import structlog

logger = structlog.get_logger(__name__)


class ToolSpec(BaseModel):
    """Specification for a tool to be created."""
    name: str = Field(description="Name of the tool (snake_case, no spaces)")
    description: str = Field(description="Clear description of what the tool does")
    category: str = Field(description="Category: math, data, api, code, or custom")
    code: str = Field(description="Python function code implementing the tool")
    needs_creation: bool = Field(description="Whether this tool needs to be created")
    reasoning: str = Field(description="Why this tool is or isn't needed")


CODER_SYSTEM_PROMPT = """You are an expert Python Coder Agent. Your responsibilities are:

1. **Analyze** if custom code or tools are needed to fulfill the research request
2. **Generate** Python tools when existing tools are insufficient
3. **Execute** Python code to process data or perform calculations

## Available Built-in Tools
You have access to these existing tools:
- browser_search: Search the web
- visit_page: Visit and extract content from URLs
- calculator: Evaluate math expressions
- statistics_calculator: Statistical operations (mean, median, stdev, etc.)
- unit_converter: Convert between units
- api_get: Make HTTP GET requests
- api_post: Make HTTP POST requests
- json_parser: Parse and extract from JSON
- execute_python: Run Python code safely
- analyze_code: Analyze Python code structure

## When to Create New Tools
Create a new tool ONLY if:
- The task requires functionality not covered by existing tools
- The same operation needs to be performed multiple times
- A reusable abstraction would significantly help

## Tool Creation Guidelines
When creating a tool, your code MUST:
1. Define a function with the exact name specified
2. Include type hints for all parameters
3. Include a docstring explaining usage
4. Return a string (tools always return strings)
5. Handle errors gracefully
6. NOT use: os, sys, subprocess, file I/O, network (use api_get/api_post instead)

## Code Execution
For one-off calculations or data processing, use execute_python instead of creating a tool.

## Response Format
If creating a tool, respond with a JSON block like:
```json
{
    "needs_creation": true,
    "name": "tool_name",
    "description": "What the tool does",
    "category": "data",
    "code": "def tool_name(param: str) -> str:\\n    '''Docstring'''\\n    return result",
    "reasoning": "Why this tool is needed"
}
```

If no tool is needed:
```json
{
    "needs_creation": false,
    "reasoning": "Explanation of why existing tools suffice or the task doesn't need code"
}
```

Always include your analysis and any code execution results in your response.
"""


def extract_json_from_response(content: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    # Try to find JSON block
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r'\{[^{}]*"needs_creation"[^{}]*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def create_tool_from_spec(spec: dict) -> tuple[bool, str]:
    """Create and register a tool from specification."""
    registry = get_tool_registry()

    name = spec.get("name", "").strip()
    description = spec.get("description", "")
    code = spec.get("code", "")
    category_str = spec.get("category", "custom").lower()

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
    category = category_map.get(category_str, ToolCategory.CUSTOM)

    # Validate
    if not name:
        return False, "Tool name is required"
    if not code:
        return False, "Tool code is required"

    # Check if tool already exists
    existing = registry.get_tool(name)
    if existing:
        return False, f"Tool '{name}' already exists"

    # Create the tool
    success, tool_instance, error = registry.create_tool_from_code(
        name=name,
        description=description,
        code=code,
        category=category,
        allowed_agents=["coder", "researcher"]
    )

    if success:
        logger.info("Dynamic tool created by coder", tool_name=name)
        return True, f"Successfully created tool '{name}'"
    else:
        logger.error("Failed to create tool", tool_name=name, error=error)
        return False, f"Failed to create tool: {error}"


def coder_node(state: AgentState):
    """
    Enhanced Coder Agent node.

    Analyzes if custom tools are needed and can create them dynamically.
    """
    messages = state["messages"]

    # Get LLM - coder uses Claude for better code generation
    llm = get_llm(task_type=TaskType.CODER)

    system_msg = SystemMessage(content=CODER_SYSTEM_PROMPT)

    # Add context about what tools currently exist
    registry = get_tool_registry()
    tools_context = "\n\nCurrently registered tools:\n"
    for tool_info in registry.get_registry_status()["tools"]:
        tools_context += f"- {tool_info['name']}: {tool_info['description'][:100]}...\n"

    enhanced_system = SystemMessage(content=CODER_SYSTEM_PROMPT + tools_context)

    logger.info("Coder node invoked", message_count=len(messages))

    # Invoke LLM
    response = llm.invoke([enhanced_system] + messages)
    response_content = response.content

    # Try to extract tool specification
    spec = extract_json_from_response(response_content)

    tool_creation_result = ""
    if spec and spec.get("needs_creation", False):
        logger.info("Coder wants to create tool", spec=spec)
        success, message = create_tool_from_spec(spec)
        tool_creation_result = f"\n\n**Tool Creation Result:** {message}"

        if success:
            # Add the new tool info to the response
            tool_creation_result += f"\nThe tool '{spec.get('name')}' is now available for use."

    # Combine response with tool creation result
    final_content = response_content + tool_creation_result

    return {
        "messages": [AIMessage(content=final_content)],
        "code_output": final_content
    }


def coder_node_with_tools(state: AgentState):
    """
    Coder node with direct tool access.

    This version binds tools directly to the LLM for autonomous tool use.
    """
    messages = state["messages"]

    # Get tools available to coder
    registry = get_tool_registry()
    tools = registry.get_tools_for_agent("coder")

    # Get LLM with tools bound
    llm = get_llm(task_type=TaskType.CODER)
    llm_with_tools = llm.bind_tools(tools)

    system_msg = SystemMessage(content="""
    You are an expert Python Coder Agent with access to tools.

    Use the available tools to:
    - Execute Python code (execute_python)
    - Analyze code structure (analyze_code)
    - Perform calculations (calculator, statistics_calculator)
    - Make API requests (api_get, api_post)
    - Parse JSON data (json_parser)

    When given a coding task:
    1. Analyze what needs to be done
    2. Use appropriate tools to accomplish the task
    3. Report your findings and results clearly
    """)

    response = llm_with_tools.invoke([system_msg] + messages)

    return {
        "messages": [response],
        "code_output": response.content
    }
