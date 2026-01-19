"""
Test script for the dynamic tool system.

Tests:
1. Tool registry initialization
2. Built-in tool registration
3. Dynamic tool creation
4. Tool execution
5. Code executor safety
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_registry_initialization():
    """Test that the tool registry initializes correctly."""
    print("\n=== Test 1: Registry Initialization ===")

    from app.agents.tools.registry import get_tool_registry, register_builtin_tools

    # Register built-in tools
    register_builtin_tools()

    registry = get_tool_registry()
    status = registry.get_registry_status()

    print(f"  Total tools: {status['total_tools']}")
    print(f"  Active tools: {status['active_tools']}")
    print(f"  Built-in tools: {status['builtin_tools']}")
    print(f"  Custom tools: {status['custom_tools']}")

    assert status['total_tools'] >= 10, "Should have at least 10 built-in tools"
    print("  [PASSED] Registry initialized with built-in tools")


def test_tool_categories():
    """Test that tools are properly categorized."""
    print("\n=== Test 2: Tool Categories ===")

    from app.agents.tools.registry import get_tool_registry, ToolCategory

    registry = get_tool_registry()

    # Check browser tools
    browser_tools = registry.get_tools_by_category(ToolCategory.BROWSER)
    print(f"  Browser tools: {len(browser_tools)}")
    assert len(browser_tools) >= 2, "Should have browser_search and visit_page"

    # Check math tools
    math_tools = registry.get_tools_by_category(ToolCategory.MATH)
    print(f"  Math tools: {len(math_tools)}")
    assert len(math_tools) >= 3, "Should have calculator, statistics_calculator, unit_converter"

    # Check code tools
    code_tools = registry.get_tools_by_category(ToolCategory.CODE)
    print(f"  Code tools: {len(code_tools)}")
    assert len(code_tools) >= 2, "Should have execute_python and analyze_code"

    print("  [PASSED] Tools properly categorized")


def test_agent_tool_filtering():
    """Test that agents get the correct tools."""
    print("\n=== Test 3: Agent Tool Filtering ===")

    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()

    # Researcher should have browser tools
    researcher_tools = registry.get_tools_for_agent("researcher")
    researcher_names = [t.name for t in researcher_tools]
    print(f"  Researcher tools ({len(researcher_tools)}): {researcher_names}")
    assert "browser_search" in researcher_names, "Researcher should have browser_search"

    # Coder should have code execution tools
    coder_tools = registry.get_tools_for_agent("coder")
    coder_names = [t.name for t in coder_tools]
    print(f"  Coder tools ({len(coder_tools)}): {coder_names}")
    assert "execute_python" in coder_names, "Coder should have execute_python"

    print("  [PASSED] Agent tool filtering works correctly")


def test_calculator_tool():
    """Test the calculator tool."""
    print("\n=== Test 4: Calculator Tool ===")

    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    calculator = registry.get_tool("calculator")

    # Test basic math
    result = calculator.invoke({"expression": "2 + 2"})
    print(f"  2 + 2 = {result}")
    assert result == "4", "2 + 2 should equal 4"

    # Test complex expression
    result = calculator.invoke({"expression": "sqrt(16) + pow(2, 3)"})
    print(f"  sqrt(16) + pow(2, 3) = {result}")
    assert result == "12", "sqrt(16) + pow(2, 3) should equal 12"

    print("  [PASSED] Calculator tool works correctly")


def test_code_executor_safety():
    """Test that the code executor blocks dangerous operations."""
    print("\n=== Test 5: Code Executor Safety ===")

    from app.agents.tools.executor import execute_python

    # Test safe code
    result = execute_python.invoke({"code": "print(2 + 2)"})
    print(f"  Safe code result: {result.strip()}")
    assert "4" in result, "Safe code should execute"

    # Test dangerous import
    result = execute_python.invoke({"code": "import os\nos.system('ls')"})
    print(f"  Dangerous import result: {result[:50]}...")
    assert "Security Error" in result or "not allowed" in result, "Should block os import"

    # Test eval
    result = execute_python.invoke({"code": "eval('1+1')"})
    print(f"  Eval attempt result: {result[:50]}...")
    assert "Security Error" in result or "not allowed" in result, "Should block eval"

    print("  [PASSED] Code executor properly blocks dangerous operations")


def test_dynamic_tool_creation():
    """Test creating a dynamic tool."""
    print("\n=== Test 6: Dynamic Tool Creation ===")

    from app.agents.tools.registry import get_tool_registry, ToolCategory

    registry = get_tool_registry()

    # Create a simple tool
    code = '''
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"
'''

    success, tool, error = registry.create_tool_from_code(
        name="greet",
        description="Greet someone by name",
        code=code,
        category=ToolCategory.CUSTOM
    )

    print(f"  Creation success: {success}")
    if error:
        print(f"  Error: {error}")

    assert success, f"Tool creation should succeed: {error}"

    # Test the tool
    result = tool.invoke({"name": "World"})
    print(f"  greet('World') = {result}")
    assert result == "Hello, World!", "Tool should return greeting"

    # Verify it's in the registry
    retrieved = registry.get_tool("greet")
    assert retrieved is not None, "Tool should be retrievable from registry"

    print("  [PASSED] Dynamic tool creation works correctly")


def test_dangerous_tool_blocked():
    """Test that dangerous tool code is blocked."""
    print("\n=== Test 7: Dangerous Tool Blocked ===")

    from app.agents.tools.registry import get_tool_registry, ToolCategory

    registry = get_tool_registry()

    # Try to create a tool with os import
    dangerous_code = '''
import os
def dangerous_tool(cmd: str) -> str:
    """Execute a shell command."""
    return os.popen(cmd).read()
'''

    success, tool, error = registry.create_tool_from_code(
        name="dangerous_tool",
        description="A dangerous tool",
        code=dangerous_code,
        category=ToolCategory.CUSTOM
    )

    print(f"  Dangerous tool creation blocked: {not success}")
    print(f"  Error message: {error}")

    assert not success, "Dangerous tool creation should be blocked"
    assert "not allowed" in error.lower() or "import" in error.lower(), "Should mention import restriction"

    print("  [PASSED] Dangerous tools are properly blocked")


def test_statistics_tool():
    """Test the statistics calculator tool."""
    print("\n=== Test 8: Statistics Calculator ===")

    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    stats_calc = registry.get_tool("statistics_calculator")

    # Test mean
    result = stats_calc.invoke({"numbers": "1, 2, 3, 4, 5", "operation": "mean"})
    print(f"  Mean of 1,2,3,4,5 = {result}")
    assert result == "3", "Mean should be 3"

    # Test median
    result = stats_calc.invoke({"numbers": "1, 2, 3, 4, 5", "operation": "median"})
    print(f"  Median of 1,2,3,4,5 = {result}")
    assert result == "3", "Median should be 3"

    print("  [PASSED] Statistics calculator works correctly")


def test_unit_converter():
    """Test the unit converter tool."""
    print("\n=== Test 9: Unit Converter ===")

    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    converter = registry.get_tool("unit_converter")

    # Test length conversion
    result = converter.invoke({"value": 1.0, "from_unit": "km", "to_unit": "m"})
    print(f"  1 km = {result}")
    assert "1000" in result, "1 km should be 1000 m"

    # Test temperature conversion
    result = converter.invoke({"value": 0.0, "from_unit": "C", "to_unit": "F"})
    print(f"  0 C = {result}")
    assert "32" in result, "0 C should be 32 F"

    print("  [PASSED] Unit converter works correctly")


def test_json_parser():
    """Test the JSON parser tool."""
    print("\n=== Test 10: JSON Parser ===")

    from app.agents.tools.registry import get_tool_registry

    registry = get_tool_registry()
    parser = registry.get_tool("json_parser")

    # Test simple path
    json_data = '{"name": "Alice", "age": 30}'
    result = parser.invoke({"json_string": json_data, "path": "name"})
    print(f"  Extract 'name' from {json_data}: {result}")
    assert "Alice" in result, "Should extract name"

    # Test nested path
    json_data = '{"user": {"profile": {"email": "test@example.com"}}}'
    result = parser.invoke({"json_string": json_data, "path": "user.profile.email"})
    print(f"  Extract nested email: {result}")
    assert "test@example.com" in result, "Should extract nested email"

    print("  [PASSED] JSON parser works correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Dynamic Tool System Tests")
    print("=" * 60)

    test_registry_initialization()
    test_tool_categories()
    test_agent_tool_filtering()
    test_calculator_tool()
    test_code_executor_safety()
    test_dynamic_tool_creation()
    test_dangerous_tool_blocked()
    test_statistics_tool()
    test_unit_converter()
    test_json_parser()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
