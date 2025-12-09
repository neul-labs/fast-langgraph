//! Edge types for graph control flow
//!
//! Edges define how execution flows between nodes in the graph.

use pyo3::prelude::*;
use std::collections::HashMap;

/// Edge defines control flow between nodes
#[derive(Clone)]
pub enum Edge {
    /// Direct edge: always go from source to target
    Direct { source: String, target: String },

    /// Conditional edge: evaluate a condition to determine next node
    Conditional {
        source: String,
        condition: PyObject,               // Function that returns next node name
        branches: HashMap<String, String>, // condition_result -> target_node
    },

    /// Start edge: entry point to a node
    Start { target: String },

    /// End edge: marks a node as a termination point
    End { source: String },
}

impl Edge {
    /// Create a direct edge
    pub fn direct(source: String, target: String) -> Self {
        Self::Direct { source, target }
    }

    /// Create a conditional edge
    pub fn conditional(
        source: String,
        condition: PyObject,
        branches: HashMap<String, String>,
    ) -> Self {
        Self::Conditional {
            source,
            condition,
            branches,
        }
    }

    /// Create a start edge
    pub fn start(target: String) -> Self {
        Self::Start { target }
    }

    /// Create an end edge
    pub fn end(source: String) -> Self {
        Self::End { source }
    }

    /// Get the source node name (if applicable)
    pub fn source(&self) -> Option<&str> {
        match self {
            Edge::Direct { source, .. } => Some(source),
            Edge::Conditional { source, .. } => Some(source),
            Edge::Start { .. } => None,
            Edge::End { source } => Some(source),
        }
    }

    /// Get the target node name (if applicable for direct edges)
    pub fn target(&self) -> Option<&str> {
        match self {
            Edge::Direct { target, .. } => Some(target),
            Edge::Start { target } => Some(target),
            _ => None,
        }
    }

    /// Evaluate conditional edge to determine next node
    ///
    /// Returns the name of the next node to execute based on the condition.
    pub fn evaluate_condition(&self, py: Python, state: PyObject) -> PyResult<Option<String>> {
        match self {
            Edge::Direct { target, .. } => Ok(Some(target.clone())),
            Edge::Start { target } => Ok(Some(target.clone())),
            Edge::End { .. } => Ok(None),
            Edge::Conditional {
                condition,
                branches,
                ..
            } => {
                // Call the condition function with the state
                let result = condition.call1(py, (state,))?;

                // Extract the result as a string
                let result_str = result.extract::<String>(py)?;

                // Look up the target in the branches map
                let target = branches
                    .get(&result_str)
                    .ok_or_else(|| {
                        pyo3::exceptions::PyKeyError::new_err(format!(
                            "Condition result '{}' not found in branches",
                            result_str
                        ))
                    })?
                    .clone();

                Ok(Some(target))
            }
        }
    }
}

impl std::fmt::Debug for Edge {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Edge::Direct { source, target } => f
                .debug_struct("Edge::Direct")
                .field("source", source)
                .field("target", target)
                .finish(),
            Edge::Conditional {
                source, branches, ..
            } => f
                .debug_struct("Edge::Conditional")
                .field("source", source)
                .field("branches", branches)
                .finish(),
            Edge::Start { target } => f
                .debug_struct("Edge::Start")
                .field("target", target)
                .finish(),
            Edge::End { source } => f.debug_struct("Edge::End").field("source", source).finish(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_direct_edge() {
        let edge = Edge::direct("node1".to_string(), "node2".to_string());

        assert_eq!(edge.source(), Some("node1"));
        assert_eq!(edge.target(), Some("node2"));
    }

    #[test]
    fn test_start_edge() {
        let edge = Edge::start("entry".to_string());

        assert_eq!(edge.source(), None);
        assert_eq!(edge.target(), Some("entry"));
    }

    #[test]
    fn test_end_edge() {
        let edge = Edge::end("final".to_string());

        assert_eq!(edge.source(), Some("final"));
        assert_eq!(edge.target(), None);
    }

    #[test]
    fn test_conditional_edge_evaluation() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            // Create a condition function that returns "yes" or "no"
            let condition = py.eval_bound("lambda state: 'yes'", None, None).unwrap();

            let mut branches = HashMap::new();
            branches.insert("yes".to_string(), "node_yes".to_string());
            branches.insert("no".to_string(), "node_no".to_string());

            let edge = Edge::conditional("node1".to_string(), condition.to_object(py), branches);

            // Evaluate the condition
            let state = py.None();
            let result = edge.evaluate_condition(py, state).unwrap();

            assert_eq!(result, Some("node_yes".to_string()));
        });
    }

    #[test]
    fn test_direct_edge_evaluation() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let edge = Edge::direct("node1".to_string(), "node2".to_string());

            let state = py.None();
            let result = edge.evaluate_condition(py, state).unwrap();

            assert_eq!(result, Some("node2".to_string()));
        });
    }
}
