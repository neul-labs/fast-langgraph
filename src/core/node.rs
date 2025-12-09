//! Node execution
//!
//! Nodes are computation units that read from and write to channels.
//! Each node has a function that processes input and produces output.

use pyo3::prelude::*;
use std::collections::HashMap;

/// Node represents a computation unit in the graph
///
/// A node consists of:
/// - name: Unique identifier
/// - func: Python callable to execute
/// - input_channels: Which channels to read from (optional)
/// - output_channels: Which channels to write to (optional)
#[derive(Clone)]
pub struct Node {
    pub name: String,
    pub func: PyObject,
    pub input_channels: Option<Vec<String>>,
    pub output_channels: Option<Vec<String>>,
}

impl Node {
    /// Create a new node
    pub fn new(name: String, func: PyObject) -> Self {
        Self {
            name,
            func,
            input_channels: None,
            output_channels: None,
        }
    }

    /// Create a node with input/output channel specifications
    pub fn with_channels(
        name: String,
        func: PyObject,
        input_channels: Option<Vec<String>>,
        output_channels: Option<Vec<String>>,
    ) -> Self {
        Self {
            name,
            func,
            input_channels,
            output_channels,
        }
    }

    /// Execute the node function with the given input
    ///
    /// This method:
    /// 1. Calls the Python function with the input
    /// 2. Returns the result
    pub fn execute(&self, py: Python, input: PyObject) -> PyResult<PyObject> {
        // Call the Python function
        self.func.call1(py, (input,))
    }

    /// Execute the node asynchronously
    ///
    /// This is a synchronous wrapper that will be used by the async executor.
    /// The actual async execution happens at the executor level.
    pub async fn execute_async(&self, input: PyObject) -> PyResult<PyObject> {
        Python::with_gil(|py| self.execute(py, input))
    }

    /// Get input from channels
    ///
    /// Extract input values from the specified input channels.
    /// Returns the input to pass to the node function.
    pub fn extract_input(
        &self,
        py: Python,
        channel_values: &HashMap<String, PyObject>,
    ) -> PyResult<PyObject> {
        match &self.input_channels {
            None => {
                // No input channels specified, return None
                Ok(py.None())
            }
            Some(channels) if channels.is_empty() => {
                // Empty input channels, return None
                Ok(py.None())
            }
            Some(channels) if channels.len() == 1 => {
                // Single input channel - return just the value
                let channel_name = &channels[0];
                channel_values.get(channel_name).cloned().ok_or_else(|| {
                    pyo3::exceptions::PyKeyError::new_err(format!(
                        "Input channel '{}' not found",
                        channel_name
                    ))
                })
            }
            Some(channels) => {
                // Multiple input channels - return dict
                let dict = pyo3::types::PyDict::new(py);
                for channel_name in channels {
                    if let Some(value) = channel_values.get(channel_name) {
                        dict.set_item(channel_name, value)?;
                    }
                }
                Ok(dict.to_object(py))
            }
        }
    }

    /// Map output to channels
    ///
    /// Takes the node's output and maps it to channel updates.
    /// Returns a HashMap of channel_name -> value.
    pub fn map_output(&self, py: Python, output: PyObject) -> PyResult<HashMap<String, PyObject>> {
        let mut updates = HashMap::new();

        match &self.output_channels {
            None => {
                // No output channels - no updates
            }
            Some(channels) if channels.is_empty() => {
                // Empty output channels - no updates
            }
            Some(channels) if channels.len() == 1 => {
                // Single output channel - output goes directly to that channel
                let channel_name = &channels[0];
                updates.insert(channel_name.clone(), output);
            }
            Some(channels) => {
                // Multiple output channels - output should be a dict
                if let Ok(dict) = output.extract::<&pyo3::types::PyDict>(py) {
                    for channel_name in channels {
                        if let Ok(Some(value)) = dict.get_item(channel_name) {
                            updates.insert(channel_name.clone(), value.to_object(py));
                        }
                    }
                } else {
                    // Output is not a dict - assign to all channels?
                    // For now, we'll just assign to the first channel
                    if let Some(first_channel) = channels.first() {
                        updates.insert(first_channel.clone(), output);
                    }
                }
            }
        }

        Ok(updates)
    }
}

