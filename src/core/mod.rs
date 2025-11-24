//! Core LangGraph execution engine compatible with Python
//!
//! This module provides the foundational types for LangGraph execution:
//! - Channels: State storage mechanisms
//! - GraphState: Collection of named channels
//! - Nodes: Computation units that read/write channels
//! - Edges: Control flow between nodes
//! - PregelCore: Main async execution engine
//!
//! This implementation is designed to be wire-compatible with Python LangGraph
//! while providing high-performance async execution in Rust.

pub mod channel;
pub mod state;
pub mod node;
pub mod edge;
pub mod executor;

pub use channel::{Channel, ChannelUpdate, LastValueChannel, TopicChannel};
pub use state::GraphState;
pub use node::Node;
pub use edge::Edge;
pub use executor::PregelCore;
