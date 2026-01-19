"""
HTTP tools for making API requests.

These tools provide HTTP request capabilities for interacting with external APIs.
"""

import json
from typing import Optional
import httpx
from langchain_core.tools import tool


@tool
def api_get(url: str, headers: Optional[str] = None) -> str:
    """
    Make an HTTP GET request to an API endpoint.

    Args:
        url: The URL to request (must be a valid HTTP/HTTPS URL)
        headers: Optional JSON string of headers (e.g., '{"Authorization": "Bearer token"}')

    Returns:
        The response body as a string (JSON formatted if applicable), or an error message.
    """
    try:
        # Parse headers if provided
        request_headers = {}
        if headers:
            try:
                request_headers = json.loads(headers)
            except json.JSONDecodeError:
                return "Error: Invalid headers JSON format"

        # Make the request
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=request_headers)

            # Format response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }

            # Try to parse as JSON
            try:
                result["body"] = response.json()
            except:
                # Limit text response size
                text = response.text
                if len(text) > 10000:
                    text = text[:10000] + "... [truncated]"
                result["body"] = text

            return json.dumps(result, indent=2)

    except httpx.TimeoutException:
        return "Error: Request timed out after 30 seconds"
    except httpx.RequestError as e:
        return f"Error: Request failed - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def api_post(url: str, body: str, headers: Optional[str] = None, content_type: str = "application/json") -> str:
    """
    Make an HTTP POST request to an API endpoint.

    Args:
        url: The URL to request (must be a valid HTTP/HTTPS URL)
        body: The request body (JSON string for JSON content type)
        headers: Optional JSON string of additional headers
        content_type: Content type of the request body (default: application/json)

    Returns:
        The response body as a string, or an error message.
    """
    try:
        # Parse headers if provided
        request_headers = {"Content-Type": content_type}
        if headers:
            try:
                extra_headers = json.loads(headers)
                request_headers.update(extra_headers)
            except json.JSONDecodeError:
                return "Error: Invalid headers JSON format"

        # Parse body for JSON content
        request_body = body
        if content_type == "application/json":
            try:
                # Validate it's valid JSON
                json.loads(body)
            except json.JSONDecodeError:
                return "Error: Invalid JSON body"

        # Make the request
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                content=request_body,
                headers=request_headers
            )

            # Format response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }

            # Try to parse as JSON
            try:
                result["body"] = response.json()
            except:
                text = response.text
                if len(text) > 10000:
                    text = text[:10000] + "... [truncated]"
                result["body"] = text

            return json.dumps(result, indent=2)

    except httpx.TimeoutException:
        return "Error: Request timed out after 30 seconds"
    except httpx.RequestError as e:
        return f"Error: Request failed - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def json_parser(json_string: str, path: str) -> str:
    """
    Parse JSON and extract values using a dot-notation path.

    Args:
        json_string: The JSON string to parse
        path: Dot-notation path to extract (e.g., "data.users.0.name" or "items.*.id")
            - Use numbers for array indices (e.g., "items.0")
            - Use * to get all items from an array (e.g., "items.*.name")

    Returns:
        The extracted value(s) as a JSON string.
    """
    try:
        data = json.loads(json_string)

        # Parse the path
        parts = path.split('.')
        current = data

        for part in parts:
            if part == '*':
                # Wildcard: apply rest of path to all items
                if not isinstance(current, list):
                    return f"Error: Cannot use '*' on non-array at path"
                remaining_path = '.'.join(parts[parts.index('*')+1:])
                if remaining_path:
                    results = []
                    for item in current:
                        # Recursively extract from each item
                        result = json_parser.invoke({
                            "json_string": json.dumps(item),
                            "path": remaining_path
                        })
                        if not result.startswith("Error:"):
                            results.append(json.loads(result))
                    return json.dumps(results, indent=2)
                else:
                    return json.dumps(current, indent=2)

            elif part.isdigit():
                # Array index
                idx = int(part)
                if not isinstance(current, list):
                    return f"Error: Cannot index non-array with '{part}'"
                if idx >= len(current):
                    return f"Error: Index {idx} out of range (length: {len(current)})"
                current = current[idx]

            else:
                # Object key
                if not isinstance(current, dict):
                    return f"Error: Cannot access key '{part}' on non-object"
                if part not in current:
                    return f"Error: Key '{part}' not found"
                current = current[part]

        return json.dumps(current, indent=2)

    except json.JSONDecodeError:
        return "Error: Invalid JSON string"
    except Exception as e:
        return f"Error: {str(e)}"
