use pyo3::prelude::*;
use pyo3::types::PyBytes;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};

#[cfg(feature = "sqlite")]
use rusqlite::{params, Connection, Result as SqliteResult};

/// Cached LLM response
#[derive(Debug, Clone, Serialize, Deserialize)]
struct CachedResponse {
    response: Vec<u8>, // Pickled Python response
    timestamp: i64,
    hits: usize,
}

/// In-memory LLM response cache
#[pyclass(name = "RustLLMCache")]
pub struct RustLLMCache {
    cache: HashMap<u64, CachedResponse>,
    max_size: usize,
    hits: usize,
    misses: usize,
}

#[pymethods]
impl RustLLMCache {
    #[new]
    #[pyo3(signature = (max_size=1000))]
    fn new(max_size: usize) -> Self {
        RustLLMCache {
            cache: HashMap::new(),
            max_size,
            hits: 0,
            misses: 0,
        }
    }

    /// Get a cached response by prompt hash
    fn get(&mut self, py: Python, prompt: &str) -> PyResult<Option<PyObject>> {
        let hash = self.hash_prompt(prompt);

        if let Some(cached) = self.cache.get_mut(&hash) {
            // Update hit count and stats
            cached.hits += 1;
            self.hits += 1;

            // Deserialize response
            let pickle = py.import("pickle")?;
            let loads = pickle.getattr("loads")?;
            let py_bytes = PyBytes::new(py, &cached.response);
            let response = loads.call1((py_bytes,))?;

            Ok(Some(response.to_object(py)))
        } else {
            self.misses += 1;
            Ok(None)
        }
    }

    /// Cache a response for a prompt
    fn put(&mut self, py: Python, prompt: &str, response: PyObject) -> PyResult<()> {
        let hash = self.hash_prompt(prompt);

        // Serialize response using pickle
        let pickle = py.import("pickle")?;
        let dumps = pickle.getattr("dumps")?;
        let serialized: &PyBytes = dumps.call1((response,))?.downcast()?;

        // Get current timestamp
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        let cached_response = CachedResponse {
            response: serialized.as_bytes().to_vec(),
            timestamp,
            hits: 0,
        };

        // Check cache size and evict if necessary
        if self.cache.len() >= self.max_size && !self.cache.contains_key(&hash) {
            // Simple LRU: evict the entry with lowest hits
            if let Some((&key_to_remove, _)) = self.cache.iter().min_by_key(|(_, v)| v.hits) {
                self.cache.remove(&key_to_remove);
            }
        }

        self.cache.insert(hash, cached_response);
        Ok(())
    }

    /// Clear the cache
    fn clear(&mut self) {
        self.cache.clear();
        self.hits = 0;
        self.misses = 0;
    }

    /// Get cache statistics
    fn stats(&self) -> HashMap<String, usize> {
        let mut stats = HashMap::new();
        stats.insert("size".to_string(), self.cache.len());
        stats.insert("max_size".to_string(), self.max_size);
        stats.insert("hits".to_string(), self.hits);
        stats.insert("misses".to_string(), self.misses);

        let hit_rate = if self.hits + self.misses > 0 {
            (self.hits as f64 / (self.hits + self.misses) as f64 * 100.0) as usize
        } else {
            0
        };
        stats.insert("hit_rate_percent".to_string(), hit_rate);

        stats
    }

    /// Get the number of cache entries
    fn __len__(&self) -> usize {
        self.cache.len()
    }

    /// Check if a prompt is cached
    fn contains(&self, prompt: &str) -> bool {
        let hash = self.hash_prompt(prompt);
        self.cache.contains_key(&hash)
    }
}

impl RustLLMCache {
    fn hash_prompt(&self, prompt: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        prompt.hash(&mut hasher);
        hasher.finish()
    }
}

/// SQLite-backed LLM response cache
#[cfg(feature = "sqlite")]
#[pyclass(name = "RustSQLiteLLMCache")]
pub struct RustSQLiteLLMCache {
    db_path: String,
    hits: usize,
    misses: usize,
    max_age_seconds: Option<i64>,
}

#[cfg(feature = "sqlite")]
#[pymethods]
impl RustSQLiteLLMCache {
    #[new]
    #[pyo3(signature = (db_path, max_age_seconds=None))]
    fn new(db_path: String, max_age_seconds: Option<i64>) -> PyResult<Self> {
        let cache = RustSQLiteLLMCache {
            db_path,
            hits: 0,
            misses: 0,
            max_age_seconds,
        };

        cache.init_db()?;
        Ok(cache)
    }

