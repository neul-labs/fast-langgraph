#![allow(unused_variables)]
#![allow(clippy::too_many_arguments)]

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple, PyType};
use std::collections::HashMap;

// Import our Rust core modules
use crate::pregel_loop::{PregelConfig, PregelLoop};
use crate::pregel_node::PregelNode;

/// BaseChannel provides the base interface for all channels
#[pyclass]
pub struct BaseChannel {
    #[pyo3(get, set)]
    pub typ: PyObject,
    #[pyo3(get, set)]
    pub key: String,
}

#[pymethods]
impl BaseChannel {
    /// Create a new BaseChannel
    #[new]
    fn new(typ: PyObject, key: Option<String>) -> PyResult<Self> {
        Ok(BaseChannel {
            typ,
            key: key.unwrap_or_default(),
        })
    }

    /// Get the ValueType property
    #[getter]
    fn value_type(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual value type
        Ok(self.typ.clone_ref(py))
    }

    /// Get the UpdateType property
    #[getter]
    fn update_type(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual update type
        Ok(self.typ.clone_ref(py))
    }

    /// Return a copy of the channel
    fn copy(&self, py: Python) -> PyResult<Py<Self>> {
        Py::new(
            py,
            BaseChannel {
                typ: self.typ.clone_ref(py),
                key: self.key.clone(),
            },
        )
    }

    /// Return a serializable representation of the channel's current state
    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual checkpoint
        Ok(py.None())
    }

    /// Return a new identical channel, optionally initialized from a checkpoint
    #[classmethod]
    fn from_checkpoint(_cls: &PyType, py: Python, _checkpoint: PyObject) -> PyResult<Py<Self>> {
        // In a real implementation, this would create a channel from a checkpoint
        Py::new(
            py,
            BaseChannel {
                typ: py.None(),
                key: String::new(),
            },
        )
    }

    /// Return the current value of the channel
    fn get(&self, _py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual value
        Err(pyo3::exceptions::PyNotImplementedError::new_err(
            "get() method must be implemented by subclasses",
        ))
    }

    /// Return True if the channel is available (not empty), False otherwise
    fn is_available(&self) -> bool {
        // In a real implementation, this would check actual availability
        false
    }

    /// Update the channel's value with the given sequence of updates
    fn update(&mut self, _py: Python, _values: &PyList) -> PyResult<bool> {
        // In a real implementation, this would update with actual values
        Err(pyo3::exceptions::PyNotImplementedError::new_err(
            "update() method must be implemented by subclasses",
        ))
    }

    /// Notify the channel that a subscribed task ran
    fn consume(&mut self) -> bool {
        // In a real implementation, this would handle consumption
        false
    }

    /// Notify the channel that the Pregel run is finishing
    fn finish(&mut self) -> bool {
        // In a real implementation, this would handle finishing
        false
    }
}

/// LastValue channel stores the last value received
#[pyclass]
pub struct LastValue {
    #[pyo3(get, set)]
    pub typ: PyObject,
    #[pyo3(get, set)]
    pub key: String,
    value: Option<PyObject>,
}

#[pymethods]
impl LastValue {
    /// Create a new LastValue channel
    #[new]
    fn new(typ: PyObject, key: Option<String>) -> PyResult<Self> {
        Ok(LastValue {
            typ,
            key: key.unwrap_or_default(),
            value: None,
        })
    }

    /// Update the channel with new values
    fn update(&mut self, py: Python, values: &PyList) -> PyResult<bool> {
        if values.is_empty() {
            return Ok(false);
        }

        if values.len() != 1 {
            // Raise InvalidUpdateError from langgraph.errors
            let result = py
                .import("langgraph.errors")
                .and_then(|m| m.getattr("InvalidUpdateError"))
                .and_then(|exc_class| exc_class.call1((
                    "At key '': Can receive only one value per step. Use an Annotated key to handle multiple values.\nFor troubleshooting, visit: https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE",
                )));

            match result {
                Ok(exc) => return Err(pyo3::PyErr::from_value(exc)),
                Err(_) => {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "LastValue channel can only receive one value per update",
                    ))
                }
            }
        }

        self.value = Some(values.get_item(0)?.into());
        Ok(true)
    }

    /// Get the current value
    fn get(&self, py: Python) -> PyResult<PyObject> {
        match &self.value {
            Some(value) => Ok(value.clone_ref(py)),
            None => {
                // Raise EmptyChannelError from LangGraph
                let result = py
                    .import("langgraph.checkpoint.base")
                    .and_then(|m| m.getattr("EmptyChannelError"))
                    .and_then(|exc_class| exc_class.call0());

                match result {
                    Ok(exc) => Err(pyo3::PyErr::from_value(exc)),
                    Err(_) => {
                        // Fallback to ValueError if EmptyChannelError not available
                        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "Channel is empty",
                        ))
                    }
                }
            }
        }
    }

    /// Check if channel is available
    fn is_available(&self) -> bool {
        self.value.is_some()
    }

    /// Consume the channel (no-op for LastValue)
    fn consume(&mut self) -> bool {
        false
    }

    /// Finish the channel (no-op for LastValue)
    fn finish(&mut self) -> bool {
        false
    }

    /// Create a checkpoint
    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        match &self.value {
            Some(value) => Ok(value.clone_ref(py)),
            None => Ok(py.None()),
        }
    }

    /// Create from checkpoint
    #[allow(clippy::wrong_self_convention)]
    fn from_checkpoint(&self, py: Python, checkpoint: PyObject) -> PyResult<Py<Self>> {
        // Check if checkpoint is MISSING sentinel or None
        let is_missing = checkpoint.is_none(py) || {
            // Try to import MISSING from multiple possible locations
            let check_missing = |module_name: &str| {
                py.import(module_name)
                    .and_then(|m| m.getattr("MISSING"))
                    .map(|missing| checkpoint.is(missing))
                    .unwrap_or(false)
            };

            check_missing("langgraph._internal._typing") || check_missing("langgraph.constants")
        };

        let value = if is_missing { None } else { Some(checkpoint) };

        Py::new(
            py,
            LastValue {
                typ: self.typ.clone_ref(py),
                key: self.key.clone(),
                value,
            },
        )
    }

    /// Return a copy of the channel
    fn copy(&self, py: Python) -> PyResult<Py<Self>> {
        Py::new(
            py,
            LastValue {
                typ: self.typ.clone_ref(py),
                key: self.key.clone(),
                value: self.value.clone(),
            },
        )
    }

    /// Get the ValueType property
    #[getter]
    fn value_type(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual value type
        Ok(self.typ.clone_ref(py))
    }

    /// Get the ValueType property (capitalized for compatibility)
    #[getter]
    #[allow(non_snake_case)]
    fn ValueType(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual value type
        Ok(self.typ.clone_ref(py))
    }

    /// Get the UpdateType property
    #[getter]
    fn update_type(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual update type
        Ok(self.typ.clone_ref(py))
    }

    /// Get the UpdateType property (capitalized for compatibility)
    #[getter]
    #[allow(non_snake_case)]
    fn UpdateType(&self, py: Python) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual update type
        Ok(self.typ.clone_ref(py))
    }
}

