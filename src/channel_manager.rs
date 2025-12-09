//! Channel Manager
//!
//! This module provides utilities for managing channel state during execution.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

/// Manages channel operations during graph execution
pub struct ChannelManager {
    /// All channels in the graph
    channels: HashMap<String, PyObject>,
}

impl ChannelManager {
    /// Create a new channel manager
    pub fn new(channels: HashMap<String, PyObject>) -> Self {
        Self { channels }
    }

    /// Read from a single channel
    pub fn read_channel(&self, py: Python, channel_name: &str) -> PyResult<Option<PyObject>> {
        if let Some(channel) = self.channels.get(channel_name) {
            // Call channel.get()
            if let Ok(get_method) = channel.getattr(py, "get") {
                match get_method.call0(py) {
                    Ok(value) => Ok(Some(value)),
                    Err(_) => Ok(None), // Channel is empty
                }
            } else {
                Ok(None)
            }
        } else {
            Ok(None)
        }
    }

    /// Read from multiple channels
    pub fn read_channels(
        &self,
        py: Python,
        channel_names: &[String],
    ) -> PyResult<HashMap<String, PyObject>> {
        let mut result = HashMap::new();

        for channel_name in channel_names {
            if let Some(value) = self.read_channel(py, channel_name)? {
                result.insert(channel_name.clone(), value);
            }
        }

        Ok(result)
    }

    /// Read all channels
    pub fn read_all_channels(&self, py: Python) -> PyResult<HashMap<String, PyObject>> {
        let channel_names: Vec<String> = self.channels.keys().cloned().collect();
        self.read_channels(py, &channel_names)
    }

    /// Write to a channel
    pub fn write_channel(
        &mut self,
        py: Python,
        channel_name: &str,
        value: PyObject,
    ) -> PyResult<bool> {
        if let Some(channel) = self.channels.get_mut(channel_name) {
            // Call channel.update([value])
            if let Ok(update_method) = channel.getattr(py, "update") {
                let values = PyList::new(py, &[value]);
                let updated = update_method.call1(py, (values,))?;
                Ok(updated.extract(py).unwrap_or(true))
            } else {
                Ok(false)
            }
        } else {
            Ok(false)
        }
    }

    /// Write to multiple channels
    pub fn write_channels(
        &mut self,
        py: Python,
        writes: &[(String, PyObject)],
    ) -> PyResult<Vec<String>> {
        let mut updated_channels = Vec::new();

        for (channel_name, value) in writes {
            if self.write_channel(py, channel_name, value.clone_ref(py))? {
                updated_channels.push(channel_name.clone());
            }
        }

        Ok(updated_channels)
    }

    /// Get a mutable reference to channels
    pub fn channels_mut(&mut self) -> &mut HashMap<String, PyObject> {
        &mut self.channels
    }

    /// Get an immutable reference to channels
    pub fn channels(&self) -> &HashMap<String, PyObject> {
        &self.channels
    }

    /// Check if a channel exists
    pub fn has_channel(&self, channel_name: &str) -> bool {
        self.channels.contains_key(channel_name)
    }

    /// Get channel count
    pub fn channel_count(&self) -> usize {
        self.channels.len()
    }

    /// Create channel values dict for output
    pub fn to_values_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);

        for (channel_name, channel) in &self.channels {
            if let Ok(get_method) = channel.getattr(py, "get") {
                match get_method.call0(py) {
                    Ok(value) => {
                        dict.set_item(channel_name, value)?;
                    }
                    Err(_) => {
                        // Skip empty channels
                        continue;
                    }
                }
            }
        }

        Ok(dict.into())
    }

    /// Get channel value or default
    pub fn get_channel_or_default(
        &self,
        py: Python,
        channel_name: &str,
        default: PyObject,
    ) -> PyResult<PyObject> {
        match self.read_channel(py, channel_name)? {
            Some(value) => Ok(value),
            None => Ok(default),
        }
    }
}

/// Helper function to create channel manager from Python dict
pub fn create_channel_manager_from_dict(
    _py: Python,
    channels_dict: &PyDict,
) -> PyResult<ChannelManager> {
    let mut channels = HashMap::new();

    for (key, value) in channels_dict.iter() {
        let channel_name: String = key.extract()?;
        channels.insert(channel_name, value.into());
    }

    Ok(ChannelManager::new(channels))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_channel_manager_creation() {
        let channels = HashMap::new();
        let manager = ChannelManager::new(channels);
        assert_eq!(manager.channel_count(), 0);
    }

    #[test]
    fn test_has_channel() {
        let mut channels = HashMap::new();
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let value = py.None();
            channels.insert("test_channel".to_string(), value);

            let manager = ChannelManager::new(channels);
            assert!(manager.has_channel("test_channel"));
            assert!(!manager.has_channel("nonexistent"));
        });
    }
}
