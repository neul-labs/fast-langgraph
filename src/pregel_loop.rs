//! Pregel Execution Loop
//!
//! This module implements the main Pregel execution loop that orchestrates
//! the superstep iteration model.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

use crate::pregel_algo::{apply_writes, prepare_next_tasks, should_interrupt, TaskWrites};
use crate::pregel_node::{PregelExecutableTask, PregelNode};

/// Configuration for Pregel execution
#[derive(Clone, Debug)]
pub struct PregelConfig {
    /// Maximum number of supersteps before stopping
    pub recursion_limit: usize,
    /// Nodes to interrupt before execution
    pub interrupt_before: Vec<String>,
    /// Nodes to interrupt after execution
    pub interrupt_after: Vec<String>,
    /// Enable debug output
    pub debug: bool,
}

impl Default for PregelConfig {
    fn default() -> Self {
        Self {
            recursion_limit: 25,
            interrupt_before: Vec::new(),
            interrupt_after: Vec::new(),
            debug: false,
        }
    }
}

/// Checkpoint state during execution
#[derive(Clone)]
pub struct CheckpointState {
    /// Unique checkpoint ID
    pub id: String,
    /// Channel versions (channel_name -> version)
    pub channel_versions: HashMap<String, usize>,
    /// Versions seen by each node (node_name -> {channel_name -> version})
    pub versions_seen: HashMap<String, HashMap<String, usize>>,
    /// Pending writes to be applied
    pub pending_writes: Vec<(String, PyObject, String)>, // (channel, value, node)
    /// Pending Send objects for dynamic dispatch
    pub pending_sends: Vec<PyObject>,
}

impl CheckpointState {
    pub fn new(checkpoint_id: String) -> Self {
        Self {
            id: checkpoint_id,
            channel_versions: HashMap::new(),
            versions_seen: HashMap::new(),
            pending_writes: Vec::new(),
            pending_sends: Vec::new(),
        }
    }

    /// Create from Python checkpoint dict
    pub fn from_py_checkpoint(_py: Python, checkpoint: &PyDict) -> PyResult<Self> {
        let id = checkpoint
            .get_item("id")?
            .and_then(|v| v.extract::<String>().ok())
            .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

        let channel_versions = checkpoint
            .get_item("channel_versions")?
            .and_then(|v| v.extract::<HashMap<String, usize>>().ok())
            .unwrap_or_default();

        let versions_seen = checkpoint
            .get_item("versions_seen")?
            .and_then(|v| v.extract::<HashMap<String, HashMap<String, usize>>>().ok())
            .unwrap_or_default();

        let pending_sends = checkpoint
            .get_item("pending_sends")?
            .and_then(|v| v.extract::<Vec<PyObject>>().ok())
            .unwrap_or_default();

        Ok(Self {
            id,
            channel_versions,
            versions_seen,
            pending_writes: Vec::new(),
            pending_sends,
        })
    }

    /// Convert to Python checkpoint dict
    pub fn to_py_checkpoint(&self, py: Python) -> PyResult<PyObject> {
        let checkpoint = PyDict::new(py);
        checkpoint.set_item("id", &self.id)?;
        checkpoint.set_item("channel_versions", self.channel_versions.clone())?;
        checkpoint.set_item("versions_seen", self.versions_seen.clone())?;
        checkpoint.set_item("pending_sends", &self.pending_sends)?;
        Ok(checkpoint.into())
    }
}

/// Main Pregel execution loop
pub struct PregelLoop {
    /// Graph nodes
    nodes: HashMap<String, PregelNode>,
    /// Channels for state management
    channels: HashMap<String, PyObject>,
    /// Current checkpoint
    checkpoint: CheckpointState,
    /// Execution configuration
    config: PregelConfig,
    /// Current step number
    step: usize,
}

impl PregelLoop {
    /// Create a new Pregel execution loop
    pub fn new(
        nodes: HashMap<String, PregelNode>,
        channels: HashMap<String, PyObject>,
        config: PregelConfig,
    ) -> Self {
        let checkpoint_id = uuid::Uuid::new_v4().to_string();
        Self {
            nodes,
            channels,
            checkpoint: CheckpointState::new(checkpoint_id),
            config,
            step: 0,
        }
    }