/// Checkpoint represents a state snapshot at a given point in time
/// Must match LangGraph's Checkpoint TypedDict structure exactly
#[pyclass(dict, mapping)]
#[derive(Debug, Clone)]
pub struct Checkpoint {
    #[pyo3(get, set)]
    pub v: i32,
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub ts: String,
    #[pyo3(get, set)]
    pub channel_values: PyObject,
    #[pyo3(get, set)]
    pub channel_versions: PyObject,
    #[pyo3(get, set)]
    pub versions_seen: PyObject,
    #[pyo3(get, set)]
    pub pending_sends: PyObject,
    #[pyo3(get, set)]
    pub current_tasks: PyObject,
}

#[pymethods]
impl Checkpoint {
    /// Create a new Checkpoint
    /// Signature matches LangGraph's Checkpoint TypedDict
    #[new]
    #[pyo3(signature = (*, v=1, id=None, ts=None, channel_values=None, channel_versions=None, versions_seen=None, pending_sends=None, current_tasks=None))]
    fn new(
        py: Python,
        v: i32,
        id: Option<String>,
        ts: Option<String>,
        channel_values: Option<PyObject>,
        channel_versions: Option<PyObject>,
        versions_seen: Option<PyObject>,
        pending_sends: Option<PyObject>,
        current_tasks: Option<PyObject>,
    ) -> PyResult<Self> {
        Ok(Checkpoint {
            v,
            id: id.unwrap_or_default(),
            ts: ts.unwrap_or_default(),
            channel_values: channel_values.unwrap_or_else(|| PyDict::new(py).into()),
            channel_versions: channel_versions.unwrap_or_else(|| PyDict::new(py).into()),
            versions_seen: versions_seen.unwrap_or_else(|| PyDict::new(py).into()),
            pending_sends: pending_sends.unwrap_or_else(|| PyList::empty(py).into()),
            current_tasks: current_tasks.unwrap_or_else(|| PyDict::new(py).into()),
        })
    }

    /// Serialize the checkpoint to JSON
    fn to_json(&self, _py: Python) -> PyResult<String> {
        // In a real implementation, this would serialize the checkpoint to JSON
        // For now, we'll return a simple JSON representation
        Ok(format!(
            r#"{{"v": {}, "id": "{}", "ts": "{}"}}"#,
            self.v, self.id, self.ts
        ))
    }

    /// Deserialize a checkpoint from JSON
    #[classmethod]
    fn from_json(_cls: &PyType, py: Python, _json_str: &str) -> PyResult<Py<Self>> {
        // In a real implementation, this would deserialize from JSON
        // For now, we'll create a simple checkpoint
        Py::new(
            py,
            Checkpoint::new(py, 1, None, None, None, None, None, None, None)?,
        )
    }

    /// Create a copy of the checkpoint
    fn copy(&self, py: Python) -> PyResult<Py<Self>> {
        Py::new(
            py,
            Checkpoint {
                v: self.v,
                id: self.id.clone(),
                ts: self.ts.clone(),
                channel_values: self.channel_values.clone_ref(py),
                channel_versions: self.channel_versions.clone_ref(py),
                versions_seen: self.versions_seen.clone_ref(py),
                pending_sends: self.pending_sends.clone_ref(py),
                current_tasks: self.current_tasks.clone_ref(py),
            },
        )
    }

    /// Support dict-like access for compatibility
    fn __getitem__(&self, py: Python, key: &str) -> PyResult<PyObject> {
        match key {
            "v" => Ok(self.v.into_py(py)),
            "id" => Ok(self.id.clone().into_py(py)),
            "ts" => Ok(self.ts.clone().into_py(py)),
            "channel_values" => Ok(self.channel_values.clone_ref(py)),
            "channel_versions" => Ok(self.channel_versions.clone_ref(py)),
            "versions_seen" => Ok(self.versions_seen.clone_ref(py)),
            "pending_sends" => Ok(self.pending_sends.clone_ref(py)),
            "current_tasks" => Ok(self.current_tasks.clone_ref(py)),
            _ => Err(PyErr::new::<pyo3::exceptions::PyKeyError, _>(format!(
                "Key not found: {}",
                key
            ))),
        }
    }

