"""
Test script for the Enhanced Coder Agent.

Tests:
1. ToolNeed schema
2. ValidationResult schema
3. Tool code validation
4. JSON extraction from LLM responses
5. Tool creation with validation
6. Tool analysis functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_tool_need_schema():
    """Test ToolNeed schema creation and validation."""
    print("\n=== Test 1: ToolNeed Schema ===")

    from app.agents.nodes.coder import ToolNeed

    # Test basic creation
    need = ToolNeed(
        needs_tool=True,
        reason="Need custom data processing",
        suggested_name="data_processor",
        suggested_description="Process and transform data",
        complexity=0.7,
        existing_alternatives=["json_parser"]
    )

    print(f"  needs_tool: {need.needs_tool}")
    print(f"  reason: {need.reason}")
    print(f"  suggested_name: {need.suggested_name}")
    print(f"  complexity: {need.complexity}")

    assert need.needs_tool == True
    assert need.complexity >= 0.0 and need.complexity <= 1.0
    assert len(need.existing_alternatives) == 1

    # Test with minimal fields
    need_minimal = ToolNeed(
        needs_tool=False,
        reason="Existing tools suffice"
    )
    assert need_minimal.suggested_name is None
    assert need_minimal.existing_alternatives == []

    print("  [PASSED] ToolNeed schema works correctly")


def test_validation_result_schema():
    """Test ValidationResult schema creation."""
    print("\n=== Test 2: ValidationResult Schema ===")

    from app.agents.nodes.coder import ValidationResult

    # Test full result
    result = ValidationResult(
        is_valid=True,
        errors=[],
        warnings=["Consider adding type hints"],
        security_score=0.9,
        test_output="Test passed",
        test_passed=True
    )

    print(f"  is_valid: {result.is_valid}")
    print(f"  security_score: {result.security_score}")
    print(f"  test_passed: {result.test_passed}")

    assert result.is_valid == True
    assert result.security_score == 0.9
    assert len(result.warnings) == 1

    # Test failure result
    failure = ValidationResult(
        is_valid=False,
        errors=["Syntax error on line 5", "Dangerous import detected"],
        security_score=0.0
    )
    assert failure.is_valid == False
    assert len(failure.errors) == 2
    assert failure.test_passed == False  # default

    print("  [PASSED] ValidationResult schema works correctly")


def test_extract_json_from_response():
    """Test JSON extraction from LLM responses."""
    print("\n=== Test 3: JSON Extraction ===")

    from app.agents.nodes.coder import extract_json_from_response

    # Test JSON in code block
    response1 = '''
    I analyzed the task and here's my recommendation:

    ```json
    {
        "needs_creation": true,
        "name": "text_formatter",
        "description": "Format text data",
        "category": "data",
        "code": "def text_formatter(text: str) -> str:\\n    return text.upper()",
        "reasoning": "Need custom formatting"
    }
    ```

    Let me know if you need anything else.
    '''

    result1 = extract_json_from_response(response1)
    print(f"  Code block JSON: {result1 is not None}")
    assert result1 is not None
    assert result1["needs_creation"] == True
    assert result1["name"] == "text_formatter"

    # Test raw JSON
    response2 = '''
    Analysis complete.
    {"needs_creation": false, "reasoning": "Existing tools work fine"}
    Done.
    '''

    result2 = extract_json_from_response(response2)
    print(f"  Raw JSON: {result2 is not None}")
    assert result2 is not None
    assert result2["needs_creation"] == False

    # Test no JSON
    response3 = "I don't think we need any tools for this task."
    result3 = extract_json_from_response(response3)
    print(f"  No JSON: {result3 is None}")
    assert result3 is None

    # Test nested JSON
    response4 = '''
    Here's the tool spec:
    ```json
    {
        "needs_creation": true,
        "name": "nested_test",
        "code": "def nested_test(data: str) -> str:\\n    result = {\\"key\\": \\"value\\"}\\n    return str(result)",
        "reasoning": "Test nested"
    }
    ```
    '''
    result4 = extract_json_from_response(response4)
    print(f"  Nested JSON: {result4 is not None}")
    assert result4 is not None
    assert result4["name"] == "nested_test"

    print("  [PASSED] JSON extraction works correctly")


def test_validate_tool_code():
    """Test tool code validation."""
    print("\n=== Test 4: Tool Code Validation ===")

    from app.agents.nodes.coder import validate_tool_code

    # Test valid code
    valid_code = '''
def process_data(data: str) -> str:
    """Process input data and return formatted result."""
    try:
        result = data.upper()
        return f"Processed: {result}"
    except Exception as e:
        return f"Error: {e}"
'''

    result = validate_tool_code(valid_code)
    print(f"  Valid code - is_valid: {result.is_valid}")
    print(f"  Valid code - security_score: {result.security_score}")
    assert result.is_valid == True
    assert result.security_score >= 0.8

    # Test code with dangerous pattern
    dangerous_code = '''
import os
def dangerous_func(cmd: str) -> str:
    return os.system(cmd)
'''

    result = validate_tool_code(dangerous_code)
    print(f"  Dangerous code - is_valid: {result.is_valid}")
    print(f"  Dangerous code - errors: {result.errors}")
    assert result.is_valid == False
    assert len(result.errors) > 0

    # Test code without docstring (warning)
    no_docstring = '''
def simple_func(x: str) -> str:
    return x.lower()
'''

    result = validate_tool_code(no_docstring)
    print(f"  No docstring - warnings: {result.warnings}")
    # Should still be valid but with warnings
    assert len(result.warnings) > 0

    # Test code with eval (blocked)
    eval_code = '''
def eval_func(expr: str) -> str:
    """Evaluate expression."""
    return str(eval(expr))
'''

    result = validate_tool_code(eval_code)
    print(f"  Eval code - is_valid: {result.is_valid}")
    assert result.is_valid == False

    print("  [PASSED] Tool code validation works correctly")


def test_validate_with_test_execution():
    """Test validation with test code execution."""
    print("\n=== Test 5: Validation with Test Execution ===")

    from app.agents.nodes.coder import validate_tool_code

    # Tool code
    tool_code = '''
def multiply(a: str, b: str) -> str:
    """Multiply two numbers.

    Args:
        a: First number as string
        b: Second number as string

    Returns:
        Product as string
    """
    try:
        result = float(a) * float(b)
        return str(result)
    except ValueError as e:
        return f"Error: Invalid numbers - {e}"
'''

    # Test code that should pass
    test_code_pass = '''
result = multiply("3", "4")
assert result == "12.0", f"Expected 12.0, got {result}"
print("Test passed!")
'''

    result = validate_tool_code(tool_code, test_code_pass)
    print(f"  Test execution - test_passed: {result.test_passed}")
    print(f"  Test execution - test_output: {result.test_output[:50] if result.test_output else 'None'}...")
    assert result.is_valid == True
    assert result.test_passed == True

    # Test code that should fail
    test_code_fail = '''
result = multiply("3", "4")
assert result == "wrong", f"Expected wrong, got {result}"
'''

    result_fail = validate_tool_code(tool_code, test_code_fail)
    print(f"  Failing test - test_passed: {result_fail.test_passed}")
    # Tool is still valid, just test didn't pass
    assert result_fail.is_valid == True
    assert result_fail.test_passed == False

    print("  [PASSED] Test execution validation works correctly")


def test_tool_spec_schema():
    """Test ToolSpec schema with test_code field."""
    print("\n=== Test 6: ToolSpec Schema ===")

    from app.agents.nodes.coder import ToolSpec

    spec = ToolSpec(
        name="my_tool",
        description="A test tool",
        category="custom",
        code="def my_tool(x: str) -> str:\n    return x",
        needs_creation=True,
        reasoning="Testing",
        test_code="assert my_tool('hello') == 'hello'"
    )

    print(f"  name: {spec.name}")
    print(f"  has test_code: {spec.test_code is not None}")

    assert spec.name == "my_tool"
    assert spec.test_code is not None
    assert spec.needs_creation == True

    print("  [PASSED] ToolSpec schema works correctly")


def test_create_tool_with_validation():
    """Test tool creation with validation."""
    print("\n=== Test 7: Tool Creation with Validation ===")

    from app.agents.nodes.coder import create_tool_from_spec

    # Valid tool spec
    spec = {
        "name": "test_formatter",
        "description": "Format text with prefix",
        "category": "data",
        "code": '''
def test_formatter(text: str, prefix: str = ">>") -> str:
    """Format text with a prefix.

    Args:
        text: Text to format
        prefix: Prefix to add (default: ">>")

    Returns:
        Formatted text string
    """
    try:
        return f"{prefix} {text}"
    except Exception as e:
        return f"Error: {e}"
''',
        "test_code": '''
result = test_formatter("hello")
assert result == ">> hello", f"Unexpected: {result}"
print("Test passed!")
'''
    }

    success, message, validation = create_tool_from_spec(spec)
    print(f"  Creation success: {success}")
    print(f"  Message: {message}")
    if validation:
        print(f"  Validation passed: {validation.is_valid}")
        print(f"  Test passed: {validation.test_passed}")

    assert success == True
    assert validation is not None
    assert validation.test_passed == True

    # Cleanup - unregister test tool
    from app.agents.tools.registry import get_tool_registry
    registry = get_tool_registry()
    registry.unregister("test_formatter")

    print("  [PASSED] Tool creation with validation works correctly")


def test_invalid_tool_name():
    """Test that invalid tool names are rejected."""
    print("\n=== Test 8: Invalid Tool Name Rejection ===")

    from app.agents.nodes.coder import create_tool_from_spec

    # Invalid name (spaces)
    spec1 = {
        "name": "my tool",
        "description": "Test",
        "category": "custom",
        "code": "def my_tool(x: str) -> str:\n    return x"
    }

    success1, message1, _ = create_tool_from_spec(spec1)
    print(f"  Spaces in name - rejected: {not success1}")
    assert success1 == False
    assert "snake_case" in message1

    # Invalid name (uppercase)
    spec2 = {
        "name": "MyTool",
        "description": "Test",
        "category": "custom",
        "code": "def MyTool(x: str) -> str:\n    return x"
    }

    success2, message2, _ = create_tool_from_spec(spec2)
    print(f"  Uppercase name - rejected: {not success2}")
    assert success2 == False

    # Invalid name (starts with number)
    spec3 = {
        "name": "2tool",
        "description": "Test",
        "category": "custom",
        "code": "def tool(x: str) -> str:\n    return x"
    }

    success3, message3, _ = create_tool_from_spec(spec3)
    print(f"  Number start - rejected: {not success3}")
    assert success3 == False

    print("  [PASSED] Invalid tool names are properly rejected")


def test_get_coder_status():
    """Test coder status reporting."""
    print("\n=== Test 9: Coder Status ===")

    from app.agents.nodes.coder import get_coder_status

    status = get_coder_status()

    print(f"  total_tools: {status['total_tools']}")
    print(f"  active_tools: {status['active_tools']}")
    print(f"  validation_enabled: {status['validation_enabled']}")
    print(f"  test_execution_enabled: {status['test_execution_enabled']}")

    assert status['total_tools'] >= 0
    assert status['validation_enabled'] == True
    assert status['test_execution_enabled'] == True

    print("  [PASSED] Coder status reporting works correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Enhanced Coder Agent Tests")
    print("=" * 60)

    # Initialize registry
    from app.agents.tools.registry import register_builtin_tools
    register_builtin_tools()

    test_tool_need_schema()
    test_validation_result_schema()
    test_extract_json_from_response()
    test_validate_tool_code()
    test_validate_with_test_execution()
    test_tool_spec_schema()
    test_create_tool_with_validation()
    test_invalid_tool_name()
    test_get_coder_status()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
