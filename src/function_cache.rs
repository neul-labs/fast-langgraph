use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyTuple};
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};

/// Fast function result caching with LRU eviction
///
/// This provides a high-performance memoization layer for expensive
/// function calls, reducing redundant computation in hot paths.
/// Cached function result with hit tracking
#[derive(Clone)]
struct CachedResult {
    result: Vec<u8>, // Pickled Python object
    hits: usize,
    timestamp: f64,
}

/// Function result cache with LRU eviction
#[pyclass(name = "RustFunctionCache")]
pub struct RustFunctionCache {
    cache: HashMap<u64, CachedResult>,
    max_size: usize,
    hits: usize,
    misses: usize,
}

#[pymethods]
impl RustFunctionCache {
    /// Create a new function cache
    #[new]
    #[pyo3(signature = (max_size=1000))]
    fn new(max_size: usize) -> Self {
        RustFunctionCache {
            cache: HashMap::new(),
            max_size,
            hits: 0,
            misses: 0,
        }
    }

    /// Hash function arguments to create cache key
    fn hash_args(&self, py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<u64> {
        let mut hasher = DefaultHasher::new();

        // Hash args
        let pickle = py.import("pickle")?;
        let dumps = pickle.getattr("dumps")?;
        let serialized: &PyBytes = dumps.call1((args,))?.downcast()?;
        serialized.as_bytes().hash(&mut hasher);

        // Hash kwargs if present
        if let Some(kw) = kwargs {
            let serialized: &PyBytes = dumps.call1((kw,))?.downcast()?;
            serialized.as_bytes().hash(&mut hasher);
        }

        Ok(hasher.finish())
    }

    /// Get cached result if available
    fn get(
        &mut self,
        py: Python,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<Option<PyObject>> {
        let hash = self.hash_args(py, args, kwargs)?;

        if let Some(cached) = self.cache.get_mut(&hash) {
            cached.hits += 1;
            self.hits += 1;

            let pickle = py.import("pickle")?;
            let loads = pickle.getattr("loads")?;
            let py_bytes = PyBytes::new(py, &cached.result);
            let result = loads.call1((py_bytes,))?;

            Ok(Some(result.to_object(py)))
        } else {
            self.misses += 1;
            Ok(None)
        }
    }

    /// Store result in cache
    #[pyo3(signature = (args, result, kwargs=None))]
    fn put(
        &mut self,
        py: Python,
        args: &PyTuple,
        result: PyObject,
        kwargs: Option<&PyDict>,
    ) -> PyResult<()> {
        let hash = self.hash_args(py, args, kwargs)?;

        // Serialize result
        let pickle = py.import("pickle")?;
        let dumps = pickle.getattr("dumps")?;
        let serialized: &PyBytes = dumps.call1((result,))?.downcast()?;

        // LRU eviction if cache is full
        if self.cache.len() >= self.max_size && !self.cache.contains_key(&hash) {
            // Find least recently used (lowest hits)
            if let Some((&key_to_remove, _)) = self.cache.iter().min_by_key(|(_, v)| v.hits) {
                self.cache.remove(&key_to_remove);
            }
        }

        // Get current timestamp
        let time = py.import("time")?;
        let timestamp: f64 = time.getattr("time")?.call0()?.extract()?;

        self.cache.insert(
            hash,
            CachedResult {
                result: serialized.as_bytes().to_vec(),
                hits: 0,
                timestamp,
            },
        );

        Ok(())
    }

    /// Clear all cached results
    fn clear(&mut self) -> PyResult<()> {
        self.cache.clear();
        self.hits = 0;
        self.misses = 0;
        Ok(())
    }

    /// Get cache statistics
    fn stats(&self, py: Python) -> PyResult<PyObject> {
        let stats = PyDict::new(py);
        stats.set_item("size", self.cache.len())?;
        stats.set_item("max_size", self.max_size)?;
        stats.set_item("hits", self.hits)?;
        stats.set_item("misses", self.misses)?;

        let total = self.hits + self.misses;
        let hit_rate = if total > 0 {
            (self.hits as f64) / (total as f64)
        } else {
            0.0
        };
        stats.set_item("hit_rate", hit_rate)?;

        Ok(stats.into())
    }

    /// Check if arguments are in cache
    fn contains(&self, py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<bool> {
        let hash = self.hash_args(py, args, kwargs)?;
        Ok(self.cache.contains_key(&hash))
    }

    /// Invalidate specific cache entry
    fn invalidate(
        &mut self,
        py: Python,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<bool> {
        let hash = self.hash_args(py, args, kwargs)?;
        Ok(self.cache.remove(&hash).is_some())
    }

    /// Get cache size
    fn __len__(&self) -> PyResult<usize> {
        Ok(self.cache.len())
    }

    /// String representation
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!(
            "RustFunctionCache(size={}/{}, hits={}, misses={}, hit_rate={:.2}%)",
            self.cache.len(),
            self.max_size,
            self.hits,
            self.misses,
            if self.hits + self.misses > 0 {
                100.0 * (self.hits as f64) / ((self.hits + self.misses) as f64)
            } else {
                0.0
            }
        ))
    }
}

/// Decorator for caching function results
#[pyclass(name = "cached")]
pub struct CachedDecorator {
    cache: Py<RustFunctionCache>,
    func: PyObject,
}

#[pymethods]
impl CachedDecorator {
    /// Create a new cached decorator
    #[new]
    #[pyo3(signature = (func, max_size=1000))]
    fn new(py: Python, func: PyObject, max_size: usize) -> PyResult<Self> {
        let cache = Py::new(py, RustFunctionCache::new(max_size))?;
        Ok(CachedDecorator { cache, func })
    }

    /// Call the decorated function with caching
    fn __call__(
        &mut self,
        py: Python,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<PyObject> {
        let mut cache = self.cache.borrow_mut(py);

        // Check cache first
        if let Some(cached_result) = cache.get(py, args, kwargs)? {
            return Ok(cached_result);
        }

        // Cache miss - call original function
        let result = if let Some(kw) = kwargs {
            self.func.call(py, args, Some(kw))?
        } else {
            self.func.call1(py, args)?
        };

        // Store in cache
        cache.put(py, args, result.clone_ref(py), kwargs)?;

        Ok(result)
    }

    /// Get cache statistics
    fn cache_stats(&self, py: Python) -> PyResult<PyObject> {
        self.cache.borrow(py).stats(py)
    }

    /// Clear cache
    fn cache_clear(&mut self, py: Python) -> PyResult<()> {
        self.cache.borrow_mut(py).clear()
    }

    /// Check if result is cached
    fn cache_contains(
        &self,
        py: Python,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<bool> {
        self.cache.borrow(py).contains(py, args, kwargs)
    }

    /// Get the wrapped function
    #[getter]
    fn __wrapped__(&self, py: Python) -> PyResult<PyObject> {
        Ok(self.func.clone_ref(py))
    }

    /// String representation
    fn __repr__(&self, py: Python) -> PyResult<String> {
        let cache = self.cache.borrow(py);
        Ok(format!(
            "cached({}, cache={})",
            self.func.as_ref(py).repr()?,
            cache.__repr__()?
        ))
    }
}

/// Time-based cache that invalidates entries after TTL
#[pyclass(name = "RustTTLCache")]
pub struct RustTTLCache {
    cache: HashMap<u64, CachedResult>,
    max_size: usize,
    ttl: f64, // Time to live in seconds
    hits: usize,
    misses: usize,
}

#[pymethods]
impl RustTTLCache {
    /// Create a new TTL cache
    #[new]
    #[pyo3(signature = (max_size=1000, ttl=3600.0))]
    fn new(max_size: usize, ttl: f64) -> Self {
        RustTTLCache {
            cache: HashMap::new(),
            max_size,
            ttl,
            hits: 0,
            misses: 0,
        }
    }

    /// Hash function arguments
    fn hash_args(&self, py: Python, args: &PyTuple, kwargs: Option<&PyDict>) -> PyResult<u64> {
        let mut hasher = DefaultHasher::new();

        let pickle = py.import("pickle")?;
        let dumps = pickle.getattr("dumps")?;
        let serialized: &PyBytes = dumps.call1((args,))?.downcast()?;
        serialized.as_bytes().hash(&mut hasher);

        if let Some(kw) = kwargs {
            let serialized: &PyBytes = dumps.call1((kw,))?.downcast()?;
            serialized.as_bytes().hash(&mut hasher);
        }

        Ok(hasher.finish())
    }

    /// Get cached result if not expired
    fn get(
        &mut self,
        py: Python,
        args: &PyTuple,
        kwargs: Option<&PyDict>,
    ) -> PyResult<Option<PyObject>> {
        let hash = self.hash_args(py, args, kwargs)?;

        // Get current time
        let time = py.import("time")?;
        let now: f64 = time.getattr("time")?.call0()?.extract()?;

        if let Some(cached) = self.cache.get_mut(&hash) {
            // Check if expired
            if now - cached.timestamp > self.ttl {
                // Entry expired, remove it
                self.cache.remove(&hash);
                self.misses += 1;
                return Ok(None);
            }

            cached.hits += 1;
            self.hits += 1;

            let pickle = py.import("pickle")?;
            let loads = pickle.getattr("loads")?;
            let py_bytes = PyBytes::new(py, &cached.result);
            let result = loads.call1((py_bytes,))?;

            Ok(Some(result.to_object(py)))
        } else {
            self.misses += 1;
            Ok(None)
        }
    }

    /// Store result in cache
    #[pyo3(signature = (args, result, kwargs=None))]
    fn put(
        &mut self,
        py: Python,
        args: &PyTuple,
        result: PyObject,
        kwargs: Option<&PyDict>,
    ) -> PyResult<()> {
        let hash = self.hash_args(py, args, kwargs)?;

        let pickle = py.import("pickle")?;
        let dumps = pickle.getattr("dumps")?;
        let serialized: &PyBytes = dumps.call1((result,))?.downcast()?;

        // LRU eviction if full
        if self.cache.len() >= self.max_size && !self.cache.contains_key(&hash) {
            if let Some((&key_to_remove, _)) = self.cache.iter().min_by_key(|(_, v)| v.hits) {
                self.cache.remove(&key_to_remove);
            }
        }

        let time = py.import("time")?;
        let timestamp: f64 = time.getattr("time")?.call0()?.extract()?;

        self.cache.insert(
            hash,
            CachedResult {
                result: serialized.as_bytes().to_vec(),
                hits: 0,
                timestamp,
            },
        );

        Ok(())
    }

    /// Clear all cached results
    fn clear(&mut self) -> PyResult<()> {
        self.cache.clear();
        self.hits = 0;
        self.misses = 0;
        Ok(())
    }

    /// Get cache statistics
    fn stats(&self, py: Python) -> PyResult<PyObject> {
        let stats = PyDict::new(py);
        stats.set_item("size", self.cache.len())?;
        stats.set_item("max_size", self.max_size)?;
        stats.set_item("ttl", self.ttl)?;
        stats.set_item("hits", self.hits)?;
        stats.set_item("misses", self.misses)?;

        let total = self.hits + self.misses;
        let hit_rate = if total > 0 {
            (self.hits as f64) / (total as f64)
        } else {
            0.0
        };
        stats.set_item("hit_rate", hit_rate)?;

        Ok(stats.into())
    }

    /// Clean expired entries
    fn cleanup(&mut self, py: Python) -> PyResult<usize> {
        let time = py.import("time")?;
        let now: f64 = time.getattr("time")?.call0()?.extract()?;

        let expired_keys: Vec<u64> = self
            .cache
            .iter()
            .filter(|(_, v)| now - v.timestamp > self.ttl)
            .map(|(k, _)| *k)
            .collect();

        let count = expired_keys.len();
        for key in expired_keys {
            self.cache.remove(&key);
        }

        Ok(count)
    }
}

/// Register function cache module
pub fn register_function_cache(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustFunctionCache>()?;
    m.add_class::<CachedDecorator>()?;
    m.add_class::<RustTTLCache>()?;
    Ok(())
}
