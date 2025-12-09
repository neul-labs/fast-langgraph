//! Graph execution engine
//!
//! This module implements the core execution logic for running graphs.
//! It handles node execution, state management, and error handling.

use crate::graph::{Edge, Graph, NodeFunction};
use std::any::Any;
use std::collections::HashMap;

/// State represents the current execution state of the graph
pub struct State {
    /// Current values for each state key
    values: HashMap<String, Box<dyn Any + Send + Sync>>,
}

impl State {
    /// Create a new empty state
    pub fn new() -> Self {
        Self {
            values: HashMap::new(),
        }
    }

    /// Create state from initial values
    pub fn from_values(values: HashMap<String, Box<dyn Any + Send + Sync>>) -> Self {
        Self { values }
    }

    /// Get a value from state
    pub fn get(&self, key: &str) -> Option<&(dyn Any + Send + Sync)> {
        self.values.get(key).map(|v| v.as_ref())
    }

    /// Set a value in state
    pub fn set(&mut self, key: String, value: Box<dyn Any + Send + Sync>) {
        self.values.insert(key, value);
    }

    /// Update state with new values (merge)
    pub fn update(&mut self, updates: HashMap<String, Box<dyn Any + Send + Sync>>) {
        for (key, value) in updates {
            self.values.insert(key, value);
        }
    }

    /// Get all values as a reference
    pub fn values(&self) -> &HashMap<String, Box<dyn Any + Send + Sync>> {
        &self.values
    }

    /// Get mutable reference to values
    pub fn values_mut(&mut self) -> &mut HashMap<String, Box<dyn Any + Send + Sync>> {
        &mut self.values
    }
}

impl Default for State {
    fn default() -> Self {
        Self::new()
    }
}

/// Executor runs graphs and manages execution state
pub struct Executor {
    /// The graph to execute
    graph: Graph,
    /// Current execution state
    state: State,
}

impl Executor {
    /// Create a new executor for the given graph
    pub fn new(graph: Graph) -> Self {
        Self {
            graph,
            state: State::new(),
        }
    }

    /// Create an executor with initial state
    pub fn with_state(graph: Graph, state: State) -> Self {
        Self { graph, state }
    }

    /// Get a reference to the current state
    pub fn state(&self) -> &State {
        &self.state
    }

    /// Get a mutable reference to the current state
    pub fn state_mut(&mut self) -> &mut State {
        &mut self.state
    }

    /// Get a reference to the graph
    pub fn graph(&self) -> &Graph {
        &self.graph
    }

    /// Execute a single node with the current state
    pub fn execute_node(&mut self, node_name: &str) -> Result<(), String> {
        // Get the node
        let node = self
            .graph
            .nodes
            .get(node_name)
            .ok_or_else(|| format!("Node '{}' not found in graph", node_name))?;

        // Execute the node function with current state
        let state_ref = &self.state as &dyn Any;
        let _result = match &node.function {
            NodeFunction::Python(func) | NodeFunction::Rust(func) => func(state_ref)?,
        };

        // Update state with result
        // For now, we'll assume the result is a HashMap update
        // In a real implementation, this would be more sophisticated
        // and handle different return types

        Ok(())
    }

    /// Execute the entire graph from entry to finish
    ///
    /// This follows the execution order determined by the graph topology.
    /// For linear graphs, this simply runs nodes in sequence.
    pub fn invoke(
        &mut self,
        input: Box<dyn Any + Send + Sync>,
    ) -> Result<Box<dyn Any + Send + Sync>, String> {
        // Set initial input as state
        // For simplicity, we'll store it under a special "__input__" key
        self.state.set("__input__".to_string(), input);

        // Get execution order (clone to avoid borrow checker issues)
        let execution_order = self
            .graph
            .execution_order()
            .ok_or_else(|| "Cannot execute graph: contains cycles or invalid topology".to_string())?
            .to_vec();

        // Execute nodes in order
        for node_name in &execution_order {
            self.execute_node(node_name)?;
        }

        // Return the final state
        // For now, return the entire state as the output
        // In a real implementation, we'd extract specific output channels
        let output = self
            .state
            .get("__output__")
            .map(|_v| {
                // This is a placeholder - in reality we need proper type handling
                Box::new(()) as Box<dyn Any + Send + Sync>
            })
            .unwrap_or_else(|| Box::new(()) as Box<dyn Any + Send + Sync>);

        Ok(output)
    }

