# Key Classes for Rust Implementation

## Core Classes to Implement

### 1. Channel Classes

#### BaseChannel (from langgraph.channels.base)
This is the abstract base class that all channels inherit from.

**Required Properties:**
- `ValueType` - The type of the value stored in the channel
- `UpdateType` - The type of the update received by the channel
- `key` - Channel identifier

**Required Methods:**
- `copy()` - Return a copy of the channel
- `checkpoint()` - Return a serializable representation of the channel's current state
- `from_checkpoint(checkpoint)` - Return a new identical channel from a checkpoint
- `get()` - Return the current value of the channel
- `is_available()` - Return True if the channel is available
- `update(values)` - Update the channel's value with a sequence of updates
- `consume()` - Notify the channel that a subscribed task ran
- `finish()` - Notify the channel that the Pregel run is finishing

#### LastValue (from langgraph.channels.last_value)
**Required Methods:**
- Inherits all from BaseChannel
- Specific implementation for storing last value only

#### Topic (from langgraph.channels.topic)
**Required Methods:**
- Inherits all from BaseChannel
- Implementation for accumulating values over time

#### BinaryOperatorAggregate (from langgraph.channels.binop)
**Required Methods:**
- Inherits all from BaseChannel
- Implementation for applying binary operators to accumulate values

### 2. Checkpoint Classes

#### Checkpoint (from langgraph.checkpoint.base)
**Required Properties:**
- `v` - Version of the checkpoint format
- `id` - ID of the checkpoint (unique and monotonically increasing)
- `ts` - Timestamp in ISO 8601 format
- `channel_values` - Values of channels at checkpoint time
- `channel_versions` - Versions of channels at checkpoint time
- `versions_seen` - Map from node ID to channel versions seen
- `updated_channels` - Channels updated in this checkpoint

**Required Functions:**
- `copy_checkpoint` - Copy a checkpoint
- `empty_checkpoint` - Create an empty checkpoint
- `create_checkpoint` - Create a checkpoint for given channels

#### BaseCheckpointSaver (from langgraph.checkpoint.base)
**Required Methods:**
- `get(config)` - Fetch a checkpoint
- `get_tuple(config)` - Fetch a checkpoint tuple
- `list(config, filter, before, limit)` - List checkpoints
- `put(config, checkpoint, metadata, new_versions)` - Store a checkpoint
- `put_writes(config, writes, task_id, task_path)` - Store intermediate writes
- `delete_thread(thread_id)` - Delete checkpoints for a thread
- Async versions of all the above
- `get_next_version(current, channel)` - Generate next version ID

#### MemorySaver (from langgraph.checkpoint.memory)
Implementation of BaseCheckpointSaver that stores checkpoints in memory.

### 3. Pregel Classes

#### Pregel (from langgraph.pregel.main)
**Required Properties:**
- `nodes` - Dictionary of nodes
- `channels` - Dictionary of channels
- `stream_mode` - Streaming mode
- `output_channels` - Output channels
- `input_channels` - Input channels
- etc.

**Required Methods:**
- `__init__` - Constructor
- `get_graph` - Return drawable representation
- `aget_graph` - Async version
- `validate` - Validate the graph
- `get_state` - Get current state
- `aget_state` - Async version
- `get_state_history` - Get state history
- `aget_state_history` - Async version
- `update_state` - Update graph state
- `aupdate_state` - Async version
- `stream` - Stream graph steps
- `astream` - Async version
- `invoke` - Run graph with single input
- `ainvoke` - Async version

#### NodeBuilder (from langgraph.pregel.main)
**Required Methods:**
- `subscribe_only(channel)` - Subscribe to single channel
- `subscribe_to(*channels, read=True)` - Subscribe to channels
- `read_from(*channels)` - Read from channels without subscribing
- `do(node)` - Add node
- `write_to(*channels, **kwargs)` - Add channel writes
- `meta(*tags, **metadata)` - Add tags or metadata
- `build()` - Build the node

### 4. Supporting Classes

#### PregelTaskWrites
Structure for representing writes from a task.

#### PregelTask
Structure for representing a task to be executed.

#### PregelStats
Structure for tracking execution statistics.

#### PregelConfig
Configuration for Pregel execution.

## Implementation Priority

### Phase 1 (MVP)
1. BaseChannel
2. LastValue channel
3. Checkpoint data structure
4. Basic PregelExecutor

### Phase 2 (Core Functionality)
1. BaseCheckpointSaver
2. MemorySaver
3. Topic channel
4. Full Pregel implementation
5. NodeBuilder

### Phase 3 (Advanced Features)
1. BinaryOperatorAggregate channel
2. Database checkpointers
3. Subgraph support
4. Interrupt handling
5. Streaming modes

## API Compatibility Requirements

All implementations must match the Python API exactly to ensure:
1. Seamless monkeypatching
2. No code changes required for users
3. Full compatibility with existing LangGraph applications
4. Proper error handling and messaging