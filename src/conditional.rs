//! Conditional Edge Evaluation
//!
//! Implements conditional routing logic for graphs with branching execution paths.

use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

/// A conditional edge that determines next node based on state
#[derive(Clone)]
pub struct ConditionalEdge {
    /// Source node
    pub source: String,
    /// Condition function (returns routing key)
    pub condition: PyObject,
    /// Path mapping from condition result to target node
    pub path_map: HashMap<String, String>,
    /// Default target if condition result not in path_map
    pub default: Option<String>,
}

impl ConditionalEdge {
    /// Create a new conditional edge
    pub fn new(source: String, condition: PyObject, path_map: HashMap<String, String>) -> Self {
        Self {
            source,
            condition,
            path_map,
            default: None,
        }
    }

    /// Create with a default target
    pub fn with_default(mut self, default: String) -> Self {
        self.default = Some(default);
        self
    }

    /// Evaluate the condition and return the target node
    pub fn evaluate(&self, py: Python, state: &PyDict) -> PyResult<String> {
        // Call the condition function with state
        let result = if let Ok(call_method) = self.condition.as_ref(py).getattr("__call__") {
            call_method.call1((state,))?.into()
        } else {
            self.condition.call1(py, (state,))?
        };

        // Extract the routing key
        let routing_key: String = result.extract(py)?;

        // Look up in path map
        if let Some(target) = self.path_map.get(&routing_key) {
            Ok(target.clone())
        } else if let Some(ref default) = self.default {
            Ok(default.clone())
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Condition returned '{}' but no matching path in map and no default provided",
                routing_key
            )))
        }
    }

    /// Check if this edge originates from the given node
    pub fn from_node(&self, node: &str) -> bool {
        self.source == node
    }

    /// Get all possible target nodes
    pub fn possible_targets(&self) -> Vec<String> {
        let mut targets: Vec<String> = self.path_map.values().cloned().collect();
        if let Some(ref default) = self.default {
            if !targets.contains(default) {
                targets.push(default.clone());
            }
        }
        targets
    }
}

/// Collection of conditional edges for a graph
pub struct ConditionalRouter {
    edges: Vec<ConditionalEdge>,
}

impl ConditionalRouter {
    pub fn new() -> Self {
        Self { edges: Vec::new() }
    }

    /// Add a conditional edge
    pub fn add_edge(&mut self, edge: ConditionalEdge) {
        self.edges.push(edge);
    }

    /// Find the next node(s) from a given source node
    pub fn route_from(
        &self,
        py: Python,
        source_node: &str,
        state: &PyDict,
    ) -> PyResult<Vec<String>> {
        let mut targets = Vec::new();

        for edge in &self.edges {
            if edge.from_node(source_node) {
                let target = edge.evaluate(py, state)?;
                targets.push(target);
            }
        }

        Ok(targets)
    }

    /// Get all conditional edges from a source node
    pub fn edges_from(&self, source_node: &str) -> Vec<&ConditionalEdge> {
        self.edges
            .iter()
            .filter(|e| e.from_node(source_node))
            .collect()
    }

    /// Check if a node has conditional edges
    pub fn has_conditional_edges(&self, node: &str) -> bool {
        self.edges.iter().any(|e| e.from_node(node))
    }
}

impl Default for ConditionalRouter {
    fn default() -> Self {
        Self::new()
    }
}

/// Branch represents a potential execution path
#[derive(Clone, Debug)]
pub struct Branch {
    /// Target node
    pub target: String,
    /// Condition that leads to this branch
    pub condition_result: String,
}

impl Branch {
    pub fn new(target: String, condition_result: String) -> Self {
        Self {
            target,
            condition_result,
        }
    }
}

/// Evaluate all possible branches from a conditional edge
pub fn evaluate_branches(edge: &ConditionalEdge) -> Vec<Branch> {
    let mut branches = Vec::new();

    for (condition_result, target) in &edge.path_map {
        branches.push(Branch::new(target.clone(), condition_result.clone()));
    }

    if let Some(ref default) = edge.default {
        branches.push(Branch::new(default.clone(), "__default__".to_string()));
    }

    branches
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_conditional_edge() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            // Create a simple condition function
            let condition = py
                .eval(
                    "lambda x: 'a' if x.get('value', 0) > 10 else 'b'",
                    None,
                    None,
                )
                .unwrap();

            let mut path_map = HashMap::new();
            path_map.insert("a".to_string(), "node_a".to_string());
            path_map.insert("b".to_string(), "node_b".to_string());

            let edge = ConditionalEdge::new("source".to_string(), condition.into(), path_map);

            assert_eq!(edge.source, "source");
            assert_eq!(edge.possible_targets().len(), 2);
        });
    }

    #[test]
    fn test_conditional_router() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut router = ConditionalRouter::new();

            let condition = py.eval("lambda x: 'continue'", None, None).unwrap();
            let mut path_map = HashMap::new();
            path_map.insert("continue".to_string(), "next".to_string());

            let edge = ConditionalEdge::new("start".to_string(), condition.into(), path_map);

            router.add_edge(edge);

            assert!(router.has_conditional_edges("start"));
            assert!(!router.has_conditional_edges("other"));
        });
    }

    #[test]
    fn test_branch_evaluation() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let condition = py.None();
            let mut path_map = HashMap::new();
            path_map.insert("path1".to_string(), "node1".to_string());
            path_map.insert("path2".to_string(), "node2".to_string());

            let edge = ConditionalEdge::new("source".to_string(), condition, path_map)
                .with_default("default_node".to_string());

            let branches = evaluate_branches(&edge);
            assert_eq!(branches.len(), 3); // 2 paths + 1 default
        });
    }
}
