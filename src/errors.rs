//! Error types for LangGraph Rust implementation

use thiserror::Error;

#[derive(Error, Debug)]
pub enum LangGraphError {
    #[error("Channel error: {0}")]
    ChannelError(String),

    #[error("Checkpoint error: {0}")]
    CheckpointError(String),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("IO error: {0}")]
    IOError(#[from] std::io::Error),

    #[error("Node execution failed: {node_id} - {source}")]
    NodeExecutionError {
        node_id: String,
        source: Box<dyn std::error::Error + Send + Sync>,
    },

    #[error("Checkpoint not found: {checkpoint_id}")]
    CheckpointNotFound { checkpoint_id: String },

    #[error("Invalid update: {0}")]
    InvalidUpdate(String),

    #[error("Graph recursion limit exceeded")]
    GraphRecursionError,
}

#[cfg(feature = "msgpack")]
impl From<rmp_serde::encode::Error> for LangGraphError {
    fn from(error: rmp_serde::encode::Error) -> Self {
        LangGraphError::SerializationError(serde_json::Error::io(std::io::Error::other(
            error.to_string(),
        )))
    }
}

#[cfg(feature = "msgpack")]
impl From<rmp_serde::decode::Error> for LangGraphError {
    fn from(error: rmp_serde::decode::Error) -> Self {
        LangGraphError::SerializationError(serde_json::Error::io(std::io::Error::other(
            error.to_string(),
        )))
    }
}
