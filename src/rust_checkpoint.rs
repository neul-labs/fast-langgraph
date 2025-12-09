use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Fast checkpoint data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckpointData {
    /// Channel values at this checkpoint
    pub channel_values: HashMap<String, Vec<u8>>, // Serialized values

    /// Channel versions
    pub channel_versions: HashMap<String, usize>,

    /// Versions seen by each task
    pub versions_seen: HashMap<String, HashMap<String, usize>>,

    /// Pending writes
    pub pending_writes: Vec<(String, String, Vec<u8>)>, // (task_id, channel, value)

    /// Current step number
    pub step: usize,
}

/// High-performance checkpoint implementation using MessagePack
#[pyclass(name = "RustCheckpointer")]
pub struct RustCheckpointer {
    /// In-memory checkpoint storage (thread_id -> checkpoint_id -> data)
    checkpoints: HashMap<String, HashMap<String, Vec<u8>>>,
}

#[pymethods]
impl RustCheckpointer {
    #[new]
    fn new() -> Self {
        RustCheckpointer {
            checkpoints: HashMap::new(),
        }
    }

    /// Save a checkpoint
    ///
    /// Args:
    ///     thread_id: Thread/conversation identifier
    ///     checkpoint_id: Unique checkpoint identifier
    ///     checkpoint: Checkpoint data dictionary
    ///
    /// Returns:
    ///     True if successful
    fn put(
        &mut self,
        py: Python,
        thread_id: String,
        checkpoint_id: String,
        checkpoint: &PyDict,
    ) -> PyResult<bool> {
        // Extract checkpoint data
        let channel_values = self.extract_channel_values(py, checkpoint)?;
        let channel_versions = self.extract_versions(checkpoint, "channel_versions")?;
        let versions_seen = self.extract_versions_seen(checkpoint)?;
        let step = checkpoint
            .get_item("step")?
            .and_then(|v| v.extract::<usize>().ok())
            .unwrap_or(0);

        // Create checkpoint data
        let checkpoint_data = CheckpointData {
            channel_values,
            channel_versions,
            versions_seen,
            pending_writes: Vec::new(),
            step,
        };

        // Serialize using MessagePack (much faster than pickle!)
        let serialized = rmp_serde::to_vec(&checkpoint_data).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {}", e))
        })?;

        // Store in memory
        self.checkpoints
            .entry(thread_id)
            .or_default()
            .insert(checkpoint_id, serialized);

        Ok(true)
    }

    /// Load a checkpoint
    ///
    /// Args:
    ///     thread_id: Thread/conversation identifier
    ///     checkpoint_id: Unique checkpoint identifier
    ///
    /// Returns:
    ///     Checkpoint dictionary or None if not found
    fn get(
        &self,
        py: Python,
        thread_id: String,
        checkpoint_id: String,
    ) -> PyResult<Option<PyObject>> {
        // Retrieve from storage
        let serialized = match self.checkpoints.get(&thread_id) {
            Some(thread_checkpoints) => match thread_checkpoints.get(&checkpoint_id) {
                Some(data) => data,
                None => return Ok(None),
            },
            None => return Ok(None),
        };

        // Deserialize using MessagePack
        let checkpoint_data: CheckpointData = rmp_serde::from_slice(serialized).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Deserialization error: {}", e))
        })?;

        // Convert back to Python dict
        let result = self.checkpoint_data_to_py(py, &checkpoint_data)?;

        Ok(Some(result))
    }

    /// List all checkpoint IDs for a thread
    fn list_checkpoints(&self, thread_id: String) -> Vec<String> {
        self.checkpoints
            .get(&thread_id)
            .map(|thread_checkpoints| thread_checkpoints.keys().cloned().collect())
            .unwrap_or_default()
    }

    /// Delete a checkpoint
    fn delete(&mut self, thread_id: String, checkpoint_id: String) -> bool {
        self.checkpoints
            .get_mut(&thread_id)
            .and_then(|thread_checkpoints| thread_checkpoints.remove(&checkpoint_id))
            .is_some()
    }

    /// Clear all checkpoints for a thread
    fn clear_thread(&mut self, thread_id: String) -> bool {
        self.checkpoints.remove(&thread_id).is_some()
    }

    /// Get statistics about stored checkpoints
    fn stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();

        let total_threads = self.checkpoints.len();
        let total_checkpoints: usize = self.checkpoints.values().map(|c| c.len()).sum();
        let total_bytes: usize = self
            .checkpoints
            .values()
            .flat_map(|c| c.values())
            .map(|v| v.len())
            .sum();

        stats.insert("total_threads".to_string(), total_threads);
        stats.insert("total_checkpoints".to_string(), total_checkpoints);
        stats.insert("total_bytes".to_string(), total_bytes);

        stats
    }
}