    /// Support get() method for compatibility
    fn get(&self, py: Python, key: &str, default: Option<PyObject>) -> PyResult<PyObject> {
        match self.__getitem__(py, key) {
            Ok(val) => Ok(val),
            Err(_) => Ok(default.unwrap_or_else(|| py.None())),
        }
    }
}

/// Helper function to extract node metadata and create PregelNode
fn extract_pregel_node(py: Python, node_name: &str, node_obj: &PyObject) -> PyResult<PregelNode> {
    // Extract triggers (channels this node depends on)
    let triggers = if let Ok(triggers_attr) = node_obj.getattr(py, "triggers") {
        triggers_attr
            .extract::<Vec<String>>(py)
            .unwrap_or_else(|_| vec![node_name.to_string()])
    } else {
        vec![node_name.to_string()]
    };

    // Extract output channels
    let channels = if let Ok(channels_attr) = node_obj.getattr(py, "channels") {
        channels_attr.extract::<Vec<String>>(py).unwrap_or_default()
    } else {
        Vec::new()
    };

    // Extract retry policy if available
    let retry_policy = if let Ok(retry_attr) = node_obj.getattr(py, "retry_policy") {
        Some(crate::pregel_node::RetryPolicyConfig::from_py_object(
            py,
            &retry_attr,
        )?)
    } else {
        None
    };

    // Extract config if available
    let config = node_obj.getattr(py, "config").ok();

    Ok(PregelNode {
        runnable: node_obj.clone_ref(py),
        name: node_name.to_string(),
        triggers,
        channels,
        mapper: None,
        retry_policy,
        config,
    })
}

/// Pregel provides the main execution engine for LangGraph
#[pyclass(subclass)]
pub struct Pregel {
    #[pyo3(get, set)]
    pub nodes: HashMap<String, PyObject>,
    #[pyo3(get, set)]
    pub channels: HashMap<String, PyObject>,
    #[pyo3(get, set)]
    pub stream_mode: String,
    #[pyo3(get, set)]
    pub output_channels: Option<PyObject>,
    #[pyo3(get, set)]
    pub input_channels: Option<PyObject>,
    #[pyo3(get, set)]
    pub checkpointer: Option<PyObject>,
    #[pyo3(get, set)]
    pub builder: Option<PyObject>,
    #[pyo3(get, set)]
    pub config_type: Option<PyObject>,
}

#[pymethods]
impl Pregel {
    /// Create a new Pregel instance
    /// All parameters are optional to support subclassing
    #[new]
    #[pyo3(signature = (*_args, **kwargs))]
    fn new(_py: Python, _args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<Self> {
        // Extract parameters from kwargs with defaults
        let stream_mode = kwargs
            .and_then(|kw| kw.get_item("stream_mode").ok().flatten())
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_else(|| "values".to_string());

        let output_channels = kwargs
            .and_then(|kw| kw.get_item("output_channels").ok().flatten())
            .map(|v| v.into());

        let input_channels = kwargs
            .and_then(|kw| kw.get_item("input_channels").ok().flatten())
            .map(|v| v.into());

        let checkpointer = kwargs
            .and_then(|kw| kw.get_item("checkpointer").ok().flatten())
            .map(|v| v.into());

        let builder = kwargs
            .and_then(|kw| kw.get_item("builder").ok().flatten())
            .map(|v| v.into());

        let config_type = kwargs
            .and_then(|kw| kw.get_item("config_type").ok().flatten())
            .map(|v| v.into());

        // Extract nodes dict if provided
        let nodes = kwargs
            .and_then(|kw| kw.get_item("nodes").ok().flatten())
            .and_then(|v| v.extract::<HashMap<String, PyObject>>().ok())
            .unwrap_or_default();

        // Extract channels dict if provided
        let channels = kwargs
            .and_then(|kw| kw.get_item("channels").ok().flatten())
            .and_then(|v| v.extract::<HashMap<String, PyObject>>().ok())
            .unwrap_or_default();

        Ok(Pregel {
            nodes,
            channels,
            stream_mode,
            output_channels,
            input_channels,
            checkpointer,
            builder,
            config_type,
        })
    }

    /// Initialize method that accepts kwargs for subclassing support
    #[pyo3(signature = (*_args, **_kwargs))]
    fn __init__(&mut self, _args: &PyTuple, _kwargs: Option<&PyDict>) -> PyResult<()> {
        // Do nothing - all initialization happens in __new__
        // This method exists solely to satisfy Python's subclassing mechanism
        Ok(())
    }

    /// Support generic type syntax like Pregel[StateT, ContextT, InputT, OutputT]
    #[classmethod]
    fn __class_getitem__(_cls: &PyType, _item: PyObject) -> PyResult<PyObject> {
        // Return the class itself for generic type compatibility
        // This allows Pregel to be subscripted with type parameters
        Ok(_cls.into())
    }

    /// Run the graph with a single input and config
    #[pyo3(signature = (input, config=None, *, context=None, stream_mode=None, print_mode=None, output_keys=None, interrupt_before=None, interrupt_after=None, durability=None, debug=None))]
    fn invoke(
        &self,
        py: Python,
        input: PyObject,
        config: Option<PyObject>,
        context: Option<PyObject>,
        stream_mode: Option<&str>,
        print_mode: Option<PyObject>,
        output_keys: Option<PyObject>,
        interrupt_before: Option<PyObject>,
        interrupt_after: Option<PyObject>,
        durability: Option<PyObject>,
        debug: Option<PyObject>,
    ) -> PyResult<PyObject> {
        // NEW: Try to use Rust PregelLoop if we have the right structure
        if !self.nodes.is_empty() {
            // Check if nodes look like PregelNodes (have metadata)
            let first_node = self.nodes.values().next();
            let use_rust_loop = if let Some(node_obj) = first_node {
                // Check if this looks like a wrapped node with metadata
                node_obj.as_ref(py).hasattr("triggers").unwrap_or(false)
                    || node_obj.as_ref(py).hasattr("channels").unwrap_or(false)
            } else {
                false
            };

            if use_rust_loop {
                return self.invoke_with_rust_loop(
                    py,
                    input,
                    interrupt_before,
                    interrupt_after,
                    debug,
                );
            }
        }

        // FALLBACK: Original Python-style execution for backwards compatibility
        if !self.nodes.is_empty() {
            // Extract recursion_limit from config
            let recursion_limit = if let Some(ref cfg) = config {
                if let Ok(cfg_dict) = cfg.downcast::<PyDict>(py) {
                    cfg_dict
                        .get_item("recursion_limit")
                        .ok()
                        .flatten()
                        .and_then(|v| v.extract::<usize>().ok())
                        .unwrap_or(25) // Default recursion limit
                } else {
                    25
                }
            } else {
                25
            };

            // Check if we would exceed recursion limit
            if self.nodes.len() > recursion_limit {
                // Raise GraphRecursionError
                let result = py
                    .import("langgraph.errors")
                    .and_then(|m| m.getattr("GraphRecursionError"))
                    .and_then(|exc_class| {
                        exc_class
                            .call1((format!("Recursion limit of {} exceeded", recursion_limit),))
                    });

                match result {
                    Ok(exc) => return Err(pyo3::PyErr::from_value(exc)),
                    Err(_) => {
                        return Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                            "Recursion limit of {} exceeded",
                            recursion_limit
                        )))
                    }
                }
            }

