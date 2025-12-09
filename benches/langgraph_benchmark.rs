//! Benchmarks for LangGraph Rust implementation

use criterion::{criterion_group, criterion_main, Criterion};
use langgraph_rs::channels::{Channel, LastValueChannel, TopicChannel};
use langgraph_rs::checkpoint::Checkpoint;
use langgraph_rs::pregel::{PregelExecutor, PregelNode};
use std::sync::Arc;

fn benchmark_channel_operations(c: &mut Criterion) {
    c.bench_function("last_value_channel_update", |b| {
        b.iter(|| {
            let mut channel = LastValueChannel::<i32>::new();
            let _ = channel.update(vec![42]);
        })
    });

    c.bench_function("last_value_channel_get", |b| {
        let channel = LastValueChannel::with_value(42);
        b.iter(|| {
            let _ = channel.get();
        })
    });

    c.bench_function("topic_channel_update", |b| {
        b.iter(|| {
            let mut channel = TopicChannel::<i32>::new(true);
            let _ = channel.update(vec![1, 2, 3, 4, 5]);
        })
    });
}

fn benchmark_checkpoint_operations(c: &mut Criterion) {
    c.bench_function("checkpoint_creation", |b| {
        b.iter(|| {
            let checkpoint = Checkpoint::new();
            std::hint::black_box(checkpoint);
        })
    });

    c.bench_function("checkpoint_json_serialization", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );

        b.iter(|| {
            let json = checkpoint.to_json().unwrap();
            std::hint::black_box(json);
        })
    });

    c.bench_function("checkpoint_json_deserialization", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );
        let json = checkpoint.to_json().unwrap();

        b.iter(|| {
            let deserialized = Checkpoint::from_json(&json).unwrap();
            std::hint::black_box(deserialized);
        })
    });

    #[cfg(feature = "msgpack")]
    c.bench_function("checkpoint_msgpack_serialization", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );

        b.iter(|| {
            let data = checkpoint.to_msgpack().unwrap();
            std::hint::black_box(data);
        })
    });

    #[cfg(feature = "msgpack")]
    c.bench_function("checkpoint_msgpack_deserialization", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );
        let data = checkpoint.to_msgpack().unwrap();

        b.iter(|| {
            let deserialized = Checkpoint::from_msgpack(&data).unwrap();
            std::hint::black_box(deserialized);
        })
    });

    #[cfg(feature = "compression")]
    c.bench_function("checkpoint_compressed_serialization", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );

        b.iter(|| {
            let data = checkpoint.to_compressed_json().unwrap();
            std::hint::black_box(data);
        })
    });

    #[cfg(feature = "compression")]
    c.bench_function("checkpoint_compressed_deserialization", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test".to_string(),
            serde_json::Value::String("value".to_string()),
        );
        let data = checkpoint.to_compressed_json().unwrap();

        b.iter(|| {
            let deserialized = Checkpoint::from_compressed_json(&data).unwrap();
            std::hint::black_box(deserialized);
        })
    });
}

fn benchmark_pregel_execution(c: &mut Criterion) {
    c.bench_function("pregel_executor_creation", |b| {
        b.iter(|| {
            let executor: PregelExecutor<i32, i32> = PregelExecutor::new();
            std::hint::black_box(executor);
        })
    });

    c.bench_function("pregel_node_creation", |b| {
        b.iter(|| {
            let node = PregelNode {
                id: "test_node".to_string(),
                triggers: vec!["input".to_string()],
                channels: vec!["input".to_string()],
                processor: Arc::new(|x: i32| Ok(x * 2)),
            };
            std::hint::black_box(node);
        })
    });
}

fn benchmark_memory_usage(c: &mut Criterion) {
    c.bench_function("checkpoint_memory_usage", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test1".to_string(),
            serde_json::Value::String("value1".to_string()),
        );
        checkpoint.channel_values.insert(
            "test2".to_string(),
            serde_json::Value::String("value2".to_string()),
        );
        checkpoint.channel_values.insert(
            "test3".to_string(),
            serde_json::Value::String("value3".to_string()),
        );

        b.iter(|| {
            let usage = checkpoint.memory_usage();
            std::hint::black_box(usage);
        })
    });

    c.bench_function("checkpoint_serialized_size", |b| {
        let mut checkpoint = Checkpoint::new();
        checkpoint.channel_values.insert(
            "test1".to_string(),
            serde_json::Value::String("value1".to_string()),
        );
        checkpoint.channel_values.insert(
            "test2".to_string(),
            serde_json::Value::String("value2".to_string()),
        );
        checkpoint.channel_values.insert(
            "test3".to_string(),
            serde_json::Value::String("value3".to_string()),
        );

        b.iter(|| {
            let size = checkpoint.serialized_size().unwrap();
            std::hint::black_box(size);
        })
    });
}

criterion_group!(
    benches,
    benchmark_channel_operations,
    benchmark_checkpoint_operations,
    benchmark_pregel_execution,
    benchmark_memory_usage
);
criterion_main!(benches);
