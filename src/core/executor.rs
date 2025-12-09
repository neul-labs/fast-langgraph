//! PregelCore executor - the main execution engine
//!
//! This module implements the core Pregel-style graph execution with async support.

use super::channel::{Channel, LastValueChannel};
use super::edge::Edge;
use super::node::Node;
use super::state::GraphState;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

/// PregelCore is the main execution engine for LangGraph
///
/// It manages:
/// - Nodes: Computation units
/// - Edges: Control flow
/// - Channels: State storage
/// - Execution: Async graph traversal
pub struct PregelCore {
    nodes: HashMap<String, Node>,
    edges: Vec<Edge>,
    state: GraphState,
    entry_point: Option<String>,
    recursion_limit: usize,
}

impl PregelCore {
    /// Create a new PregelCore executor
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
            state: GraphState::new(),
            entry_point: None,
            recursion_limit: 25, // Default from LangGraph
        }
    }

    /// Add a node to the graph
    pub fn add_node(&mut self, node: Node) {
        self.nodes.insert(node.name.clone(), node);
    }

    /// Add an edge to the graph
    pub fn add_edge(&mut self, edge: Edge) {
        self.edges.push(edge);
    }

    /// Add a channel to the state
    pub fn add_channel(&mut self, name: String, channel: Box<dyn Channel>) {
        self.state.add_channel(name, channel);
    }

    /// Set the entry point for execution
    pub fn set_entry_point(&mut self, node_name: String) {
        self.entry_point = Some(node_name);
    }

    /// Set the recursion limit
    pub fn set_recursion_limit(&mut self, limit: usize) {
        self.recursion_limit = limit;
    }

    /// Get a reference to the state
    pub fn state(&self) -> &GraphState {
        &self.state
    }

    /// Get a mutable reference to the state
    pub fn state_mut(&mut self) -> &mut GraphState {
        &mut self.state
    }

    /// Invoke the graph with the given input
    ///
    /// This is the main entry point for graph execution.
    /// It handles:
    /// 1. Setting up initial state from input
    /// 2. Determining starting node(s)
    /// 3. Executing nodes in order
    /// 4. Following edges (direct or conditional)
    /// 5. Extracting output from designated channels
    pub async fn invoke_async(&mut self, py: Python<'_>, input: PyObject) -> PyResult<PyObject> {
        // Initialize state with input
        // For now, we'll store the input in a special __input__ channel
        if !self.state.has_channel("__input__") {
            self.state
                .add_channel("__input__".to_string(), Box::new(LastValueChannel::new()));
        }
        self.state.update_channel(py, "__input__", input)?;

        // Determine starting node
        let start_node = self.get_start_node()?;

        // Execute the graph
        self.execute_from(py, start_node).await?;

        // Extract output
        // For now, return the state (will be refined when wiring to Python)
        Ok(py.None())
    }

    /// Synchronous invoke wrapper
    pub fn invoke(&mut self, py: Python<'_>, input: PyObject) -> PyResult<PyObject> {
        // Use tokio runtime for async execution
        let rt = tokio::runtime::Runtime::new().map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Failed to create runtime: {}", e))
        })?;

        rt.block_on(self.invoke_async(py, input))
    }

    /// Get the starting node for execution
    fn get_start_node(&self) -> PyResult<String> {
        // Check for explicit entry point
        if let Some(ref entry) = self.entry_point {
            return Ok(entry.clone());
        }

        // Look for Start edges
        for edge in &self.edges {
            if let Edge::Start { target } = edge {
                return Ok(target.clone());
            }
        }

        // If no explicit start, look for nodes with no incoming edges
        let nodes_with_incoming: HashSet<String> = self
            .edges
            .iter()
            .filter_map(|e| match e {
                Edge::Direct { target, .. } => Some(target.clone()),
                Edge::Conditional { branches, .. } => Some(branches.values().next()?.clone()),
                _ => None,
            })
            .collect();

        // Find nodes without incoming edges
        let candidates: Vec<String> = self
            .nodes
            .keys()
            .filter(|name| !nodes_with_incoming.contains(*name))
            .cloned()
            .collect();

        if candidates.is_empty() {
            Err(pyo3::exceptions::PyValueError::new_err(
                "No entry point found for graph",
            ))
        } else {
            Ok(candidates[0].clone())
        }
    }

    /// Execute the graph starting from a specific node
    async fn execute_from(&mut self, py: Python<'_>, start_node: String) -> PyResult<()> {
        let mut current_node = start_node;
        let mut visited = HashSet::new();
        let mut iterations = 0;

        loop {
            iterations += 1;
            if iterations > self.recursion_limit {
                return Err(pyo3::exceptions::PyRecursionError::new_err(format!(
                    "Recursion limit ({}) exceeded",
                    self.recursion_limit
                )));
            }

            // Check if we've hit a cycle (optional - for debugging)
            if visited.contains(&current_node) {
                // In some graphs, revisiting is OK (loops), but we rely on iteration limit
                // For now, we'll allow it but rely on recursion_limit
            }
            visited.insert(current_node.clone());

            // Execute the current node
            self.execute_node(py, &current_node).await?;

            // Determine next node
            match self.get_next_node(py, &current_node).await? {
                Some(next) => current_node = next,
                None => break, // No next node, we're done
            }
        }

        Ok(())
    }

    /// Execute a single node
    async fn execute_node(&mut self, py: Python<'_>, node_name: &str) -> PyResult<()> {
        // Get the node
        let node = self
            .nodes
            .get(node_name)
            .ok_or_else(|| {
                pyo3::exceptions::PyKeyError::new_err(format!("Node '{}' not found", node_name))
            })?
            .clone(); // Clone to avoid borrow issues

        // Collect input from channels
        let channel_values: HashMap<String, PyObject> = node
            .input_channels
            .as_ref()
            .map(|channels| {
                channels
                    .iter()
                    .filter_map(|ch_name| {
                        self.state
                            .get_value(py, ch_name)
                            .map(|val| (ch_name.clone(), val))
                    })
                    .collect()
            })
            .unwrap_or_default();

        // Extract input for the node
        let input = node.extract_input(py, &channel_values)?;

        // Execute the node
        let output = node.execute(py, input)?;

        // Map output to channel updates
        let updates = node.map_output(py, output)?;

        // Apply updates to channels
        for (channel_name, value) in updates {
            if self.state.has_channel(&channel_name) {
                self.state.update_channel(py, &channel_name, value)?;
            } else {
                // Auto-create channel if it doesn't exist
                self.state
                    .add_channel(channel_name.clone(), Box::new(LastValueChannel::new()));
                self.state.update_channel(py, &channel_name, value)?;
            }
        }

        Ok(())
    }

    /// Determine the next node to execute
    async fn get_next_node(&self, py: Python<'_>, current_node: &str) -> PyResult<Option<String>> {
        // Find outgoing edges from current node
        for edge in &self.edges {
            if let Some(source) = edge.source() {
                if source == current_node {
                    // This edge applies
                    // For conditional edges, evaluate the condition
                    // For now, we'll pass the entire state as a dict to the condition
                    let state_dict = self.create_state_dict(py)?;
                    return edge.evaluate_condition(py, state_dict);
                }
            }
        }

        // Check for End edges
        for edge in &self.edges {
            if let Edge::End { source } = edge {
                if source == current_node {
                    return Ok(None);
                }
            }
        }

        // No outgoing edges found - we're done
        Ok(None)
    }

    /// Create a dictionary representation of the current state
    fn create_state_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new(py);

        for channel_name in self.state.channel_names() {
            if let Some(value) = self.state.get_value(py, &channel_name) {
                dict.set_item(channel_name, value)?;
            }
        }

        Ok(dict.to_object(py))
    }

    /// Get checkpoint of current state
    pub fn checkpoint(&self, py: Python<'_>) -> PyResult<HashMap<String, PyObject>> {
        self.state.checkpoint(py)
    }

    /// Restore from checkpoint
    pub fn from_checkpoint(
        &mut self,
        py: Python<'_>,
        checkpoint: HashMap<String, PyObject>,
    ) -> PyResult<()> {
        self.state.from_checkpoint(py, checkpoint)
    }
}

