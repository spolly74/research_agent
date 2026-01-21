"""
Filesystem Tools - Secure file reading and writing operations.

This module provides tools for:
- Reading local files with path validation
- Writing files with safety checks
- Path sanitization to prevent directory traversal
"""

import os
import re
from pathlib import Path
from typing import Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)

# Configuration
MAX_FILE_SIZE_READ = 10 * 1024 * 1024  # 10 MB max read
MAX_FILE_SIZE_WRITE = 5 * 1024 * 1024  # 5 MB max write
MAX_OUTPUT_LENGTH = 100000  # Max characters returned

# Default allowed directories - can be configured
ALLOWED_READ_DIRS = [
    os.path.expanduser("~/research_data"),
    os.path.expanduser("~/Documents"),
    "/tmp/research_agent",
]

ALLOWED_WRITE_DIRS = [
    os.path.expanduser("~/research_output"),
    "/tmp/research_agent/output",
]

# Allowed file extensions for reading
ALLOWED_READ_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml",
    ".py", ".js", ".ts", ".html", ".css", ".sql", ".sh",
    ".log", ".conf", ".cfg", ".ini", ".toml",
}

# Blocked file patterns
BLOCKED_PATTERNS = [
    r"\.env",  # Environment files
    r"\.ssh",  # SSH keys
    r"\.aws",  # AWS credentials
    r"\.git/config",  # Git config
    r"credentials",  # Credential files
    r"secret",  # Secret files
    r"password",  # Password files
    r"\.pem$",  # Certificates
    r"\.key$",  # Private keys
]


def _is_path_safe(path: str, allowed_dirs: list[str]) -> tuple[bool, str]:
    """
    Validate that a path is safe to access.

    Checks:
    - Path doesn't contain traversal sequences
    - Resolved path is within allowed directories
    - Path doesn't match blocked patterns

    Args:
        path: The file path to validate
        allowed_dirs: List of allowed directory paths

    Returns:
        Tuple of (is_safe, error_message)
    """
    # Check for obvious traversal attempts
    if ".." in path:
        return False, "Path traversal (..) not allowed"

    # Resolve to absolute path
    try:
        resolved = Path(path).resolve()
    except (ValueError, OSError) as e:
        return False, f"Invalid path: {e}"

    # Check against blocked patterns
    path_str = str(resolved).lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, path_str, re.IGNORECASE):
            return False, f"Access to files matching pattern '{pattern}' is not allowed"

    # Check if path is within allowed directories
    allowed = False
    for allowed_dir in allowed_dirs:
        try:
            allowed_path = Path(allowed_dir).resolve()
            if str(resolved).startswith(str(allowed_path)):
                allowed = True
                break
        except (ValueError, OSError):
            continue

    if not allowed:
        return False, f"Path must be within allowed directories: {allowed_dirs}"

    return True, ""


def _ensure_directory_exists(path: str) -> None:
    """Ensure the parent directory exists for a file path."""
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)


def configure_allowed_directories(
    read_dirs: Optional[list[str]] = None,
    write_dirs: Optional[list[str]] = None
) -> None:
    """
    Configure allowed directories for file operations.

    Args:
        read_dirs: List of directories allowed for reading
        write_dirs: List of directories allowed for writing
    """
    global ALLOWED_READ_DIRS, ALLOWED_WRITE_DIRS

    if read_dirs is not None:
        ALLOWED_READ_DIRS = [os.path.expanduser(d) for d in read_dirs]
        logger.info("Updated allowed read directories", dirs=ALLOWED_READ_DIRS)

    if write_dirs is not None:
        ALLOWED_WRITE_DIRS = [os.path.expanduser(d) for d in write_dirs]
        logger.info("Updated allowed write directories", dirs=ALLOWED_WRITE_DIRS)


@tool
def file_reader(file_path: str, encoding: str = "utf-8") -> str:
    """
    Read the contents of a local file securely.

    The file must be within allowed directories and have an allowed extension.
    Maximum file size is 10 MB. Sensitive files (credentials, keys, etc.) are blocked.

    Args:
        file_path: Absolute path to the file to read
        encoding: Text encoding to use (default: utf-8)

    Returns:
        The file contents as a string, or an error message if the operation fails

    Examples:
        - file_reader("/home/user/research_data/report.txt")
        - file_reader("/tmp/research_agent/data.json")
    """
    logger.info("File read requested", path=file_path)

    # Validate path safety
    is_safe, error = _is_path_safe(file_path, ALLOWED_READ_DIRS)
    if not is_safe:
        logger.warning("File read blocked", path=file_path, reason=error)
        return f"Error: {error}"

    resolved_path = Path(file_path).resolve()

    # Check file extension
    extension = resolved_path.suffix.lower()
    if extension not in ALLOWED_READ_EXTENSIONS:
        return f"Error: File extension '{extension}' not allowed. Allowed: {', '.join(sorted(ALLOWED_READ_EXTENSIONS))}"

    # Check if file exists
    if not resolved_path.exists():
        return f"Error: File not found: {file_path}"

    if not resolved_path.is_file():
        return f"Error: Path is not a file: {file_path}"

    # Check file size
    file_size = resolved_path.stat().st_size
    if file_size > MAX_FILE_SIZE_READ:
        return f"Error: File too large ({file_size:,} bytes). Maximum: {MAX_FILE_SIZE_READ:,} bytes"

    # Read the file
    try:
        content = resolved_path.read_text(encoding=encoding)

        # Truncate if too long
        if len(content) > MAX_OUTPUT_LENGTH:
            content = content[:MAX_OUTPUT_LENGTH] + f"\n\n... [Truncated - file has {len(content):,} characters, showing first {MAX_OUTPUT_LENGTH:,}]"

        logger.info("File read successful", path=file_path, size=file_size)
        return content

    except UnicodeDecodeError:
        return f"Error: Unable to decode file with encoding '{encoding}'. Try a different encoding."
    except PermissionError:
        return f"Error: Permission denied reading file: {file_path}"
    except Exception as e:
        logger.error("File read failed", path=file_path, error=str(e))
        return f"Error reading file: {str(e)}"


