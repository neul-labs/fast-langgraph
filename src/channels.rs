//! Channel implementations for LangGraph

use crate::errors::LangGraphError;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// Base trait for all channels
#[allow(clippy::wrong_self_convention)]
pub trait Channel<T, U>: Send + Sync {
    /// Get the current value of the channel
    fn get(&self) -> Result<&T, LangGraphError>;

    /// Update the channel with new values
    fn update(&mut self, values: Vec<U>) -> Result<bool, LangGraphError>;

    /// Check if the channel is available (has a value)
    fn is_available(&self) -> bool;

    /// Consume the channel value
    fn consume(&mut self) -> bool;

    /// Finish the channel
    fn finish(&mut self) -> bool;

    /// Create a checkpoint of the channel state
    fn checkpoint(&self) -> Result<serde_json::Value, LangGraphError>;

    /// Restore from a checkpoint
    fn from_checkpoint(&mut self, checkpoint: serde_json::Value) -> Result<(), LangGraphError>;

    /// Get memory usage estimate
    fn memory_usage(&self) -> usize;
}

/// A channel that stores the last value received
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LastValueChannel<T> {
    value: Option<T>,
}

impl<T: Clone + Send + Sync + Serialize + for<'de> Deserialize<'de>> Default
    for LastValueChannel<T>
{
    fn default() -> Self {
        Self::new()
    }
}

impl<T: Clone + Send + Sync + Serialize + for<'de> Deserialize<'de>> LastValueChannel<T> {
    pub fn new() -> Self {
        Self { value: None }
    }

    pub fn with_value(value: T) -> Self {
        Self { value: Some(value) }
    }
}

impl<T: Clone + Send + Sync + Serialize + for<'de> Deserialize<'de>> Channel<T, T>
    for LastValueChannel<T>
{
    fn get(&self) -> Result<&T, LangGraphError> {
        self.value
            .as_ref()
            .ok_or(LangGraphError::ChannelError("Channel is empty".to_string()))
    }

    fn update(&mut self, values: Vec<T>) -> Result<bool, LangGraphError> {
        if values.is_empty() {
            return Ok(false);
        }

        if values.len() != 1 {
            return Err(LangGraphError::InvalidUpdate(
                "LastValueChannel can only receive one value per update".to_string(),
            ));
        }

        self.value = Some(values.into_iter().next().unwrap());
        Ok(true)
    }

    fn is_available(&self) -> bool {
        self.value.is_some()
    }

    fn consume(&mut self) -> bool {
        false // No-op for LastValueChannel
    }

    fn finish(&mut self) -> bool {
        false // No-op for LastValueChannel
    }

    fn checkpoint(&self) -> Result<serde_json::Value, LangGraphError> {
        match &self.value {
            Some(value) => Ok(serde_json::to_value(value)?),
            None => Ok(serde_json::Value::Null),
        }
    }

    fn from_checkpoint(&mut self, checkpoint: serde_json::Value) -> Result<(), LangGraphError> {
        if checkpoint.is_null() {
            self.value = None;
        } else {
            self.value = Some(serde_json::from_value(checkpoint)?);
        }
        Ok(())
    }

    fn memory_usage(&self) -> usize {
        // Approximate memory usage - this is a simplified calculation
        // In a real implementation, this would be more sophisticated
        std::mem::size_of::<Option<T>>()
            + self
                .value
                .as_ref()
                .map(|v| std::mem::size_of_val(v))
                .unwrap_or(0)
    }
}

/// A channel that accumulates values over time (like a topic)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopicChannel<T> {
    values: VecDeque<T>,
    accumulate: bool,
}

impl<T: Clone + Send + Sync + Serialize + for<'de> Deserialize<'de>> TopicChannel<T> {
    pub fn new(accumulate: bool) -> Self {
        Self {
            values: VecDeque::new(),
            accumulate,
        }
    }

    pub fn with_values(values: Vec<T>, accumulate: bool) -> Self {
        Self {
            values: values.into(),
            accumulate,
        }
    }

    /// Get all values in the topic
    pub fn get_values(&self) -> &VecDeque<T> {
        &self.values
    }

    /// Get mutable reference to values
    pub fn get_values_mut(&mut self) -> &mut VecDeque<T> {
        &mut self.values
    }
}

