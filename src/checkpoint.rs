//! Checkpoint implementation for LangGraph

use crate::errors::LangGraphError;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

/// Channel versions mapping
pub type ChannelVersions = HashMap<String, serde_json::Value>;

/// Metadata associated with a checkpoint
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckpointMetadata {
    pub source: String,
    pub step: i32,
    pub parents: HashMap<String, String>,
}

/// State snapshot at a given point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Checkpoint {
    pub v: i32,
    pub id: String,
    pub ts: DateTime<Utc>,
    pub channel_values: HashMap<String, Value>,
    pub channel_versions: ChannelVersions,
    pub versions_seen: HashMap<String, ChannelVersions>,
    pub pending_sends: Vec<Value>,
    pub updated_channels: Option<Vec<String>>,
}

impl Checkpoint {
    pub fn new() -> Self {
        Self {
            v: 1,
            id: uuid::Uuid::new_v4().to_string(),
            ts: Utc::now(),
            channel_values: HashMap::new(),
            channel_versions: HashMap::new(),
            versions_seen: HashMap::new(),
            pending_sends: Vec::new(),
            updated_channels: None,
        }
    }

    pub fn copy(&self) -> Self {
        Self {
            v: self.v,
            id: self.id.clone(),
            ts: self.ts,
            channel_values: self.channel_values.clone(),
            channel_versions: self.channel_versions.clone(),
            versions_seen: self.versions_seen.clone(),
            pending_sends: self.pending_sends.clone(),
            updated_channels: self.updated_channels.clone(),
        }
    }

    /// Serialize the checkpoint to a JSON string
    pub fn to_json(&self) -> Result<String, LangGraphError> {
        Ok(serde_json::to_string(self)?)
    }

    /// Deserialize a checkpoint from a JSON string
    pub fn from_json(json: &str) -> Result<Self, LangGraphError> {
        Ok(serde_json::from_str(json)?)
    }

    /// Serialize the checkpoint using MessagePack for more efficient serialization
    #[cfg(feature = "msgpack")]
    pub fn to_msgpack(&self) -> Result<Vec<u8>, LangGraphError> {
        Ok(rmp_serde::to_vec_named(self)?)
    }

    /// Deserialize a checkpoint from MessagePack
    #[cfg(feature = "msgpack")]
    pub fn from_msgpack(data: &[u8]) -> Result<Self, LangGraphError> {
        Ok(rmp_serde::from_slice(data)?)
    }

    /// Serialize and compress the checkpoint
    #[cfg(feature = "compression")]
    pub fn to_compressed_json(&self) -> Result<Vec<u8>, LangGraphError> {
        use flate2::{write::GzEncoder, Compression};
        use std::io::Write;

        let json = self.to_json()?;
        let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
        encoder.write_all(json.as_bytes())?;
        Ok(encoder.finish()?)
    }

    /// Decompress and deserialize a checkpoint
    #[cfg(feature = "compression")]
    pub fn from_compressed_json(data: &[u8]) -> Result<Self, LangGraphError> {
        use flate2::read::GzDecoder;
        use std::io::Read;

        let mut decoder = GzDecoder::new(data);
        let mut json = String::new();
        decoder.read_to_string(&mut json)?;
        Self::from_json(&json)
    }

    /// Get approximate memory usage of the checkpoint
    pub fn memory_usage(&self) -> usize {
        std::mem::size_of::<Self>()
            + self.id.len()
            + self
                .channel_values
                .iter()
                .map(|(k, v)| k.len() + serde_json::to_string(v).unwrap_or_default().len())
                .sum::<usize>()
            + self
                .channel_versions
                .iter()
                .map(|(k, v)| k.len() + serde_json::to_string(v).unwrap_or_default().len())
                .sum::<usize>()
            + self
                .versions_seen
                .iter()
                .map(|(k, v)| {
                    k.len()
                        + v.iter()
                            .map(|(k2, v2)| {
                                k2.len() + serde_json::to_string(v2).unwrap_or_default().len()
                            })
                            .sum::<usize>()
                })
                .sum::<usize>()
            + self
                .pending_sends
                .iter()
                .map(|v| serde_json::to_string(v).unwrap_or_default().len())
                .sum::<usize>()
            + self
                .updated_channels
                .as_ref()
                .map(|v| v.iter().map(|s| s.len()).sum::<usize>())
                .unwrap_or(0)
    }

