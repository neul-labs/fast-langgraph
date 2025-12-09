//! Channel implementations for state management
//!
//! Channels are the core state storage mechanism in LangGraph.
//! They store values that flow between nodes during graph execution.

use pyo3::prelude::*;
use std::fmt;

/// Represents an update to be applied to a channel
#[derive(Clone)]
pub struct ChannelUpdate {
    pub values: Vec<PyObject>,
}

impl ChannelUpdate {
    pub fn new(values: Vec<PyObject>) -> Self {
        Self { values }
    }

    pub fn single(value: PyObject) -> Self {
        Self {
            values: vec![value],
        }
    }
}

/// Base trait for all channel types
///
/// Channels provide:
/// - `update`: Apply new values to the channel
/// - `get`: Retrieve the current value(s)
/// - `checkpoint`: Serialize for persistence
/// - `from_checkpoint`: Restore from serialized state
#[allow(clippy::wrong_self_convention)]
pub trait Channel: Send + Sync {
    /// Update the channel with new values
    fn update(&mut self, py: Python, update: ChannelUpdate) -> PyResult<()>;

    /// Get the current value from the channel
    /// Returns None if the channel is empty
    fn get(&self, py: Python) -> Option<PyObject>;

    /// Check if the channel has a value
    fn is_available(&self) -> bool;

    /// Create a checkpoint of the current state
    fn checkpoint(&self, py: Python) -> PyResult<PyObject>;

    /// Restore from a checkpoint
    fn from_checkpoint(&mut self, py: Python, data: PyObject) -> PyResult<()>;

    /// Get a debug representation
    fn debug_repr(&self) -> String;
}

/// LastValue channel - stores only the most recent value
///
/// This is the most common channel type. When updated, it replaces
/// the previous value with the new one.
pub struct LastValueChannel {
    value: Option<PyObject>,
}

impl LastValueChannel {
    pub fn new() -> Self {
        Self { value: None }
    }

    pub fn with_value(value: PyObject) -> Self {
        Self { value: Some(value) }
    }
}

impl Default for LastValueChannel {
    fn default() -> Self {
        Self::new()
    }
}

impl Channel for LastValueChannel {
    fn update(&mut self, _py: Python, update: ChannelUpdate) -> PyResult<()> {
        if update.values.is_empty() {
            return Ok(());
        }

        // For LastValue, we only keep the last value in the update
        self.value = Some(update.values.into_iter().last().unwrap());
        Ok(())
    }

    fn get(&self, py: Python) -> Option<PyObject> {
        self.value.as_ref().map(|v| v.clone_ref(py))
    }

    fn is_available(&self) -> bool {
        self.value.is_some()
    }

    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        match &self.value {
            Some(val) => Ok(val.clone_ref(py)),
            None => Ok(py.None()),
        }
    }

    fn from_checkpoint(&mut self, py: Python, data: PyObject) -> PyResult<()> {
        if data.is_none(py) {
            self.value = None;
        } else {
            self.value = Some(data);
        }
        Ok(())
    }

    fn debug_repr(&self) -> String {
        format!("LastValueChannel(has_value={})", self.value.is_some())
    }
}

impl fmt::Debug for LastValueChannel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.debug_repr())
    }
}

/// Topic channel - accumulates values over time
///
/// This channel stores a list of values. Each update appends to the list
/// (or replaces it, depending on configuration).
pub struct TopicChannel {
    values: Vec<PyObject>,
    accumulate: bool,
}

impl TopicChannel {
    pub fn new(accumulate: bool) -> Self {
        Self {
            values: Vec::new(),
            accumulate,
        }
    }

    pub fn with_values(values: Vec<PyObject>, accumulate: bool) -> Self {
        Self { values, accumulate }
    }
}

impl Channel for TopicChannel {
    fn update(&mut self, _py: Python, update: ChannelUpdate) -> PyResult<()> {
        if update.values.is_empty() {
            return Ok(());
        }

        if self.accumulate {
            // Append all new values
            self.values.extend(update.values);
        } else {
            // Replace all values
            self.values = update.values;
        }

        Ok(())
    }

