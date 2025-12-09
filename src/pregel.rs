//! Core Pregel execution engine implementation

use crate::channels::Channel;
use crate::checkpoint::Checkpoint;
use crate::errors::LangGraphError;
use petgraph::graph::DiGraph;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Represents a node in the computation graph
#[derive(Clone)]
pub struct PregelNode<T, U> {
    pub id: String,
    pub triggers: Vec<String>,
    pub channels: Vec<String>,
    pub processor: Arc<dyn Fn(T) -> Result<U, LangGraphError> + Send + Sync>,
}

// Manual Debug implementation since dyn Fn doesn't implement Debug
impl<T, U> std::fmt::Debug for PregelNode<T, U> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PregelNode")
            .field("id", &self.id)
            .field("triggers", &self.triggers)
            .field("channels", &self.channels)
            .finish()
    }
}

/// Represents a task to be executed
#[derive(Debug, Clone)]
pub struct PregelTask<T> {
    pub id: String,
    pub node_id: String,
    pub input: T,
}

/// Represents writes to channels
#[derive(Debug, Clone)]
pub struct PregelTaskWrites<U> {
    pub task_id: String,
    pub writes: Vec<(String, U)>,
}

/// Statistics about Pregel execution
#[derive(Debug, Clone)]
pub struct PregelStats {
    pub tasks_executed: usize,
    pub supersteps_completed: usize,
    pub total_execution_time: std::time::Duration,
    pub memory_usage: usize,
}

/// Configuration for Pregel execution
#[derive(Debug, Clone)]
pub struct PregelConfig {
    pub max_supersteps: usize,
    pub parallelism: usize,
    pub timeout: Option<std::time::Duration>,
}

impl Default for PregelConfig {
    fn default() -> Self {
        Self {
            max_supersteps: 1000,
            parallelism: num_cpus::get(),
            timeout: None,
        }
    }
}

/// Core Pregel execution engine
pub struct PregelExecutor<T: Clone + Send + Sync, U: Clone + Send + Sync> {
    #[allow(dead_code)]
    graph: DiGraph<String, ()>,
    nodes: HashMap<String, PregelNode<T, U>>,
    channels: HashMap<String, Arc<RwLock<dyn Channel<T, U>>>>,
    checkpoint: Arc<RwLock<Checkpoint>>,
    stats: Arc<RwLock<PregelStats>>,
    config: PregelConfig,
}

impl<T: Clone + Send + Sync + 'static, U: Clone + Send + Sync + 'static> PregelExecutor<T, U> {
    pub fn new() -> Self {
        Self::with_config(PregelConfig::default())
    }

    pub fn with_config(config: PregelConfig) -> Self {
        Self {
            graph: DiGraph::new(),
            nodes: HashMap::new(),
            channels: HashMap::new(),
            checkpoint: Arc::new(RwLock::new(Checkpoint::new())),
            stats: Arc::new(RwLock::new(PregelStats {
                tasks_executed: 0,
                supersteps_completed: 0,
                total_execution_time: std::time::Duration::from_secs(0),
                memory_usage: 0,
            })),
            config,
        }
    }

    /// Add a node to the execution graph
    pub fn add_node(&mut self, node: PregelNode<T, U>) -> Result<(), LangGraphError> {
        self.nodes.insert(node.id.clone(), node);
        Ok(())
    }

    /// Add a channel to the execution graph
    pub fn add_channel(
        &mut self,
        name: String,
        channel: Arc<RwLock<dyn Channel<T, U>>>,
    ) -> Result<(), LangGraphError> {
        self.channels.insert(name, channel);
        Ok(())
    }

    /// Execute the graph for a single superstep
    pub async fn execute_step(&self) -> Result<Vec<PregelTaskWrites<U>>, LangGraphError> {
        let start_time = std::time::Instant::now();

        // Prepare tasks for this step
        let tasks = self.prepare_tasks().await?;

        // Execute tasks in parallel
        let task_writes = self.execute_tasks(tasks).await?;

        // Apply writes to channels
        self.apply_writes(&task_writes).await?;

        // Update statistics
        {
            let mut stats = self.stats.write().await;
            stats.tasks_executed += task_writes.len();
            stats.supersteps_completed += 1;
            stats.total_execution_time += start_time.elapsed();
        }

        Ok(task_writes)
    }

    /// Execute the graph until completion or max steps reached
    pub async fn execute_until_completion(
        &self,
    ) -> Result<Vec<PregelTaskWrites<U>>, LangGraphError> {
        let start_time = std::time::Instant::now();
        let mut all_writes = Vec::new();

        for _step in 0..self.config.max_supersteps {
            let writes = self.execute_step().await?;

            // If no writes were produced, we're done
            if writes.is_empty() {
                break;
            }

            all_writes.extend(writes);

            // Check timeout if configured
            if let Some(timeout) = self.config.timeout {
                if start_time.elapsed() > timeout {
                    return Err(LangGraphError::GraphRecursionError);
                }
            }
        }

        // Update final statistics
        {
            let mut stats = self.stats.write().await;
            stats.total_execution_time += start_time.elapsed();
        }

        Ok(all_writes)
    }

