# API Compatibility Layer Design

## Overview

The API compatibility layer ensures that the Rust implementation can seamlessly replace the Python implementation without requiring any code changes from users. This is achieved through:

1. **Exact API Matching**: All public methods and properties must match the Python API exactly
2. **Error Compatibility**: Error types and messages must be identical
3. **Serialization Compatibility**: Data structures must serialize identically
4. **Behavioral Compatibility**: All edge cases and behaviors must be preserved

## Design Principles

### 1. PyO3 Bindings Strategy

We'll use PyO3 to create Python classes that wrap Rust implementations:

```rust
use pyo3::prelude::*;

#[pyclass]
struct BaseChannel {
    // Rust implementation
    inner: channels::BaseChannelImpl,
}

#[pymethods]
impl BaseChannel {
    // Python-compatible methods
}
```

### 2. Trait-Based Implementation

Rust traits will implement the core logic, with PyO3 wrappers providing the Python interface:

```rust
// Rust trait (core logic)
pub trait Channel<T, U> {
    fn get(&self) -> Result<&T, LangGraphError>;
    fn update(&mut self, values: Vec<U>) -> Result<bool, LangGraphError>;
    // ... other methods
}

// PyO3 wrapper (Python interface)
#[pyclass]
struct PyBaseChannel {
    inner: Box<dyn Channel<PyObject, PyObject>>,
}
```

## Channel API Compatibility

### BaseChannel

**Python API:**
```python
class BaseChannel(Generic[Value, Update, Checkpoint], ABC):
    def __init__(self, typ: Any, key: str = "") -> None:
        self.typ = typ
        self.key = key
    
    @property
    @abstractmethod
    def ValueType(self) -> Any:
        """The type of the value stored in the channel."""
    
    @property
    @abstractmethod
    def UpdateType(self) -> Any:
        """The type of the update received by the channel."""
    
    def copy(self) -> Self:
        """Return a copy of the channel."""
    
    def checkpoint(self) -> Checkpoint | Any:
        """Return a serializable representation of the channel's current state."""
    
    @abstractmethod
    def from_checkpoint(self, checkpoint: Checkpoint | Any) -> Self:
        """Return a new identical channel, optionally initialized from a checkpoint."""
    
    @abstractmethod
    def get(self) -> Value:
        """Return the current value of the channel."""
    
    def is_available(self) -> bool:
        """Return True if the channel is available (not empty), False otherwise."""
    
    @abstractmethod
    def update(self, values: Sequence[Update]) -> bool:
        """Update the channel's value with the given sequence of updates."""
    
    def consume(self) -> bool:
        """Notify the channel that a subscribed task ran."""
    
    def finish(self) -> bool:
        """Notify the channel that the Pregel run is finishing."""
```

**Rust Implementation:**
```rust
#[pyclass]
pub struct BaseChannel {
    #[pyo3(get, set)]
    pub typ: PyObject,
    #[pyo3(get, set)]
    pub key: String,
    inner: Box<dyn ChannelTrait>,
}

#[pymethods]
impl BaseChannel {
    #[new]
    fn new(typ: PyObject, key: Option<String>) -> PyResult<Self> {
        // Implementation
    }
    
    #[getter]
    fn value_type(&self, py: Python) -> PyResult<PyObject> {
        // Return Python-compatible type
    }
    
    #[getter]
    fn update_type(&self, py: Python) -> PyResult<PyObject> {
        // Return Python-compatible type
    }
    
    fn copy(&self, py: Python) -> PyResult<Py<Self>> {
        // Return copy
    }
    
    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        // Return checkpoint
    }
    
    #[classmethod]
    fn from_checkpoint(cls, py: Python, checkpoint: PyObject) -> PyResult<Py<Self>> {
        // Create from checkpoint
    }
    
    fn get(&self, py: Python) -> PyResult<PyObject> {
        // Get value
    }
    
    fn is_available(&self) -> bool {
        // Check availability
    }
    
    fn update(&mut self, py: Python, values: &PyList) -> PyResult<bool> {
        // Update with values
    }
    
    fn consume(&mut self) -> bool {
        // Consume
    }
    
    fn finish(&mut self) -> bool {
        // Finish
    }
}
```

## Checkpoint API Compatibility

### Checkpoint Data Structure

**Python:**
```python
class Checkpoint(TypedDict):
    v: int
    id: str
    ts: str
    channel_values: dict[str, Any]
    channel_versions: ChannelVersions
    versions_seen: dict[str, ChannelVersions]
    updated_channels: list[str] | None
```

