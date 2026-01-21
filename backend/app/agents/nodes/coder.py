"""
Enhanced Coder Agent - Can analyze, write, and register tools dynamically.

This agent can:
1. Analyze if custom code/tools are needed
2. Generate Python code for new tools
3. Validate tools in sandbox before registration
4. Register tools dynamically in the registry
5. Execute code safely in sandbox
"""

import asyncio
import json
import re
from typing import Optional, Any
from langchain_core.messages import SystemMessage, AIMessage
from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType
from app.agents.tools.registry import get_tool_registry, ToolCategory, ToolStatus
from app.agents.tools.executor import execute_python, analyze_code

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Schemas for Tool Analysis and Validation
# ============================================================================

class ToolNeed(BaseModel):
    """Result of analyzing whether a new tool is needed."""
    needs_tool: bool = Field(description="Whether a new tool needs to be created")
    reason: str = Field(description="Explanation of why a tool is or isn't needed")
    suggested_name: Optional[str] = Field(default=None, description="Suggested tool name if needed")
    suggested_description: Optional[str] = Field(default=None, description="Suggested description")
    complexity: float = Field(default=0.5, ge=0.0, le=1.0, description="Estimated complexity 0-1")
    existing_alternatives: list[str] = Field(default_factory=list, description="Existing tools that could work")


class ValidationResult(BaseModel):
    """Result of validating tool code."""
    is_valid: bool = Field(description="Whether the code passed validation")
    errors: list[str] = Field(default_factory=list, description="Critical errors found")
    warnings: list[str] = Field(default_factory=list, description="Non-critical warnings")
    security_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Security score 0-1")
    test_output: Optional[str] = Field(default=None, description="Output from test execution")
    test_passed: bool = Field(default=False, description="Whether test execution passed")


class ToolSpec(BaseModel):
    """Specification for a tool to be created."""
    name: str = Field(description="Name of the tool (snake_case, no spaces)")
    description: str = Field(description="Clear description of what the tool does")
    category: str = Field(description="Category: math, data, api, code, or custom")
    code: str = Field(description="Python function code implementing the tool")
    needs_creation: bool = Field(description="Whether this tool needs to be created")
    reasoning: str = Field(description="Why this tool is or isn't needed")
    test_code: Optional[str] = Field(default=None, description="Optional test code to validate the tool")


CODER_SYSTEM_PROMPT = """You are an expert Python Coder Agent. Your responsibilities are:

1. **Analyze** if custom code or tools are needed to fulfill the research request
2. **Generate** Python tools when existing tools are insufficient
3. **Validate** generated tools with test code before registration
4. **Execute** Python code to process data or perform calculations

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
2. Include type hints for all parameters and return type
3. Include a docstring explaining usage with examples
4. Return a string (tools always return strings)
5. Handle errors gracefully with try/except
6. NOT use: os, sys, subprocess, file I/O, network (use api_get/api_post instead)

## Tool Testing
Always include test_code to validate your tool works correctly:
- Test with typical inputs
- Test edge cases (empty strings, zero values, etc.)
- Verify the output format is correct

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
    "code": "def tool_name(param: str) -> str:\\n    '''Docstring with example.'''\\n    try:\\n        result = process(param)\\n        return str(result)\\n    except Exception as e:\\n        return f'Error: {e}'",
    "test_code": "result = tool_name('test_input')\\nassert 'expected' in result.lower(), f'Unexpected: {result}'\\nprint('Test passed:', result)",
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

    # Try to find raw JSON object (handle nested braces)
    brace_count = 0
    start_idx = None
    for i, char in enumerate(content):
        if char == '{':
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                try:
                    candidate = content[start_idx:i+1]
                    parsed = json.loads(candidate)
                    if "needs_creation" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    start_idx = None
                    continue

    return None


def validate_tool_code(code: str, test_code: Optional[str] = None) -> ValidationResult:
    """
    Validate tool code before registration.

    Performs:
    1. Static analysis for security issues
    2. Optional test execution to verify functionality
    """
    errors = []
    warnings = []
    security_score = 1.0
    test_output = None
    test_passed = False

    # Static analysis - invoke the tool properly
    try:
        analysis_result = analyze_code.invoke({"code": code})
    except Exception as e:
        analysis_result = f"Error: {str(e)}"

    if "Error:" in analysis_result or "SyntaxError" in analysis_result:
        errors.append(f"Code analysis failed: {analysis_result}")
        security_score = 0.0
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            security_score=security_score
        )

    # Check for dangerous patterns
    dangerous_patterns = [
        (r'\beval\s*\(', "Use of eval() is forbidden"),
        (r'\bexec\s*\(', "Use of exec() is forbidden"),
        (r'\b__import__\s*\(', "Dynamic imports are forbidden"),
        (r'\bopen\s*\(', "File operations are forbidden"),
        (r'\bos\.\w+', "os module access is forbidden"),
        (r'\bsys\.\w+', "sys module access is forbidden"),
        (r'\bsubprocess', "subprocess module is forbidden"),
        (r'import\s+os\b', "Importing os is forbidden"),
        (r'import\s+sys\b', "Importing sys is forbidden"),
        (r'from\s+os\s+import', "Importing from os is forbidden"),
    ]

    for pattern, message in dangerous_patterns:
        if re.search(pattern, code):
            errors.append(message)
            security_score -= 0.2

    # Check for recommended patterns
    if "def " not in code:
        errors.append("Code must define a function")

    if '"""' not in code and "'''" not in code:
        warnings.append("Function should have a docstring")

    if "-> str" not in code:
        warnings.append("Function should have return type hint '-> str'")

    if "try:" not in code:
        warnings.append("Consider adding error handling with try/except")

    # Run test code if provided
    if test_code and not errors:
        # Combine tool code with test code
        full_test = f"{code}\n\n# Test execution\n{test_code}"
        try:
            test_output = execute_python.invoke({"code": full_test})
            if "Error:" not in test_output and "Traceback" not in test_output:
                test_passed = True
            else:
                warnings.append(f"Test execution had issues: {test_output[:200]}")
        except Exception as e:
            warnings.append(f"Test execution failed: {str(e)}")

    security_score = max(0.0, security_score)
    is_valid = len(errors) == 0 and security_score >= 0.5

    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        security_score=security_score,
        test_output=test_output,
        test_passed=test_passed
    )