    /// Prepare tasks for execution based on channel updates
    async fn prepare_tasks(&self) -> Result<Vec<PregelTask<T>>, LangGraphError> {
        let mut tasks = Vec::new();

        // For each node, check if its triggers have been updated
        for (node_id, node) in &self.nodes {
            let mut inputs = Vec::new();

            // Collect inputs from channels
            for channel_name in &node.channels {
                if let Some(channel) = self.channels.get(channel_name) {
                    let channel_guard = channel.read().await;
                    if channel_guard.is_available() {
                        // In a real implementation, we would collect the actual values
                        // For now, we'll use a placeholder - this is a simplification
                        // that would need to be expanded in a full implementation
                        if let Ok(value) = channel_guard.get() {
                            inputs.push(value.clone());
                        }
                    }
                }
            }

            // If we have inputs, create a task
            if !inputs.is_empty() {
                // In a real implementation, we would combine inputs appropriately
                // For now, we'll just use the first input as a placeholder
                let input = inputs.into_iter().next().unwrap().clone();

                tasks.push(PregelTask {
                    id: format!("task_{}", uuid::Uuid::new_v4()),
                    node_id: node_id.clone(),
                    input,
                });
            }
        }

        Ok(tasks)
    }

    /// Execute tasks in parallel
    async fn execute_tasks(
        &self,
        tasks: Vec<PregelTask<T>>,
    ) -> Result<Vec<PregelTaskWrites<U>>, LangGraphError> {
        let mut task_futures = Vec::new();

        for task in tasks {
            if let Some(node) = self.nodes.get(&task.node_id) {
                let processor = Arc::clone(&node.processor);
                let input = task.input;
                let task_id = task.id.clone();

                task_futures.push(tokio::spawn(async move {
                    match processor(input) {
                        Ok(output) => Ok(PregelTaskWrites {
                            task_id,
                            writes: vec![("output".to_string(), output)], // Simplified
                        }),
                        Err(e) => Err(e),
                    }
                }));
            }
        }

        let mut results = Vec::new();
        for future in task_futures {
            match future.await {
                Ok(Ok(writes)) => results.push(writes),
                Ok(Err(e)) => return Err(e),
                Err(e) => {
                    return Err(LangGraphError::NodeExecutionError {
                        node_id: "unknown".to_string(),
                        source: Box::new(e),
                    })
                }
            }
        }

        Ok(results)
    }

    /// Apply task writes to channels
    async fn apply_writes(
        &self,
        task_writes: &[PregelTaskWrites<U>],
    ) -> Result<(), LangGraphError> {
        // Group writes by channel
        let mut channel_writes: HashMap<String, Vec<U>> = HashMap::new();

        for task_write in task_writes {
            for (channel_name, value) in &task_write.writes {
                channel_writes
                    .entry(channel_name.clone())
                    .or_default()
                    .push(value.clone());
            }
        }

        // Apply writes to channels
        for (channel_name, values) in channel_writes {
            if let Some(channel) = self.channels.get(&channel_name) {
                let mut channel_guard = channel.write().await;
                channel_guard.update(values)?;
            }
        }

        Ok(())
    }

    /// Get the current checkpoint
    pub async fn get_checkpoint(&self) -> Checkpoint {
        self.checkpoint.read().await.clone()
    }

    /// Set a new checkpoint
    pub async fn set_checkpoint(&self, checkpoint: Checkpoint) {
        *self.checkpoint.write().await = checkpoint;
    }

    /// Get execution statistics
    pub async fn get_stats(&self) -> PregelStats {
        self.stats.read().await.clone()
    }

    /// Reset execution statistics
    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        *stats = PregelStats {
            tasks_executed: 0,
            supersteps_completed: 0,
            total_execution_time: std::time::Duration::from_secs(0),
            memory_usage: 0,
        };
    }
}

impl<T: Clone + Send + Sync + 'static, U: Clone + Send + Sync + 'static> Default
    for PregelExecutor<T, U>
{
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_pregel_executor_creation() {
        let executor: PregelExecutor<i32, i32> = PregelExecutor::new();
        assert_eq!(executor.nodes.len(), 0);
        assert_eq!(executor.channels.len(), 0);
    }

    #[tokio::test]
    async fn test_pregel_stats() {
        let executor: PregelExecutor<i32, i32> = PregelExecutor::new();
        let stats = executor.get_stats().await;
        assert_eq!(stats.tasks_executed, 0);
        assert_eq!(stats.supersteps_completed, 0);
    }

    #[test]
    fn test_pregel_config() {
        let config = PregelConfig::default();
        assert_eq!(config.max_supersteps, 1000);
        assert!(config.parallelism > 0);
    }
}
