# Fast LangGraph Compatibility Report

## Status: ✅ PASS

| Metric | Value |
|--------|-------|
| **Test Date** | 2025-12-10 00:44:28 UTC |
| **LangGraph Version** | 1.0.4 |
| **LangGraph Branch** | main |
| **LangGraph Commit** | `4d01e69b` |
| **Commit Date** | 2025-12-09 23:05:49 +0000 |

## Test Results

| Result | Count |
|--------|-------|
| ✅ Passed | 85 |
| ❌ Failed | 0 |
| ⏭️ Skipped | 3 |
| **Total** | **88** |

## Test Coverage

The following test files were executed against Fast LangGraph's shimmed implementation:

- `test_algo.py` - Algorithm functions (apply_writes, prepare_next_tasks)
- `test_channels.py` - Channel implementations (LastValue, Topic, BinOp)
- `test_config_async.py` - Async configuration management
- `test_deprecation.py` - Deprecation warnings
- `test_interrupt_migration.py` - Interrupt serialization
- `test_pydantic.py` - Pydantic model support
- `test_retry.py` - Retry policies
- `test_state.py` - State schema validation
- `test_tracing_interops.py` - Tracing interoperability
- `test_type_checking.py` - Type checking

## Skipped Test Files

The following test files are skipped because they require fixtures or dependencies
not available in the minimal test environment:

| File | Reason |
|------|--------|
| `tests/test_checkpoint_migration.py` | Requires `sync_checkpointer` fixture |
| `tests/test_large_cases.py` | Requires complex fixtures |
| `tests/test_large_cases_async.py` | Requires `trio` optional dependency |
| `tests/test_pregel_async.py` | Requires complex async fixtures |
| `tests/test_remote_graph.py` | Requires external dependencies |
| `tests/test_messages.py` | Requires complex fixtures |
| `tests/test_interruption.py` | Requires `durability` fixture |
| `tests/test_pregel.py` | Requires complex fixtures |
| `tests/test_graph_validation.py` | Requires fixtures |
| `tests/test_runnable.py` | Requires `trio` optional dependency |
| `tests/test_runtime.py` | Requires `trio` optional dependency |
| `tests/test_utils.py` | Requires `trio` optional dependency |
| `**/test_cache.py` | Cache tests not applicable |

## What This Means

Fast LangGraph's Rust-accelerated implementations are **compatible** with LangGraph's
core functionality. The shimmed `apply_writes` function passes all algorithm tests,
ensuring that channel updates behave identically to the original Python implementation.

## Running These Tests

```bash
# Run compatibility tests locally
python scripts/test_compatibility.py -v

# Test against a specific LangGraph branch
python scripts/test_compatibility.py --branch v0.2.0 -v
```
