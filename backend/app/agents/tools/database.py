"""
Database Tools - Secure database query operations.

This module provides tools for:
- Querying SQLite databases safely
- Read-only database operations
- Query result formatting
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import Optional, Any

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger(__name__)

# Configuration
MAX_QUERY_RESULTS = 1000  # Maximum rows returned
QUERY_TIMEOUT = 30  # Seconds
MAX_OUTPUT_LENGTH = 50000  # Max characters in output

# Allowed database paths - configurable
ALLOWED_DB_PATHS = [
    "~/research_data",
    "/tmp/research_agent",
]

# Blocked SQL patterns (for additional safety beyond read-only)
BLOCKED_SQL_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"--",  # SQL comments (potential injection)
    r";.*\w",  # Multiple statements
]


def _is_db_path_allowed(db_path: str) -> tuple[bool, str]:
    """
    Check if the database path is within allowed directories.

    Args:
        db_path: Path to the database file

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        resolved = Path(db_path).expanduser().resolve()
    except (ValueError, OSError) as e:
        return False, f"Invalid path: {e}"

    # Check if path is within allowed directories
    for allowed in ALLOWED_DB_PATHS:
        allowed_path = Path(allowed).expanduser().resolve()
        try:
            if str(resolved).startswith(str(allowed_path)):
                return True, ""
        except (ValueError, OSError):
            continue

    return False, f"Database must be in allowed directories: {ALLOWED_DB_PATHS}"


