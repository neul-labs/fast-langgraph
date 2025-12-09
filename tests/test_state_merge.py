"""
Tests for Rust-based state merge operations.

These tests validate the performance and correctness of state merging functions
that optimize LangGraph's hot-path operations.
"""

import pytest

from fast_langgraph import (
    apply_writes_batch,
    deep_merge_dicts,
    get_state_diff,
    langgraph_state_update,
    merge_dicts,
    merge_lists,
    merge_many_dicts,
    states_equal,
    update_dict_inplace,
)


def test_merge_dicts_basic():
    """Test basic dictionary merging."""
    base = {"a": 1, "b": 2}
    updates = {"b": 3, "c": 4}

    result = merge_dicts(base, updates)

    assert result == {"a": 1, "b": 3, "c": 4}
    # Original dicts unchanged
    assert base == {"a": 1, "b": 2}
    assert updates == {"b": 3, "c": 4}


def test_merge_dicts_empty():
    """Test merging with empty dictionaries."""
    base = {"a": 1}
    updates = {}

    result = merge_dicts(base, updates)
    assert result == {"a": 1}

    result = merge_dicts({}, {"b": 2})
    assert result == {"b": 2}


def test_deep_merge_dicts():
    """Test deep merging of nested dictionaries."""
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    updates = {"a": {"c": 3, "e": 4}, "f": 5}

    result = deep_merge_dicts(base, updates)

    assert result == {"a": {"b": 1, "c": 3, "e": 4}, "d": 3, "f": 5}


def test_deep_merge_replaces_non_dicts():
    """Test that deep merge replaces values when not both dicts."""
    base = {"a": {"b": 1}, "c": 2}
    updates = {"a": [1, 2, 3], "c": {"d": 4}}

    result = deep_merge_dicts(base, updates)

    # When value types don't match, updates win
    assert result == {"a": [1, 2, 3], "c": {"d": 4}}


def test_merge_many_dicts():
    """Test merging multiple dictionaries at once."""
    dicts = [{"a": 1}, {"b": 2}, {"c": 3}, {"a": 10}]  # Overwrites earlier "a"

    result = merge_many_dicts(dicts)

    assert result == {"a": 10, "b": 2, "c": 3}


def test_merge_many_dicts_empty():
    """Test merging empty list of dicts."""
    result = merge_many_dicts([])
    assert result == {}


def test_update_dict_inplace():
    """Test in-place dictionary update."""
    base = {"a": 1, "b": 2}
    updates = {"b": 3, "c": 4}

    update_dict_inplace(base, updates)

    # Base is mutated
    assert base == {"a": 1, "b": 3, "c": 4}


def test_merge_lists():
    """Test list merging (concatenation)."""
    base = [1, 2, 3]
    updates = [4, 5]

    result = merge_lists(base, updates)

    assert result == [1, 2, 3, 4, 5]
    # Originals unchanged
    assert base == [1, 2, 3]
    assert updates == [4, 5]


def test_merge_lists_empty():
    """Test merging with empty lists."""
    result = merge_lists([1, 2], [])
    assert result == [1, 2]

    result = merge_lists([], [3, 4])
    assert result == [3, 4]


def test_apply_writes_batch():
    """Test applying multiple writes to state."""
    state = {"count": 0, "items": []}
    writes = [{"count": 1}, {"count": 2, "name": "test"}, {"count": 3}]

    result = apply_writes_batch(state, writes)

    # Last write wins for each key
    assert result == {"count": 3, "name": "test", "items": []}


def test_states_equal_identical():
    """Test equality check for identical states."""
    state1 = {"a": 1, "b": [2, 3], "c": {"d": 4}}
    state2 = {"a": 1, "b": [2, 3], "c": {"d": 4}}

    assert states_equal(state1, state2) is True


def test_states_equal_different():
    """Test equality check for different states."""
    state1 = {"a": 1, "b": 2}
    state2 = {"a": 1, "b": 3}

    assert states_equal(state1, state2) is False


def test_states_equal_different_keys():
    """Test equality check with different keys."""
    state1 = {"a": 1, "b": 2}
    state2 = {"a": 1, "c": 2}

    assert states_equal(state1, state2) is False


def test_states_equal_different_length():
    """Test equality check with different lengths."""
    state1 = {"a": 1, "b": 2}
    state2 = {"a": 1}

    assert states_equal(state1, state2) is False


