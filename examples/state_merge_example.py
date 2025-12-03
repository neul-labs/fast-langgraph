"""
Example usage of fast state merge operations.

This demonstrates how to use the Rust-based state merging functions
for high-performance state updates in LangGraph applications.
"""

from fast_langgraph import (
    merge_dicts,
    deep_merge_dicts,
    merge_many_dicts,
    update_dict_inplace,
    merge_lists,
    apply_writes_batch,
    states_equal,
    get_state_diff,
    langgraph_state_update,
)


def example_basic_merge():
    """Basic dictionary merging."""
    print("=" * 60)
    print("Basic Dictionary Merge")
    print("=" * 60)

    base = {"name": "Alice", "age": 30, "city": "NYC"}
    updates = {"age": 31, "country": "USA"}

    result = merge_dicts(base, updates)
    print(f"Base: {base}")
    print(f"Updates: {updates}")
    print(f"Result: {result}")
    print()


def example_deep_merge():
    """Deep merging of nested dictionaries."""
    print("=" * 60)
    print("Deep Dictionary Merge (Nested Structures)")
    print("=" * 60)

    base = {
        "user": {
            "name": "Alice",
            "settings": {"theme": "dark", "notifications": True}
        },
        "metadata": {"version": 1}
    }

    updates = {
        "user": {
            "settings": {"theme": "light"}  # Only update theme
        },
        "metadata": {"last_updated": "2024-01-01"}
    }

    result = deep_merge_dicts(base, updates)
    print(f"Base: {base}")
    print(f"Updates: {updates}")
    print(f"Result: {result}")
    print("Note: settings.notifications is preserved!")
    print()


def example_merge_many():
    """Merging multiple dictionaries at once."""
    print("=" * 60)
    print("Merge Many Dictionaries")
    print("=" * 60)

    dicts = [
        {"a": 1, "b": 2},
        {"b": 3, "c": 4},
        {"c": 5, "d": 6},
    ]

    result = merge_many_dicts(dicts)
    print(f"Input dicts: {dicts}")
    print(f"Result: {result}")
    print("Note: Later values override earlier ones")
    print()


def example_inplace_update():
    """In-place dictionary updates for maximum performance."""
    print("=" * 60)
    print("In-Place Update (Zero-Copy)")
    print("=" * 60)

    state = {"count": 0, "items": [1, 2, 3]}
    updates = {"count": 5, "status": "active"}

    print(f"Before: {state}")
    update_dict_inplace(state, updates)
    print(f"After: {state}")
    print("Note: Original dict is modified in-place")
    print()


def example_list_merge():
    """Merging lists (concatenation)."""
    print("=" * 60)
    print("List Merge Operations")
    print("=" * 60)

    list1 = [1, 2, 3]
    list2 = [4, 5, 6]

    # Concatenation
    result = merge_lists(list1, list2)
    print(f"List 1: {list1}")
    print(f"List 2: {list2}")
    print(f"Merged: {result}")
    print("Note: Lists are concatenated")
    print()


def example_batch_writes():
    """Applying multiple writes in a batch."""
    print("=" * 60)
    print("Batch Write Operations")
    print("=" * 60)

    state = {"a": 1, "b": 2}
    writes = [
        ("a", 10),
        ("c", 30),
        ("d", 40),
    ]

    result = apply_writes_batch(state, writes)
    print(f"Initial state: {state}")
    print(f"Writes: {writes}")
    print(f"Result: {result}")
    print()


def example_state_equality():
    """Checking state equality."""
    print("=" * 60)
    print("State Equality Check")
    print("=" * 60)

    state1 = {"name": "Alice", "age": 30}
    state2 = {"name": "Alice", "age": 30}
    state3 = {"name": "Alice", "age": 31}

    print(f"State 1: {state1}")
    print(f"State 2: {state2}")
    print(f"State 3: {state3}")
    print(f"State 1 == State 2: {states_equal(state1, state2)}")
    print(f"State 1 == State 3: {states_equal(state1, state3)}")
    print()


def example_state_diff():
    """Computing differences between states."""
    print("=" * 60)
    print("State Difference Computation")
    print("=" * 60)

    old_state = {"name": "Alice", "age": 30, "city": "NYC"}
    new_state = {"name": "Alice", "age": 31, "city": "SF", "country": "USA"}

    diff = get_state_diff(old_state, new_state)
    print(f"Old state: {old_state}")
    print(f"New state: {new_state}")
    print(f"Diff: {diff}")
    print()


def example_langgraph_state_update():
    """LangGraph-specific state updates with append mode."""
    print("=" * 60)
    print("LangGraph State Update (with message append)")
    print("=" * 60)

    # Typical LangGraph state with message history
    state = {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "step_count": 1,
        "context": {"user_id": "123"}
    }

    # New messages and updates
    updates = {
        "messages": [
            {"role": "user", "content": "How are you?"}
        ],
        "step_count": 2,
    }

    # Use append mode for messages
    result = langgraph_state_update(state, updates, append_keys=["messages"])

    print(f"Original messages: {state['messages']}")
    print(f"New messages: {updates['messages']}")
    print(f"Result messages: {result['messages']}")
    print(f"Step count updated: {result['step_count']}")
    print("Note: Messages are appended, not replaced!")
    print()


def example_performance_comparison():
    """Demonstrate performance benefits."""
    print("=" * 60)
    print("Performance Comparison")
    print("=" * 60)

    import time

    # Large state for testing
    large_state = {f"key_{i}": i for i in range(1000)}
    updates = {f"key_{i}": i + 1000 for i in range(500, 1000)}

    # Rust merge
    start = time.perf_counter()
    for _ in range(1000):
        result = merge_dicts(large_state, updates)
    rust_time = time.perf_counter() - start

    # Python merge
    start = time.perf_counter()
    for _ in range(1000):
        result = {**large_state, **updates}
    python_time = time.perf_counter() - start

    print(f"Rust merge: {rust_time*1000:.2f} ms")
    print(f"Python merge: {python_time*1000:.2f} ms")
    print(f"Speedup: {python_time/rust_time:.2f}x")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Fast LangGraph State Merge Examples")
    print("=" * 60 + "\n")

    example_basic_merge()
    example_deep_merge()
    example_merge_many()
    example_inplace_update()
    example_list_merge()
    example_batch_writes()
    example_state_equality()
    example_state_diff()
    example_langgraph_state_update()
    example_performance_comparison()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