    /// Create from existing checkpoint (for resuming)
    pub fn from_checkpoint(
        _py: Python,
        nodes: HashMap<String, PregelNode>,
        channels: HashMap<String, PyObject>,
        checkpoint: CheckpointState,
        config: PregelConfig,
    ) -> Self {
        Self {
            nodes,
            channels,
            checkpoint,
            config,
            step: 0,
        }
    }

    /// Execute one superstep
    fn execute_step(&mut self, py: Python) -> PyResult<Vec<TaskWrites>> {
        // Prepare tasks for this step
        let mut tasks = prepare_next_tasks(
            py,
            &self.checkpoint.id,
            &self.checkpoint.channel_versions,
            &self.checkpoint.versions_seen,
            &self.checkpoint.pending_sends,
            &self.nodes,
            self.step,
            true,
        )?;

        if tasks.is_empty() {
            // No tasks to execute - we've reached convergence
            return Ok(Vec::new());
        }

        // Execute all tasks
        let mut task_writes = Vec::new();
        for task in &mut tasks {
            // Execute the task
            match task.execute_with_retry(py) {
                Ok(result) => {
                    // Process the result and extract writes
                    let writes = self.process_task_result(py, task, result)?;
                    task_writes.push(TaskWrites {
                        name: task.name.clone(),
                        writes,
                        triggers: task.triggers.clone(),
                    });
                }
                Err(e) => {
                    // Task failed even after retries
                    return Err(e);
                }
            }
        }

        Ok(task_writes)
    }

    /// Process task result and extract channel writes
    fn process_task_result(
        &self,
        py: Python,
        task: &PregelExecutableTask,
        result: PyObject,
    ) -> PyResult<Vec<(String, PyObject)>> {
        let mut writes = Vec::new();

        // Get the node to check its output channels
        if let Some(node) = self.nodes.get(&task.name) {
            if !node.channels.is_empty() {
                // Node specifies output channels
                if result.as_ref(py).is_instance_of::<PyDict>() {
                    // Result is a dict - extract values for each channel
                    let result_dict = result.downcast::<PyDict>(py)?;
                    for channel_name in &node.channels {
                        if let Some(value) = result_dict.get_item(channel_name)? {
                            writes.push((channel_name.clone(), value.into()));
                        }
                    }
                } else {
                    // Result is a single value - write to all channels
                    for channel_name in &node.channels {
                        writes.push((channel_name.clone(), result.clone_ref(py)));
                    }
                }
            } else {
                // No specific channels - assume result is a dict of channel updates
                if result.as_ref(py).is_instance_of::<PyDict>() {
                    let result_dict = result.downcast::<PyDict>(py)?;
                    for item in result_dict.items() {
                        let (key, value): (String, PyObject) = item.extract()?;
                        writes.push((key, value));
                    }
                }
            }
        }

        // Add accumulated writes from the task
        writes.extend(task.writes.clone());

        Ok(writes)
    }

    /// Main execution loop - invoke pattern
    pub fn invoke(&mut self, py: Python, input: PyObject) -> PyResult<PyObject> {
        // Initialize channels with input
        self.initialize_input(py, input)?;

        // Execute supersteps until convergence or limit
        while self.step < self.config.recursion_limit {
            // Check for interrupt before execution
            if !self.config.interrupt_before.is_empty() {
                let tasks_to_run = prepare_next_tasks(
                    py,
                    &self.checkpoint.id,
                    &self.checkpoint.channel_versions,
                    &self.checkpoint.versions_seen,
                    &self.checkpoint.pending_sends,
                    &self.nodes,
                    self.step,
                    true,
                )?;

                if should_interrupt(
                    &self.checkpoint.channel_versions,
                    &HashMap::new(),
                    &self.config.interrupt_before,
                    &tasks_to_run,
                ) {
                    // Return current state with interrupt marker
                    return self.get_current_state(py);
                }
            }

            // Execute one superstep
            let task_writes = self.execute_step(py)?;

            if task_writes.is_empty() {
                // No more tasks - reached convergence
                break;
            }

            // Apply writes to channels
            apply_writes(
                py,
                &mut self.checkpoint.channel_versions,
                &mut self.checkpoint.versions_seen,
                &mut self.channels,
                &task_writes,
            )?;

            // Check for interrupt after execution
            if !self.config.interrupt_after.is_empty() {
                let tasks_just_ran = prepare_next_tasks(
                    py,
                    &self.checkpoint.id,
                    &self.checkpoint.channel_versions,
                    &self.checkpoint.versions_seen,
                    &self.checkpoint.pending_sends,
                    &self.nodes,
                    self.step,
                    true,
                )?;

                if should_interrupt(
                    &self.checkpoint.channel_versions,
                    &HashMap::new(),
                    &self.config.interrupt_after,
                    &tasks_just_ran,
                ) {
                    return self.get_current_state(py);
                }
            }

            self.step += 1;

            if self.config.debug {
                eprintln!("Step {}: {} tasks executed", self.step, task_writes.len());
            }
        }

        if self.step >= self.config.recursion_limit {
            return Err(PyErr::new::<pyo3::exceptions::PyRecursionError, _>(
                format!("Recursion limit of {} reached", self.config.recursion_limit),
            ));
        }

        // Return final state
        self.get_current_state(py)
    }