def create_tool_from_spec(spec: dict) -> tuple[bool, str, Optional[ValidationResult]]:
    """
    Create and register a tool from specification.

    Returns:
        Tuple of (success, message, validation_result)
    """
    registry = get_tool_registry()

    name = spec.get("name", "").strip()
    description = spec.get("description", "")
    code = spec.get("code", "")
    test_code = spec.get("test_code")
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

    # Basic validation
    if not name:
        return False, "Tool name is required", None
    if not code:
        return False, "Tool code is required", None

    # Validate name format
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        return False, "Tool name must be snake_case (lowercase letters, numbers, underscores)", None

    # Check if tool already exists
    existing = registry.get_tool(name)
    if existing:
        return False, f"Tool '{name}' already exists", None

    # Validate the code
    validation = validate_tool_code(code, test_code)
    logger.info(
        "Tool validation result",
        tool_name=name,
        is_valid=validation.is_valid,
        errors=validation.errors,
        warnings=validation.warnings,
        security_score=validation.security_score,
        test_passed=validation.test_passed
    )

    if not validation.is_valid:
        error_summary = "; ".join(validation.errors)
        return False, f"Tool validation failed: {error_summary}", validation

    # Create the tool
    success, tool_instance, error = registry.create_tool_from_code(
        name=name,
        description=description,
        code=code,
        category=category,
        allowed_agents=["coder", "researcher"]
    )

    if success:
        logger.info(
            "Dynamic tool created by coder",
            tool_name=name,
            category=category_str,
            test_passed=validation.test_passed
        )
        msg = f"Successfully created tool '{name}'"
        if validation.test_passed:
            msg += " (tests passed)"
        if validation.warnings:
            msg += f". Warnings: {'; '.join(validation.warnings)}"
        return True, msg, validation
    else:
        logger.error("Failed to create tool", tool_name=name, error=error)
        return False, f"Failed to create tool: {error}", validation


def coder_node(state: AgentState):
    """
    Enhanced Coder Agent node (synchronous version).

    Analyzes if custom tools are needed and can create them dynamically.
    """
    messages = state["messages"]

    # Get LLM - coder uses Claude for better code generation
    llm = get_llm(task_type=TaskType.CODER)

    # Add context about what tools currently exist
    registry = get_tool_registry()
    tools_context = "\n\n## Currently Registered Tools\n"
    for tool_info in registry.get_registry_status()["tools"]:
        status_icon = "✓" if tool_info.get("status") == "active" else "○"
        tools_context += f"- {status_icon} **{tool_info['name']}**: {tool_info['description'][:100]}\n"

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
        success, message, validation = create_tool_from_spec(spec)
        tool_creation_result = f"\n\n**Tool Creation Result:** {message}"

        if success:
            tool_creation_result += f"\nThe tool '{spec.get('name')}' is now available for use."
        elif validation:
            # Include validation details for debugging
            if validation.errors:
                tool_creation_result += f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in validation.errors)
            if validation.test_output:
                tool_creation_result += f"\n\nTest output:\n```\n{validation.test_output[:500]}\n```"

    # Combine response with tool creation result
    final_content = response_content + tool_creation_result

    return {
        "messages": [AIMessage(content=final_content)],
        "code_output": final_content
    }


