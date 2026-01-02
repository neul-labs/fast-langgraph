# Configuration

Configure Fast-LangGraph behavior through environment variables and runtime settings.

## Environment Variables

### FAST_LANGGRAPH_AUTO_PATCH

Automatically apply acceleration patches when Fast-LangGraph is imported.

| Value | Behavior |
|-------|----------|
| `0` (default) | Manual patching required |
| `1` | Auto-patch on import |

**Usage:**

```bash
# Enable auto-patching
export FAST_LANGGRAPH_AUTO_PATCH=1
python your_app.py
```

Equivalent to calling:

```python
import fast_langgraph
fast_langgraph.shim.patch_langgraph()
```

### FAST_LANGGRAPH_LOG_LEVEL

Control logging verbosity.

| Value | Description |
|-------|-------------|
| `DEBUG` | Detailed debugging information |
| `INFO` | General operational messages |
| `WARNING` (default) | Warnings and errors only |
| `ERROR` | Errors only |

**Usage:**

```bash
export FAST_LANGGRAPH_LOG_LEVEL=DEBUG
python your_app.py
```

## Runtime Configuration

### Cache Sizes

Configure cache sizes based on your workload:

```python
from fast_langgraph import cached, RustLLMCache, RustTTLCache

# Function cache
@cached(max_size=1000)  # 1000 entries
def my_function(arg):
    pass

# Direct cache
llm_cache = RustLLMCache(max_size=5000)
ttl_cache = RustTTLCache(max_size=1000, ttl=300.0)
```

**Sizing Guidelines:**

| Workload | Recommended Size | Memory (approx) |
|----------|------------------|-----------------|
| Light | 100-500 | ~1-5 MB |
| Medium | 1000-5000 | ~10-50 MB |
| Heavy | 10000+ | ~100+ MB |

Memory depends on cached value sizes.

### TTL Values

For `RustTTLCache`, choose TTL based on data freshness requirements:

| Use Case | Suggested TTL |
|----------|---------------|
| Session data | 3600s (1 hour) |
| API responses | 300-600s (5-10 min) |
| Rate limiting | 60s (1 min) |
| Real-time data | 5-30s |

### Checkpointer Path

```python
from fast_langgraph import RustSQLiteCheckpointer

# File-based (persistent)
checkpointer = RustSQLiteCheckpointer("./data/checkpoints.db")

# In-memory (testing)
checkpointer = RustSQLiteCheckpointer(":memory:")

# Absolute path
checkpointer = RustSQLiteCheckpointer("/var/lib/myapp/state.db")
```

## Production Configuration

### Recommended Settings

```python
# config.py
import os

# Auto-patch in production
os.environ.setdefault("FAST_LANGGRAPH_AUTO_PATCH", "1")
os.environ.setdefault("FAST_LANGGRAPH_LOG_LEVEL", "WARNING")

# Import after setting env vars
import fast_langgraph
from fast_langgraph import RustSQLiteCheckpointer, cached

# Production cache settings
LLM_CACHE_SIZE = int(os.getenv("LLM_CACHE_SIZE", "5000"))
CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "/var/lib/app/state.db")

@cached(max_size=LLM_CACHE_SIZE)
def call_llm(prompt):
    return llm.invoke(prompt)

checkpointer = RustSQLiteCheckpointer(CHECKPOINT_PATH)
```

### Docker Configuration

```dockerfile
FROM python:3.12-slim

# Set Fast-LangGraph configuration
ENV FAST_LANGGRAPH_AUTO_PATCH=1
ENV FAST_LANGGRAPH_LOG_LEVEL=WARNING
ENV LLM_CACHE_SIZE=5000
ENV CHECKPOINT_PATH=/data/state.db

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "main.py"]
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fast-langgraph-config
data:
  FAST_LANGGRAPH_AUTO_PATCH: "1"
  FAST_LANGGRAPH_LOG_LEVEL: "WARNING"
  LLM_CACHE_SIZE: "10000"
```

## Logging Configuration

### Basic Setup

```python
import logging

# Configure Fast-LangGraph logging
logging.getLogger("fast_langgraph").setLevel(logging.DEBUG)

# Add handler
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logging.getLogger("fast_langgraph").addHandler(handler)
```

### Structured Logging

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("fast_langgraph").addHandler(handler)
```

## Performance Tuning

### Memory vs Speed Trade-offs

| Setting | Higher Value | Lower Value |
|---------|--------------|-------------|
| Cache `max_size` | More hits, more memory | Less memory, more misses |
| TTL `ttl` | Fewer recomputes, staler data | Fresher data, more recomputes |

### Monitoring

```python
from fast_langgraph import cached
from fast_langgraph.shim import get_patch_status

@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)

def get_metrics():
    """Get performance metrics for monitoring."""
    cache_stats = call_llm.cache_stats()
    hit_rate = (
        cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
        if cache_stats['hits'] + cache_stats['misses'] > 0
        else 0
    )

    return {
        "cache_hit_rate": hit_rate,
        "cache_size": cache_stats['size'],
        "acceleration_status": get_patch_status(),
    }
```

## Troubleshooting

### Check Configuration

```python
import fast_langgraph
from fast_langgraph.shim import get_patch_status

print(f"Version: {fast_langgraph.__version__}")
print(f"Status: {get_patch_status()}")
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Patches not applied | Import order | Set env var or call `patch_langgraph()` first |
| Cache not helping | Low hit rate | Increase `max_size` or check key generation |
| Memory growth | Unbounded cache | Set `max_size` limit |
| Stale data | Long TTL | Reduce TTL or use non-TTL cache |