            // Handle input extraction based on input_channels type
            let mut current_state = if let Some(ref input_channels) = self.input_channels {
                // If input_channels is a list and input is a dict, extract the value(s)
                if let Ok(channel_names) = input_channels.extract::<Vec<String>>(py) {
                    // input_channels is a list - check if input is a dict
                    if let Ok(input_dict) = input.extract::<HashMap<String, PyObject>>(py) {
                        // For single channel, extract just the value
                        if channel_names.len() == 1 {
                            if let Some(value) = input_dict.get(&channel_names[0]) {
                                value.clone_ref(py)
                            } else {
                                input
                            }
                        } else {
                            // Multiple channels - keep as dict
                            input
                        }
                    } else {
                        // Input is not a dict, use as-is
                        input
                    }
                } else {
                    // input_channels is not a list (probably string), use input as-is
                    input
                }
            } else {
                // No input_channels specified, use input as-is
                input
            };

            // Get node names in a deterministic order
            let mut node_names: Vec<String> = self.nodes.keys().cloned().collect();
            node_names.sort();

            for node_name in &node_names {
                if let Some(node_func) = self.nodes.get(node_name) {
                    // Try different calling conventions
                    let result = if let Ok(build_method) = node_func.getattr(py, "build") {
                        // NodeBuilder - call build() to get the actual runnable, then invoke it
                        match build_method.call0(py) {
                            Ok(built_func) => {
                                // Try invoke method on built func
                                if let Ok(invoke_method) = built_func.getattr(py, "invoke") {
                                    invoke_method.call1(py, (current_state.clone_ref(py),))
                                } else {
                                    built_func.call1(py, (current_state.clone_ref(py),))
                                }
                            }
                            Err(e) => Err(e),
                        }
                    } else if let Ok(invoke_method) = node_func.getattr(py, "invoke") {
                        // RunnableLike with invoke method
                        invoke_method.call1(py, (current_state.clone_ref(py),))
                    } else {
                        // Direct callable
                        node_func.call1(py, (current_state.clone_ref(py),))
                    };

                    match result {
                        Ok(res) => {
                            current_state = res;
                        }
                        Err(e) => {
                            return Err(e);
                        }
                    }
                }
            }

            // Output formatting rules (in order of precedence):
            // 1. output_keys parameter (highest precedence) → always return dict
            // 2. output_channels as list → return dict
            // 3. output_channels as string → return raw value
            // 4. output_channels None/empty → return None

            // Rule 1: Check output_keys first (parameter overrides attribute)
            if let Some(ref keys) = output_keys {
                if let Ok(keys_list) = keys.extract::<Vec<String>>(py) {
                    let result_dict = PyDict::new(py);
                    for key in keys_list {
                        result_dict.set_item(&key, current_state.clone_ref(py))?;
                    }
                    return Ok(result_dict.into());
                }
            }

            // Rules 2-4: Check output_channels
            if let Some(ref output_channels) = self.output_channels {
                // Check if it's Python None
                if output_channels.as_ref(py).is_none() {
                    return Ok(py.None());
                }

                // Try to extract as list (Rule 2)
                if let Ok(channels_list) = output_channels.extract::<Vec<String>>(py) {
                    // Empty list means no output
                    if channels_list.is_empty() {
                        return Ok(py.None());
                    }
                    // Non-empty list → return dict
                    let result_dict = PyDict::new(py);
                    for channel in channels_list {
                        result_dict.set_item(&channel, current_state.clone_ref(py))?;
                    }
                    return Ok(result_dict.into());
                }

                // Try to extract as string (Rule 3)
                if let Ok(channel_str) = output_channels.extract::<String>(py) {
                    if channel_str.is_empty() {
                        return Ok(py.None());
                    }
                    // Non-empty string → return raw value
                    return Ok(current_state);
                }

                // Other type, return value directly
                return Ok(current_state);
            }