impl<T: Clone + Send + Sync + Serialize + for<'de> Deserialize<'de>> Channel<Vec<T>, T>
    for TopicChannel<T>
{
    fn get(&self) -> Result<&Vec<T>, LangGraphError> {
        // This is awkward but needed for compatibility - we can't easily return a Vec reference
        // from a VecDeque. In a real implementation, we might store as Vec instead.
        // For now, we'll use a thread-local storage approach or return an error suggesting
        // use of get_values() instead
        Err(LangGraphError::ChannelError(
            "TopicChannel::get() is not supported. Use get_values() instead.".to_string(),
        ))
    }

    fn update(&mut self, values: Vec<T>) -> Result<bool, LangGraphError> {
        if values.is_empty() {
            return Ok(false);
        }

        if self.accumulate {
            // Add all values to the queue
            for value in values {
                self.values.push_back(value);
            }
        } else {
            // Replace all values with the new ones
            self.values.clear();
            for value in values {
                self.values.push_back(value);
            }
        }

        Ok(true)
    }

    fn is_available(&self) -> bool {
        !self.values.is_empty()
    }

    fn consume(&mut self) -> bool {
        if !self.accumulate {
            // If not accumulating, clear the values after consuming
            let was_available = !self.values.is_empty();
            self.values.clear();
            was_available
        } else {
            false
        }
    }

    fn finish(&mut self) -> bool {
        false // No-op for TopicChannel
    }

    fn checkpoint(&self) -> Result<serde_json::Value, LangGraphError> {
        Ok(serde_json::to_value(&self.values)?)
    }

    fn from_checkpoint(&mut self, checkpoint: serde_json::Value) -> Result<(), LangGraphError> {
        self.values = serde_json::from_value(checkpoint)?;
        Ok(())
    }

    fn memory_usage(&self) -> usize {
        std::mem::size_of::<Self>()
            + self
                .values
                .iter()
                .map(|v| std::mem::size_of_val(v))
                .sum::<usize>()
    }
}

/// A channel that applies a binary operator to accumulate values
#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct BinaryOperatorAggregateChannel<T, F> {
    value: Option<T>,
    operator: F,
}

impl<T: Clone, F> BinaryOperatorAggregateChannel<T, F> {
    pub fn new(operator: F) -> Self {
        Self {
            value: None,
            operator,
        }
    }

    pub fn with_value(value: T, operator: F) -> Self {
        Self {
            value: Some(value),
            operator,
        }
    }

    /// Get the current value
    pub fn get_value(&self) -> Option<&T> {
        self.value.as_ref()
    }

    /// Set the current value
    pub fn set_value(&mut self, value: T) {
        self.value = Some(value);
    }
}

// Note: This implementation is simplified and would need more work for a complete implementation
// We're not implementing the Channel trait for this because it would require complex generic bounds

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_last_value_channel() {
        let mut channel = LastValueChannel::<i32>::new();
        assert!(!channel.is_available());
        assert_eq!(channel.memory_usage(), 8); // Option<i32> size

        // Update with a value
        assert!(channel.update(vec![42]).unwrap());
        assert!(channel.is_available());
        assert_eq!(*channel.get().unwrap(), 42);
        assert!(channel.memory_usage() > 8); // Now has a value

        // Update with another value
        assert!(channel.update(vec![84]).unwrap());
        assert_eq!(*channel.get().unwrap(), 84);

        // Test checkpointing
        let checkpoint = channel.checkpoint().unwrap();
        let mut new_channel = LastValueChannel::<i32>::new();
        new_channel.from_checkpoint(checkpoint).unwrap();
        assert_eq!(*new_channel.get().unwrap(), 84);
    }

    #[test]
    fn test_topic_channel() {
        let mut channel = TopicChannel::<i32>::new(true);
        assert!(!channel.is_available());
        let initial_memory = channel.memory_usage();

        // Update with values
        assert!(channel.update(vec![1, 2, 3]).unwrap());
        assert!(channel.is_available());
        assert!(channel.memory_usage() > initial_memory);

        // Test checkpointing
        let checkpoint = channel.checkpoint().unwrap();
        let mut new_channel = TopicChannel::<i32>::new(true);
        new_channel.from_checkpoint(checkpoint).unwrap();
        assert!(new_channel.is_available());
    }

    #[test]
    fn test_binary_operator_aggregate_channel() {
        let mut channel = BinaryOperatorAggregateChannel::new(|a: i32, b: i32| a + b);
        assert!(channel.get_value().is_none());

        channel.set_value(42);
        assert_eq!(*channel.get_value().unwrap(), 42);
    }
}
