/// Performance comparison benchmark between estimated Python and actual Rust performance
use criterion::{criterion_group, criterion_main, Criterion};
use langgraph_rs::channels::{Channel, LastValueChannel};
use langgraph_rs::checkpoint::Checkpoint;
use serde_json;

fn benchmark_channel_vs_estimated_python(c: &mut Criterion) {
    c.bench_function("rust_last_value_channel_update", |b| {
        b.iter(|| {
            let mut channel = LastValueChannel::<i32>::new();
            let _ = channel.update(vec![42]);
        })
    });

    c.bench_function("rust_last_value_channel_get", |b| {
        let channel = LastValueChannel::with_value(42);
        b.iter(|| {
            let _ = channel.get();
        })
    });

    c.bench_function("rust_checkpoint_creation", |b| {
        b.iter(|| {
            let checkpoint = Checkpoint::new();
            std::hint::black_box(checkpoint);
        })
    });

    c.bench_function("rust_checkpoint_json_serialization", |b| {
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

    c.bench_function("rust_checkpoint_json_deserialization", |b| {
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
}

criterion_group!(benches, benchmark_channel_vs_estimated_python);
criterion_main!(benches);