impl std::fmt::Debug for Node {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Node")
            .field("name", &self.name)
            .field("input_channels", &self.input_channels)
            .field("output_channels", &self.output_channels)
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_node_creation() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let func = py.eval_bound("lambda x: x + 1", None, None).unwrap();
            let node = Node::new("test".to_string(), func.to_object(py));

            assert_eq!(node.name, "test");
            assert!(node.input_channels.is_none());
            assert!(node.output_channels.is_none());
        });
    }

    #[test]
    fn test_node_execute() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let func = py.eval("lambda x: x + 1", None, None).unwrap();
            let node = Node::new("test".to_string(), func.to_object(py));

            let input = 42.to_object(py);
            let result = node.execute(py, input).unwrap();

            assert_eq!(result.extract::<i32>(py).unwrap(), 43);
        });
    }

    #[test]
    fn test_extract_input_single_channel() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let func = py.eval("lambda x: x", None, None).unwrap();
            let node = Node::with_channels(
                "test".to_string(),
                func.to_object(py),
                Some(vec!["input".to_string()]),
                None,
            );

            let mut channel_values = HashMap::new();
            channel_values.insert("input".to_string(), 42.to_object(py));

            let input = node.extract_input(py, &channel_values).unwrap();
            assert_eq!(input.extract::<i32>(py).unwrap(), 42);
        });
    }

    #[test]
    fn test_extract_input_multiple_channels() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let func = py.eval("lambda x: x", None, None).unwrap();
            let node = Node::with_channels(
                "test".to_string(),
                func.to_object(py),
                Some(vec!["a".to_string(), "b".to_string()]),
                None,
            );

            let mut channel_values = HashMap::new();
            channel_values.insert("a".to_string(), 1.to_object(py));
            channel_values.insert("b".to_string(), 2.to_object(py));

            let input = node.extract_input(py, &channel_values).unwrap();
            let dict = input.downcast::<pyo3::types::PyDict>(py).unwrap();

            assert_eq!(
                dict.get_item("a")
                    .unwrap()
                    .unwrap()
                    .extract::<i32>()
                    .unwrap(),
                1
            );
            assert_eq!(
                dict.get_item("b")
                    .unwrap()
                    .unwrap()
                    .extract::<i32>()
                    .unwrap(),
                2
            );
        });
    }

    #[test]
    fn test_map_output_single_channel() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let func = py.eval("lambda x: x", None, None).unwrap();
            let node = Node::with_channels(
                "test".to_string(),
                func.to_object(py),
                None,
                Some(vec!["output".to_string()]),
            );

            let output = 42.to_object(py);
            let updates = node.map_output(py, output).unwrap();

            assert_eq!(updates.len(), 1);
            assert_eq!(
                updates.get("output").unwrap().extract::<i32>(py).unwrap(),
                42
            );
        });
    }

    #[test]
    fn test_map_output_multiple_channels() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let func = py.eval("lambda x: x", None, None).unwrap();
            let node = Node::with_channels(
                "test".to_string(),
                func.to_object(py),
                None,
                Some(vec!["out1".to_string(), "out2".to_string()]),
            );

            // Create a dict output
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("out1", 1).unwrap();
            dict.set_item("out2", 2).unwrap();

            let output = dict.to_object(py);
            let updates = node.map_output(py, output).unwrap();

            assert_eq!(updates.len(), 2);
            assert_eq!(updates.get("out1").unwrap().extract::<i32>(py).unwrap(), 1);
            assert_eq!(updates.get("out2").unwrap().extract::<i32>(py).unwrap(), 2);
        });
    }
}