    /// Execute a specific path through the graph
    ///
    /// This is useful for conditional execution where only certain nodes should run.
    pub fn invoke_path(
        &mut self,
        node_names: &[String],
        input: Box<dyn Any + Send + Sync>,
    ) -> Result<Box<dyn Any + Send + Sync>, String> {
        // Set initial input
        self.state.set("__input__".to_string(), input);

        // Execute specified nodes in order
        for node_name in node_names {
            self.execute_node(node_name)?;
        }

        // Return output
        let output = self
            .state
            .get("__output__")
            .map(|_| Box::new(()) as Box<dyn Any + Send + Sync>)
            .unwrap_or_else(|| Box::new(()) as Box<dyn Any + Send + Sync>);

        Ok(output)
    }

    /// Determine next node based on conditional edges
    fn evaluate_conditional_edge(&self, edge: &Edge) -> Result<Option<String>, String> {
        match edge {
            Edge::Direct { target, .. } => Ok(Some(target.clone())),
            Edge::Conditional {
                condition,
                path_map,
                ..
            } => {
                let state_ref = &self.state as &dyn Any;
                let condition_result = condition(state_ref)?;

                // Look up the target in the path map
                let target = path_map.get(&condition_result).ok_or_else(|| {
                    format!(
                        "Condition result '{}' not found in path map",
                        condition_result
                    )
                })?;

                Ok(Some(target.clone()))
            }
            Edge::Entry { .. } => Ok(None),
        }
    }

    /// Execute graph with support for conditional edges
    ///
    /// This is more advanced than invoke() and handles branching logic.
    pub fn invoke_with_conditions(
        &mut self,
        input: Box<dyn Any + Send + Sync>,
    ) -> Result<Box<dyn Any + Send + Sync>, String> {
        // Set initial input
        self.state.set("__input__".to_string(), input);

        // Start from entry point
        let mut current_node = self
            .graph
            .entry_point
            .as_ref()
            .ok_or_else(|| "No entry point defined in graph".to_string())?
            .clone();

        let mut visited = std::collections::HashSet::new();
        let max_iterations = 1000; // Prevent infinite loops
        let mut iterations = 0;

        loop {
            iterations += 1;
            if iterations > max_iterations {
                return Err("Maximum iterations exceeded - possible infinite loop".to_string());
            }

            // Check if we've reached a finish point
            if self.graph.finish_points.contains(&current_node) {
                break;
            }

            // Execute current node
            self.execute_node(&current_node)?;
            visited.insert(current_node.clone());

            // Find outgoing edges from current node
            let mut next_node: Option<String> = None;
            for edge in &self.graph.edges {
                match edge {
                    Edge::Direct { source, target } if source == &current_node => {
                        next_node = Some(target.clone());
                        break;
                    }
                    Edge::Conditional { source, .. } if source == &current_node => {
                        next_node = self.evaluate_conditional_edge(edge)?;
                        break;
                    }
                    _ => {}
                }
            }

            // Move to next node or finish
            match next_node {
                Some(next) => current_node = next,
                None => break, // No outgoing edges, we're done
            }
        }

        // Return output
        let output = self
            .state
            .get("__output__")
            .map(|_| Box::new(()) as Box<dyn Any + Send + Sync>)
            .unwrap_or_else(|| Box::new(()) as Box<dyn Any + Send + Sync>);

        Ok(output)
    }

    /// Reset the executor state
    pub fn reset(&mut self) {
        self.state = State::new();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    #[test]
    fn test_state_operations() {
        let mut state = State::new();

        // Test setting and getting values
        state.set("key1".to_string(), Box::new(42));
        state.set("key2".to_string(), Box::new("hello".to_string()));

        assert!(state.get("key1").is_some());
        assert!(state.get("key2").is_some());
        assert!(state.get("key3").is_none());
    }

    #[test]
    fn test_state_update() {
        let mut state = State::new();
        state.set("key1".to_string(), Box::new(42));

        let mut updates = HashMap::new();
        updates.insert(
            "key2".to_string(),
            Box::new("value".to_string()) as Box<dyn Any + Send + Sync>,
        );

        state.update(updates);

        assert!(state.get("key1").is_some());
        assert!(state.get("key2").is_some());
    }

    #[test]
    fn test_executor_creation() {
        let graph = Graph::new();
        let executor = Executor::new(graph);

        assert_eq!(executor.state().values().len(), 0);
    }

    #[test]
    fn test_executor_with_state() {
        let graph = Graph::new();
        let mut state = State::new();
        state.set("initial".to_string(), Box::new(100));

        let executor = Executor::with_state(graph, state);
        assert!(executor.state().get("initial").is_some());
    }
}
