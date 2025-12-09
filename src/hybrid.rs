//! Hybrid acceleration module for LangGraph
//!
//! This module provides Rust-accelerated implementations of hot paths
//! within the Python Pregel execution loop, while keeping the orchestration
//! in Python for maximum compatibility.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use std::collections::HashMap;

/// ChannelManager provides accelerated channel operations
///
/// This wraps multiple channels and provides fast batch operations
/// for the Pregel execution loop.
#[pyclass]
pub struct ChannelManager {
    /// Channel values stored as Python objects
    channels: HashMap<String, PyObject>,
    /// Channel versions for checkpoint tracking
    versions: HashMap<String, u64>,
}

#[pymethods]
impl ChannelManager {
    #[new]
    fn new() -> Self {
        ChannelManager {
            channels: HashMap::new(),
            versions: HashMap::new(),
        }
    }

    /// Initialize channels from a dict of channel specs
    fn init_channels(&mut self, _py: Python, channel_specs: &PyDict) -> PyResult<()> {
        for (key, value) in channel_specs.iter() {
            let key_str: String = key.extract()?;
            self.channels.insert(key_str.clone(), value.into());
            self.versions.insert(key_str, 0);
        }
        Ok(())
    }

    /// Get current values from all channels
    fn get_all_values(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for (key, channel) in &self.channels {
            // Call channel.get() to get current value
            if let Ok(get_method) = channel.getattr(py, "get") {
                if let Ok(value) = get_method.call0(py) {
                    dict.set_item(key, value)?;
                }
            }
        }
        Ok(dict.into())
    }

    /// Apply writes to channels in batch (hot path optimization)
    ///
    /// This is one of the most frequently called operations in the Pregel loop.
    /// Writes are tuples of (channel_name, value).
    fn apply_writes_batch(&mut self, py: Python, writes: &PyList) -> PyResult<Vec<String>> {
        let mut updated_channels = Vec::new();

        // Group writes by channel
        let mut grouped: HashMap<String, Vec<PyObject>> = HashMap::new();

        for item in writes.iter() {
            let tuple: &PyTuple = item.downcast()?;
            if tuple.len() >= 2 {
                let channel_name: String = tuple.get_item(0)?.extract()?;
                let value: PyObject = tuple.get_item(1)?.into();
                grouped.entry(channel_name).or_default().push(value);
            }
        }

        // Apply writes to each channel
        for (channel_name, values) in grouped {
            if let Some(channel) = self.channels.get(&channel_name) {
                // Create PyList from values
                let py_values = PyList::new(py, &values);

                // Call channel.update(values)
                if let Ok(update_method) = channel.getattr(py, "update") {
                    match update_method.call1(py, (py_values,)) {
                        Ok(result) => {
                            // Check if update returned True (something changed)
                            if result.is_true(py).unwrap_or(false) {
                                // Increment version
                                if let Some(version) = self.versions.get_mut(&channel_name) {
                                    *version += 1;
                                }
                                updated_channels.push(channel_name);
                            }
                        }
                        Err(e) => return Err(e),
                    }
                }
            }
        }

        Ok(updated_channels)
    }

    /// Get channel versions for checkpoint
    fn get_versions(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for (key, version) in &self.versions {
            dict.set_item(key, *version)?;
        }
        Ok(dict.into())
    }

    /// Checkpoint all channels (serialize state)
    fn checkpoint_channels(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for (key, channel) in &self.channels {
            // Call channel.checkpoint() if available
            if let Ok(checkpoint_method) = channel.getattr(py, "checkpoint") {
                if let Ok(value) = checkpoint_method.call0(py) {
                    dict.set_item(key, value)?;
                }
            }
        }
        Ok(dict.into())
    }

    /// Restore channels from checkpoint
    fn restore_from_checkpoint(&mut self, py: Python, checkpoint: &PyDict) -> PyResult<()> {
        for (key, value) in checkpoint.iter() {
            let key_str: String = key.extract()?;
            if let Some(channel) = self.channels.get(&key_str) {
                // Call channel.update() with checkpointed value
                if let Ok(update_method) = channel.getattr(py, "from_checkpoint") {
                    update_method.call1(py, (value,))?;
                }
            }
        }
        Ok(())
    }
}

/// TaskScheduler provides accelerated task scheduling
///
/// This determines which nodes should execute based on channel updates.
#[pyclass]
pub struct TaskScheduler {
    /// Node triggers: node_name -> list of channel names that trigger it
    triggers: HashMap<String, Vec<String>>,
    /// Node subscriptions: node_name -> list of channels to read from
    subscriptions: HashMap<String, Vec<String>>,
}

#[pymethods]
impl TaskScheduler {
    #[new]
    fn new() -> Self {
        TaskScheduler {
            triggers: HashMap::new(),
            subscriptions: HashMap::new(),
        }
    }

    /// Register a node with its triggers and subscriptions
    fn register_node(
        &mut self,
        node_name: String,
        triggers: Vec<String>,
        subscriptions: Vec<String>,
    ) -> PyResult<()> {
        self.triggers.insert(node_name.clone(), triggers);
        self.subscriptions.insert(node_name, subscriptions);
        Ok(())
    }

