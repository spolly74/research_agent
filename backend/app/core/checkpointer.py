"""
Database-backed checkpointer for LangGraph state persistence.

Implements LangGraph's BaseCheckpointSaver interface to persist
graph state to SQLite, enabling session recovery across restarts.
"""

import base64
import json
import uuid
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple
from datetime import datetime
import structlog

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.graph_state import GraphCheckpoint, GraphWrite, SessionRecovery

logger = structlog.get_logger(__name__)


def _serialize_data(data: Any) -> str:
    """Serialize data to a JSON-safe string, handling bytes."""
    if isinstance(data, bytes):
        return json.dumps({"__bytes__": True, "data": base64.b64encode(data).decode("utf-8")})
    return json.dumps(data)


def _deserialize_data(data_str: str) -> Any:
    """Deserialize data from JSON string, handling bytes."""
    data = json.loads(data_str)
    if isinstance(data, dict) and data.get("__bytes__"):
        return base64.b64decode(data["data"])
    return data


class DatabaseCheckpointer(BaseCheckpointSaver):
    """
    SQLite-backed checkpointer for LangGraph.

    Persists graph checkpoints to the database for recovery after restarts.
    Uses JSON serialization for checkpoint data.
    """

    def __init__(self, serde: Optional[SerializerProtocol] = None):
        """Initialize the checkpointer with optional serializer."""
        super().__init__(serde=serde or JsonPlusSerializer())

    def _get_db(self) -> Session:
        """Get a database session."""
        return SessionLocal()

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        Get a checkpoint tuple by config.

        Args:
            config: Configuration dict with thread_id and optionally checkpoint_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")

        db = self._get_db()
        try:
            query = db.query(GraphCheckpoint).filter(
                GraphCheckpoint.thread_id == thread_id
            )

            if checkpoint_id:
                query = query.filter(GraphCheckpoint.checkpoint_id == checkpoint_id)
            else:
                # Get the latest checkpoint for this thread
                query = query.order_by(GraphCheckpoint.created_at.desc())

            checkpoint_row = query.first()

            if not checkpoint_row:
                return None

            # Deserialize checkpoint data
            checkpoint_data = json.loads(checkpoint_row.checkpoint_data)
            # Handle both old format (data) and new format (data_str) for backwards compatibility
            if "data_str" in checkpoint_data:
                data = _deserialize_data(checkpoint_data["data_str"])
            else:
                data = checkpoint_data["data"]
            checkpoint = self.serde.loads_typed((checkpoint_data["type"], data))

            # Parse metadata - ensure 'step' is always present
            metadata = {"step": -1}  # Default step value
            if checkpoint_row.checkpoint_metadata:
                saved_metadata = json.loads(checkpoint_row.checkpoint_metadata)
                metadata.update(saved_metadata)

            # Get pending writes
            writes = self._get_writes(db, thread_id, checkpoint_row.checkpoint_id)

            # Build config for this checkpoint
            checkpoint_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_row.checkpoint_id,
                }
            }

            # Build parent config if exists
            parent_config = None
            if checkpoint_row.parent_checkpoint_id:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": checkpoint_row.parent_checkpoint_id,
                    }
                }

            return CheckpointTuple(
                config=checkpoint_config,
                checkpoint=checkpoint,
                metadata=CheckpointMetadata(**metadata) if metadata else CheckpointMetadata(),
                parent_config=parent_config,
                pending_writes=writes,
            )

        except Exception as e:
            logger.error("Error getting checkpoint", error=str(e), thread_id=thread_id)
            return None
        finally:
            db.close()

    def _get_writes(
        self, db: Session, thread_id: str, checkpoint_id: str
    ) -> list[Tuple[str, str, Any]]:
        """Get pending writes for a checkpoint."""
        writes_rows = (
            db.query(GraphWrite)
            .filter(
                GraphWrite.thread_id == thread_id,
                GraphWrite.checkpoint_id == checkpoint_id,
            )
            .all()
        )

        writes = []
        for row in writes_rows:
            value = None
            if row.value:
                value_data = json.loads(row.value)
                # Handle both old format (data) and new format (data_str)
                if "data_str" in value_data:
                    data = _deserialize_data(value_data["data_str"])
                else:
                    data = value_data["data"]
                value = self.serde.loads_typed((value_data["type"], data))
            writes.append((row.task_id, row.channel, value))

        return writes

    def list(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """
        List checkpoints matching the given criteria.

        Args:
            config: Configuration with thread_id
            filter: Optional filter criteria
            before: Return checkpoints before this config
            limit: Maximum number of checkpoints to return

        Yields:
            CheckpointTuple for each matching checkpoint
        """
        if not config:
            return

        thread_id = config["configurable"]["thread_id"]

        db = self._get_db()
        try:
            query = db.query(GraphCheckpoint).filter(
                GraphCheckpoint.thread_id == thread_id
            )

            if before:
                before_checkpoint_id = before["configurable"].get("checkpoint_id")
                if before_checkpoint_id:
                    # Get the created_at of the before checkpoint
                    before_row = (
                        db.query(GraphCheckpoint)
                        .filter(
                            GraphCheckpoint.thread_id == thread_id,
                            GraphCheckpoint.checkpoint_id == before_checkpoint_id,
                        )
                        .first()
                    )
                    if before_row:
                        query = query.filter(
                            GraphCheckpoint.created_at < before_row.created_at
                        )

            query = query.order_by(GraphCheckpoint.created_at.desc())

            if limit:
                query = query.limit(limit)

            for row in query.all():
                checkpoint_data = json.loads(row.checkpoint_data)
                # Handle both old format (data) and new format (data_str)
                if "data_str" in checkpoint_data:
                    data = _deserialize_data(checkpoint_data["data_str"])
                else:
                    data = checkpoint_data["data"]
                checkpoint = self.serde.loads_typed((checkpoint_data["type"], data))

                # Ensure 'step' is always present in metadata
                metadata = {"step": -1}  # Default step value
                if row.checkpoint_metadata:
                    saved_metadata = json.loads(row.checkpoint_metadata)
                    metadata.update(saved_metadata)

                writes = self._get_writes(db, thread_id, row.checkpoint_id)

                checkpoint_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": row.checkpoint_id,
                    }
                }

                parent_config = None
                if row.parent_checkpoint_id:
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": row.parent_checkpoint_id,
                        }
                    }

                yield CheckpointTuple(
                    config=checkpoint_config,
                    checkpoint=checkpoint,
                    metadata=CheckpointMetadata(**metadata) if metadata else CheckpointMetadata(),
                    parent_config=parent_config,
                    pending_writes=writes,
                )

        except Exception as e:
            logger.error("Error listing checkpoints", error=str(e), thread_id=thread_id)
        finally:
            db.close()

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Save a checkpoint to the database.

        Args:
            config: Configuration with thread_id
            checkpoint: The checkpoint to save
            metadata: Checkpoint metadata
            new_versions: Optional new channel versions

        Returns:
            Updated config with new checkpoint_id
        """
        thread_id = config["configurable"]["thread_id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_id = str(uuid.uuid4())

        db = self._get_db()
        try:
            # Serialize checkpoint
            type_name, data = self.serde.dumps_typed(checkpoint)
            # Handle bytes data by encoding to base64
            data_serialized = _serialize_data(data)
            checkpoint_data = json.dumps({"type": type_name, "data_str": data_serialized})

            # Serialize metadata
            metadata_json = json.dumps(metadata.__dict__ if hasattr(metadata, '__dict__') else {})

            # Create checkpoint record
            checkpoint_row = GraphCheckpoint(
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                parent_checkpoint_id=parent_checkpoint_id,
                checkpoint_data=checkpoint_data,
                checkpoint_metadata=metadata_json,
            )

            db.add(checkpoint_row)
            db.commit()

            logger.debug(
                "Checkpoint saved",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
            )

            # Update session recovery info
            self._update_session_recovery(db, thread_id, checkpoint_id)

            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                }
            }

        except Exception as e:
            db.rollback()
            logger.error("Error saving checkpoint", error=str(e), thread_id=thread_id)
            raise
        finally:
            db.close()

    def put_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """
        Save pending writes for a checkpoint.

        Args:
            config: Configuration with thread_id and checkpoint_id
            writes: List of (channel, value) tuples
            task_id: The task that created these writes
        """
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id", "")

        db = self._get_db()
        try:
            for channel, value in writes:
                # Serialize value
                if value is not None:
                    type_name, data = self.serde.dumps_typed(value)
                    data_serialized = _serialize_data(data)
                    value_json = json.dumps({"type": type_name, "data_str": data_serialized})
                else:
                    value_json = None

                write_row = GraphWrite(
                    thread_id=thread_id,
                    checkpoint_id=checkpoint_id,
                    task_id=task_id,
                    channel=channel,
                    write_type="put",
                    value=value_json,
                )
                db.add(write_row)

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error("Error saving writes", error=str(e), thread_id=thread_id)
            raise
        finally:
            db.close()

    def _update_session_recovery(
        self, db: Session, thread_id: str, checkpoint_id: str
    ) -> None:
        """Update session recovery tracking."""
        try:
            # Find or create session recovery record
            # Extract session_id from thread_id (they may be the same or related)
            session_id = f"chat-{thread_id}"

            recovery = (
                db.query(SessionRecovery)
                .filter(SessionRecovery.session_id == session_id)
                .first()
            )

            if recovery:
                recovery.last_checkpoint_id = checkpoint_id
                recovery.last_activity_at = datetime.utcnow()
            else:
                recovery = SessionRecovery(
                    session_id=session_id,
                    thread_id=thread_id,
                    last_checkpoint_id=checkpoint_id,
                    status="active",
                )
                db.add(recovery)

            db.commit()

        except Exception as e:
            logger.warning("Could not update session recovery", error=str(e))


def get_database_checkpointer() -> DatabaseCheckpointer:
    """Get a configured database checkpointer instance."""
    return DatabaseCheckpointer()


def cleanup_old_checkpoints(thread_id: str, keep_count: int = 10) -> int:
    """
    Clean up old checkpoints for a thread, keeping only the most recent.

    Args:
        thread_id: The thread to clean up
        keep_count: Number of recent checkpoints to keep

    Returns:
        Number of checkpoints deleted
    """
    db = SessionLocal()
    try:
        # Get checkpoint IDs to keep
        keep_ids = (
            db.query(GraphCheckpoint.checkpoint_id)
            .filter(GraphCheckpoint.thread_id == thread_id)
            .order_by(GraphCheckpoint.created_at.desc())
            .limit(keep_count)
            .all()
        )
        keep_ids = [r[0] for r in keep_ids]

        if not keep_ids:
            return 0

        # Delete old checkpoints
        deleted = (
            db.query(GraphCheckpoint)
            .filter(
                GraphCheckpoint.thread_id == thread_id,
                ~GraphCheckpoint.checkpoint_id.in_(keep_ids),
            )
            .delete(synchronize_session=False)
        )

        # Delete associated writes
        db.query(GraphWrite).filter(
            GraphWrite.thread_id == thread_id,
            ~GraphWrite.checkpoint_id.in_(keep_ids),
        ).delete(synchronize_session=False)

        db.commit()
        logger.info(
            "Cleaned up old checkpoints",
            thread_id=thread_id,
            deleted=deleted,
        )
        return deleted

    except Exception as e:
        db.rollback()
        logger.error("Error cleaning up checkpoints", error=str(e))
        return 0
    finally:
        db.close()
