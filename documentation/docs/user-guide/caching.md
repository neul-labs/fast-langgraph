# Caching

Fast-LangGraph provides multiple caching options for different use cases.

## Overview

| Cache Type | Use Case | Features |
|------------|----------|----------|
| `@cached` decorator | Function memoization | Simple, automatic |
| `RustLLMCache` | LLM response caching | Manual control, stats |
| `RustTTLCache` | Time-based caching | Auto-expiration |

## The @cached Decorator

The simplest way to add caching to any function.

### Basic Usage

```python
from fast_langgraph import cached

@cached
def expensive_computation(x, y):
    # This runs only once per unique (x, y)
    return complex_calculation(x, y)
```

### With Size Limit

```python
@cached(max_size=1000)
def call_llm(prompt):
    return llm.invoke(prompt)
```

When the cache reaches `max_size`, the least recently used entries are evicted.

### Cache Management

```python
@cached(max_size=500)
def my_function(arg):
    return result

# Get cache statistics
stats = my_function.cache_stats()
print(stats)
# {'hits': 42, 'misses': 10, 'size': 10}

# Clear all cached entries
my_function.cache_clear()
```

### How Cache Keys Work

The cache key is computed from all function arguments:

```python
@cached
def search(query, limit=10):
    return db.search(query, limit)

# These are different cache entries:
search("hello")           # key: ("hello", 10)
search("hello", limit=20) # key: ("hello", 20)
search("world")           # key: ("world", 10)
```

### Caching with Complex Arguments

For complex objects, convert to hashable types:

```python
@cached
def process_messages(messages_tuple):
    messages = list(messages_tuple)
    return llm.invoke(messages)

# Convert list to tuple for caching
messages = [HumanMessage(content="Hello")]
result = process_messages(tuple(str(m) for m in messages))
```

## RustLLMCache

Direct cache access for fine-grained control.

### Basic Usage

```python
from fast_langgraph import RustLLMCache

cache = RustLLMCache(max_size=1000)

# Store a value
cache.put("prompt1", "response1")

# Retrieve a value
result = cache.get("prompt1")  # Returns "response1"
result = cache.get("unknown")  # Returns None

# Check statistics
stats = cache.stats()
print(stats)  # {'hits': 1, 'misses': 1, 'size': 1}
```

### Manual Caching Pattern

```python
from fast_langgraph import RustLLMCache

cache = RustLLMCache(max_size=1000)

def cached_llm_call(prompt):
    # Check cache first
    result = cache.get(prompt)
    if result is not None:
        return result

    # Cache miss - call LLM
    result = llm.invoke(prompt)
    cache.put(prompt, result)
    return result
```

### When to Use RustLLMCache vs @cached

| Use `@cached` when... | Use `RustLLMCache` when... |
|-----------------------|---------------------------|
| Caching a single function | Sharing cache across functions |
| Simple key-value caching | Need custom key generation |
| Don't need cache control | Need to clear specific entries |

## RustTTLCache

Cache with automatic time-based expiration.

### Basic Usage

```python
from fast_langgraph import RustTTLCache

# Entries expire after 300 seconds (5 minutes)
cache = RustTTLCache(max_size=1000, ttl=300.0)

cache.put("session_data", {"user": "alice"})
result = cache.get("session_data")  # Returns the dict

# After 5 minutes...
result = cache.get("session_data")  # Returns None
```

### Use Cases

**API Rate Limiting:**

```python
rate_cache = RustTTLCache(max_size=10000, ttl=60.0)

def check_rate_limit(user_id):
    count = rate_cache.get(user_id) or 0
    if count >= 100:
        raise RateLimitError("Too many requests")
    rate_cache.put(user_id, count + 1)
```

**Session Data:**

```python
session_cache = RustTTLCache(max_size=5000, ttl=3600.0)  # 1 hour

def get_user_session(session_id):
    return session_cache.get(session_id)

def set_user_session(session_id, data):
    session_cache.put(session_id, data)
```

**Caching External API Responses:**

```python
api_cache = RustTTLCache(max_size=1000, ttl=600.0)  # 10 minutes

def fetch_weather(city):
    cached = api_cache.get(city)
    if cached:
        return cached

    result = weather_api.get(city)
    api_cache.put(city, result)
    return result
```

## Common Patterns

### Multi-Level Caching for RAG

```python
from fast_langgraph import cached, RustTTLCache

# Level 1: Cache embeddings (long-lived)
@cached(max_size=10000)
def get_embedding(text):
    return embedding_model.embed(text)

# Level 2: Cache retrieval results (medium-lived)
retrieval_cache = RustTTLCache(max_size=1000, ttl=300.0)

def retrieve_documents(query):
    cached = retrieval_cache.get(query)
    if cached:
        return cached

    embedding = get_embedding(query)
    docs = vector_store.search(embedding)
    retrieval_cache.put(query, docs)
    return docs

# Level 3: Cache LLM responses (varies by use case)
@cached(max_size=500)
def generate_answer(query, context_tuple):
    context = "\n".join(context_tuple)
    return llm.invoke(f"Context: {context}\n\nQuestion: {query}")
```

### Caching with Fallback

```python
from fast_langgraph import RustLLMCache

primary_cache = RustLLMCache(max_size=1000)
fallback_cache = RustLLMCache(max_size=10000)  # Larger, slower

def cached_call(key, compute_fn):
    # Try primary cache
    result = primary_cache.get(key)
    if result:
        return result

    # Try fallback cache
    result = fallback_cache.get(key)
    if result:
        primary_cache.put(key, result)  # Promote to primary
        return result

    # Compute and cache in both
    result = compute_fn()
    primary_cache.put(key, result)
    fallback_cache.put(key, result)
    return result
```

### Cache Warmup

```python
from fast_langgraph import RustLLMCache

cache = RustLLMCache(max_size=1000)

def warm_cache(common_queries):
    """Pre-populate cache with common queries."""
    for query in common_queries:
        result = llm.invoke(query)
        cache.put(query, result)
    print(f"Warmed cache with {len(common_queries)} entries")
```

## Performance Tips

1. **Choose appropriate cache size** - Too small causes evictions, too large wastes memory

2. **Use TTL for changing data** - API responses, session data, etc.

3. **Cache at the right level** - Cache LLM calls, not individual words

4. **Monitor hit rates** - Low hit rate means cache isn't helping:

```python
stats = my_function.cache_stats()
hit_rate = stats['hits'] / (stats['hits'] + stats['misses'])
if hit_rate < 0.5:
    print("Consider different caching strategy")
```

## Next Steps

- [Checkpointing](checkpointing.md) - State persistence
- [Profiling](profiling.md) - Measure cache effectiveness
