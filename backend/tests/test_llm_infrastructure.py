"""
Test script for the new LLM infrastructure.

Tests:
1. Configuration loading
2. LLM Manager initialization
3. Complexity analysis
4. Provider selection/routing
5. Health checks
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def test_config_loading():
    """Test that configuration loads correctly."""
    print("\n=== Test 1: Configuration Loading ===")

    from app.core.llm_manager import get_llm_manager

    manager = get_llm_manager()
    config = manager.config

    print(f"  Ollama endpoints: {len(config.ollama_endpoints)}")
    for ep in config.ollama_endpoints:
        print(f"    - {ep.url} (models: {ep.models}, priority: {ep.priority})")

    print(f"  Ollama default model: {config.ollama_default_model}")
    print(f"  Claude enabled: {config.claude_enabled}")
    print(f"  Claude default model: {config.claude_default_model}")
    print(f"  Claude powerful model: {config.claude_powerful_model}")
    print(f"  Complexity threshold: {config.complexity_threshold}")

    assert len(config.ollama_endpoints) > 0, "No Ollama endpoints configured"
    print("  [PASSED] Configuration loaded successfully")


def test_complexity_analyzer():
    """Test complexity analysis."""
    print("\n=== Test 2: Complexity Analyzer ===")

    from app.core.complexity_analyzer import analyze_complexity

    # Simple query
    simple = analyze_complexity("What is the weather today?")
    print(f"  Simple query score: {simple.score:.2f} ({simple.recommendation})")
    print(f"    Reasoning: {simple.reasoning}")

    # Complex query
    complex_query = """
    Analyze the performance implications of using microservices architecture
    versus monolithic architecture for a high-traffic e-commerce platform.
    Compare the following aspects in detail:
    1. Scalability and load balancing
    2. Database management and consistency
    3. Deployment and DevOps complexity
    4. Security considerations
    Provide a comprehensive technical evaluation with specific recommendations.
    """
    complex_result = analyze_complexity(complex_query)
    print(f"  Complex query score: {complex_result.score:.2f} ({complex_result.recommendation})")
    print(f"    Reasoning: {complex_result.reasoning}")

    # Code query
    code_query = "Write a Python function to implement a binary search algorithm"
    code_result = analyze_complexity(code_query)
    print(f"  Code query score: {code_result.score:.2f} ({code_result.recommendation})")
    print(f"    Reasoning: {code_result.reasoning}")

    assert simple.score < complex_result.score, "Complex query should score higher than simple"
    print("  [PASSED] Complexity analysis working correctly")


def test_provider_selection():
    """Test LLM provider selection based on task type."""
    print("\n=== Test 3: Provider Selection ===")

    from app.core.llm_manager import get_llm, get_llm_manager, TaskType, Provider
    from langchain_ollama import ChatOllama
    from langchain_anthropic import ChatAnthropic

    # Test Ollama selection
    ollama_llm = get_llm(task_type=TaskType.RESEARCHER, force_provider=Provider.OLLAMA)
    print(f"  Researcher (forced Ollama): {type(ollama_llm).__name__}")
    assert isinstance(ollama_llm, ChatOllama), "Should return ChatOllama"

    # Test Claude selection (if enabled)
    manager = get_llm_manager()
    if manager.config.claude_enabled:
        claude_llm = get_llm(task_type=TaskType.CODER, force_provider=Provider.CLAUDE)
        print(f"  Coder (forced Claude): {type(claude_llm).__name__}")
        assert isinstance(claude_llm, ChatAnthropic), "Should return ChatAnthropic"

        # Test powerful model
        powerful_llm = get_llm(task_type=TaskType.EDITOR, force_provider=Provider.CLAUDE, use_powerful=True)
        print(f"  Editor (Claude powerful): {type(powerful_llm).__name__}")
        assert isinstance(powerful_llm, ChatAnthropic), "Should return ChatAnthropic"
    else:
        print("  [SKIP] Claude not enabled, skipping Claude tests")

    print("  [PASSED] Provider selection working correctly")


def test_health_check():
    """Test endpoint health checking."""
    print("\n=== Test 4: Health Check ===")

    from app.core.llm_manager import get_llm_manager

    manager = get_llm_manager()

    # Check first endpoint
    if manager.config.ollama_endpoints:
        endpoint = manager.config.ollama_endpoints[0]
        status = manager.check_endpoint_health_sync(endpoint)

        print(f"  Endpoint: {status.url}")
        print(f"  Healthy: {status.is_healthy}")
        if status.is_healthy:
            print(f"  Response time: {status.response_time_ms:.1f}ms")
            print(f"  Available models: {status.available_models}")
        else:
            print(f"  Error: {status.last_error}")

        # This might fail if Ollama isn't running, which is OK for the test
        if status.is_healthy:
            print("  [PASSED] Health check successful")
        else:
            print("  [WARNING] Ollama not responding - make sure it's running")
    else:
        print("  [SKIP] No Ollama endpoints configured")


def test_status_report():
    """Test status reporting."""
    print("\n=== Test 5: Status Report ===")

    from app.core.llm_manager import get_llm_manager
    import json

    manager = get_llm_manager()
    status = manager.get_status()

    print(f"  Status report:")
    print(f"    Ollama endpoints: {len(status['ollama']['endpoints'])}")
    print(f"    Claude enabled: {status['claude']['enabled']}")
    print(f"    Complexity threshold: {status['routing']['complexity_threshold']}")

    # Verify structure
    assert 'ollama' in status
    assert 'claude' in status
    assert 'routing' in status
    print("  [PASSED] Status report generated correctly")


def test_llm_invocation():
    """Test actual LLM invocation."""
    print("\n=== Test 6: LLM Invocation ===")

    from app.core.llm_manager import get_llm, TaskType

    llm = get_llm(task_type=TaskType.GENERAL)
    print(f"  Using LLM: {type(llm).__name__}")

    try:
        response = llm.invoke("Say 'Hello from LLM Manager!' and nothing else.")
        print(f"  Response: {response.content[:100]}...")
        print("  [PASSED] LLM invocation successful")
    except Exception as e:
        print(f"  [WARNING] LLM invocation failed: {e}")
        print("  Make sure Ollama is running with llama3.2 model")


def main():
    """Run all tests."""
    print("=" * 60)
    print("LLM Infrastructure Tests")
    print("=" * 60)

    # Import here to test imports work
    from app.core.llm_manager import get_llm_manager

    test_config_loading()
    test_complexity_analyzer()
    test_provider_selection()
    test_health_check()
    test_status_report()
    test_llm_invocation()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
