"""
Algorithm-level shims for LangGraph Pregel execution.

This module provides Rust-accelerated implementations of hot-path functions
in the LangGraph Pregel algorithm (_algo.py).
"""

from collections import defaultdict
from typing import Set

try:
    from fast_langgraph import ChannelManager, FastChannelUpdater

    _rust_available = True
except ImportError:
    _rust_available = False
    ChannelManager = None
    FastChannelUpdater = None


def create_accelerated_apply_writes(original_apply_writes):
    """
    Create an accelerated version of apply_writes using Rust ChannelManager.

    This is the hottest path in Pregel execution - called every superstep
    to apply all pending writes to channels.
    """
    if not _rust_available:
        return original_apply_writes

    def accelerated_apply_writes(
        checkpoint,
        channels,
        tasks,
        get_next_version,
        trigger_to_nodes,
    ) -> Set[str]:
        """
        Rust-accelerated version of apply_writes.

        Uses ChannelManager for batch write operations instead of
        iterating in Python.
        """
        from langgraph._internal._constants import (
            ERROR,
            INTERRUPT,
            NO_WRITES,
            PUSH,
            RESERVED,
            RESUME,
            RETURN,
        )
        from langgraph.pregel._call import task_path_str
        from langgraph.pregel._log import logger

        # Sort tasks (same as original)
        tasks = sorted(tasks, key=lambda t: task_path_str(t.path[:3]))
        _bump_step = any(t.triggers for t in tasks)  # noqa: F841

        # Update seen versions (same as original)
        for task in tasks:
            checkpoint["versions_seen"].setdefault(task.name, {}).update(
                {
                    chan: checkpoint["channel_versions"][chan]
                    for chan in task.triggers
                    if chan in checkpoint["channel_versions"]
                }
            )

        # Get next version (same as original)
        if get_next_version is None:
            next_version = None
        else:
            next_version = get_next_version(
                (
                    max(checkpoint["channel_versions"].values())
                    if checkpoint["channel_versions"]
                    else None
                ),
                None,
            )

        # Consume channels (same as original)
        for chan in {
            chan
            for task in tasks
            for chan in task.triggers
            if chan not in RESERVED and chan in channels
        }:
            if channels[chan].consume() and next_version is not None:
                checkpoint["channel_versions"][chan] = next_version

        # Group writes by channel (same as original)
        pending_writes_by_channel = defaultdict(list)
        for task in tasks:
            for chan, val in task.writes:
                if chan in (NO_WRITES, PUSH, RESUME, INTERRUPT, RETURN, ERROR):
                    pass
                elif chan in channels:
                    pending_writes_by_channel[chan].append(val)
                else:
                    logger.warning(
                        f"Task {task.name} with path {task.path} wrote to unknown channel {chan}, ignoring it."
                    )

        # RUST ACCELERATION STARTS HERE
        # Use Rust FastChannelUpdater for batch operations
        updated_channels = set()

        if pending_writes_by_channel:
            # Create FastChannelUpdater for this operation
            updater = FastChannelUpdater()

            # Apply writes in batch using Rust
            # This handles both RustLastValue channels (fast path) and
            # Python channels (fallback path) automatically
            updated_list = updater.apply_writes_batch(
                channels, pending_writes_by_channel
            )

            # Update channel versions for all updated channels
            if next_version is not None:
                for chan in updated_list:
                    checkpoint["channel_versions"][chan] = next_version
                    updated_channels.add(chan)
            else:
                updated_channels.update(updated_list)

        return updated_channels

    return accelerated_apply_writes


def create_accelerated_prepare_next_tasks(original_prepare_next_tasks):
    """
    Create an accelerated version of prepare_next_tasks using Rust TaskScheduler.

    This function determines which nodes should execute based on channel updates.
    """
    if not _rust_available:
        return original_prepare_next_tasks

    # For now, return original since prepare_next_tasks has complex logic
    # We'll implement this after apply_writes is working
    return original_prepare_next_tasks


def create_accelerated_read_channels(original_read_channels):
    """
    Create an accelerated version of read_channels for batch reading.

    This function reads multiple channels at once for node inputs.
    """
    if not _rust_available:
        return original_read_channels

    # For now, return original
    # We'll implement this after apply_writes is working
    return original_read_channels
