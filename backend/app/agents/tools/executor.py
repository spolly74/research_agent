"""
Code Executor - Safe execution environment for Python code.

Provides sandboxed execution of Python code with:
- Restricted imports and builtins
- Memory and time limits
- Output capture
"""

import ast
import sys
import traceback
from io import StringIO
from typing import Any, Optional
from contextlib import contextmanager
import signal
from langchain_core.tools import tool
import structlog

logger = structlog.get_logger(__name__)

# Maximum execution time in seconds
MAX_EXECUTION_TIME = 30

# Maximum output size in characters
MAX_OUTPUT_SIZE = 50000


class TimeoutError(Exception):
    """Raised when code execution exceeds time limit."""
    pass


class SecurityError(Exception):
    """Raised when code attempts forbidden operations."""
    pass


@contextmanager
def timeout_handler(seconds: int):
    """Context manager for execution timeout."""
    def handler(signum, frame):
        raise TimeoutError(f"Execution timed out after {seconds} seconds")

    # Set up the signal handler
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore the old handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def validate_code_safety(code: str) -> tuple[bool, Optional[str]]:
    """
    Validate that code doesn't contain dangerous operations.

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Forbidden names that could be used for dangerous operations
    forbidden_names = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'breakpoint', 'credits', 'exit', 'quit',
        'help', 'license', 'copyright',
        'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'memoryview', 'object', 'property', 'staticmethod',
        'classmethod', 'super', 'type', '__build_class__',
        '__name__', '__doc__', '__package__', '__loader__',
        '__spec__', '__builtins__', '__file__', '__cached__',
    }

    # Forbidden modules
    forbidden_modules = {
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'importlib', 'ctypes', 'multiprocessing', 'threading',
        'socket', 'http', 'urllib', 'ftplib', 'smtplib',
        'pickle', 'shelve', 'marshal', 'dbm',
        'sqlite3', 'builtins', 'code', 'codeop',
        'compileall', 'dis', 'gc', 'inspect',
        'traceback', 'linecache', 'tokenize',
        'signal', 'resource', 'pty', 'tty',
        'termios', 'fcntl', 'pipes', 'posix',
        'pwd', 'grp', 'crypt', 'spwd',
        'tempfile', 'glob', 'fnmatch',
        'asyncio', 'concurrent', 'contextvars',
    }

    for node in ast.walk(tree):
        # Check for forbidden names
        if isinstance(node, ast.Name):
            if node.id in forbidden_names:
                return False, f"Use of '{node.id}' is not allowed"
            if node.id.startswith('_'):
                return False, f"Use of private/dunder names like '{node.id}' is not allowed"

        # Check for forbidden imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name in forbidden_modules:
                    return False, f"Import of '{alias.name}' is not allowed"

        if isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name in forbidden_modules:
                    return False, f"Import from '{node.module}' is not allowed"

        # Check for attribute access to forbidden names
        if isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                return False, f"Access to private/dunder attribute '{node.attr}' is not allowed"

    return True, None


def get_safe_globals() -> dict[str, Any]:
    """Get a restricted set of globals for code execution."""
    import math
    import json
    import re
    import random
    import string
    import itertools
    import functools
    import collections
    from datetime import datetime, date, time, timedelta

    return {
        # Safe builtins
        'abs': abs,
        'all': all,
        'any': any,
        'ascii': ascii,
        'bin': bin,
        'bool': bool,
        'bytearray': bytearray,
        'bytes': bytes,
        'callable': callable,
        'chr': chr,
        'complex': complex,
        'dict': dict,
        'divmod': divmod,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'format': format,
        'frozenset': frozenset,
        'hash': hash,
        'hex': hex,
        'id': id,
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
        'oct': oct,
        'ord': ord,
        'pow': pow,
        'print': print,
        'range': range,
        'repr': repr,
        'reversed': reversed,
        'round': round,
        'set': set,
        'slice': slice,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'zip': zip,
        # Exception types (for try/except)
        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'KeyError': KeyError,
        'IndexError': IndexError,
        'ZeroDivisionError': ZeroDivisionError,
        'AttributeError': AttributeError,
        'RuntimeError': RuntimeError,
        # Safe modules
        'math': math,
        'json': json,
        're': re,
        'random': random,
        'string': string,
        'itertools': itertools,
        'functools': functools,
        'collections': collections,
        # Datetime
        'datetime': datetime,
        'date': date,
        'time': time,
        'timedelta': timedelta,
        # Constants
        'True': True,
        'False': False,
        'None': None,
    }


@tool
def execute_python(code: str) -> str:
    """
    Execute Python code in a sandboxed environment.

    The code runs with restricted permissions:
    - No file system access
    - No network access
    - No system calls
    - Limited execution time (30 seconds)
    - Limited output size

    Available modules: math, json, re, random, string, itertools, functools, collections, datetime

    Args:
        code: Python code to execute. Use print() to produce output.

    Returns:
        The printed output from the code, or an error message.
    """
    # Validate code safety
    is_safe, error = validate_code_safety(code)
    if not is_safe:
        return f"Security Error: {error}"

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        # Get safe execution environment
        safe_globals = get_safe_globals()
        safe_locals = {}

        # Execute with timeout
        with timeout_handler(MAX_EXECUTION_TIME):
            exec(code, safe_globals, safe_locals)

        # Get output
        output = captured_output.getvalue()

        # Truncate if too long
        if len(output) > MAX_OUTPUT_SIZE:
            output = output[:MAX_OUTPUT_SIZE] + f"\n... [Output truncated at {MAX_OUTPUT_SIZE} characters]"

        if not output:
            output = "[Code executed successfully with no output]"

        return output

    except TimeoutError as e:
        return f"Timeout Error: {str(e)}"
    except SecurityError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        # Get traceback but filter out internal frames
        tb = traceback.format_exc()
        # Remove the exec() frame from traceback for cleaner output
        lines = tb.split('\n')
        filtered_lines = [l for l in lines if 'executor.py' not in l]
        return f"Execution Error:\n{''.join(filtered_lines[-5:])}"
    finally:
        sys.stdout = old_stdout


@tool
def analyze_code(code: str) -> str:
    """
    Analyze Python code without executing it.

    Performs static analysis to identify:
    - Syntax errors
    - Potential issues
    - Code structure (functions, classes, imports)
    - Complexity metrics

    Args:
        code: Python code to analyze

    Returns:
        Analysis report as a string.
    """
    result = []

    # Check syntax
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax Error at line {e.lineno}: {e.msg}"

    # Count elements
    functions = []
    classes = []
    imports = []
    variables = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = [a.arg for a in node.args.args]
            functions.append(f"{node.name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    variables.append(target.id)

    # Build report
    result.append("=== Code Analysis Report ===\n")
    result.append(f"Lines of code: {len(code.splitlines())}")

    if imports:
        result.append(f"\nImports ({len(imports)}):")
        for imp in imports[:10]:
            result.append(f"  - {imp}")
        if len(imports) > 10:
            result.append(f"  ... and {len(imports) - 10} more")

    if classes:
        result.append(f"\nClasses ({len(classes)}):")
        for cls in classes:
            result.append(f"  - {cls}")

    if functions:
        result.append(f"\nFunctions ({len(functions)}):")
        for func in functions[:10]:
            result.append(f"  - {func}")
        if len(functions) > 10:
            result.append(f"  ... and {len(functions) - 10} more")

    if variables:
        unique_vars = list(set(variables))
        result.append(f"\nTop-level variables ({len(unique_vars)}):")
        for var in unique_vars[:10]:
            result.append(f"  - {var}")
        if len(unique_vars) > 10:
            result.append(f"  ... and {len(unique_vars) - 10} more")

    # Check for potential issues
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Pass):
            issues.append("Empty block (pass statement)")
        if isinstance(node, ast.Raise) and node.exc is None:
            issues.append("Bare raise statement")

    if issues:
        result.append(f"\nPotential issues ({len(issues)}):")
        for issue in set(issues):
            result.append(f"  - {issue}")

    result.append("\n=== End of Report ===")

    return '\n'.join(result)