    /// Get a cached response by prompt
    fn get(&mut self, py: Python, prompt: &str) -> PyResult<Option<PyObject>> {
        let hash = self.hash_prompt(prompt);

        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        // Check for max age
        let cutoff_time = if let Some(max_age) = self.max_age_seconds {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs() as i64;
            Some(now - max_age)
        } else {
            None
        };

        let result: SqliteResult<(Vec<u8>, i64)> = if let Some(cutoff) = cutoff_time {
            conn.query_row(
                "SELECT response, timestamp FROM llm_cache WHERE hash = ?1 AND timestamp >= ?2",
                params![hash.to_string(), cutoff],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
        } else {
            conn.query_row(
                "SELECT response, timestamp FROM llm_cache WHERE hash = ?1",
                params![hash.to_string()],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
        };

        match result {
            Ok((response_bytes, _)) => {
                // Update hit count
                conn.execute(
                    "UPDATE llm_cache SET hits = hits + 1 WHERE hash = ?1",
                    params![hash.to_string()],
                )
                .ok();

                self.hits += 1;

                // Deserialize response
                let pickle = py.import("pickle")?;
                let loads = pickle.getattr("loads")?;
                let py_bytes = PyBytes::new(py, &response_bytes);
                let response = loads.call1((py_bytes,))?;

                Ok(Some(response.to_object(py)))
            }
            Err(rusqlite::Error::QueryReturnedNoRows) => {
                self.misses += 1;
                Ok(None)
            }
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!(
                "Query error: {}",
                e
            ))),
        }
    }

    /// Cache a response for a prompt
    fn put(&mut self, py: Python, prompt: &str, response: PyObject) -> PyResult<()> {
        let hash = self.hash_prompt(prompt);

        // Serialize response using pickle
        let pickle = py.import("pickle")?;
        let dumps = pickle.getattr("dumps")?;
        let serialized: &PyBytes = dumps.call1((response,))?.downcast()?;

        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (hash, prompt, response, timestamp, hits)
             VALUES (?1, ?2, ?3, ?4, 0)",
            params![hash.to_string(), prompt, serialized.as_bytes(), timestamp],
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Insert error: {}", e)))?;

        Ok(())
    }

    /// Clear the cache
    fn clear(&mut self) -> PyResult<()> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        conn.execute("DELETE FROM llm_cache", [])
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Delete error: {}", e)))?;

        self.hits = 0;
        self.misses = 0;
        Ok(())
    }

    /// Get cache statistics
    fn stats(&self) -> PyResult<HashMap<String, usize>> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let size: usize = conn
            .query_row("SELECT COUNT(*) FROM llm_cache", [], |row| row.get(0))
            .unwrap_or(0);

        let total_hits: usize = conn
            .query_row("SELECT SUM(hits) FROM llm_cache", [], |row| row.get(0))
            .unwrap_or(0);

        let mut stats = HashMap::new();
        stats.insert("size".to_string(), size);
        stats.insert("hits".to_string(), self.hits);
        stats.insert("misses".to_string(), self.misses);
        stats.insert("total_cache_hits".to_string(), total_hits);

        let hit_rate = if self.hits + self.misses > 0 {
            (self.hits as f64 / (self.hits + self.misses) as f64 * 100.0) as usize
        } else {
            0
        };
        stats.insert("hit_rate_percent".to_string(), hit_rate);

        Ok(stats)
    }

    /// Remove expired entries
    fn cleanup(&self) -> PyResult<usize> {
        if let Some(max_age) = self.max_age_seconds {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs() as i64;
            let cutoff = now - max_age;

            let conn = Connection::open(&self.db_path).map_err(|e| {
                pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e))
            })?;

            let rows_deleted = conn
                .execute(
                    "DELETE FROM llm_cache WHERE timestamp < ?1",
                    params![cutoff],
                )
                .map_err(|e| {
                    pyo3::exceptions::PyIOError::new_err(format!("Delete error: {}", e))
                })?;

            Ok(rows_deleted)
        } else {
            Ok(0)
        }
    }

    /// Check if a prompt is cached
    fn contains(&self, prompt: &str) -> PyResult<bool> {
        let hash = self.hash_prompt(prompt);

        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let count: usize = conn
            .query_row(
                "SELECT COUNT(*) FROM llm_cache WHERE hash = ?1",
                params![hash.to_string()],
                |row| row.get(0),
            )
            .unwrap_or(0);

        Ok(count > 0)
    }
}

#[cfg(feature = "sqlite")]
impl RustSQLiteLLMCache {
    fn init_db(&self) -> PyResult<()> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS llm_cache (
                hash TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                response BLOB NOT NULL,
                timestamp INTEGER NOT NULL,
                hits INTEGER DEFAULT 0
            )",
            [],
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Create table error: {}", e)))?;

        // Create index for timestamp-based queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON llm_cache(timestamp)",
            [],
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Create index error: {}", e)))?;

        Ok(())
    }

    fn hash_prompt(&self, prompt: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        prompt.hash(&mut hasher);
        hasher.finish()
    }
}

/// Register LLM cache module
pub fn register_llm_cache(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustLLMCache>()?;

    #[cfg(feature = "sqlite")]
    m.add_class::<RustSQLiteLLMCache>()?;

    Ok(())
}
