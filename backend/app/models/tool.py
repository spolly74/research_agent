"""
Database models for tool persistence.

Stores dynamically created tools so they survive restarts.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from datetime import datetime
from app.core.database import Base


class Tool(Base):
    """Persisted tool definition."""
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(50), default="custom")
    source_code = Column(Text, nullable=False)
    code_hash = Column(String(32))

    is_builtin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Metadata
    allowed_agents = Column(JSON, default=list)  # List of agent types
    execution_count = Column(Integer, default=0)
    last_execution = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ToolExecution(Base):
    """Log of tool executions for analytics."""
    __tablename__ = "tool_executions"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    session_id = Column(Integer, nullable=True)  # Optional link to chat session
    agent_type = Column(String(50))

    # Execution details
    input_args = Column(JSON)
    output = Column(Text)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
