//! Fast LangGraph - High-performance Rust Implementation
//!
//! This crate provides high-performance implementations of core LangGraph components
//! using Rust for significant performance improvements over the Python implementation.

// Allow non-local definitions for pyo3 macros across all modules
#![allow(non_local_definitions)]

pub mod channel_manager;
pub mod channels;
pub mod checkpoint;
pub mod checkpoint_sqlite;
pub mod conditional;
pub mod errors;
pub mod executor;
pub mod fast_channels;
pub mod function_cache;
pub mod graph;
pub mod llm_cache;
pub mod pregel;
pub mod pregel_algo;
pub mod pregel_loop;
pub mod pregel_node;
pub mod rust_checkpoint;
pub mod send;
pub mod state_merge;
pub mod stream_output;
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
pub use channels::{Channel, LastValueChannel};
pub use checkpoint::Checkpoint;
pub use executor::Executor;
pub use graph::Graph;
pub use pregel::PregelExecutor;

// Re-export core types when python feature is enabled
#[cfg(feature = "python")]
pub use core::{Edge as CoreEdge, GraphState, Node as CoreNode, PregelCore};
