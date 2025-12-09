//! Stream Output Modes
//!
//! This module defines different streaming output modes for Pregel execution.

use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

/// Stream mode determines what information is yielded during streaming execution
#[derive(Clone, Debug, PartialEq, Eq, Default)]
pub enum StreamMode {
    /// Emit all channel values after each step
    #[default]
    Values,
    /// Emit only the updates (node outputs) for each step
    Updates,
    /// Emit debug information including task execution details
    Debug,
    /// Emit multiple modes combined
    Multiple(Vec<StreamMode>),
}

impl std::str::FromStr for StreamMode {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "values" => Ok(StreamMode::Values),
            "updates" => Ok(StreamMode::Updates),
            "debug" => Ok(StreamMode::Debug),
            _ => Err(format!("Unknown stream mode: {}", s)),
        }
    }
}

impl StreamMode {
    /// Convert to string
    pub fn to_str(&self) -> &'static str {
        match self {
            StreamMode::Values => "values",
            StreamMode::Updates => "updates",
            StreamMode::Debug => "debug",
            StreamMode::Multiple(_) => "multiple",
        }
    }
}

/// Output chunk from streaming execution
#[derive(Clone)]
pub struct StreamChunk {
    /// The mode this chunk represents
    pub mode: StreamMode,
    /// The data payload
    pub data: PyObject,
    /// Step number
    pub step: usize,
    /// Metadata
    pub metadata: Option<HashMap<String, PyObject>>,
}

impl StreamChunk {
    /// Create a new stream chunk
    pub fn new(mode: StreamMode, data: PyObject, step: usize) -> Self {
        Self {
            mode,
            data,
            step,
            metadata: None,
        }
    }

    /// Create a values chunk (all channel values)
    pub fn values(py: Python, channels: &HashMap<String, PyObject>, step: usize) -> PyResult<Self> {
        let dict = PyDict::new(py);

        for (channel_name, channel) in channels {
            if let Ok(get_method) = channel.getattr(py, "get") {
                match get_method.call0(py) {
                    Ok(value) => {
                        dict.set_item(channel_name, value)?;
                    }
                    Err(_) => continue,
                }
            }
        }

        Ok(Self::new(StreamMode::Values, dict.into(), step))
    }

    /// Create an updates chunk (node outputs)
    pub fn updates(py: Python, node_name: &str, output: PyObject, step: usize) -> PyResult<Self> {
        let dict = PyDict::new(py);
        dict.set_item(node_name, output)?;

        Ok(Self::new(StreamMode::Updates, dict.into(), step))
    }

    /// Create a debug chunk
    pub fn debug(py: Python, node_name: &str, info: &DebugInfo, step: usize) -> PyResult<Self> {
        let dict = PyDict::new(py);
        dict.set_item("type", "task")?;
        dict.set_item("node", node_name)?;
        dict.set_item("step", step)?;

        if let Some(ref input) = info.input {
            dict.set_item("input", input)?;
        }

        if let Some(ref output) = info.output {
            dict.set_item("output", output)?;
        }

        if let Some(ref error) = info.error {
            dict.set_item("error", error)?;
        }

        dict.set_item("duration_ms", info.duration_ms)?;

        Ok(Self::new(StreamMode::Debug, dict.into(), step))
    }

    /// Convert to Python object
    pub fn to_py_object(&self, py: Python) -> PyResult<PyObject> {
        // For now, just return the data
        // In a full implementation, we might wrap it with mode and metadata
        Ok(self.data.clone_ref(py))
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: String, value: PyObject) -> Self {
        self.metadata
            .get_or_insert_with(HashMap::new)
            .insert(key, value);
        self
    }
}

/// Debug information for a task execution
#[derive(Clone)]
pub struct DebugInfo {
    pub input: Option<PyObject>,
    pub output: Option<PyObject>,
    pub error: Option<String>,
    pub duration_ms: f64,
}

impl DebugInfo {
    pub fn new() -> Self {
        Self {
            input: None,
            output: None,
            error: None,
            duration_ms: 0.0,
        }
    }

    pub fn with_input(mut self, input: PyObject) -> Self {
        self.input = Some(input);
        self
    }

    pub fn with_output(mut self, output: PyObject) -> Self {
        self.output = Some(output);
        self
    }

    pub fn with_error(mut self, error: String) -> Self {
        self.error = Some(error);
        self
    }

    pub fn with_duration(mut self, duration_ms: f64) -> Self {
        self.duration_ms = duration_ms;
        self
    }
}

impl Default for DebugInfo {
    fn default() -> Self {
        Self::new()
    }
}

/// Stream buffer that accumulates chunks
#[allow(dead_code)]
pub struct StreamBuffer {
    chunks: Vec<StreamChunk>,
    mode: StreamMode,
}

impl StreamBuffer {
    pub fn new(mode: StreamMode) -> Self {
        Self {
            chunks: Vec::new(),
            mode,
        }
    }

    /// Add a chunk to the buffer
    pub fn push(&mut self, chunk: StreamChunk) {
        self.chunks.push(chunk);
    }

    /// Get all chunks
    pub fn chunks(&self) -> &[StreamChunk] {
        &self.chunks
    }

    /// Convert all chunks to Python list
    pub fn to_py_list(&self, py: Python) -> PyResult<PyObject> {
        let list = pyo3::types::PyList::empty(py);

        for chunk in &self.chunks {
            list.append(chunk.to_py_object(py)?)?;
        }

        Ok(list.into())
    }

    /// Clear the buffer
    pub fn clear(&mut self) {
        self.chunks.clear();
    }

    /// Get the number of chunks
    pub fn len(&self) -> usize {
        self.chunks.len()
    }

    /// Check if buffer is empty
    pub fn is_empty(&self) -> bool {
        self.chunks.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    #[test]
    fn test_stream_mode_from_str() {
        assert_eq!(StreamMode::from_str("values").unwrap(), StreamMode::Values);
        assert_eq!(
            StreamMode::from_str("updates").unwrap(),
            StreamMode::Updates
        );
        assert_eq!(StreamMode::from_str("debug").unwrap(), StreamMode::Debug);
        assert!(StreamMode::from_str("invalid").is_err());
    }

    #[test]
    fn test_stream_mode_to_str() {
        assert_eq!(StreamMode::Values.to_str(), "values");
        assert_eq!(StreamMode::Updates.to_str(), "updates");
        assert_eq!(StreamMode::Debug.to_str(), "debug");
    }

    #[cfg(feature = "python")]
    #[test]
    fn test_stream_buffer() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut buffer = StreamBuffer::new(StreamMode::Values);
            assert_eq!(buffer.len(), 0);
            assert!(buffer.is_empty());

            let chunk = StreamChunk::new(StreamMode::Values, py.None(), 0);
            buffer.push(chunk);

            assert_eq!(buffer.len(), 1);
            assert!(!buffer.is_empty());

            buffer.clear();
            assert_eq!(buffer.len(), 0);
        });
    }

    #[cfg(feature = "python")]
    #[test]
    fn test_debug_info() {
        let info = DebugInfo::new()
            .with_duration(123.45)
            .with_error("test error".to_string());

        assert_eq!(info.duration_ms, 123.45);
        assert_eq!(info.error, Some("test error".to_string()));
        assert!(info.input.is_none());
        assert!(info.output.is_none());
    }
}
