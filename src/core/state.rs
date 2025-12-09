//! Graph state management
//!
//! GraphState manages a collection of named channels that store
//! the current state of the graph execution.

use super::channel::{Channel, ChannelUpdate};
use pyo3::prelude::*;
use std::collections::HashMap;

/// GraphState manages all channels in a graph
///
/// It provides:
/// - Channel lookup by name
/// - Atomic updates to multiple channels
/// - Checkpointing and restoration
pub struct GraphState {
    channels: HashMap<String, Box<dyn Channel>>,
}

impl GraphState {
    /// Create a new empty graph state
    pub fn new() -> Self {
        Self {
            channels: HashMap::new(),
        }
    }

    /// Create graph state with initial channels
    pub fn with_channels(channels: HashMap<String, Box<dyn Channel>>) -> Self {
        Self { channels }
    }

    /// Add a channel to the state
    pub fn add_channel(&mut self, name: String, channel: Box<dyn Channel>) {
        self.channels.insert(name, channel);
    }

    /// Get a reference to a channel by name
    pub fn get_channel(&self, name: &str) -> Option<&dyn Channel> {
        self.channels.get(name).map(|c| c.as_ref())
    }

    /// Get a mutable reference to a channel by name
    pub fn get_channel_mut(&mut self, name: &str) -> Option<&mut dyn Channel> {
        match self.channels.get_mut(name) {
            Some(channel) => Some(&mut **channel),
            None => None,
        }
    }

    /// Get the value from a specific channel
    pub fn get_value(&self, py: Python, channel_name: &str) -> Option<PyObject> {
        self.get_channel(channel_name).and_then(|ch| ch.get(py))
    }

    /// Update a single channel with a value
    pub fn update_channel(
        &mut self,
        py: Python,
        channel_name: &str,
        value: PyObject,
    ) -> PyResult<()> {
        if let Some(channel) = self.get_channel_mut(channel_name) {
            channel.update(py, ChannelUpdate::single(value))
        } else {
            Err(pyo3::exceptions::PyKeyError::new_err(format!(
                "Channel '{}' not found",
                channel_name
            )))
        }
    }

    /// Update multiple channels atomically
    pub fn update_many(&mut self, py: Python, updates: HashMap<String, PyObject>) -> PyResult<()> {
        for (channel_name, value) in updates {
            self.update_channel(py, &channel_name, value)?;
        }
        Ok(())
    }

    /// Check if a channel exists
    pub fn has_channel(&self, name: &str) -> bool {
        self.channels.contains_key(name)
    }

    /// Get all channel names
    pub fn channel_names(&self) -> Vec<String> {
        self.channels.keys().cloned().collect()
    }

    /// Create a checkpoint of all channels
    pub fn checkpoint(&self, py: Python) -> PyResult<HashMap<String, PyObject>> {
        let mut checkpoint = HashMap::new();
        for (name, channel) in &self.channels {
            checkpoint.insert(name.clone(), channel.checkpoint(py)?);
        }
        Ok(checkpoint)
    }

    /// Restore state from a checkpoint
    pub fn from_checkpoint(
        &mut self,
        py: Python,
        checkpoint: HashMap<String, PyObject>,
    ) -> PyResult<()> {
        for (name, data) in checkpoint {
            if let Some(channel) = self.get_channel_mut(&name) {
                channel.from_checkpoint(py, data)?;
            }
        }
        Ok(())
    }

    /// Get the number of channels
    pub fn len(&self) -> usize {
        self.channels.len()
    }

    /// Check if the state is empty
    pub fn is_empty(&self) -> bool {
        self.channels.is_empty()
    }
}

impl Default for GraphState {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for GraphState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GraphState")
            .field("channel_count", &self.channels.len())
            .field("channels", &self.channels.keys().collect::<Vec<_>>())
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::channel::LastValueChannel;

    #[test]
    fn test_graph_state_creation() {
        let state = GraphState::new();
        assert_eq!(state.len(), 0);
        assert!(state.is_empty());
    }

    #[test]
    fn test_add_channel() {
        pyo3::prepare_freethreaded_python();

        let mut state = GraphState::new();
        let channel = Box::new(LastValueChannel::new()) as Box<dyn Channel>;
        state.add_channel("test".to_string(), channel);

        assert_eq!(state.len(), 1);
        assert!(state.has_channel("test"));
        assert!(!state.has_channel("missing"));
    }

    #[test]
    fn test_update_and_get() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut state = GraphState::new();
            let channel = Box::new(LastValueChannel::new()) as Box<dyn Channel>;
            state.add_channel("value".to_string(), channel);

            // Update the channel
            let value = 42.to_object(py);
            state.update_channel(py, "value", value).unwrap();

            // Retrieve the value
            let retrieved = state.get_value(py, "value").unwrap();
            assert_eq!(retrieved.extract::<i32>(py).unwrap(), 42);
        });
    }

    #[test]
    fn test_update_many() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut state = GraphState::new();
            state.add_channel("a".to_string(), Box::new(LastValueChannel::new()));
            state.add_channel("b".to_string(), Box::new(LastValueChannel::new()));

            // Update multiple channels
            let mut updates = HashMap::new();
            updates.insert("a".to_string(), 1.to_object(py));
            updates.insert("b".to_string(), 2.to_object(py));

            state.update_many(py, updates).unwrap();

            // Check both values
            assert_eq!(
                state
                    .get_value(py, "a")
                    .unwrap()
                    .extract::<i32>(py)
                    .unwrap(),
                1
            );
            assert_eq!(
                state
                    .get_value(py, "b")
                    .unwrap()
                    .extract::<i32>(py)
                    .unwrap(),
                2
            );
        });
    }

    #[test]
    fn test_checkpoint_restore() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut state = GraphState::new();
            state.add_channel("value".to_string(), Box::new(LastValueChannel::new()));

            // Set a value
            state.update_channel(py, "value", 42.to_object(py)).unwrap();

            // Create checkpoint
            let checkpoint = state.checkpoint(py).unwrap();

            // Create new state and restore
            let mut new_state = GraphState::new();
            new_state.add_channel("value".to_string(), Box::new(LastValueChannel::new()));
            new_state.from_checkpoint(py, checkpoint).unwrap();

            // Check restored value
            let retrieved = new_state.get_value(py, "value").unwrap();
            assert_eq!(retrieved.extract::<i32>(py).unwrap(), 42);
        });
    }

    #[test]
    fn test_channel_names() {
        let mut state = GraphState::new();
        state.add_channel("a".to_string(), Box::new(LastValueChannel::new()));
        state.add_channel("b".to_string(), Box::new(LastValueChannel::new()));
        state.add_channel("c".to_string(), Box::new(LastValueChannel::new()));

        let mut names = state.channel_names();
        names.sort();

        assert_eq!(names, vec!["a", "b", "c"]);
    }
}
