//! Graph topology and structure
//!
//! This module defines the graph structure for LangGraph execution,
//! including nodes, edges, and execution flow.

use std::collections::{HashMap, HashSet};
use std::sync::Arc;

/// A node in the graph represents a computation unit
#[derive(Clone, Debug)]
pub struct Node {
    /// Name of the node
    pub name: String,
    /// Function to execute (can be Python callable or Rust function)
    pub function: NodeFunction,
    /// Retry policy for this node
    pub retry_policy: Option<RetryPolicy>,
}

/// Type alias for node function signature
type NodeFn =
    Arc<dyn Fn(&dyn std::any::Any) -> Result<Box<dyn std::any::Any>, String> + Send + Sync>;

/// Type alias for condition function signature
type ConditionFn = Arc<dyn Fn(&dyn std::any::Any) -> Result<String, String> + Send + Sync>;

/// Node function can be either Python or Rust
#[derive(Clone)]
pub enum NodeFunction {
    /// Python callable (PyObject wrapper)
    Python(NodeFn),
    /// Rust function
    Rust(NodeFn),
}

impl std::fmt::Debug for NodeFunction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            NodeFunction::Python(_) => write!(f, "NodeFunction::Python(<function>)"),
            NodeFunction::Rust(_) => write!(f, "NodeFunction::Rust(<function>)"),
        }
    }
}

/// Edge defines data flow between nodes
#[derive(Clone)]
pub enum Edge {
    /// Direct edge from source to target
    Direct { source: String, target: String },
    /// Conditional edge that evaluates a function to determine target
    Conditional {
        source: String,
        condition: ConditionFn,
        path_map: HashMap<String, String>,
    },
    /// Entry point edge (no source)
    Entry { target: String },
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
                source, path_map, ..
            } => f
                .debug_struct("Edge::Conditional")
                .field("source", source)
                .field("condition", &"<function>")
                .field("path_map", path_map)
                .finish(),
            Edge::Entry { target } => f
                .debug_struct("Edge::Entry")
                .field("target", target)
                .finish(),
        }
    }
}

/// Retry policy for node execution
#[derive(Clone, Debug)]
pub struct RetryPolicy {
    pub max_attempts: usize,
    pub retry_on: Vec<String>, // Exception types to retry on
    pub backoff: BackoffStrategy,
}

#[derive(Clone, Debug)]
pub enum BackoffStrategy {
    Constant { delay_ms: u64 },
    Exponential { base_ms: u64, max_ms: u64 },
    Linear { increment_ms: u64 },
}

/// Graph represents the complete execution topology
#[derive(Debug)]
pub struct Graph {
    /// All nodes in the graph
    pub nodes: HashMap<String, Node>,
    /// All edges defining data flow
    pub edges: Vec<Edge>,
    /// Entry point node name
    pub entry_point: Option<String>,
    /// Finish point(s) - nodes that produce final output
    pub finish_points: Vec<String>,
    /// Computed execution order (topologically sorted)
    execution_order: Option<Vec<String>>,
}