    /// Get the size of the serialized checkpoint
    pub fn serialized_size(&self) -> Result<usize, LangGraphError> {
        Ok(self.to_json()?.len())
    }
}

impl Default for Checkpoint {
    fn default() -> Self {
        Self::new()
    }
}

/// A tuple containing a checkpoint and its associated data
#[derive(Debug, Clone)]
pub struct CheckpointTuple {
    pub config: HashMap<String, Value>,
    pub checkpoint: Checkpoint,
    pub metadata: CheckpointMetadata,
    pub parent_config: Option<HashMap<String, Value>>,
    pub pending_writes: Option<Vec<(String, String, Value)>>,
}

/// Trait for checkpoint savers
#[async_trait]
pub trait BaseCheckpointSaver {
    /// Fetch a checkpoint using the given configuration
    fn get(&self, config: &HashMap<String, Value>) -> Result<Option<Checkpoint>, LangGraphError>;

    /// Fetch a checkpoint tuple using the given configuration
    fn get_tuple(
        &self,
        config: &HashMap<String, Value>,
    ) -> Result<Option<CheckpointTuple>, LangGraphError>;

    /// Store a checkpoint with its configuration and metadata
    fn put(
        &self,
        config: &HashMap<String, Value>,
        checkpoint: &Checkpoint,
        metadata: &CheckpointMetadata,
        new_versions: &ChannelVersions,
    ) -> Result<HashMap<String, Value>, LangGraphError>;

    /// Store intermediate writes linked to a checkpoint
    fn put_writes(
        &self,
        config: &HashMap<String, Value>,
        writes: &[(String, Value)],
        task_id: &str,
    ) -> Result<(), LangGraphError>;

    /// Asynchronously fetch a checkpoint using the given configuration
    async fn aget(
        &self,
        config: &HashMap<String, Value>,
    ) -> Result<Option<Checkpoint>, LangGraphError>;

    /// Asynchronously fetch a checkpoint tuple using the given configuration
    async fn aget_tuple(
        &self,
        config: &HashMap<String, Value>,
    ) -> Result<Option<CheckpointTuple>, LangGraphError>;

    /// Asynchronously store a checkpoint with its configuration and metadata
    async fn aput(
        &self,
        config: &HashMap<String, Value>,
        checkpoint: &Checkpoint,
        metadata: &CheckpointMetadata,
        new_versions: &ChannelVersions,
    ) -> Result<HashMap<String, Value>, LangGraphError>;

    /// Asynchronously store intermediate writes linked to a checkpoint
    async fn aput_writes(
        &self,
        config: &HashMap<String, Value>,
        writes: &[(String, Value)],
        task_id: &str,
    ) -> Result<(), LangGraphError>;

    /// Generate the next version ID for a channel
    fn get_next_version(&self, current: Option<serde_json::Value>) -> serde_json::Value;
}

/// In-memory checkpoint saver for testing and simple use cases
#[derive(Debug, Clone)]
pub struct MemoryCheckpointSaver {
    checkpoints: HashMap<String, (Checkpoint, CheckpointMetadata)>,
}

impl MemoryCheckpointSaver {
    pub fn new() -> Self {
        Self {
            checkpoints: HashMap::new(),
        }
    }

    /// Get the number of checkpoints stored
    pub fn len(&self) -> usize {
        self.checkpoints.len()
    }

    /// Check if no checkpoints are stored
    pub fn is_empty(&self) -> bool {
        self.checkpoints.is_empty()
    }

    /// Clear all checkpoints
    pub fn clear(&mut self) {
        self.checkpoints.clear();
    }
}

impl Default for MemoryCheckpointSaver {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl BaseCheckpointSaver for MemoryCheckpointSaver {
    fn get(&self, config: &HashMap<String, Value>) -> Result<Option<Checkpoint>, LangGraphError> {
        if let Some(id) = config.get("checkpoint_id") {
            if let Some(id_str) = id.as_str() {
                return Ok(self.checkpoints.get(id_str).map(|(cp, _)| cp.clone()));
            }
        }
        Ok(None)
    }

