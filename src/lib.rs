//! Fast LangGraph - High-performance Rust Implementation
//!
//! This crate provides high-performance implementations of core LangGraph components
//! using Rust for significant performance improvements over the Python implementation.

pub mod graph;
pub mod executor;
pub mod pregel;
pub mod channels;
pub mod checkpoint;
pub mod errors;
pub mod pregel_node;
pub mod pregel_algo;
pub mod pregel_loop;
pub mod channel_manager;
pub mod stream_output;
pub mod send;
pub mod conditional;
// pub mod state;  // Will be created in Phase 2

// Hybrid acceleration module
#[cfg(feature = "python")]
pub mod hybrid;

// New core module with Python-compatible async execution
#[cfg(feature = "python")]
pub mod core;

#[cfg(feature = "python")]
pub mod python;

// Re-export key types
pub use graph::Graph;
pub use executor::Executor;
pub use pregel::PregelExecutor;
pub use channels::{Channel, LastValueChannel};
pub use checkpoint::Checkpoint;

// Re-export core types when python feature is enabled
#[cfg(feature = "python")]
pub use core::{PregelCore, Node as CoreNode, Edge as CoreEdge, GraphState};