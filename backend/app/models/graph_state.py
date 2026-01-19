"""
Database models for LangGraph state persistence.

Stores graph checkpoints to enable session recovery across server restarts.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from datetime import datetime
from app.core.database import Base


class GraphCheckpoint(Base):
    """
    Stores LangGraph checkpoint data for state persistence.

    Each checkpoint represents a snapshot of the graph state at a specific point.
    Multiple checkpoints can exist for a single thread (for history/rollback).
    """
    __tablename__ = "graph_checkpoints"

    id = Column(Integer, primary_key=True, index=True)

    # LangGraph thread identification
    thread_id = Column(String(255), nullable=False, index=True)
    checkpoint_id = Column(String(255), nullable=False)
    parent_checkpoint_id = Column(String(255), nullable=True)

    # Checkpoint data (serialized state)
    checkpoint_data = Column(Text, nullable=False)  # JSON serialized

    # Metadata
    metadata = Column(Text, nullable=True)  # JSON serialized metadata

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for efficient lookups
    __table_args__ = (
        Index('ix_thread_checkpoint', 'thread_id', 'checkpoint_id'),
    )


class GraphWrite(Base):
    """
    Stores pending writes for a checkpoint.

    LangGraph may need to track writes that haven't been committed yet.
    """
    __tablename__ = "graph_writes"

    id = Column(Integer, primary_key=True, index=True)

    # Link to checkpoint
    thread_id = Column(String(255), nullable=False, index=True)
    checkpoint_id = Column(String(255), nullable=False)

    # Write identification
    task_id = Column(String(255), nullable=False)
    channel = Column(String(255), nullable=False)

    # Write data
    write_type = Column(String(50), nullable=False)  # 'put', 'delete', etc.
    value = Column(Text, nullable=True)  # JSON serialized

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_write_thread_checkpoint', 'thread_id', 'checkpoint_id'),
    )


class SessionRecovery(Base):
    """
    Tracks session recovery information.

    Stores the last known good state for quick session resumption.
    """
    __tablename__ = "session_recovery"

    id = Column(Integer, primary_key=True, index=True)

    # Session identification
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    thread_id = Column(String(255), nullable=False)

    # Last checkpoint reference
    last_checkpoint_id = Column(String(255), nullable=True)

    # Session state
    status = Column(String(50), default="active")  # active, completed, error, abandoned
    last_phase = Column(String(50), nullable=True)

    # Recovery metadata
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