impl Graph {
    /// Create a new empty graph
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
            entry_point: None,
            finish_points: Vec::new(),
            execution_order: None,
        }
    }

    /// Add a node to the graph
    pub fn add_node(&mut self, node: Node) {
        self.nodes.insert(node.name.clone(), node);
        // Invalidate cached execution order
        self.execution_order = None;
    }

    /// Add an edge to the graph
    pub fn add_edge(&mut self, edge: Edge) {
        self.edges.push(edge);
        // Invalidate cached execution order
        self.execution_order = None;
    }

    /// Set the entry point for graph execution
    pub fn set_entry_point(&mut self, node_name: String) {
        self.entry_point = Some(node_name);
    }

    /// Add a finish point (node that can produce final output)
    pub fn add_finish_point(&mut self, node_name: String) {
        if !self.finish_points.contains(&node_name) {
            self.finish_points.push(node_name);
        }
    }

    /// Get the execution order (topologically sorted)
    /// Returns None if graph has cycles
    pub fn execution_order(&mut self) -> Option<&[String]> {
        if self.execution_order.is_none() {
            self.execution_order = self.compute_execution_order();
        }
        self.execution_order.as_deref()
    }

    /// Compute topological sort of nodes for execution order
    fn compute_execution_order(&self) -> Option<Vec<String>> {
        let mut order = Vec::new();
        let mut visited = HashSet::new();
        let mut visiting = HashSet::new();

        // Build adjacency list
        let mut adj_list: HashMap<String, Vec<String>> = HashMap::new();
        for node_name in self.nodes.keys() {
            adj_list.insert(node_name.clone(), Vec::new());
        }

        for edge in &self.edges {
            match edge {
                Edge::Direct { source, target } => {
                    adj_list
                        .entry(source.clone())
                        .or_default()
                        .push(target.clone());
                }
                Edge::Conditional {
                    source, path_map, ..
                } => {
                    for target in path_map.values() {
                        adj_list
                            .entry(source.clone())
                            .or_default()
                            .push(target.clone());
                    }
                }
                Edge::Entry { target } => {
                    // Entry edges don't contribute to ordering
                    if let Some(entry) = &self.entry_point {
                        adj_list
                            .entry(entry.clone())
                            .or_default()
                            .push(target.clone());
                    }
                }
            }
        }

        // DFS-based topological sort
        fn dfs(
            node: &str,
            adj_list: &HashMap<String, Vec<String>>,
            visited: &mut HashSet<String>,
            visiting: &mut HashSet<String>,
            order: &mut Vec<String>,
        ) -> bool {
            if visiting.contains(node) {
                // Cycle detected
                return false;
            }
            if visited.contains(node) {
                return true;
            }

            visiting.insert(node.to_string());

            if let Some(neighbors) = adj_list.get(node) {
                for neighbor in neighbors {
                    if !dfs(neighbor, adj_list, visited, visiting, order) {
                        return false;
                    }
                }
            }

            visiting.remove(node);
            visited.insert(node.to_string());
            order.push(node.to_string());

            true
        }

        // Start from entry point if available, otherwise process all nodes
        if let Some(entry) = &self.entry_point {
            if !dfs(entry, &adj_list, &mut visited, &mut visiting, &mut order) {
                return None; // Cycle detected
            }
        }

        // Process remaining nodes (in case of disconnected components)
        for node_name in self.nodes.keys() {
            if !visited.contains(node_name)
                && !dfs(
                    node_name,
                    &adj_list,
                    &mut visited,
                    &mut visiting,
                    &mut order,
                )
            {
                return None; // Cycle detected
            }
        }

        // Reverse to get correct execution order (post-order to pre-order)
        order.reverse();
        Some(order)
    }

    /// Get all nodes that have no incoming edges (potential entry points)
    pub fn find_entry_candidates(&self) -> Vec<String> {
        let mut has_incoming = HashSet::new();

        for edge in &self.edges {
            match edge {
                Edge::Direct { target, .. } => {
                    has_incoming.insert(target.clone());
                }
                Edge::Conditional { path_map, .. } => {
                    for target in path_map.values() {
                        has_incoming.insert(target.clone());
                    }
                }
                Edge::Entry { .. } => {}
            }
        }

        self.nodes
            .keys()
            .filter(|name| !has_incoming.contains(*name))
            .cloned()
            .collect()
    }

    /// Get all nodes that have no outgoing edges (potential finish points)
    pub fn find_finish_candidates(&self) -> Vec<String> {
        let mut has_outgoing = HashSet::new();

        for edge in &self.edges {
            match edge {
                Edge::Direct { source, .. } => {
                    has_outgoing.insert(source.clone());
                }
                Edge::Conditional { source, .. } => {
                    has_outgoing.insert(source.clone());
                }
                Edge::Entry { .. } => {}
            }
        }

        self.nodes
            .keys()
            .filter(|name| !has_outgoing.contains(*name))
            .cloned()
            .collect()
    }

    /// Validate the graph structure
    pub fn validate(&self) -> Result<(), String> {
        // Check that all edge targets exist
        for edge in &self.edges {
            match edge {
                Edge::Direct { source, target } => {
                    if !self.nodes.contains_key(source) {
                        return Err(format!("Edge source '{}' not found in nodes", source));
                    }
                    if !self.nodes.contains_key(target) {
                        return Err(format!("Edge target '{}' not found in nodes", target));
                    }
                }
                Edge::Conditional {
                    source, path_map, ..
                } => {
                    if !self.nodes.contains_key(source) {
                        return Err(format!("Edge source '{}' not found in nodes", source));
                    }
                    for target in path_map.values() {
                        if !self.nodes.contains_key(target) {
                            return Err(format!("Edge target '{}' not found in nodes", target));
                        }
                    }
                }
                Edge::Entry { target } => {
                    if !self.nodes.contains_key(target) {
                        return Err(format!("Entry target '{}' not found in nodes", target));
                    }
                }
            }
        }

        // Check for cycles by computing execution order
        let mut graph_mut = Graph {
            nodes: self.nodes.clone(),
            edges: self.edges.clone(),
            entry_point: self.entry_point.clone(),
            finish_points: self.finish_points.clone(),
            execution_order: None,
        };

        if graph_mut.execution_order().is_none() {
            return Err("Graph contains cycles".to_string());
        }

        Ok(())
    }
}