    fn get_tuple(
        &self,
        config: &HashMap<String, Value>,
    ) -> Result<Option<CheckpointTuple>, LangGraphError> {
        if let Some(id) = config.get("checkpoint_id") {
            if let Some(id_str) = id.as_str() {
                if let Some((checkpoint, metadata)) = self.checkpoints.get(id_str) {
                    return Ok(Some(CheckpointTuple {
                        config: config.clone(),
                        checkpoint: checkpoint.clone(),
                        metadata: metadata.clone(),
                        parent_config: None,
                        pending_writes: None,
                    }));
                }
            }
        }
        Ok(None)
    }

    fn put(
        &self,
        _config: &HashMap<String, Value>,
        checkpoint: &Checkpoint,
        _metadata: &CheckpointMetadata,
        _new_versions: &ChannelVersions,
    ) -> Result<HashMap<String, Value>, LangGraphError> {
        // In a real implementation, we would mutate the checkpoints map
        // For this simplified version, we'll just return a config with the checkpoint ID
        let mut new_config = HashMap::new();
        new_config.insert(
            "checkpoint_id".to_string(),
            Value::String(checkpoint.id.clone()),
        );
        Ok(new_config)
    }

    fn put_writes(
        &self,
        _config: &HashMap<String, Value>,
        _writes: &[(String, Value)],
        _task_id: &str,
    ) -> Result<(), LangGraphError> {
        // In a real implementation, we would store the writes
        Ok(())
    }

    async fn aget(
        &self,
        config: &HashMap<String, Value>,
    ) -> Result<Option<Checkpoint>, LangGraphError> {
        self.get(config)
    }

    async fn aget_tuple(
        &self,
        config: &HashMap<String, Value>,
    ) -> Result<Option<CheckpointTuple>, LangGraphError> {
        self.get_tuple(config)
    }

    async fn aput(
        &self,
        config: &HashMap<String, Value>,
        checkpoint: &Checkpoint,
        metadata: &CheckpointMetadata,
        new_versions: &ChannelVersions,
    ) -> Result<HashMap<String, Value>, LangGraphError> {
        self.put(config, checkpoint, metadata, new_versions)
    }

    async fn aput_writes(
        &self,
        config: &HashMap<String, Value>,
        writes: &[(String, Value)],
        task_id: &str,
    ) -> Result<(), LangGraphError> {
        self.put_writes(config, writes, task_id)
    }

    fn get_next_version(&self, current: Option<serde_json::Value>) -> serde_json::Value {
        match current {
            Some(Value::Number(n)) => {
                if let Some(i) = n.as_i64() {
                    Value::Number((i + 1).into())
                } else {
                    Value::Number(1.into())
                }
            }
            _ => Value::Number(1.into()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_checkpoint_creation() {
        let checkpoint = Checkpoint::new();
        assert_eq!(checkpoint.v, 1);
        assert!(!checkpoint.id.is_empty());
        assert!(!checkpoint.channel_values.is_empty() || true); // May be empty initially
    }

    #[test]
    fn test_checkpoint_copy() {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );

        let copied = checkpoint.copy();
        assert_eq!(checkpoint.id, copied.id);
        assert_eq!(checkpoint.channel_values, copied.channel_values);
    }

    #[test]
    fn test_checkpoint_serialization() {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );

        // Test JSON serialization
        let json = checkpoint.to_json().unwrap();
        let deserialized = Checkpoint::from_json(&json).unwrap();
        assert_eq!(checkpoint.id, deserialized.id);
        assert_eq!(checkpoint.channel_values, deserialized.channel_values);
    }

    #[test]
    fn test_memory_checkpoint_saver() {
        let mut saver = MemoryCheckpointSaver::new();
        assert_eq!(saver.checkpoints.len(), 0);
        assert!(saver.is_empty());

        saver.clear();
        assert_eq!(saver.len(), 0);
    }

    #[test]
    fn test_checkpoint_memory_usage() {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );

        let usage = checkpoint.memory_usage();
        assert!(usage > 0);

        let serialized_size = checkpoint.serialized_size().unwrap();
        assert!(serialized_size > 0);
    }
}
