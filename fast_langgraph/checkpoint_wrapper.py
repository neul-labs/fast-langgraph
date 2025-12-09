"""
LangGraph-compatible wrapper for RustCheckpointer.

This module provides a Python wrapper that makes RustCheckpointer compatible
with LangGraph's BaseCheckpointSaver interface.
"""

from collections.abc import Iterator
from typing import Any, Dict, Optional

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
)


class RustCheckpointSaver(BaseCheckpointSaver):
    """
    LangGraph-compatible checkpoint saver using RustCheckpointer.

    This wrapper implements the BaseCheckpointSaver interface while using
    the high-performance RustCheckpointer backend for storage.
    """

    def __init__(self):
        """Initialize the RustCheckpointSaver."""
        try:
            from .fast_langgraph import RustCheckpointer

            self._rust_checkpointer = RustCheckpointer()
        except ImportError as e:
            raise ImportError(
                "RustCheckpointer not available. "
                "Build the Rust extension with: uv run maturin develop --release"
            ) from e

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> None:
        """
        Save a checkpoint.

        Args:
            config: Configuration dict with thread_id
            checkpoint: Checkpoint object to save
            metadata: Checkpoint metadata
        """
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = checkpoint.get("ts", "latest")

        # Convert checkpoint to dict format expected by RustCheckpointer
        checkpoint_dict = {
            "channel_values": checkpoint.get("channel_values", {}),
            "channel_versions": checkpoint.get("channel_versions", {}),
            "versions_seen": checkpoint.get("versions_seen", {}),
            "step": checkpoint.get("step", 0),
        }

        self._rust_checkpointer.put(thread_id, str(checkpoint_id), checkpoint_dict)

    def get(
        self,
        config: Dict[str, Any],
    ) -> Optional[Checkpoint]:
        """
        Load the latest checkpoint for a thread.

        Args:
            config: Configuration dict with thread_id

        Returns:
            Checkpoint object or None if not found
        """
        thread_id = config.get("configurable", {}).get("thread_id", "default")

        # Get list of checkpoints and return the latest one
        checkpoint_ids = self._rust_checkpointer.list_checkpoints(thread_id)
        if not checkpoint_ids:
            return None

        # For now, just get the first checkpoint
        # In a full implementation, we'd sort by timestamp
        checkpoint_id = checkpoint_ids[0]

        checkpoint_data = self._rust_checkpointer.get(thread_id, checkpoint_id)
        if not checkpoint_data:
            return None

        # Convert back to Checkpoint format
        return {
            "channel_values": checkpoint_data.get("channel_values", {}),
            "channel_versions": checkpoint_data.get("channel_versions", {}),
            "versions_seen": checkpoint_data.get("versions_seen", {}),
            "step": checkpoint_data.get("step", 0),
            "ts": checkpoint_id,
        }

    def get_tuple(self, config: Dict[str, Any]) -> Optional[tuple]:
        """
        Get checkpoint tuple (config, checkpoint, metadata).

        Args:
            config: Configuration dict with thread_id

        Returns:
            Tuple of (config, checkpoint, metadata) or None
        """
        checkpoint = self.get(config)
        if not checkpoint:
            return None

        thread_id = config.get("configurable", {}).get("thread_id", "default")
        metadata = {"thread_id": thread_id, "checkpoint_id": checkpoint.get("ts")}

        return (config, checkpoint, metadata)

    def list(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> Iterator[tuple[Dict[str, Any], Checkpoint, CheckpointMetadata]]:
        """
        List checkpoints for a thread.

        Args:
            config: Configuration dict with thread_id
            limit: Maximum number of checkpoints to return

        Yields:
            Tuples of (config, checkpoint, metadata)
        """
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_ids = self._rust_checkpointer.list_checkpoints(thread_id)

        if limit:
            checkpoint_ids = checkpoint_ids[:limit]

        for checkpoint_id in checkpoint_ids:
            checkpoint_data = self._rust_checkpointer.get(thread_id, checkpoint_id)
            if checkpoint_data:
                checkpoint = {
                    "channel_values": checkpoint_data.get("channel_values", {}),
                    "channel_versions": checkpoint_data.get("channel_versions", {}),
                    "versions_seen": checkpoint_data.get("versions_seen", {}),
                    "step": checkpoint_data.get("step", 0),
                    "ts": checkpoint_id,
                }

                metadata = {"thread_id": thread_id, "checkpoint_id": checkpoint_id}

                yield (config, checkpoint, metadata)

    def put_writes(self, config: Dict[str, Any], writes: list, task_id: str) -> None:
        """
        Store intermediate writes.

        This method is called during graph execution to save pending writes.
        For the in-memory implementation, we skip this for now.

        Args:
            config: Configuration dict with thread_id
            writes: List of writes to store
            task_id: ID of the task making the writes
        """
        # For in-memory checkpointer, we don't need to persist intermediate writes
        # They will be included in the final checkpoint via `put()`
        pass