impl Default for Graph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_graph() {
        let graph = Graph::new();
        assert_eq!(graph.nodes.len(), 0);
        assert_eq!(graph.edges.len(), 0);
    }

    #[test]
    fn test_add_node() {
        let mut graph = Graph::new();
        let node = Node {
            name: "test_node".to_string(),
            function: NodeFunction::Rust(Arc::new(|_| Ok(Box::new(())))),
            retry_policy: None,
        };
        graph.add_node(node);
        assert_eq!(graph.nodes.len(), 1);
        assert!(graph.nodes.contains_key("test_node"));
    }

    #[test]
    fn test_linear_graph_order() {
        let mut graph = Graph::new();

        // Create nodes
        for i in 0..3 {
            let node = Node {
                name: format!("node{}", i),
                function: NodeFunction::Rust(Arc::new(|_| Ok(Box::new(())))),
                retry_policy: None,
            };
            graph.add_node(node);
        }

        // Create linear edges: node0 -> node1 -> node2
        graph.add_edge(Edge::Direct {
            source: "node0".to_string(),
            target: "node1".to_string(),
        });
        graph.add_edge(Edge::Direct {
            source: "node1".to_string(),
            target: "node2".to_string(),
        });
        graph.set_entry_point("node0".to_string());

        let order = graph.execution_order().unwrap();
        assert_eq!(order.len(), 3);
        assert_eq!(order[0], "node0");
        assert_eq!(order[1], "node1");
        assert_eq!(order[2], "node2");
    }

    #[test]
    fn test_cycle_detection() {
        let mut graph = Graph::new();

        // Create nodes
        for i in 0..3 {
            let node = Node {
                name: format!("node{}", i),
                function: NodeFunction::Rust(Arc::new(|_| Ok(Box::new(())))),
                retry_policy: None,
            };
            graph.add_node(node);
        }

        // Create cycle: node0 -> node1 -> node2 -> node0
        graph.add_edge(Edge::Direct {
            source: "node0".to_string(),
            target: "node1".to_string(),
        });
        graph.add_edge(Edge::Direct {
            source: "node1".to_string(),
            target: "node2".to_string(),
        });
        graph.add_edge(Edge::Direct {
            source: "node2".to_string(),
            target: "node0".to_string(),
        });

        // Should detect cycle
        assert!(graph.execution_order().is_none());
    }
}
