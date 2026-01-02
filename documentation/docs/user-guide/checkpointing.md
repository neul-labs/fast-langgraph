# Checkpointing

Fast-LangGraph provides a high-performance checkpointer for state persistence.

## RustSQLiteCheckpointer

A drop-in replacement for LangGraph's SQLite checkpointer with 5-6x better performance.

### Basic Usage

```python
from fast_langgraph import RustSQLiteCheckpointer
from langgraph.graph import StateGraph

# Create checkpointer
checkpointer = RustSQLiteCheckpointer("checkpoints.db")

# Build your graph
graph = StateGraph(YourState)
graph.add_node("agent", agent_node)
graph.set_entry_point("agent")
graph.set_finish_point("agent")

# Compile with checkpointing
app = graph.compile(checkpointer=checkpointer)

# Run with thread_id for state persistence
config = {"configurable": {"thread_id": "conversation-1"}}
result = app.invoke({"messages": [HumanMessage(content="Hello")]}, config)
```

### Why It's Faster

| Optimization | Benefit |
|-------------|---------|
| Rust serialization (serde) | 10-100x faster than Python json |
| Prepared statements | Eliminates SQL parsing overhead |
| Transaction batching | Reduces disk I/O |
| Efficient memory layout | Less copying |

### Performance by State Size

| State Size | Rust | Python (deepcopy) | Speedup |
|------------|------|-------------------|---------|
| 3.8 KB | 0.35 ms | 15.29 ms | **43x** |
| 35 KB | 0.29 ms | 52.00 ms | **178x** |
| 235 KB | 0.28 ms | 206.21 ms | **737x** |

Rust's advantage grows with state complexity.

## Common Patterns

### Conversation Persistence

```python
from fast_langgraph import RustSQLiteCheckpointer

checkpointer = RustSQLiteCheckpointer("conversations.db")
app = graph.compile(checkpointer=checkpointer)

def chat(user_id: str, message: str):
    """Handle a chat message with full history."""
    config = {"configurable": {"thread_id": f"user-{user_id}"}}
    result = app.invoke(
        {"messages": [HumanMessage(content=message)]},
        config
    )
    return result["messages"][-1].content
```

### Multi-User Support

Each `thread_id` maintains separate state:

```python
# User Alice's conversation
alice_config = {"configurable": {"thread_id": "alice-session-1"}}
app.invoke({"messages": [HumanMessage(content="Hello")]}, alice_config)

# User Bob's conversation (completely separate)
bob_config = {"configurable": {"thread_id": "bob-session-1"}}
app.invoke({"messages": [HumanMessage(content="Hi there")]}, bob_config)
```

### Resuming Conversations

```python
checkpointer = RustSQLiteCheckpointer("app.db")
app = graph.compile(checkpointer=checkpointer)

# First session
config = {"configurable": {"thread_id": "thread-123"}}
app.invoke({"messages": [HumanMessage(content="My name is Alice")]}, config)

# Later... resume the conversation
# The graph remembers the name
result = app.invoke(
    {"messages": [HumanMessage(content="What's my name?")]},
    config
)
# Response will reference "Alice"
```

### Time-Travel Debugging

Access historical state:

```python
from langgraph.checkpoint.base import CheckpointTuple

checkpointer = RustSQLiteCheckpointer("debug.db")
app = graph.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "debug-session"}}

# Run multiple steps
app.invoke({"messages": [HumanMessage(content="Step 1")]}, config)
app.invoke({"messages": [HumanMessage(content="Step 2")]}, config)
app.invoke({"messages": [HumanMessage(content="Step 3")]}, config)

# List all checkpoints for this thread
checkpoints = list(checkpointer.list(config))
for cp in checkpoints:
    print(f"Checkpoint: {cp.checkpoint['ts']}")
```

## Database Management

### File Location

```python
# Relative path (current directory)
checkpointer = RustSQLiteCheckpointer("checkpoints.db")

# Absolute path
checkpointer = RustSQLiteCheckpointer("/var/data/app/checkpoints.db")

# In-memory (for testing)
checkpointer = RustSQLiteCheckpointer(":memory:")
```

### Database Size

The database grows with:

- Number of threads
- State size per checkpoint
- History depth

For production, consider:

```python
import os

db_path = "checkpoints.db"
size_mb = os.path.getsize(db_path) / (1024 * 1024)
print(f"Database size: {size_mb:.2f} MB")
```

### Cleanup

Remove old checkpoints to manage size:

```python
import sqlite3

def cleanup_old_checkpoints(db_path, days=30):
    """Remove checkpoints older than N days."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM checkpoints
        WHERE created_at < datetime('now', ? || ' days')
    """, (-days,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    # Reclaim space
    conn = sqlite3.connect(db_path)
    conn.execute("VACUUM")
    conn.close()

    return deleted
```

## Comparison with LangGraph Checkpointers

| Feature | RustSQLiteCheckpointer | LangGraph SQLiteSaver |
|---------|------------------------|----------------------|
| Performance | 5-6x faster | Baseline |
| API Compatibility | Full | N/A |
| Dependencies | Included in fast-langgraph | langgraph |
| State Serialization | Rust (serde) | Python (json) |

## Migration from LangGraph

Switching is straightforward:

```python
# Before (LangGraph)
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# After (Fast-LangGraph)
from fast_langgraph import RustSQLiteCheckpointer
checkpointer = RustSQLiteCheckpointer("checkpoints.db")
```

Both use compatible SQLite schemas, so existing databases work.

## Best Practices

1. **Use meaningful thread IDs** - Include user ID, session type, etc.

```python
thread_id = f"{user_id}-{session_type}-{datetime.now().isoformat()}"
```

2. **Handle database errors gracefully**

```python
try:
    result = app.invoke(input_data, config)
except sqlite3.Error as e:
    logger.error(f"Checkpoint error: {e}")
    # Fall back to stateless execution
    result = app.invoke(input_data)
```

3. **Use in-memory for tests**

```python
# tests/test_graph.py
def test_conversation():
    checkpointer = RustSQLiteCheckpointer(":memory:")
    app = graph.compile(checkpointer=checkpointer)
    # Test without leaving files
```

4. **Monitor database size in production**

```python
# Add to monitoring
@app.on_event("startup")
def check_db_size():
    size = os.path.getsize("checkpoints.db")
    if size > 1_000_000_000:  # 1 GB
        logger.warning("Checkpoint database is large, consider cleanup")
```

## Next Steps

- [State Operations](state-operations.md) - Working with state
- [Profiling](profiling.md) - Measure checkpoint performance
