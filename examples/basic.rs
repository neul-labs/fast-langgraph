//! Example usage of LangGraph Rust implementation

use fast_langgraph::channels::LastValueChannel;
use fast_langgraph::pregel::{PregelExecutor, PregelNode};
use std::sync::Arc;

fn main() {
    // Create a new Pregel executor
    let mut executor: PregelExecutor<i32, i32> = PregelExecutor::new();

    // Create a simple node that doubles its input
    let node = PregelNode {
        id: "double".to_string(),
        triggers: vec!["input".to_string()],
        channels: vec!["input".to_string()],
        processor: Arc::new(|x: i32| Ok(x * 2)),
    };

    // Add the node to the executor
    executor.add_node(node).expect("Failed to add node");

    // Create a channel
    let channel = Arc::new(tokio::sync::RwLock::new(LastValueChannel::with_value(21)));

    // Add the channel to the executor
    executor
        .add_channel("input".to_string(), channel)
        .expect("Failed to add channel");

    println!("LangGraph Rust implementation example");
    println!("Input: 21");
    println!("Node doubles the input");
    // In a real implementation, we would execute the graph here
    println!("Expected output: 42");
}
