//! Send - Dynamic Task Dispatch
//!
//! Implements the Send mechanism for dynamic task creation during graph execution.
//! Send allows nodes to dynamically create new tasks that will be executed in the same superstep.

use pyo3::prelude::*;
use std::fmt;

/// Send represents a dynamic task to be dispatched
#[derive(Clone)]
pub struct Send {
    /// The node to send to
    pub node: String,
    /// The argument/input for the node
    pub arg: PyObject,
}

impl Send {
    /// Create a new Send
    pub fn new(node: String, arg: PyObject) -> Self {
        Self { node, arg }
    }

    /// Create from Python Send object
    pub fn from_py_send(_py: Python, send_obj: &PyAny) -> PyResult<Self> {
        let node: String = send_obj.getattr("node")?.extract()?;
        let arg: PyObject = send_obj.getattr("arg")?.extract()?;
        Ok(Self::new(node, arg))
    }

    /// Convert to Python Send object
    pub fn to_py_send(&self, py: Python) -> PyResult<PyObject> {
        // Import Send class from langgraph.constants
        let langgraph = py.import("langgraph.constants")?;
        let send_class = langgraph.getattr("Send")?;

        // Create Send(node, arg)
        Ok(send_class
            .call1((self.node.clone(), self.arg.clone_ref(py)))?
            .into())
    }

    /// Check if a Python object is a Send
    pub fn is_send(py: Python, obj: &PyAny) -> bool {
        if let Ok(langgraph) = py.import("langgraph.constants") {
            if let Ok(send_class) = langgraph.getattr("Send") {
                return obj.is_instance(send_class).unwrap_or(false);
            }
        }
        false
    }
}

impl fmt::Debug for Send {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Send")
            .field("node", &self.node)
            .field("arg", &"<PyObject>")
            .finish()
    }
}

/// Collection of Send objects from a single task
pub struct SendBatch {
    /// The node that generated these sends
    pub source_node: String,
    /// The Send objects
    pub sends: Vec<Send>,
}

impl SendBatch {
    pub fn new(source_node: String) -> Self {
        Self {
            source_node,
            sends: Vec::new(),
        }
    }

    pub fn add(&mut self, send: Send) {
        self.sends.push(send);
    }

    pub fn len(&self) -> usize {
        self.sends.len()
    }

    pub fn is_empty(&self) -> bool {
        self.sends.is_empty()
    }

    pub fn iter(&self) -> impl Iterator<Item = &Send> {
        self.sends.iter()
    }
}

/// Extract Send objects from a task result
pub fn extract_sends_from_result(py: Python, result: &PyAny) -> PyResult<Vec<Send>> {
    let mut sends = Vec::new();

    // Check if result is a list
    if let Ok(list) = result.downcast::<pyo3::types::PyList>() {
        for item in list.iter() {
            if Send::is_send(py, item) {
                sends.push(Send::from_py_send(py, item)?);
            }
        }
    }
    // Check if result is a single Send
    else if Send::is_send(py, result) {
        sends.push(Send::from_py_send(py, result)?);
    }
    // Check if result is a dict with Send values
    else if let Ok(dict) = result.downcast::<pyo3::types::PyDict>() {
        for (_key, value) in dict.iter() {
            if Send::is_send(py, value) {
                sends.push(Send::from_py_send(py, value)?);
            } else if let Ok(list) = value.downcast::<pyo3::types::PyList>() {
                for item in list.iter() {
                    if Send::is_send(py, item) {
                        sends.push(Send::from_py_send(py, item)?);
                    }
                }
            }
        }
    }

    Ok(sends)
}

/// Process pending sends and create tasks
pub fn process_pending_sends(py: Python, pending_sends: &[PyObject]) -> PyResult<Vec<Send>> {
    let mut sends = Vec::new();

    for send_obj in pending_sends {
        if let Ok(send_any) = send_obj.as_ref(py).downcast::<PyAny>() {
            if Send::is_send(py, send_any) {
                sends.push(Send::from_py_send(py, send_any)?);
            }
        }
    }

    Ok(sends)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_send_creation() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let node = "test_node".to_string();
            let arg = py.None();

            let send = Send::new(node.clone(), arg);
            assert_eq!(send.node, node);
        });
    }

    #[test]
    fn test_send_batch() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut batch = SendBatch::new("source".to_string());
            assert_eq!(batch.len(), 0);
            assert!(batch.is_empty());

            let send = Send::new("target".to_string(), py.None());
            batch.add(send);

            assert_eq!(batch.len(), 1);
            assert!(!batch.is_empty());
        });
    }
}