    /// Initialize channels with input data
    fn initialize_input(&mut self, py: Python, input: PyObject) -> PyResult<()> {
        // Determine which channels to write input to
        // For now, write to all channels that exist
        if input.as_ref(py).is_instance_of::<PyDict>() {
            let input_dict = input.downcast::<PyDict>(py)?;
            for (key, value) in input_dict.iter() {
                let channel_name: String = key.extract()?;
                if let Some(channel) = self.channels.get_mut(&channel_name) {
                    // Call channel.update([value])
                    if let Ok(update_method) = channel.getattr(py, "update") {
                        let values = PyList::new(py, [value]);
                        update_method.call1(py, (values,))?;

                        // Set initial version
                        self.checkpoint.channel_versions.insert(channel_name, 1);
                    }
                }
            }
        }

        Ok(())
    }

    /// Get current state from all channels
    fn get_current_state(&self, py: Python) -> PyResult<PyObject> {
        let state = PyDict::new(py);

        for (channel_name, channel) in &self.channels {
            // Call channel.get()
            if let Ok(get_method) = channel.getattr(py, "get") {
                match get_method.call0(py) {
                    Ok(value) => {
                        state.set_item(channel_name, value)?;
                    }
                    Err(_) => {
                        // Channel might be empty, skip it
                        continue;
                    }
                }
            }
        }

        Ok(state.into())
    }

    /// Execute with streaming - yields intermediate states
    pub fn stream(&mut self, py: Python, input: PyObject) -> PyResult<Vec<PyObject>> {
        let mut results = Vec::new();

        // Initialize channels with input
        self.initialize_input(py, input)?;

        // Execute supersteps until convergence or limit
        while self.step < self.config.recursion_limit {
            // Execute one superstep
            let task_writes = self.execute_step(py)?;

            if task_writes.is_empty() {
                // No more tasks - reached convergence
                break;
            }

            // Apply writes to channels
            apply_writes(
                py,
                &mut self.checkpoint.channel_versions,
                &mut self.checkpoint.versions_seen,
                &mut self.channels,
                &task_writes,
            )?;

            // Yield current state
            let current_state = self.get_current_state(py)?;
            results.push(current_state);

            self.step += 1;

            if self.config.debug {
                eprintln!("Step {}: {} tasks executed", self.step, task_writes.len());
            }
        }

        if self.step >= self.config.recursion_limit {
            return Err(PyErr::new::<pyo3::exceptions::PyRecursionError, _>(
                format!("Recursion limit of {} reached", self.config.recursion_limit),
            ));
        }

        Ok(results)
    }

    /// Get the current checkpoint
    pub fn get_checkpoint(&self) -> &CheckpointState {
        &self.checkpoint
    }

    /// Get current step number
    pub fn get_step(&self) -> usize {
        self.step
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_checkpoint_state() {
        let checkpoint = CheckpointState::new("test-id".to_string());
        assert_eq!(checkpoint.id, "test-id");
        assert_eq!(checkpoint.channel_versions.len(), 0);
        assert_eq!(checkpoint.versions_seen.len(), 0);
    }

    #[test]
    fn test_pregel_config() {
        let config = PregelConfig::default();
        assert_eq!(config.recursion_limit, 25);
        assert_eq!(config.interrupt_before.len(), 0);
        assert_eq!(config.interrupt_after.len(), 0);
        assert!(!config.debug);
    }
}