def _validate_query(query: str) -> tuple[bool, str]:
    """
    Validate that a SQL query is safe to execute.

    Args:
        query: The SQL query to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    query_upper = query.upper().strip()

    # Must start with SELECT or WITH (for CTEs)
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        return False, "Only SELECT queries are allowed"

    # Check for blocked patterns
    for pattern in BLOCKED_SQL_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return False, f"Query contains blocked pattern"

    return True, ""


def _format_results(columns: list[str], rows: list[tuple], format_type: str = "table") -> str:
    """
    Format query results for display.

    Args:
        columns: List of column names
        rows: List of row tuples
        format_type: Output format ("table", "json", "csv")

    Returns:
        Formatted result string
    """
    if not rows:
        return "Query returned no results."

    if format_type == "json":
        results = [dict(zip(columns, row)) for row in rows]
        return json.dumps(results, indent=2, default=str)

    elif format_type == "csv":
        lines = [",".join(columns)]
        for row in rows:
            lines.append(",".join(str(v) if v is not None else "" for v in row))
        return "\n".join(lines)

    else:  # table format
        # Calculate column widths
        widths = [len(col) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val) if val is not None else "NULL"))

        # Cap widths at 50 characters
        widths = [min(w, 50) for w in widths]

        # Build table
        separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        header = "| " + " | ".join(col.ljust(widths[i])[:widths[i]] for i, col in enumerate(columns)) + " |"

        lines = [separator, header, separator]

        for row in rows:
            row_str = "| " + " | ".join(
                str(val if val is not None else "NULL").ljust(widths[i])[:widths[i]]
                for i, val in enumerate(row)
            ) + " |"
            lines.append(row_str)

        lines.append(separator)
        lines.append(f"\n{len(rows)} row(s) returned")

        return "\n".join(lines)


def configure_allowed_db_paths(paths: list[str]) -> None:
    """
    Configure allowed database paths.

    Args:
        paths: List of directory paths where databases can be accessed
    """
    global ALLOWED_DB_PATHS
    ALLOWED_DB_PATHS = paths
    logger.info("Updated allowed database paths", paths=paths)


@tool
def database_query(
    db_path: str,
    query: str,
    params: Optional[str] = None,
    output_format: str = "table"
) -> str:
    """
    Execute a read-only SQL query on a SQLite database.

    Only SELECT queries are allowed. The database must be in an allowed directory.
    Maximum 1000 rows returned. Use LIMIT clause for large result sets.

    Args:
        db_path: Path to the SQLite database file
        query: SQL SELECT query to execute
        params: Optional JSON array of query parameters for placeholders (?)
        output_format: Output format - "table", "json", or "csv"

    Returns:
        Query results in the specified format, or an error message

    Examples:
        - database_query("/tmp/research_agent/data.db", "SELECT * FROM users LIMIT 10")
        - database_query("~/research_data/metrics.db", "SELECT name, value FROM metrics WHERE date > ?", '["2024-01-01"]')
        - database_query("/tmp/research_agent/data.db", "SELECT COUNT(*) as total FROM orders", output_format="json")
    """
    logger.info("Database query requested", db_path=db_path, query_length=len(query))

    # Validate output format
    if output_format not in ("table", "json", "csv"):
        return "Error: output_format must be 'table', 'json', or 'csv'"

    # Validate database path
    is_allowed, error = _is_db_path_allowed(db_path)
    if not is_allowed:
        logger.warning("Database access blocked", db_path=db_path, reason=error)
        return f"Error: {error}"

    # Validate query
    is_valid, error = _validate_query(query)
    if not is_valid:
        logger.warning("Query blocked", reason=error)
        return f"Error: {error}"

    # Parse parameters
    query_params: list[Any] = []
    if params:
        try:
            query_params = json.loads(params)
            if not isinstance(query_params, list):
                return "Error: params must be a JSON array"
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON params: {e}"

    # Resolve path
    resolved_path = Path(db_path).expanduser().resolve()

    if not resolved_path.exists():
        return f"Error: Database not found: {db_path}"

    if not resolved_path.is_file():
        return f"Error: Path is not a file: {db_path}"

    # Execute query
    conn = None
    try:
        # Connect in read-only mode with URI
        uri = f"file:{resolved_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=QUERY_TIMEOUT)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        # Execute with timeout
        cursor.execute(query, query_params)

        # Fetch results with limit
        rows = cursor.fetchmany(MAX_QUERY_RESULTS + 1)

        # Check if there are more results
        has_more = len(rows) > MAX_QUERY_RESULTS
        if has_more:
            rows = rows[:MAX_QUERY_RESULTS]

        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []

        # Format results
        result = _format_results(columns, rows, output_format)

        if has_more:
            result += f"\n\nNote: Results truncated at {MAX_QUERY_RESULTS} rows. Use LIMIT clause to paginate."

        # Truncate if too long
        if len(result) > MAX_OUTPUT_LENGTH:
            result = result[:MAX_OUTPUT_LENGTH] + f"\n\n... [Output truncated at {MAX_OUTPUT_LENGTH:,} characters]"

        logger.info("Query executed successfully", rows_returned=len(rows))
        return result

    except sqlite3.OperationalError as e:
        error_msg = str(e)
        if "readonly database" in error_msg.lower():
            return "Error: Database is read-only or locked"
        elif "no such table" in error_msg.lower():
            return f"Error: {error_msg}"
        else:
            logger.error("Query failed", error=error_msg)
            return f"Error executing query: {error_msg}"

    except sqlite3.Error as e:
        logger.error("Database error", error=str(e))
        return f"Database error: {str(e)}"

    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        return f"Error: {str(e)}"

    finally:
        if conn:
            conn.close()


@tool
def database_schema(db_path: str, table_name: Optional[str] = None) -> str:
    """
    Get the schema of a SQLite database or a specific table.

    Returns table names, column definitions, and indexes.

    Args:
        db_path: Path to the SQLite database file
        table_name: Optional specific table name (if omitted, shows all tables)

    Returns:
        Schema information as formatted text, or an error message

    Examples:
        - database_schema("/tmp/research_agent/data.db")
        - database_schema("~/research_data/metrics.db", table_name="users")
    """
    logger.info("Database schema requested", db_path=db_path, table_name=table_name)

    # Validate database path
    is_allowed, error = _is_db_path_allowed(db_path)
    if not is_allowed:
        logger.warning("Database access blocked", db_path=db_path, reason=error)
        return f"Error: {error}"

    # Resolve path
    resolved_path = Path(db_path).expanduser().resolve()

    if not resolved_path.exists():
        return f"Error: Database not found: {db_path}"

    conn = None
    try:
        uri = f"file:{resolved_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=QUERY_TIMEOUT)
        cursor = conn.cursor()

        output_lines = [f"Schema for database: {db_path}\n"]

        if table_name:
            # Get specific table schema
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            result = cursor.fetchone()
            if not result:
                return f"Error: Table '{table_name}' not found"

            output_lines.append(f"Table: {table_name}")
            output_lines.append("-" * 40)
            output_lines.append(result[0])

            # Get indexes
            cursor.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
                (table_name,)
            )
            indexes = cursor.fetchall()
            if indexes:
                output_lines.append("\nIndexes:")
                for idx_name, idx_sql in indexes:
                    if idx_sql:  # Skip auto-created indexes
                        output_lines.append(f"  - {idx_name}: {idx_sql}")

        else:
            # Get all tables
            cursor.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = cursor.fetchall()

            if not tables:
                return f"Database has no tables: {db_path}"

            output_lines.append(f"Tables ({len(tables)}):\n")

            for table_name, create_sql in tables:
                output_lines.append(f"Table: {table_name}")
                output_lines.append("-" * 40)
                output_lines.append(create_sql)
                output_lines.append("")

        logger.info("Schema retrieved successfully")
        return "\n".join(output_lines)

    except sqlite3.Error as e:
        logger.error("Schema retrieval failed", error=str(e))
        return f"Database error: {str(e)}"

    finally:
        if conn:
            conn.close()