            // Rule 4: No output_channels specified → return None
            return Ok(py.None());
        }

        // Try to execute using builder if available
        if let Some(ref builder) = self.builder {
            if let Ok(nodes_dict) = builder.getattr(py, "nodes") {
                if let Ok(nodes) = nodes_dict.extract::<HashMap<String, PyObject>>(py) {
                    let mut current_state = input;
                    let mut node_names: Vec<String> = nodes.keys().cloned().collect();
                    node_names.sort();

                    for node_name in &node_names {
                        if let Some(node_func) = nodes.get(node_name) {
                            match node_func.call1(py, (current_state.clone_ref(py),)) {
                                Ok(result) => {
                                    current_state = result;
                                }
                                Err(e) => {
                                    return Err(e);
                                }
                            }
                        }
                    }

                    return Ok(current_state);
                }
            }
        }

        // Fallback: simple pass-through
        Ok(input)
    }

    /// Stream graph steps for a single input
    fn stream(
        &self,
        py: Python,
        input: PyObject,
        config: Option<PyObject>,
        context: Option<PyObject>,
        stream_mode: Option<PyObject>,
        print_mode: Option<PyObject>,
        output_keys: Option<PyObject>,
        interrupt_before: Option<PyObject>,
        interrupt_after: Option<PyObject>,
        durability: Option<PyObject>,
        subgraphs: Option<bool>,
        debug: Option<bool>,
    ) -> PyResult<PyObject> {
        // NEW: Try to use Rust PregelLoop if we have the right structure
        if !self.nodes.is_empty() {
            let first_node = self.nodes.values().next();
            let use_rust_loop = if let Some(node_obj) = first_node {
                node_obj.as_ref(py).hasattr("triggers").unwrap_or(false)
                    || node_obj.as_ref(py).hasattr("channels").unwrap_or(false)
            } else {
                false
            };

            if use_rust_loop {
                return self.stream_with_rust_loop(
                    py,
                    input,
                    interrupt_before,
                    interrupt_after,
                    debug,
                );
            }
        }

        // FALLBACK: Return empty list for backwards compatibility
        Ok(PyList::empty(py).into())
    }

    /// Asynchronously invoke the graph on a single input
    fn ainvoke(
        &self,
        py: Python,
        input: PyObject,
        config: Option<PyObject>,
        context: Option<PyObject>,
        stream_mode: Option<&str>,
        print_mode: Option<PyObject>,
        output_keys: Option<PyObject>,
        interrupt_before: Option<PyObject>,
        interrupt_after: Option<PyObject>,
        durability: Option<PyObject>,
    ) -> PyResult<PyObject> {
        // In a real implementation, this would async execute the graph
        // For now, we'll just return the input as output
        Ok(input)
    }

    /// Asynchronously stream graph steps for a single input
    fn astream(
        &self,
        py: Python,
        input: PyObject,
        config: Option<PyObject>,
        context: Option<PyObject>,
        stream_mode: Option<PyObject>,
        print_mode: Option<PyObject>,
        output_keys: Option<PyObject>,
        interrupt_before: Option<PyObject>,
        interrupt_after: Option<PyObject>,
        durability: Option<PyObject>,
        subgraphs: Option<bool>,
        debug: Option<bool>,
    ) -> PyResult<PyObject> {
        // In a real implementation, this would async stream the graph execution
        // For now, we'll return an empty list
        Ok(PyList::empty(py).into())
    }

    /// Batch invoke the graph with multiple inputs
    fn batch(
        &self,
        py: Python,
        inputs: Vec<PyObject>,
        config: Option<PyObject>,
        context: Option<PyObject>,
    ) -> PyResult<Vec<PyObject>> {
        // In a real implementation, this would execute the graph for multiple inputs
        // For now, we'll just return the inputs
        Ok(inputs)
    }

    /// Asynchronously batch invoke the graph with multiple inputs
    fn abatch(
        &self,
        py: Python,
        inputs: Vec<PyObject>,
        config: Option<PyObject>,
        context: Option<PyObject>,
    ) -> PyResult<Vec<PyObject>> {
        // In a real implementation, this would async execute the graph for multiple inputs
        // For now, we'll just return the inputs
        Ok(inputs)
    }

    /// Get the input schema for the graph
    #[getter]
    fn input_schema(&self, py: Python) -> PyResult<PyObject> {
        // Generate schema from input_channels if available (PRIORITIZE THIS)
        // This is more specific than the builder's generic schema
        if let Some(ref input_channels) = self.input_channels {
            eprintln!("DEBUG input_schema: Trying to extract channel name");

            // Try to extract as a list first (for dict-style inputs)
            if let Ok(channel_names) = input_channels.extract::<Vec<String>>(py) {
                eprintln!(
                    "DEBUG input_schema: input_channels is a list with {} items",
                    channel_names.len()
                );
                // Multiple channels - create object schema with properties
                let mut properties = std::collections::HashMap::new();

                for channel_name in &channel_names {
                    if let Some(channel) = self.channels.get(channel_name) {
                        if let Ok(channel_type) = channel.getattr(py, "typ") {
                            let type_name = if let Ok(name) = channel_type.getattr(py, "__name__") {
                                name.extract::<String>(py)
                                    .unwrap_or_else(|_| "object".to_string())
                            } else {
                                "object".to_string()
                            };

                            let json_type = match type_name.as_str() {
                                "int" => "integer",
                                "str" => "string",
                                "bool" => "boolean",
                                "float" | "number" => "number",
                                "list" => "array",
                                "dict" => "object",
                                _ => "object",
                            };

                            properties.insert(
                                channel_name.clone(),
                                (json_type.to_string(), channel_name.clone()),
                            );
                        }
                    }
                }

                // Build properties dict for the schema
                let mut props_code = String::from("{");
                for (idx, (name, (json_type, title))) in properties.iter().enumerate() {
                    if idx > 0 {
                        props_code.push_str(", ");
                    }
                    // Convert title: replace underscores with spaces and capitalize each word
                    let title_case = title
                        .split('_')
                        .map(|word| {
                            let mut chars = word.chars();
                            match chars.next() {
                                None => String::new(),
                                Some(first) => {
                                    first.to_uppercase().collect::<String>() + chars.as_str()
                                }
                            }
                        })
                        .collect::<Vec<_>>()
                        .join(" ");
                    props_code.push_str(&format!(
                        "'{}': {{'title': '{}', 'type': '{}', 'default': None}}",
                        name, title_case, json_type
                    ));
                }
                props_code.push('}');

                let code = format!(
                    r#"
class InputSchema(dict):
    @classmethod
    def model_json_schema(cls):
        return {{"title": "LangGraphInput", "type": "object", "properties": {}}}
InputSchema
"#,
                    props_code
                );
                let locals = PyDict::new(py);
                py.run(&code, None, Some(locals))?;
                let schema = locals.get_item("InputSchema")?.ok_or_else(|| {
                    pyo3::exceptions::PyRuntimeError::new_err("Failed to create InputSchema")
                })?;
                return Ok(schema.into());
            }

            // If input_channels is a string, get that channel's type
            if let Ok(channel_name) = input_channels.extract::<String>(py) {
                eprintln!("DEBUG input_schema: channel_name={}", channel_name);
                // Get the channel from self.channels
                if let Some(channel) = self.channels.get(&channel_name) {
                    eprintln!("DEBUG input_schema: Found channel");
                    // The channel has a 'typ' attribute that contains the Python type
                    if let Ok(channel_type) = channel.getattr(py, "typ") {
                        eprintln!("DEBUG input_schema: Got channel.typ");
                        // Get the type name - channel_type IS the type (e.g., int, str, etc.)
                        let type_name = if let Ok(name) = channel_type.getattr(py, "__name__") {
                            let n = name
                                .extract::<String>(py)
                                .unwrap_or_else(|_| "object".to_string());
                            eprintln!("DEBUG input_schema: type_name={}", n);
                            n
                        } else {
                            // Fallback to "object"
                            eprintln!("DEBUG input_schema: No __name__ attr");
                            "object".to_string()
                        };

                        // Convert Python type to JSON schema type
                        let json_type = match type_name.as_str() {
                            "int" => "integer",
                            "str" => "string",
                            "bool" => "boolean",
                            "float" | "number" => "number",
                            "list" => "array",
                            "dict" => "object",
                            _ => "object",
                        };

                        eprintln!("DEBUG input_schema: json_type={}", json_type);

                        // Create a Pydantic-like schema class
                        let code = format!(
                            r#"
class InputSchema(dict):
    @classmethod
    def model_json_schema(cls):
        return {{"title": "LangGraphInput", "type": "{}"}}
InputSchema
"#,
                            json_type
                        );
                        let locals = PyDict::new(py);
                        py.run(&code, None, Some(locals))?;
                        let schema = locals.get_item("InputSchema")?.ok_or_else(|| {
                            pyo3::exceptions::PyRuntimeError::new_err(
                                "Failed to create InputSchema",
                            )
                        })?;
                        return Ok(schema.into());
                    } else {
                        eprintln!("DEBUG input_schema: Failed to get typ attr");
                    }
                } else {
                    eprintln!(
                        "DEBUG input_schema: Channel '{}' not found in self.channels",
                        channel_name
                    );
                }
            } else {
                eprintln!("DEBUG input_schema: Failed to extract channel_name as string");
            }
        } else {
            eprintln!("DEBUG input_schema: No input_channels");
        }

        // Fallback: create a generic object schema
        eprintln!("DEBUG input_schema: Using fallback");

        let code = r#"
class MockSchema(dict):
    @classmethod
    def model_json_schema(cls):
        return {"title": "LangGraphInput", "type": "object"}
MockSchema
"#;
        let locals = PyDict::new(py);
        py.run(code, None, Some(locals))?;
        let schema = locals.get_item("MockSchema")?.ok_or_else(|| {
            pyo3::exceptions::PyRuntimeError::new_err("Failed to create MockSchema")
        })?;
        Ok(schema.into())
    }

    /// Get the output schema for the graph
    #[getter]
    fn output_schema(&self, py: Python) -> PyResult<PyObject> {
        // Generate schema from output_channels if available (PRIORITIZE THIS)
        if let Some(ref output_channels) = self.output_channels {
            // Try to extract as a list first (for dict-style outputs)
            if let Ok(channel_names) = output_channels.extract::<Vec<String>>(py) {
                // Multiple channels - create object schema with properties
                let mut properties = std::collections::HashMap::new();

                for channel_name in &channel_names {
                    if let Some(channel) = self.channels.get(channel_name) {
                        if let Ok(channel_type) = channel.getattr(py, "typ") {
                            let type_name = if let Ok(name) = channel_type.getattr(py, "__name__") {
                                name.extract::<String>(py)
                                    .unwrap_or_else(|_| "object".to_string())
                            } else {
                                "object".to_string()
                            };

                            let json_type = match type_name.as_str() {
                                "int" => "integer",
                                "str" => "string",
                                "bool" => "boolean",
                                "float" | "number" => "number",
                                "list" => "array",
                                "dict" => "object",
                                _ => "object",
                            };

                            properties.insert(
                                channel_name.clone(),
                                (json_type.to_string(), channel_name.clone()),
                            );
                        }
                    }
                }

                // Build properties dict for the schema
                let mut props_code = String::from("{");
                for (idx, (name, (json_type, title))) in properties.iter().enumerate() {
                    if idx > 0 {
                        props_code.push_str(", ");
                    }
                    // Convert title: replace underscores with spaces and capitalize each word
                    let title_case = title
                        .split('_')
                        .map(|word| {
                            let mut chars = word.chars();
                            match chars.next() {
                                None => String::new(),
                                Some(first) => {
                                    first.to_uppercase().collect::<String>() + chars.as_str()
                                }
                            }
                        })
                        .collect::<Vec<_>>()
                        .join(" ");
                    props_code.push_str(&format!(
                        "'{}': {{'title': '{}', 'type': '{}', 'default': None}}",
                        name, title_case, json_type
                    ));
                }
                props_code.push('}');

                let code = format!(
                    r#"
class OutputSchema(dict):
    @classmethod
    def model_json_schema(cls):
        return {{"title": "LangGraphOutput", "type": "object", "properties": {}}}
OutputSchema
"#,
                    props_code
                );
                let locals = PyDict::new(py);
                py.run(&code, None, Some(locals))?;
                let schema = locals.get_item("OutputSchema")?.ok_or_else(|| {
                    pyo3::exceptions::PyRuntimeError::new_err("Failed to create OutputSchema")
                })?;
                return Ok(schema.into());
            }

            // If output_channels is a string, get that channel's type
            if let Ok(channel_name) = output_channels.extract::<String>(py) {
                // Get the channel from self.channels
                if let Some(channel) = self.channels.get(&channel_name) {
                    // The channel has a 'typ' attribute that contains the Python type
                    if let Ok(channel_type) = channel.getattr(py, "typ") {
                        // Get the type name
                        let type_name = if let Ok(name) = channel_type.getattr(py, "__name__") {
                            name.extract::<String>(py)
                                .unwrap_or_else(|_| "object".to_string())
                        } else {
                            "object".to_string()
                        };

                        // Convert Python type to JSON schema type
                        let json_type = match type_name.as_str() {
                            "int" => "integer",
                            "str" => "string",
                            "bool" => "boolean",
                            "float" | "number" => "number",
                            "list" => "array",
                            "dict" => "object",
                            _ => "object",
                        };

                        // Create a Pydantic-like schema class
                        let code = format!(
                            r#"
class OutputSchema(dict):
    @classmethod
    def model_json_schema(cls):
        return {{"title": "LangGraphOutput", "type": "{}"}}
OutputSchema
"#,
                            json_type
                        );
                        let locals = PyDict::new(py);
                        py.run(&code, None, Some(locals))?;
                        let schema = locals.get_item("OutputSchema")?.ok_or_else(|| {
                            pyo3::exceptions::PyRuntimeError::new_err(
                                "Failed to create OutputSchema",
                            )
                        })?;
                        return Ok(schema.into());
                    }
                }
            }
        }

        // Fallback: create a generic object schema
        let code = r#"
class MockSchema(dict):
    @classmethod
    def model_json_schema(cls):
        return {"title": "LangGraphOutput", "type": "object"}
MockSchema
"#;
        let locals = PyDict::new(py);
        py.run(code, None, Some(locals))?;
        let schema = locals.get_item("MockSchema")?.ok_or_else(|| {
            pyo3::exceptions::PyRuntimeError::new_err("Failed to create MockSchema")
        })?;
        Ok(schema.into())
    }

    /// Get the output JSON schema for the graph
    fn get_output_jsonschema(&self, py: Python, config: Option<PyObject>) -> PyResult<PyObject> {
        // In a real implementation, this would return the actual output schema
        // For now, return an empty dict
        Ok(PyDict::new(py).into())
    }

    /// Get the context JSON schema for the graph
    fn get_context_jsonschema(&self, py: Python, _config: Option<PyObject>) -> PyResult<PyObject> {
        // Return None to indicate no context schema
        Ok(py.None())
    }

    /// Internal: Invoke using Rust PregelLoop
    fn invoke_with_rust_loop(
        &self,
        py: Python,
        input: PyObject,
        interrupt_before: Option<PyObject>,
        interrupt_after: Option<PyObject>,
        debug: Option<PyObject>,
    ) -> PyResult<PyObject> {
        // 1. Convert Python nodes to PregelNode structures
        let mut pregel_nodes = HashMap::new();
        for (node_name, node_obj) in &self.nodes {
            let pregel_node = extract_pregel_node(py, node_name, node_obj)?;
            pregel_nodes.insert(node_name.clone(), pregel_node);
        }

        // 2. Extract interrupt configuration
        let interrupt_before_list = interrupt_before
            .and_then(|v| v.extract::<Vec<String>>(py).ok())
            .unwrap_or_default();

        let interrupt_after_list = interrupt_after
            .and_then(|v| v.extract::<Vec<String>>(py).ok())
            .unwrap_or_default();

        let debug_flag = debug
            .and_then(|v| v.extract::<bool>(py).ok())
            .unwrap_or(false);

        // 3. Create PregelConfig
        let config = PregelConfig {
            recursion_limit: 25,
            interrupt_before: interrupt_before_list,
            interrupt_after: interrupt_after_list,
            debug: debug_flag,
        };

        // 4. Create PregelLoop
        let mut loop_executor = PregelLoop::new(pregel_nodes, self.channels.clone(), config);

        // 5. Execute
        let result = loop_executor.invoke(py, input)?;

        // 6. Format output based on output_channels
        self.format_output(py, result)
    }

    /// Internal: Format output based on output_channels configuration
    fn format_output(&self, py: Python, state: PyObject) -> PyResult<PyObject> {
        // Output formatting rules (in order of precedence):
        // 1. output_channels as list → return dict with those keys
        // 2. output_channels as string → return raw value from that key
        // 3. output_channels None/empty → return None
        // 4. No output_channels → return full state

        if let Some(ref output_channels) = self.output_channels {
            // Check if it's Python None
            if output_channels.as_ref(py).is_none() {
                return Ok(py.None());
            }

            // Try to extract as list (Rule 1)
            if let Ok(channels_list) = output_channels.extract::<Vec<String>>(py) {
                if channels_list.is_empty() {
                    return Ok(py.None());
                }
                // Non-empty list → return dict with those keys
                let result_dict = PyDict::new(py);
                if let Ok(state_dict) = state.downcast::<PyDict>(py) {
                    for channel in channels_list {
                        if let Some(value) = state_dict.get_item(&channel)? {
                            result_dict.set_item(&channel, value)?;
                        }
                    }
                }
                return Ok(result_dict.into());
            }

            // Try to extract as string (Rule 2)
            if let Ok(channel_str) = output_channels.extract::<String>(py) {
                if channel_str.is_empty() {
                    return Ok(py.None());
                }
                // Non-empty string → return raw value from that key
                if let Ok(state_dict) = state.downcast::<PyDict>(py) {
                    if let Some(value) = state_dict.get_item(&channel_str)? {
                        return Ok(value.into());
                    }
                }
                return Ok(py.None());
            }
        }

        // Rule 4: No output_channels → return full state
        Ok(state)
    }

    /// Internal: Stream using Rust PregelLoop
    fn stream_with_rust_loop(
        &self,
        py: Python,
        input: PyObject,
        interrupt_before: Option<PyObject>,
        interrupt_after: Option<PyObject>,
        debug: Option<bool>,
    ) -> PyResult<PyObject> {
        // 1. Convert Python nodes to PregelNode structures
        let mut pregel_nodes = HashMap::new();
        for (node_name, node_obj) in &self.nodes {
            let pregel_node = extract_pregel_node(py, node_name, node_obj)?;
            pregel_nodes.insert(node_name.clone(), pregel_node);
        }

        // 2. Extract interrupt configuration
        let interrupt_before_list = interrupt_before
            .and_then(|v| v.extract::<Vec<String>>(py).ok())
            .unwrap_or_default();

        let interrupt_after_list = interrupt_after
            .and_then(|v| v.extract::<Vec<String>>(py).ok())
            .unwrap_or_default();

        let debug_flag = debug.unwrap_or(false);

        // 3. Create PregelConfig
        let config = PregelConfig {
            recursion_limit: 25,
            interrupt_before: interrupt_before_list,
            interrupt_after: interrupt_after_list,
            debug: debug_flag,
        };

        // 4. Create PregelLoop
        let mut loop_executor = PregelLoop::new(pregel_nodes, self.channels.clone(), config);

        // 5. Execute with streaming
        let results = loop_executor.stream(py, input)?;

        // 6. Format each result and return as list
        let formatted_results = PyList::empty(py);
        for result in results {
            let formatted = self.format_output(py, result)?;
            formatted_results.append(formatted)?;
        }

        Ok(formatted_results.into())
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn fast_langgraph(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<BaseChannel>()?;
    m.add_class::<LastValue>()?;
    m.add_class::<Checkpoint>()?;
    m.add_class::<Pregel>()?;
    m.add_class::<GraphExecutor>()?;

    // Register hybrid acceleration classes
    crate::hybrid::register_hybrid_classes(m)?;

    // Register fast channel types
    crate::fast_channels::register_fast_channels(_py, m)?;

    // Register rust checkpoint
    crate::rust_checkpoint::register_checkpoint(_py, m)?;

    // Register SQLite checkpoint
    crate::checkpoint_sqlite::register_sqlite_checkpoint(_py, m)?;

    // Register LLM cache
    crate::llm_cache::register_llm_cache(_py, m)?;

    // Register state merge operations
    crate::state_merge::register_state_merge(_py, m)?;

    // Register function cache
    crate::function_cache::register_function_cache(_py, m)?;

    Ok(())
}

/// GraphExecutor provides a high-performance execution engine for LangGraph
#[pyclass]
pub struct GraphExecutor {
    // In a real implementation, this would hold a reference to our PregelExecutor
}

#[pymethods]
impl GraphExecutor {
    /// Create a new GraphExecutor
    #[new]
    fn new() -> Self {
        GraphExecutor {}
    }

    /// Execute the graph
    fn execute_graph(&self, _py: Python, input: &PyDict) -> PyResult<PyObject> {
        // This is a simplified implementation
        // In a real implementation, we would convert the Python input
        // to Rust types, execute the graph, and convert the result back

        // For now, we'll just return the input as output
        Ok(input.into())
    }

    /// Add a node to the graph
    fn add_node(
        &mut self,
        _py: Python,
        _node_id: String,
        _triggers: Vec<String>,
        _channels: Vec<String>,
    ) -> PyResult<()> {
        // In a real implementation, we would create a proper PregelNode
        // with a Python callable as the processor
        Ok(())
    }
}