    /// Determine which nodes should execute based on updated channels
    ///
    /// Returns a list of node names that should run.
    fn get_triggered_nodes(&self, updated_channels: Vec<String>) -> Vec<String> {
        let mut triggered = Vec::new();
        let updated_set: std::collections::HashSet<_> = updated_channels.into_iter().collect();

        for (node_name, triggers) in &self.triggers {
            // Node triggers if any of its trigger channels were updated
            if triggers.iter().any(|t| updated_set.contains(t)) {
                triggered.push(node_name.clone());
            }
        }

        triggered
    }

    /// Get the input channels for a node
    fn get_node_inputs(&self, node_name: &str) -> Vec<String> {
        self.subscriptions
            .get(node_name)
            .cloned()
            .unwrap_or_default()
    }
}

/// PregelAccelerator combines ChannelManager and TaskScheduler
/// for full hybrid acceleration of the Pregel loop.
#[pyclass]
pub struct PregelAccelerator {
    channel_manager: ChannelManager,
    task_scheduler: TaskScheduler,
    step: usize,
    max_steps: usize,
}

#[pymethods]
impl PregelAccelerator {
    #[new]
    #[pyo3(signature = (max_steps=25))]
    fn new(max_steps: usize) -> Self {
        PregelAccelerator {
            channel_manager: ChannelManager::new(),
            task_scheduler: TaskScheduler::new(),
            step: 0,
            max_steps,
        }
    }

    /// Initialize the accelerator with channels and nodes
    fn initialize(&mut self, py: Python, channels: &PyDict, nodes: &PyDict) -> PyResult<()> {
        // Initialize channels
        self.channel_manager.init_channels(py, channels)?;

        // Initialize node triggers from PregelNode metadata
        for (name, node) in nodes.iter() {
            let node_name: String = name.extract()?;

            // Get triggers from node
            let triggers: Vec<String> = if let Ok(t) = node.getattr("triggers") {
                t.extract().unwrap_or_default()
            } else {
                vec![]
            };

            // Get channels (subscriptions) from node
            let channels: Vec<String> = if let Ok(c) = node.getattr("channels") {
                c.extract().unwrap_or_default()
            } else {
                vec![]
            };

            self.task_scheduler
                .register_node(node_name, triggers, channels)?;
        }

        Ok(())
    }

    /// Execute one step of the Pregel loop
    ///
    /// Returns (tasks_to_run, should_continue)
    fn execute_step(&mut self, py: Python, writes: &PyList) -> PyResult<(Vec<String>, bool)> {
        // Check recursion limit
        if self.step >= self.max_steps {
            // Raise GraphRecursionError
            let result = py
                .import("langgraph.errors")
                .and_then(|m| m.getattr("GraphRecursionError"))
                .and_then(|exc_class| {
                    exc_class.call1((format!("Recursion limit of {} exceeded", self.max_steps),))
                });

            match result {
                Ok(exc) => return Err(pyo3::PyErr::from_value(exc)),
                Err(_) => {
                    return Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                        "Recursion limit of {} exceeded",
                        self.max_steps
                    )))
                }
            }
        }

        // Apply writes to channels
        let updated = self.channel_manager.apply_writes_batch(py, writes)?;

        // Determine which nodes to trigger
        let tasks = self.task_scheduler.get_triggered_nodes(updated);

        // Increment step counter
        self.step += 1;

        // Continue if there are tasks
        let should_continue = !tasks.is_empty();

        Ok((tasks, should_continue))
    }

    /// Get current channel values for a set of nodes
    fn get_node_inputs(&self, py: Python, node_names: Vec<String>) -> PyResult<PyObject> {
        let result = PyDict::new(py);

        for node_name in node_names {
            let input_channels = self.task_scheduler.get_node_inputs(&node_name);
            let inputs = PyDict::new(py);

            for channel_name in input_channels {
                if let Some(channel) = self.channel_manager.channels.get(&channel_name) {
                    if let Ok(get_method) = channel.getattr(py, "get") {
                        if let Ok(value) = get_method.call0(py) {
                            inputs.set_item(&channel_name, value)?;
                        }
                    }
                }
            }

            result.set_item(&node_name, inputs)?;
        }

        Ok(result.into())
    }

    /// Get channel manager for direct access
    fn get_channel_manager(&self) -> ChannelManager {
        ChannelManager {
            channels: self.channel_manager.channels.clone(),
            versions: self.channel_manager.versions.clone(),
        }
    }

    /// Reset for new invocation
    fn reset(&mut self) {
        self.step = 0;
    }

    /// Get current step
    fn get_step(&self) -> usize {
        self.step
    }

    /// Checkpoint current state
    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("step", self.step)?;
        dict.set_item("channels", self.channel_manager.checkpoint_channels(py)?)?;
        dict.set_item("versions", self.channel_manager.get_versions(py)?)?;
        Ok(dict.into())
    }
}

/// Register hybrid acceleration classes with the module
pub fn register_hybrid_classes(m: &PyModule) -> PyResult<()> {
    m.add_class::<ChannelManager>()?;
    m.add_class::<TaskScheduler>()?;
    m.add_class::<PregelAccelerator>()?;
    Ok(())
}