def test_get_state_diff_changes():
    """Test getting diff between states."""
    old_state = {"a": 1, "b": 2, "c": 3}
    new_state = {"a": 1, "b": 20, "d": 4}

    diff = get_state_diff(old_state, new_state)

    # Should only include changed/new keys
    assert diff == {"b": 20, "d": 4}


def test_get_state_diff_no_changes():
    """Test diff with no changes."""
    state = {"a": 1, "b": 2}
    diff = get_state_diff(state, state)

    assert diff == {}


def test_langgraph_state_update_simple():
    """Test LangGraph-specific state update without append keys."""
    state = {"count": 1, "name": "old"}
    updates = {"count": 2, "status": "active"}

    result = langgraph_state_update(state, updates, None)

    assert result == {"count": 2, "name": "old", "status": "active"}


def test_langgraph_state_update_with_append():
    """Test LangGraph state update with append mode for specific keys."""
    state = {"count": 0, "messages": [{"role": "user", "content": "hello"}]}
    updates = {"count": 1, "messages": [{"role": "assistant", "content": "hi"}]}

    # "messages" should be appended, not replaced
    result = langgraph_state_update(state, updates, append_keys=["messages"])

    assert result["count"] == 1
    assert len(result["messages"]) == 2
    assert result["messages"][0] == {"role": "user", "content": "hello"}
    assert result["messages"][1] == {"role": "assistant", "content": "hi"}


def test_langgraph_state_update_append_creates_list():
    """Test that append mode works even when key doesn't exist."""
    state = {"count": 0}
    updates = {"messages": [{"role": "user", "content": "test"}]}

    result = langgraph_state_update(state, updates, append_keys=["messages"])

    # Key didn't exist, so it gets created with the value
    assert result == {"count": 0, "messages": [{"role": "user", "content": "test"}]}


def test_langgraph_state_update_append_non_list():
    """Test append mode when value is not a list."""
    state = {"count": 0, "messages": "not a list"}
    updates = {"messages": "also not a list"}

    # Should fall back to regular update if values aren't lists
    result = langgraph_state_update(state, updates, append_keys=["messages"])

    assert result == {"count": 0, "messages": "also not a list"}


def test_merge_dicts_with_none_values():
    """Test merging with None values."""
    base = {"a": 1, "b": None}
    updates = {"b": 2, "c": None}

    result = merge_dicts(base, updates)

    assert result == {"a": 1, "b": 2, "c": None}


def test_deep_merge_complex_nesting():
    """Test deep merge with complex nested structures."""
    base = {"level1": {"level2": {"level3": {"value": 1}}, "other": 2}}
    updates = {"level1": {"level2": {"level3": {"value": 2, "new": 3}}}}

    result = deep_merge_dicts(base, updates)

    assert result == {
        "level1": {"level2": {"level3": {"value": 2, "new": 3}}, "other": 2}
    }


def test_performance_comparison():
    """Basic performance comparison with Python dict operations.

    Note: For simple dict merging, Python's built-in {**a, **b} is highly
    optimized and may be faster. The Rust functions provide value for:
    1. Deep merging (which Python doesn't have built-in)
    2. Complex operations like langgraph_state_update with append mode
    3. Batch operations like apply_writes_batch
    4. Consistency and type safety
    """
    import time

    # Create test data
    base = {f"key_{i}": i for i in range(1000)}
    updates = {f"key_{i}": i * 2 for i in range(500, 1500)}

    # Test Rust merge_dicts
    start = time.perf_counter()
    for _ in range(100):
        result = merge_dicts(base, updates)
    rust_time = time.perf_counter() - start

    # Test Python dict merge
    start = time.perf_counter()
    for _ in range(100):
        result = {**base, **updates}
    python_time = time.perf_counter() - start

    print(f"\nRust merge_dicts: {rust_time:.4f}s")
    print(f"Python dict merge: {python_time:.4f}s")
    if rust_time < python_time:
        print(f"Speedup: {python_time/rust_time:.2f}x faster")
    else:
        print(f"Slowdown: {rust_time/python_time:.2f}x slower (PyO3 overhead expected)")

    # Just verify it completes without error - performance will vary
    # Python's built-in is highly optimized, PyO3 overhead is expected
    assert rust_time < 1.0  # Should complete in reasonable time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