@tool
def file_writer(file_path: str, content: str, mode: str = "write", encoding: str = "utf-8") -> str:
    """
    Write content to a local file securely.

    The file must be within allowed output directories.
    Maximum content size is 5 MB. Creates parent directories if needed.

    Args:
        file_path: Absolute path where the file should be written
        content: The text content to write to the file
        mode: Write mode - "write" (overwrite) or "append"
        encoding: Text encoding to use (default: utf-8)

    Returns:
        Success message with file path, or an error message if the operation fails

    Examples:
        - file_writer("/home/user/research_output/analysis.txt", "Analysis results...")
        - file_writer("/tmp/research_agent/output/log.txt", "New entry", mode="append")
    """
    logger.info("File write requested", path=file_path, mode=mode, size=len(content))

    # Validate mode
    if mode not in ("write", "append"):
        return "Error: Mode must be 'write' or 'append'"

    # Validate path safety
    is_safe, error = _is_path_safe(file_path, ALLOWED_WRITE_DIRS)
    if not is_safe:
        logger.warning("File write blocked", path=file_path, reason=error)
        return f"Error: {error}"

    # Check content size
    content_size = len(content.encode(encoding))
    if content_size > MAX_FILE_SIZE_WRITE:
        return f"Error: Content too large ({content_size:,} bytes). Maximum: {MAX_FILE_SIZE_WRITE:,} bytes"

    resolved_path = Path(file_path).resolve()

    # Ensure parent directory exists
    try:
        _ensure_directory_exists(str(resolved_path))
    except PermissionError:
        return f"Error: Cannot create directory for: {file_path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"

    # Write the file
    try:
        write_mode = "w" if mode == "write" else "a"
        with open(resolved_path, write_mode, encoding=encoding) as f:
            f.write(content)

        logger.info("File write successful", path=file_path, size=content_size)
        return f"Successfully wrote {content_size:,} bytes to: {file_path}"

    except PermissionError:
        return f"Error: Permission denied writing to: {file_path}"
    except Exception as e:
        logger.error("File write failed", path=file_path, error=str(e))
        return f"Error writing file: {str(e)}"


@tool
def list_directory(directory_path: str, pattern: str = "*") -> str:
    """
    List contents of a directory securely.

    The directory must be within allowed read directories.
    Supports glob patterns for filtering files.

    Args:
        directory_path: Absolute path to the directory to list
        pattern: Glob pattern to filter files (default: "*" for all files)

    Returns:
        A formatted list of files and directories, or an error message

    Examples:
        - list_directory("/home/user/research_data")
        - list_directory("/tmp/research_agent", pattern="*.json")
    """
    logger.info("Directory list requested", path=directory_path, pattern=pattern)

    # Validate path safety
    is_safe, error = _is_path_safe(directory_path, ALLOWED_READ_DIRS)
    if not is_safe:
        logger.warning("Directory list blocked", path=directory_path, reason=error)
        return f"Error: {error}"

    resolved_path = Path(directory_path).resolve()

    if not resolved_path.exists():
        return f"Error: Directory not found: {directory_path}"

    if not resolved_path.is_dir():
        return f"Error: Path is not a directory: {directory_path}"

    try:
        # Get matching files
        entries = list(resolved_path.glob(pattern))

        if not entries:
            return f"No files matching pattern '{pattern}' in {directory_path}"

        # Format output
        output_lines = [f"Contents of {directory_path} (pattern: {pattern}):\n"]

        # Separate directories and files
        dirs = sorted([e for e in entries if e.is_dir()])
        files = sorted([e for e in entries if e.is_file()])

        for d in dirs:
            output_lines.append(f"  [DIR]  {d.name}/")

        for f in files:
            size = f.stat().st_size
            size_str = _format_size(size)
            output_lines.append(f"  [FILE] {f.name} ({size_str})")

        output_lines.append(f"\nTotal: {len(dirs)} directories, {len(files)} files")

        logger.info("Directory list successful", path=directory_path, count=len(entries))
        return "\n".join(output_lines)

    except PermissionError:
        return f"Error: Permission denied accessing: {directory_path}"
    except Exception as e:
        logger.error("Directory list failed", path=directory_path, error=str(e))
        return f"Error listing directory: {str(e)}"


def _format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