async def async_coder_node(state: AgentState):
    """
    Enhanced Coder Agent node (async version).

    Analyzes if custom tools are needed and can create them dynamically.
    Uses asyncio for non-blocking LLM calls.
    """
    messages = state["messages"]

    # Get LLM - coder uses Claude for better code generation
    llm = get_llm(task_type=TaskType.CODER)

    # Add context about what tools currently exist
    registry = get_tool_registry()
    tools_context = "\n\n## Currently Registered Tools\n"
    for tool_info in registry.get_registry_status()["tools"]:
        status_icon = "✓" if tool_info.get("status") == "active" else "○"
        tools_context += f"- {status_icon} **{tool_info['name']}**: {tool_info['description'][:100]}\n"

    enhanced_system = SystemMessage(content=CODER_SYSTEM_PROMPT + tools_context)

    logger.info("Async coder node invoked", message_count=len(messages))

    # Invoke LLM asynchronously
    response = await llm.ainvoke([enhanced_system] + messages)
    response_content = response.content

    # Try to extract tool specification
    spec = extract_json_from_response(response_content)

    tool_creation_result = ""
    if spec and spec.get("needs_creation", False):
        logger.info("Coder wants to create tool", spec=spec)

        # Run validation in thread pool to not block
        loop = asyncio.get_event_loop()
        success, message, validation = await loop.run_in_executor(
            None, create_tool_from_spec, spec
        )

        tool_creation_result = f"\n\n**Tool Creation Result:** {message}"

        if success:
            tool_creation_result += f"\nThe tool '{spec.get('name')}' is now available for use."
        elif validation:
            if validation.errors:
                tool_creation_result += f"\n\nValidation errors:\n" + "\n".join(f"- {e}" for e in validation.errors)
            if validation.test_output:
                tool_creation_result += f"\n\nTest output:\n```\n{validation.test_output[:500]}\n```"

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


# ============================================================================
# Utility Functions for External Use
# ============================================================================

def analyze_tool_need(task: str, available_tools: list[str]) -> ToolNeed:
    """
    Analyze if a new tool is needed for the given task.

    Args:
        task: Description of the task to accomplish
        available_tools: List of available tool names

    Returns:
        ToolNeed with analysis results
    """
    llm = get_llm(task_type=TaskType.CODER)

    analysis_prompt = f"""Analyze if a new tool needs to be created for this task.

Task: {task}

Available tools: {', '.join(available_tools) if available_tools else 'None'}

Respond with JSON:
{{
    "needs_tool": true/false,
    "reason": "explanation",
    "suggested_name": "tool_name" or null,
    "suggested_description": "description" or null,
    "complexity": 0.0-1.0,
    "existing_alternatives": ["tool1", "tool2"]
}}
"""

    response = llm.invoke([SystemMessage(content=analysis_prompt)])
    content = response.content

    # Parse response
    try:
        data = extract_json_from_response(content)
        if data:
            return ToolNeed(
                needs_tool=data.get("needs_tool", False),
                reason=data.get("reason", ""),
                suggested_name=data.get("suggested_name"),
                suggested_description=data.get("suggested_description"),
                complexity=data.get("complexity", 0.5),
                existing_alternatives=data.get("existing_alternatives", [])
            )
    except Exception as e:
        logger.warning("Failed to parse tool need analysis", error=str(e))

    # Default response
    return ToolNeed(
        needs_tool=False,
        reason="Could not analyze task requirements",
        complexity=0.5
    )


def get_coder_status() -> dict[str, Any]:
    """Get status information about the coder agent and tool creation capabilities."""
    registry = get_tool_registry()
    status = registry.get_registry_status()

    return {
        "total_tools": status["total_tools"],
        "active_tools": status["active_tools"],
        "custom_tools": status["custom_tools"],
        "builtin_tools": status["builtin_tools"],
        "coder_tools": len(registry.get_tools_for_agent("coder")),
        "validation_enabled": True,
        "test_execution_enabled": True,
    }