**Rust:**
```rust
#[pyclass(dict)]
#[derive(Debug, Clone)]
pub struct Checkpoint {
    #[pyo3(get, set)]
    pub v: i32,
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub ts: String,
    #[pyo3(get, set)]
    pub channel_values: HashMap<String, PyObject>,
    #[pyo3(get, set)]
    pub channel_versions: HashMap<String, PyObject>,
    #[pyo3(get, set)]
    pub versions_seen: HashMap<String, HashMap<String, PyObject>>,
    #[pyo3(get, set)]
    pub updated_channels: Option<Vec<String>>,
}

#[pymethods]
impl Checkpoint {
    #[new]
    fn new() -> Self {
        // Create new checkpoint
    }
    
    fn to_json(&self, py: Python) -> PyResult<String> {
        // Serialize to JSON
    }
    
    #[classmethod]
    fn from_json(cls, py: Python, json: &str) -> PyResult<Py<Self>> {
        // Deserialize from JSON
    }
}
```

## Pregel API Compatibility

### Core Pregel Class

**Python Constructor:**
```python
def __init__(
    self,
    *,
    nodes: dict[str, PregelNode | NodeBuilder],
    channels: dict[str, BaseChannel | ManagedValueSpec] | None,
    auto_validate: bool = True,
    stream_mode: StreamMode = "values",
    stream_eager: bool = False,
    output_channels: str | Sequence[str],
    stream_channels: str | Sequence[str] | None = None,
    interrupt_after_nodes: All | Sequence[str] = (),
    interrupt_before_nodes: All | Sequence[str] = (),
    input_channels: str | Sequence[str],
    step_timeout: float | None = None,
    debug: bool | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
    cache: BaseCache | None = None,
    retry_policy: RetryPolicy | Sequence[RetryPolicy] = (),
    cache_policy: CachePolicy | None = None,
    context_schema: type[ContextT] | None = None,
    config: RunnableConfig | None = None,
    trigger_to_nodes: Mapping[str, Sequence[str]] | None = None,
    name: str = "LangGraph",
    **deprecated_kwargs: Unpack[DeprecatedKwargs],
) -> None:
```

**Rust Implementation:**
```rust
#[pyclass]
pub struct Pregel {
    // All the Python-compatible fields
}

#[pymethods]
impl Pregel {
    #[new]
    #[pyo3(signature = (
        *,
        nodes,
        channels=None,
        auto_validate=true,
        stream_mode="values",
        stream_eager=false,
        output_channels,
        stream_channels=None,
        interrupt_after_nodes=(),
        interrupt_before_nodes=(),
        input_channels,
        step_timeout=None,
        debug=None,
        checkpointer=None,
        store=None,
        cache=None,
        retry_policy=(),
        cache_policy=None,
        context_schema=None,
        config=None,
        trigger_to_nodes=None,
        name="LangGraph",
    ))]
    fn new(
        py: Python,
        nodes: PyObject,
        channels: Option<PyObject>,
        auto_validate: bool,
        stream_mode: &str,
        stream_eager: bool,
        output_channels: PyObject,
        stream_channels: Option<PyObject>,
        interrupt_after_nodes: PyObject,
        interrupt_before_nodes: PyObject,
        input_channels: PyObject,
        step_timeout: Option<f64>,
        debug: Option<bool>,
        checkpointer: Option<PyObject>,
        store: Option<PyObject>,
        cache: Option<PyObject>,
        retry_policy: PyObject,
        cache_policy: Option<PyObject>,
        context_schema: Option<PyObject>,
        config: Option<PyObject>,
        trigger_to_nodes: Option<PyObject>,
        name: &str,
    ) -> PyResult<Self> {
        // Implementation that matches Python constructor exactly
    }
    
    // All required methods with exact Python signatures
}
```

## Error Handling Compatibility

### Error Types Mapping

**Python Errors:**
- `EmptyChannelError`
- `InvalidUpdateError`
- `GraphRecursionError`
- etc.

**Rust Implementation:**
```rust
#[derive(Debug, thiserror::Error)]
pub enum LangGraphError {
    #[error("Channel is empty")]
    EmptyChannelError,
    
    #[error("Invalid update: {0}")]
    InvalidUpdateError(String),
    
    #[error("Graph recursion limit reached")]
    GraphRecursionError,
    
    // Map to Python exceptions when converted
}

impl From<LangGraphError> for PyErr {
    fn from(err: LangGraphError) -> PyErr {
        match err {
            LangGraphError::EmptyChannelError => {
                // Create Python EmptyChannelError
            }
            LangGraphError::InvalidUpdateError(msg) => {
                // Create Python InvalidUpdateError
            }
            // ... other mappings
        }
    }
}
```

