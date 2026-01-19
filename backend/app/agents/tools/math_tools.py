"""
Math tools for calculations and data analysis.

These tools provide mathematical computation capabilities.
"""

import math
import statistics
from typing import Union
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression safely.

    Supports basic arithmetic (+, -, *, /, **, %), parentheses,
    and common math functions (sqrt, sin, cos, tan, log, exp, abs, round).

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)", "sin(3.14/2)")

    Returns:
        The result of the calculation as a string, or an error message.
    """
    # Define allowed names for eval
    allowed_names = {
        # Basic math operations are handled by Python
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'pow': pow,
        # Math module functions
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'log': math.log,
        'log10': math.log10,
        'log2': math.log2,
        'exp': math.exp,
        'floor': math.floor,
        'ceil': math.ceil,
        'factorial': math.factorial,
        'gcd': math.gcd,
        # Constants
        'pi': math.pi,
        'e': math.e,
        'inf': math.inf,
    }

    try:
        # Remove any potentially dangerous characters
        # Only allow digits, operators, parentheses, dots, commas, and function names
        import re
        if not re.match(r'^[\d\s\+\-\*\/\%\(\)\.\,\w]+$', expression):
            return f"Error: Invalid characters in expression"

        # Evaluate the expression in a restricted namespace
        result = eval(expression, {"__builtins__": {}}, allowed_names)

        # Format the result
        if isinstance(result, float):
            # Round to reasonable precision
            if result == int(result):
                return str(int(result))
            return f"{result:.10g}"
        return str(result)

    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: Invalid value - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def statistics_calculator(numbers: str, operation: str) -> str:
    """
    Perform statistical calculations on a list of numbers.

    Args:
        numbers: Comma-separated list of numbers (e.g., "1, 2, 3, 4, 5")
        operation: Statistical operation to perform. Options:
            - mean: Calculate the average
            - median: Calculate the middle value
            - mode: Calculate the most common value
            - stdev: Calculate standard deviation
            - variance: Calculate variance
            - min: Find minimum value
            - max: Find maximum value
            - sum: Calculate sum
            - count: Count the numbers

    Returns:
        The result of the statistical calculation.
    """
    try:
        # Parse the numbers
        num_list = [float(n.strip()) for n in numbers.split(',')]

        if not num_list:
            return "Error: No numbers provided"

        operation = operation.lower().strip()

        if operation == "mean":
            result = statistics.mean(num_list)
        elif operation == "median":
            result = statistics.median(num_list)
        elif operation == "mode":
            try:
                result = statistics.mode(num_list)
            except statistics.StatisticsError:
                return "Error: No unique mode found"
        elif operation == "stdev":
            if len(num_list) < 2:
                return "Error: Need at least 2 numbers for standard deviation"
            result = statistics.stdev(num_list)
        elif operation == "variance":
            if len(num_list) < 2:
                return "Error: Need at least 2 numbers for variance"
            result = statistics.variance(num_list)
        elif operation == "min":
            result = min(num_list)
        elif operation == "max":
            result = max(num_list)
        elif operation == "sum":
            result = sum(num_list)
        elif operation == "count":
            result = len(num_list)
        else:
            return f"Error: Unknown operation '{operation}'. Valid options: mean, median, mode, stdev, variance, min, max, sum, count"

        # Format result
        if isinstance(result, float):
            return f"{result:.10g}"
        return str(result)

    except ValueError as e:
        return f"Error: Invalid number format - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """
    Convert values between different units of measurement.

    Supported conversions:
    - Length: m, km, cm, mm, mi, ft, in, yd
    - Weight: kg, g, mg, lb, oz
    - Temperature: C, F, K
    - Time: s, ms, min, h, d
    - Data: B, KB, MB, GB, TB

    Args:
        value: The numeric value to convert
        from_unit: The source unit (e.g., "km", "lb", "C")
        to_unit: The target unit (e.g., "mi", "kg", "F")

    Returns:
        The converted value with units.
    """
    # Conversion factors to base units
    conversions = {
        # Length (base: meters)
        'm': ('length', 1),
        'km': ('length', 1000),
        'cm': ('length', 0.01),
        'mm': ('length', 0.001),
        'mi': ('length', 1609.344),
        'ft': ('length', 0.3048),
        'in': ('length', 0.0254),
        'yd': ('length', 0.9144),

        # Weight (base: grams)
        'g': ('weight', 1),
        'kg': ('weight', 1000),
        'mg': ('weight', 0.001),
        'lb': ('weight', 453.592),
        'oz': ('weight', 28.3495),

        # Time (base: seconds)
        's': ('time', 1),
        'ms': ('time', 0.001),
        'min': ('time', 60),
        'h': ('time', 3600),
        'd': ('time', 86400),

        # Data (base: bytes)
        'B': ('data', 1),
        'KB': ('data', 1024),
        'MB': ('data', 1024**2),
        'GB': ('data', 1024**3),
        'TB': ('data', 1024**4),
    }

    from_unit = from_unit.strip()
    to_unit = to_unit.strip()

    # Handle temperature separately (not linear conversion)
    if from_unit in ['C', 'F', 'K'] or to_unit in ['C', 'F', 'K']:
        try:
            # Convert to Celsius first
            if from_unit == 'C':
                celsius = value
            elif from_unit == 'F':
                celsius = (value - 32) * 5/9
            elif from_unit == 'K':
                celsius = value - 273.15
            else:
                return f"Error: Unknown temperature unit '{from_unit}'"

            # Convert from Celsius to target
            if to_unit == 'C':
                result = celsius
            elif to_unit == 'F':
                result = celsius * 9/5 + 32
            elif to_unit == 'K':
                result = celsius + 273.15
            else:
                return f"Error: Unknown temperature unit '{to_unit}'"

            return f"{result:.6g} {to_unit}"

        except Exception as e:
            return f"Error: {str(e)}"

    # Check if units are valid
    if from_unit not in conversions:
        return f"Error: Unknown unit '{from_unit}'"
    if to_unit not in conversions:
        return f"Error: Unknown unit '{to_unit}'"

    # Check if units are compatible
    from_type, from_factor = conversions[from_unit]
    to_type, to_factor = conversions[to_unit]

    if from_type != to_type:
        return f"Error: Cannot convert between {from_type} and {to_type}"

    try:
        # Convert: value * from_factor / to_factor
        result = value * from_factor / to_factor
        return f"{result:.10g} {to_unit}"
    except Exception as e:
        return f"Error: {str(e)}"
