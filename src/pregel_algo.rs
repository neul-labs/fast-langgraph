//! Pregel Algorithm - core execution logic
//!
//! This module implements the key algorithms for Pregel execution:
//! - prepare_next_tasks: Determines which nodes to execute next
//! - apply_writes: Applies task outputs to channels

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

use crate::pregel_node::{PregelExecutableTask, PregelNode};
use crate::send::process_pending_sends;

/// Result of task execution with writes
pub struct TaskWrites {
    pub name: String,
    pub writes: Vec<(String, PyObject)>,
    pub triggers: Vec<String>,
}

/// Prepare next tasks to execute based on current checkpoint state
#[allow(clippy::too_many_arguments)]
pub fn prepare_next_tasks(
    py: Python,
    checkpoint_id: &str,
    channel_versions: &HashMap<String, usize>,
    versions_seen: &HashMap<String, HashMap<String, usize>>,
    pending_sends: &[PyObject],
    nodes: &HashMap<String, PregelNode>,
    step: usize,
    for_execution: bool,
) -> PyResult<Vec<PregelExecutableTask>> {
    let mut tasks = Vec::new();

    // First, process pending sends (dynamic task creation)
    let sends = process_pending_sends(py, pending_sends)?;
    for send in sends {
        // Check if the target node exists
        if let Some(node) = nodes.get(&send.node) {
            let task_id = format!("{}:{}:send:{}", checkpoint_id, step, send.node);

            // Get the runnable
            let proc = node.get_runnable(py)?;

            // Create config
            let config = if let Some(ref node_config) = node.config {
                node_config.clone_ref(py)
            } else {
                PyDict::new(py).into()
            };

            let task = PregelExecutableTask {
                name: send.node.clone(),
                input: send.arg,
                proc,
                writes: Vec::new(),
                config,
                triggers: vec!["__send__".to_string()],
                retry_policy: node.retry_policy.clone(),
                id: task_id,
            };

            tasks.push(task);
        }
    }

    // Find all nodes that should execute based on channel versions
    for (node_name, node) in nodes {
        if node.should_run(channel_versions, versions_seen) {
            // This node should run - create a task for it

            // Prepare input by reading from trigger channels
            let input = prepare_node_input(py, node, channel_versions)?;

            if for_execution {
                // Create executable task
                let task_id = format!("{}:{}:{}", checkpoint_id, step, node_name);

                // Get the actual runnable
                let proc = node.get_runnable(py)?;

                // Create config
                let config = if let Some(ref node_config) = node.config {
                    node_config.clone_ref(py)
                } else {
                    PyDict::new(py).into()
                };

                let task = PregelExecutableTask {
                    name: node_name.clone(),
                    input,
                    proc,
                    writes: Vec::new(),
                    config,
                    triggers: node.triggers.clone(),
                    retry_policy: node.retry_policy.clone(),
                    id: task_id,
                };

                tasks.push(task);
            }
        }
    }

    Ok(tasks)
}

/// Prepare input for a node by reading its trigger channels
fn prepare_node_input(
    py: Python,
    _node: &PregelNode,
    _channel_versions: &HashMap<String, usize>,
) -> PyResult<PyObject> {
    // For now, create an empty dict as input
    // In a full implementation, this would read from channels
    Ok(PyDict::new(py).into())
}

/// Apply task writes to channels and update checkpoint
pub fn apply_writes(
    py: Python,
    checkpoint_versions: &mut HashMap<String, usize>,
    versions_seen: &mut HashMap<String, HashMap<String, usize>>,
    channels: &mut HashMap<String, PyObject>,
    tasks: &[TaskWrites],
) -> PyResult<()> {
    // Update versions_seen for all tasks
    for task in tasks {
        let task_seen = versions_seen.entry(task.name.clone()).or_default();

        for trigger in &task.triggers {
            if let Some(&version) = checkpoint_versions.get(trigger) {
                task_seen.insert(trigger.clone(), version);
            }
        }
    }

    // Find the current maximum version
    let max_version = checkpoint_versions.values().max().copied().unwrap_or(0);

    // Group writes by channel
    let mut writes_by_channel: HashMap<String, Vec<PyObject>> = HashMap::new();
    for task in tasks {
        for (channel, value) in &task.writes {
            writes_by_channel
                .entry(channel.clone())
                .or_default()
                .push(value.clone_ref(py));
        }
    }

    // Apply writes to each channel
    for (channel_name, values) in &writes_by_channel {
        if let Some(channel) = channels.get_mut(channel_name) {
            // Call channel.update(values)
            if let Ok(update_method) = channel.getattr(py, "update") {
                let values_list = PyList::new(py, values.as_slice());
                let updated = update_method.call1(py, (values_list,))?;

                // Check if channel was updated (returns True/False)
                let was_updated: bool = updated.extract(py).unwrap_or(true);

                if was_updated {
                    // Increment version for this channel
                    let new_version = max_version + 1;
                    checkpoint_versions.insert(channel_name.clone(), new_version);
                }
            }
        }
    }

    // Notify channels that weren't updated (for consume logic)
    for (channel_name, channel) in channels.iter() {
        if !writes_by_channel.contains_key(channel_name) {
            // Call channel.update([])
            if let Ok(update_method) = channel.getattr(py, "update") {
                let empty_list = PyList::empty(py);
                let updated = update_method.call1(py, (empty_list,))?;

                let was_updated: bool = updated.extract(py).unwrap_or(false);
                if was_updated {
                    let new_version = max_version + 1;
                    checkpoint_versions.insert(channel_name.clone(), new_version);
                }
            }
        }
    }

    Ok(())
}

/// Check if execution should interrupt at this point
pub fn should_interrupt(
    checkpoint_versions: &HashMap<String, usize>,
    versions_seen_interrupt: &HashMap<String, usize>,
    interrupt_nodes: &[String],
    tasks: &[PregelExecutableTask],
) -> bool {
    // Check if any channel has been updated since last interrupt
    let any_channel_updated = checkpoint_versions.iter().any(|(chan, &version)| {
        versions_seen_interrupt
            .get(chan)
            .map(|&seen_version| version > seen_version)
            .unwrap_or(true)
    });

    if !any_channel_updated {
        return false;
    }

    // Check if any triggered node is in interrupt_nodes list
    let should_interrupt_node = tasks
        .iter()
        .any(|task| interrupt_nodes.is_empty() || interrupt_nodes.contains(&task.name));

    any_channel_updated && should_interrupt_node
}

/// Increment version counter
pub fn increment_version(current: Option<usize>) -> usize {
    current.map(|v| v + 1).unwrap_or(1)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_increment_version() {
        assert_eq!(increment_version(None), 1);
        assert_eq!(increment_version(Some(0)), 1);
        assert_eq!(increment_version(Some(5)), 6);
    }
}