## Serialization Compatibility

### JSON Serialization

**Requirements:**
1. Exact field names and types
2. Same timestamp format (ISO 8601)
3. Same UUID format
4. Same data structure nesting

**Implementation:**
```rust
use serde::{Deserialize, Serialize};
use serde_json::Value;

impl Checkpoint {
    pub fn to_json(&self) -> Result<String, LangGraphError> {
        // Serialize with exact Python-compatible format
        serde_json::to_string(self)
    }
    
    pub fn from_json(json: &str) -> Result<Self, LangGraphError> {
        // Deserialize with exact Python-compatible format
        serde_json::from_str(json)
    }
}
```

## Monkeypatching Support

### Shim Module Design

**Current Implementation:**
```python
def patch_langgraph() -> bool:
    try:
        import langgraph.pregel
        langgraph.pregel.Pregel = RustPregel
        # ... other patches
        return True
    except ImportError:
        return False
```

**Enhanced Implementation:**
```python
def patch_langgraph() -> bool:
    """Monkeypatch langgraph with Rust implementations."""
    try:
        # Import all required modules
        import langgraph.pregel
        import langgraph.channels
        import langgraph.checkpoint
        
        # Store original classes for unpatching
        _store_original_classes()
        
        # Patch with Rust implementations
        langgraph.pregel.Pregel = RustPregel
        langgraph.channels.BaseChannel = RustBaseChannel
        langgraph.channels.LastValue = RustLastValue
        langgraph.checkpoint.Checkpoint = RustCheckpoint
        langgraph.checkpoint.BaseCheckpointSaver = RustBaseCheckpointSaver
        langgraph.checkpoint.MemorySaver = RustMemorySaver
        
        return True
    except ImportError as e:
        print(f"Failed to patch langgraph: {e}")
        return False

def unpatch_langgraph() -> bool:
    """Restore original langgraph classes."""
    try:
        # Restore all original classes
        _restore_original_classes()
        return True
    except Exception as e:
        print(f"Failed to unpatch langgraph: {e}")
        return False
```

## Testing Strategy

### Compatibility Tests

**1. API Signature Tests:**
```python
def test_api_signatures():
    """Verify all method signatures match Python exactly."""
    import inspect
    import langgraph.pregel
    
    # Compare method signatures
    py_methods = inspect.getmembers(langgraph.pregel.Pregel, inspect.isfunction)
    rust_methods = inspect.getmembers(RustPregel, inspect.isfunction)
    
    for name, py_method in py_methods:
        assert name in dict(rust_methods)
        # Compare signatures
```

**2. Behavior Tests:**
```python
def test_behavior_compatibility():
    """Verify identical behavior between Python and Rust implementations."""
    # Test with identical inputs
    py_result = python_implementation.invoke(input_data)
    rust_result = rust_implementation.invoke(input_data)
    
    assert py_result == rust_result
```

**3. Error Tests:**
```python
def test_error_compatibility():
    """Verify identical error handling."""
    try:
        python_implementation.invalid_operation()
    except PythonError as e:
        py_error = e
    
    try:
        rust_implementation.invalid_operation()
    except PythonError as e:
        rust_error = e
    
    assert type(py_error) == type(rust_error)
    assert str(py_error) == str(rust_error)
```

## Performance Considerations

### Memory Layout

**Optimize for:**
1. Minimal Python object overhead
2. Efficient conversion between Python and Rust types
3. Proper reference counting
4. Avoid unnecessary copying

### Concurrency

**Design for:**
1. GIL release when possible
2. Async compatibility
3. Thread safety
4. Efficient locking strategies

## Implementation Roadmap

### Phase 1: Basic Compatibility Layer
1. BaseChannel implementation
2. Checkpoint data structure
3. Basic Pregel skeleton
4. Error mapping

### Phase 2: Core Functionality
1. LastValue channel
2. MemorySaver
3. Core Pregel methods
4. Serialization compatibility

### Phase 3: Full Compatibility
1. All channel types
2. All Pregel methods
3. Complete error compatibility
4. Monkeypatching enhancements

### Phase 4: Optimization
1. Performance profiling
2. Memory optimization
3. Concurrency improvements
4. Benchmark validation