"""
Test SQLite Checkpointer functionality
"""

import os
import tempfile

import pytest

from fast_langgraph import RustSQLiteCheckpointer


def test_sqlite_checkpointer_basic():
    """Test basic SQLite checkpoint operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Create checkpointer with no compression
        cp = RustSQLiteCheckpointer(db_path)

        # Create test checkpoint data
        checkpoint = {
            "channel_values": {
                "messages": ["hello", "world"],
                "counter": 42,
            },
            "channel_versions": {
                "messages": 1,
                "counter": 1,
            },
            "versions_seen": {
                "task1": {"messages": 1, "counter": 0},
            },
            "step": 1,
        }

        # Save checkpoint
        result = cp.put("thread1", "checkpoint1", checkpoint)
        assert result is True

        # Load checkpoint
        loaded = cp.get("thread1", "checkpoint1")
        assert loaded is not None
        assert loaded["step"] == 1
        assert loaded["channel_values"]["counter"] == 42

        # List checkpoints
        checkpoints = cp.list_checkpoints("thread1")
        assert len(checkpoints) == 1
        assert "checkpoint1" in checkpoints

        # Get stats
        stats = cp.stats()
        assert stats["total_threads"] == 1
        assert stats["total_checkpoints"] == 1
        assert stats["total_bytes"] > 0


def test_sqlite_checkpointer_compression_zstd():
    """Test SQLite checkpoint with zstd compression."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_zstd.db")

        # Create checkpointer with zstd compression
        cp = RustSQLiteCheckpointer(db_path, compression="zstd")

        # Create test checkpoint with larger data
        checkpoint = {
            "channel_values": {
                "messages": ["message_" + str(i) for i in range(100)],
                "counter": 42,
            },
            "channel_versions": {
                "messages": 1,
                "counter": 1,
            },
            "versions_seen": {},
            "step": 1,
        }

        # Save and load
        cp.put("thread1", "checkpoint1", checkpoint)
        loaded = cp.get("thread1", "checkpoint1")

        assert loaded is not None
        assert len(loaded["channel_values"]["messages"]) == 100
        assert loaded["channel_values"]["counter"] == 42


@pytest.mark.skip(reason="lz4 compression feature not enabled by default")
def test_sqlite_checkpointer_compression_lz4():
    """Test SQLite checkpoint with lz4 compression."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_lz4.db")

        # Create checkpointer with lz4 compression
        cp = RustSQLiteCheckpointer(db_path, compression="lz4")

        checkpoint = {
            "channel_values": {
                "data": "x" * 1000,
            },
            "channel_versions": {
                "data": 1,
            },
            "versions_seen": {},
            "step": 1,
        }

        cp.put("thread1", "checkpoint1", checkpoint)
        loaded = cp.get("thread1", "checkpoint1")

        assert loaded is not None
        assert loaded["channel_values"]["data"] == "x" * 1000


def test_sqlite_checkpointer_multiple_threads():
    """Test multiple threads and checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_multi.db")
        cp = RustSQLiteCheckpointer(db_path)

        # Create checkpoints for multiple threads
        for thread_idx in range(3):
            thread_id = f"thread{thread_idx}"
            for checkpoint_idx in range(5):
                checkpoint_id = f"checkpoint{checkpoint_idx}"
                checkpoint = {
                    "channel_values": {"idx": thread_idx * 10 + checkpoint_idx},
                    "channel_versions": {"idx": 1},
                    "versions_seen": {},
                    "step": checkpoint_idx,
                }
                cp.put(thread_id, checkpoint_id, checkpoint)

        # Verify
        stats = cp.stats()
        assert stats["total_threads"] == 3
        assert stats["total_checkpoints"] == 15

        # List checkpoints for one thread
        checkpoints = cp.list_checkpoints("thread1")
        assert len(checkpoints) == 5


def test_sqlite_checkpointer_delete():
    """Test deleting checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_delete.db")
        cp = RustSQLiteCheckpointer(db_path)

        checkpoint = {
            "channel_values": {},
            "channel_versions": {},
            "versions_seen": {},
            "step": 1,
        }

        # Create and delete
        cp.put("thread1", "checkpoint1", checkpoint)
        cp.put("thread1", "checkpoint2", checkpoint)

        assert len(cp.list_checkpoints("thread1")) == 2

        # Delete one
        result = cp.delete("thread1", "checkpoint1")
        assert result is True
        assert len(cp.list_checkpoints("thread1")) == 1

        # Clear thread
        result = cp.clear_thread("thread1")
        assert result is True
        assert len(cp.list_checkpoints("thread1")) == 0


def test_sqlite_checkpointer_nonexistent():
    """Test loading non-existent checkpoint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_nonexist.db")
        cp = RustSQLiteCheckpointer(db_path)

        # Try to load non-existent checkpoint
        loaded = cp.get("thread1", "checkpoint1")
        assert loaded is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
