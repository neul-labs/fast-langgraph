use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyType};
use std::collections::HashMap;

/// Marker trait for values that can be missing
#[allow(dead_code)]
const MISSING_MARKER: i64 = i64::MIN;

/// Fast Rust implementation of LastValue channel
///
/// This provides a drop-in replacement for langgraph.channels.LastValue
/// with significantly better performance for update operations.
#[pyclass(name = "RustLastValue")]
#[derive(Clone)]
pub struct RustLastValue {
    #[pyo3(get, set)]
    pub key: String,

    /// Type hint (for compatibility, not enforced in Rust)
    typ: PyObject,

    /// The stored value (None represents MISSING)
    value: Option<PyObject>,
}

#[pymethods]
impl RustLastValue {
    #[new]
    #[pyo3(signature = (typ, key = String::new()))]
    fn new(typ: PyObject, key: String) -> Self {
        RustLastValue {
            key,
            typ,
            value: None,
        }
    }

    /// Update the channel with new values
    /// Returns True if the channel was updated, False if no values provided
    fn update(&mut self, _py: Python, values: &PyList) -> PyResult<bool> {
        let len = values.len();

        if len == 0 {
            return Ok(false);
        }

        if len != 1 {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "At key '{}': Can receive only one value per step. Use an Annotated key to handle multiple values.",
                self.key
            )));
        }

        // Store the last (and only) value
        self.value = Some(values.get_item(len - 1)?.into());
        Ok(true)
    }

    /// Get the current value
    fn get(&self, py: Python) -> PyResult<PyObject> {
        match &self.value {
            Some(v) => Ok(v.clone_ref(py)),
            None => Err(pyo3::exceptions::PyValueError::new_err(
                "EmptyChannelError: Channel has no value",
            )),
        }
    }

    /// Check if channel has a value
    fn is_available(&self) -> bool {
        self.value.is_some()
    }

    /// Create a checkpoint of the current value
    fn checkpoint(&self, py: Python) -> PyResult<PyObject> {
        match &self.value {
            Some(v) => Ok(v.clone_ref(py)),
            None => Ok(py.None()),
        }
    }

    /// Create a copy of this channel
    fn copy(&self, py: Python) -> PyResult<Py<Self>> {
        Py::new(
            py,
            RustLastValue {
                key: self.key.clone(),
                typ: self.typ.clone_ref(py),
                value: self.value.as_ref().map(|v| v.clone_ref(py)),
            },
        )
    }

    /// Restore from checkpoint
    #[classmethod]
    fn from_checkpoint(
        _cls: &PyType,
        py: Python,
        typ: PyObject,
        checkpoint: PyObject,
        key: Option<String>,
    ) -> PyResult<Py<Self>> {
        let mut channel = RustLastValue::new(typ, key.unwrap_or_default());

        // Check if checkpoint is None (MISSING)
        if !checkpoint.is_none(py) {
            channel.value = Some(checkpoint);
        }

        Py::new(py, channel)
    }

    /// Consume the channel (no-op for LastValue)
    fn consume(&mut self) -> bool {
        false
    }

    /// Finish the channel (no-op for LastValue)
    fn finish(&mut self) -> bool {
        false
    }

    /// Get the ValueType property (for compatibility)
    #[getter]
    fn value_type(&self, py: Python) -> PyResult<PyObject> {
        Ok(self.typ.clone_ref(py))
    }

    /// Get the UpdateType property (for compatibility)
    #[getter]
    fn update_type(&self, py: Python) -> PyResult<PyObject> {
        Ok(self.typ.clone_ref(py))
    }
}

/// Batch channel update manager for fast write operations
#[pyclass(name = "FastChannelUpdater")]
pub struct FastChannelUpdater {
    /// Tracks which channels were updated
    updated: HashMap<String, bool>,
}

#[pymethods]
impl FastChannelUpdater {
    #[new]
    fn new() -> Self {
        FastChannelUpdater {
            updated: HashMap::new(),
        }
    }

    /// Apply a batch of writes to RustLastValue channels
    ///
    /// Args:
    ///     channels: Dict of channel_name -> channel object
    ///     pending_writes: Dict of channel_name -> [values]
    ///
    /// Returns:
    ///     Set of channel names that were updated
    fn apply_writes_batch(
        &mut self,
        py: Python,
        channels: &PyDict,
        pending_writes: &PyDict,
    ) -> PyResult<Vec<String>> {
        self.updated.clear();
        let mut updated_channels = Vec::new();

        for (chan_name, values) in pending_writes.iter() {
            let chan_name_str: String = chan_name.extract()?;

            // Get the channel
            if let Ok(Some(channel)) = channels.get_item(chan_name) {
                // Check if it's a RustLastValue channel
                if let Ok(mut rust_chan) = channel.extract::<PyRefMut<RustLastValue>>() {
                    // Fast path: Rust channel
                    let values_list: &PyList = values.downcast()?;
                    if rust_chan.update(py, values_list)? {
                        updated_channels.push(chan_name_str.clone());
                    }
                } else {
                    // Fallback: Python channel - call its update method
                    let update_method = channel.getattr("update")?;
                    let result = update_method.call1((values,))?;

                    if let Ok(updated) = result.extract::<bool>() {
                        if updated {
                            updated_channels.push(chan_name_str.clone());
                        }
                    }
                }
            }
        }

        Ok(updated_channels)
    }

    /// Get all channels that were updated in last batch
    fn get_updated(&self) -> Vec<String> {
        self.updated.keys().cloned().collect()
    }
}

/// Register the fast channels module
pub fn register_fast_channels(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustLastValue>()?;
    m.add_class::<FastChannelUpdater>()?;
    Ok(())
}