    fn get(&self, py: Python) -> Option<PyObject> {
        if self.values.is_empty() {
            None
        } else {
            // Return the list of all values
            Some(pyo3::types::PyList::new(py, &self.values).to_object(py))
        }
    }

    fn is_available(&self) -> bool {
        !self.values.is_empty()
    }

    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        Ok(pyo3::types::PyList::new(py, &self.values).to_object(py))
    }

    fn from_checkpoint(&mut self, py: Python, data: PyObject) -> PyResult<()> {
        if data.is_none(py) {
            self.values.clear();
        } else {
            // Extract list from PyObject
            let list: &pyo3::types::PyList = data.extract(py)?;
            self.values = list.iter().map(|item| item.to_object(py)).collect();
        }
        Ok(())
    }

    fn debug_repr(&self) -> String {
        format!(
            "TopicChannel(count={}, accumulate={})",
            self.values.len(),
            self.accumulate
        )
    }
}

impl fmt::Debug for TopicChannel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.debug_repr())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_last_value_channel() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut channel = LastValueChannel::new();

            // Initially empty
            assert!(!channel.is_available());
            assert!(channel.get(py).is_none());

            // Update with a value
            let value = 42.to_object(py);
            channel
                .update(py, ChannelUpdate::single(value.clone_ref(py)))
                .unwrap();

            assert!(channel.is_available());
            let retrieved = channel.get(py).unwrap();
            assert_eq!(retrieved.extract::<i32>(py).unwrap(), 42);

            // Update with another value - should replace
            let new_value = 84.to_object(py);
            channel
                .update(py, ChannelUpdate::single(new_value))
                .unwrap();

            let retrieved = channel.get(py).unwrap();
            assert_eq!(retrieved.extract::<i32>(py).unwrap(), 84);

            // Test checkpoint/restore
            let checkpoint = channel.checkpoint(py).unwrap();
            let mut new_channel = LastValueChannel::new();
            new_channel.from_checkpoint(py, checkpoint).unwrap();

            assert!(new_channel.is_available());
            assert_eq!(new_channel.get(py).unwrap().extract::<i32>(py).unwrap(), 84);
        });
    }

    #[test]
    fn test_topic_channel_accumulate() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut channel = TopicChannel::new(true);

            // Initially empty
            assert!(!channel.is_available());

            // Update with values
            let values = vec![1.to_object(py), 2.to_object(py), 3.to_object(py)];
            channel.update(py, ChannelUpdate::new(values)).unwrap();

            assert!(channel.is_available());

            // Update with more values - should accumulate
            let more_values = vec![4.to_object(py), 5.to_object(py)];
            channel.update(py, ChannelUpdate::new(more_values)).unwrap();

            // Should have all 5 values
            let result = channel.get(py).unwrap();
            let list = result.downcast_bound::<pyo3::types::PyList>(py).unwrap();
            assert_eq!(list.len(), 5);

            // Test checkpoint
            let checkpoint = channel.checkpoint(py).unwrap();
            let mut new_channel = TopicChannel::new(true);
            new_channel.from_checkpoint(py, checkpoint).unwrap();

            assert!(new_channel.is_available());
            let restored = new_channel.get(py).unwrap();
            let restored_list = restored.downcast_bound::<pyo3::types::PyList>(py).unwrap();
            assert_eq!(restored_list.len(), 5);
        });
    }

    #[test]
    fn test_topic_channel_replace() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut channel = TopicChannel::new(false); // accumulate=false

            // Update with initial values
            let values = vec![1.to_object(py), 2.to_object(py)];
            channel.update(py, ChannelUpdate::new(values)).unwrap();

            // Update with new values - should replace
            let new_values = vec![3.to_object(py), 4.to_object(py)];
            channel.update(py, ChannelUpdate::new(new_values)).unwrap();

            // Should only have the latest 2 values
            let result = channel.get(py).unwrap();
            let list = result.downcast_bound::<pyo3::types::PyList>(py).unwrap();
            assert_eq!(list.len(), 2);
            assert_eq!(list.get_item(0).unwrap().extract::<i32>().unwrap(), 3);
            assert_eq!(list.get_item(1).unwrap().extract::<i32>().unwrap(), 4);
        });
    }
}