impl RustCheckpointer {
    /// Extract channel values from Python checkpoint dict
    fn extract_channel_values(
        &self,
        py: Python,
        checkpoint: &PyDict,
    ) -> PyResult<HashMap<String, Vec<u8>>> {
        let mut channel_values = HashMap::new();

        if let Ok(Some(channels)) = checkpoint.get_item("channel_values") {
            if let Ok(channels_dict) = channels.downcast::<PyDict>() {
                for (key, value) in channels_dict.iter() {
                    let key_str: String = key.extract()?;

                    // Serialize the value using pickle
                    let pickle = py.import("pickle")?;
                    let dumps = pickle.getattr("dumps")?;
                    let serialized: &PyBytes = dumps.call1((value,))?.downcast()?;

                    channel_values.insert(key_str, serialized.as_bytes().to_vec());
                }
            }
        }

        Ok(channel_values)
    }

    /// Extract version dict
    fn extract_versions(&self, checkpoint: &PyDict, key: &str) -> PyResult<HashMap<String, usize>> {
        let mut versions = HashMap::new();

        if let Ok(Some(versions_obj)) = checkpoint.get_item(key) {
            if let Ok(versions_dict) = versions_obj.downcast::<PyDict>() {
                for (k, v) in versions_dict.iter() {
                    let key_str: String = k.extract()?;
                    let version: usize = v.extract()?;
                    versions.insert(key_str, version);
                }
            }
        }

        Ok(versions)
    }

    /// Extract versions_seen nested dict
    fn extract_versions_seen(
        &self,
        checkpoint: &PyDict,
    ) -> PyResult<HashMap<String, HashMap<String, usize>>> {
        let mut versions_seen = HashMap::new();

        if let Ok(Some(vs_obj)) = checkpoint.get_item("versions_seen") {
            if let Ok(vs_dict) = vs_obj.downcast::<PyDict>() {
                for (task, channels) in vs_dict.iter() {
                    let task_str: String = task.extract()?;
                    let mut channel_versions = HashMap::new();

                    if let Ok(channels_dict) = channels.downcast::<PyDict>() {
                        for (chan, ver) in channels_dict.iter() {
                            let chan_str: String = chan.extract()?;
                            let version: usize = ver.extract()?;
                            channel_versions.insert(chan_str, version);
                        }
                    }

                    versions_seen.insert(task_str, channel_versions);
                }
            }
        }

        Ok(versions_seen)
    }

    /// Convert checkpoint data back to Python dict
    fn checkpoint_data_to_py(&self, py: Python, data: &CheckpointData) -> PyResult<PyObject> {
        let result = PyDict::new(py);

        // Deserialize channel values
        let channel_values_dict = PyDict::new(py);
        let pickle = py.import("pickle")?;
        let loads = pickle.getattr("loads")?;

        for (key, value_bytes) in &data.channel_values {
            let py_bytes = PyBytes::new(py, value_bytes);
            let value = loads.call1((py_bytes,))?;
            channel_values_dict.set_item(key, value)?;
        }
        result.set_item("channel_values", channel_values_dict)?;

        // Convert channel versions
        let channel_versions_dict = PyDict::new(py);
        for (key, version) in &data.channel_versions {
            channel_versions_dict.set_item(key, version)?;
        }
        result.set_item("channel_versions", channel_versions_dict)?;

        // Convert versions_seen
        let versions_seen_dict = PyDict::new(py);
        for (task, channels) in &data.versions_seen {
            let channels_dict = PyDict::new(py);
            for (chan, ver) in channels {
                channels_dict.set_item(chan, ver)?;
            }
            versions_seen_dict.set_item(task, channels_dict)?;
        }
        result.set_item("versions_seen", versions_seen_dict)?;

        // Add step
        result.set_item("step", data.step)?;

        Ok(result.into())
    }
}

/// Register checkpoint module
pub fn register_checkpoint(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustCheckpointer>()?;
    Ok(())
}