impl Default for PregelCore {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for PregelCore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PregelCore")
            .field("nodes", &self.nodes.keys().collect::<Vec<_>>())
            .field("edges", &self.edges)
            .field("entry_point", &self.entry_point)
            .field("channels", &self.state.channel_names())
            .finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_pregel_core_creation() {
        let executor = PregelCore::new();
        assert_eq!(executor.nodes.len(), 0);
        assert_eq!(executor.edges.len(), 0);
        assert!(executor.entry_point.is_none());
    }

    #[test]
    fn test_add_node() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut executor = PregelCore::new();
            let func = py.eval_bound("lambda x: x + 1", None, None).unwrap();
            let node = Node::new("test".to_string(), func.to_object(py));

            executor.add_node(node);
            assert_eq!(executor.nodes.len(), 1);
        });
    }

    #[test]
    fn test_add_edge() {
        let mut executor = PregelCore::new();
        let edge = Edge::direct("node1".to_string(), "node2".to_string());

        executor.add_edge(edge);
        assert_eq!(executor.edges.len(), 1);
    }

    #[tokio::test]
    async fn test_simple_execution() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut executor = PregelCore::new();

            // Create a simple node that adds 1
            let func = py.eval_bound("lambda x: x + 1", None, None).unwrap();
            let node = Node::with_channels(
                "add_one".to_string(),
                func.to_object(py),
                Some(vec!["input".to_string()]),
                Some(vec!["output".to_string()]),
            );

            // Add the node
            executor.add_node(node);

            // Add channels
            executor.add_channel("input".to_string(), Box::new(LastValueChannel::new()));
            executor.add_channel("output".to_string(), Box::new(LastValueChannel::new()));

            // Set entry point
            executor.set_entry_point("add_one".to_string());

            // Set initial input
            executor
                .state_mut()
                .update_channel(py, "input", 42.to_object(py))
                .unwrap();

            // Execute
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                executor
                    .execute_from(py, "add_one".to_string())
                    .await
                    .unwrap();
            });

            // Check output
            let result = executor.state().get_value(py, "output").unwrap();
            assert_eq!(result.extract::<i32>(py).unwrap(), 43);
        });
    }

    #[tokio::test]
    async fn test_linear_graph() {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| {
            let mut executor = PregelCore::new();

            // Node 1: x + 1
            let func1 = py.eval_bound("lambda x: x + 1", None, None).unwrap();
            let node1 = Node::with_channels(
                "add_one".to_string(),
                func1.to_object(py),
                Some(vec!["input".to_string()]),
                Some(vec!["intermediate".to_string()]),
            );

            // Node 2: x * 2
            let func2 = py.eval_bound("lambda x: x * 2", None, None).unwrap();
            let node2 = Node::with_channels(
                "multiply_two".to_string(),
                func2.to_object(py),
                Some(vec!["intermediate".to_string()]),
                Some(vec!["output".to_string()]),
            );

            executor.add_node(node1);
            executor.add_node(node2);

            // Add edge: add_one -> multiply_two
            executor.add_edge(Edge::direct(
                "add_one".to_string(),
                "multiply_two".to_string(),
            ));

            // Add channels
            executor.add_channel("input".to_string(), Box::new(LastValueChannel::new()));
            executor.add_channel(
                "intermediate".to_string(),
                Box::new(LastValueChannel::new()),
            );
            executor.add_channel("output".to_string(), Box::new(LastValueChannel::new()));

            // Set entry
            executor.set_entry_point("add_one".to_string());

            // Set input
            executor
                .state_mut()
                .update_channel(py, "input", 5.to_object(py))
                .unwrap();

            // Execute
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(async {
                executor
                    .execute_from(py, "add_one".to_string())
                    .await
                    .unwrap();
            });

            // Check: (5 + 1) * 2 = 12
            let result = executor.state().get_value(py, "output").unwrap();
            assert_eq!(result.extract::<i32>(py).unwrap(), 12);
        });
    }
}
