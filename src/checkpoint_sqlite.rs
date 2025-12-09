use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
#[allow(unused_imports)]
use serde::Deserialize;
use std::collections::HashMap;

#[cfg(feature = "sqlite")]
use rusqlite::{params, Connection, Result as SqliteResult};

#[cfg(feature = "compression-zstd")]
use zstd;

use crate::rust_checkpoint::CheckpointData;

/// Compression algorithm
#[derive(Debug, Clone, Copy)]
pub enum Compression {
    None,
    #[cfg(feature = "compression-zstd")]
    Zstd,
    #[cfg(feature = "compression-lz4")]
    Lz4,
}

impl Compression {
    fn compress(&self, data: &[u8]) -> Vec<u8> {
        match self {
            Compression::None => data.to_vec(),
            #[cfg(feature = "compression-zstd")]
            Compression::Zstd => zstd::encode_all(data, 3).unwrap_or_else(|_| data.to_vec()),
            #[cfg(feature = "compression-lz4")]
            Compression::Lz4 => {
                lz4::block::compress(data, None, true).unwrap_or_else(|_| data.to_vec())
            }
        }
    }

    fn decompress(&self, data: &[u8]) -> Vec<u8> {
        match self {
            Compression::None => data.to_vec(),
            #[cfg(feature = "compression-zstd")]
            Compression::Zstd => zstd::decode_all(data).unwrap_or_else(|_| data.to_vec()),
            #[cfg(feature = "compression-lz4")]
            Compression::Lz4 => {
                lz4::block::decompress(data, None).unwrap_or_else(|_| data.to_vec())
            }
        }
    }
}

/// SQLite-based checkpoint storage with optional compression
#[cfg(feature = "sqlite")]
#[pyclass(name = "RustSQLiteCheckpointer")]
pub struct RustSQLiteCheckpointer {
    db_path: String,
    compression: Compression,
}

#[cfg(feature = "sqlite")]
#[pymethods]
impl RustSQLiteCheckpointer {
    #[new]
    #[pyo3(signature = (db_path, compression=None))]
    fn new(db_path: String, compression: Option<&str>) -> PyResult<Self> {
        let comp = match compression {
            None => Compression::None,
            #[cfg(feature = "compression-zstd")]
            Some("zstd") => Compression::Zstd,
            #[cfg(feature = "compression-lz4")]
            Some("lz4") => Compression::Lz4,
            Some(other) => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Unknown compression: {}. Use 'zstd' or 'lz4'",
                    other
                )));
            }
        };

        let checkpointer = RustSQLiteCheckpointer {
            db_path,
            compression: comp,
        };

        // Initialize database
        checkpointer.init_db()?;

        Ok(checkpointer)
    }

    /// Save a checkpoint
    fn put(
        &self,
        py: Python,
        thread_id: String,
        checkpoint_id: String,
        checkpoint: &PyDict,
    ) -> PyResult<bool> {
        // Extract checkpoint data (reuse from rust_checkpoint.rs)
        let channel_values = self.extract_channel_values(py, checkpoint)?;
        let channel_versions = self.extract_versions(checkpoint, "channel_versions")?;
        let versions_seen = self.extract_versions_seen(checkpoint)?;
        let step = checkpoint
            .get_item("step")?
            .and_then(|v| v.extract::<usize>().ok())
            .unwrap_or(0);

        let checkpoint_data = CheckpointData {
            channel_values,
            channel_versions,
            versions_seen,
            pending_writes: Vec::new(),
            step,
        };

        // Serialize using MessagePack
        let serialized = rmp_serde::to_vec(&checkpoint_data).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Serialization error: {}", e))
        })?;

        // Compress if enabled
        let data = self.compression.compress(&serialized);

        // Store in SQLite
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        conn.execute(
            "INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_id, data, created_at)
             VALUES (?1, ?2, ?3, datetime('now'))",
            params![thread_id, checkpoint_id, data],
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Insert error: {}", e)))?;

        Ok(true)
    }

    /// Load a checkpoint
    fn get(
        &self,
        py: Python,
        thread_id: String,
        checkpoint_id: String,
    ) -> PyResult<Option<PyObject>> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let result: SqliteResult<Vec<u8>> = conn.query_row(
            "SELECT data FROM checkpoints WHERE thread_id = ?1 AND checkpoint_id = ?2",
            params![thread_id, checkpoint_id],
            |row| row.get(0),
        );

        match result {
            Ok(compressed_data) => {
                // Decompress if needed
                let serialized = self.compression.decompress(&compressed_data);

                // Deserialize using MessagePack
                let checkpoint_data: CheckpointData =
                    rmp_serde::from_slice(&serialized).map_err(|e| {
                        pyo3::exceptions::PyValueError::new_err(format!(
                            "Deserialization error: {}",
                            e
                        ))
                    })?;

                // Convert back to Python dict
                let result = self.checkpoint_data_to_py(py, &checkpoint_data)?;
                Ok(Some(result))
            }
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!(
                "Query error: {}",
                e
            ))),
        }
    }

    /// List all checkpoint IDs for a thread
    fn list_checkpoints(&self, thread_id: String) -> PyResult<Vec<String>> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let mut stmt = conn.prepare(
            "SELECT checkpoint_id FROM checkpoints WHERE thread_id = ?1 ORDER BY created_at DESC"
        ).map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Prepare error: {}", e)))?;

        let checkpoint_ids: Result<Vec<String>, _> = stmt
            .query_map(params![thread_id], |row| row.get(0))
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Query error: {}", e)))?
            .collect();

        checkpoint_ids
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Collection error: {}", e)))
    }

    /// Delete a checkpoint
    fn delete(&self, thread_id: String, checkpoint_id: String) -> PyResult<bool> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let rows = conn
            .execute(
                "DELETE FROM checkpoints WHERE thread_id = ?1 AND checkpoint_id = ?2",
                params![thread_id, checkpoint_id],
            )
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Delete error: {}", e)))?;

        Ok(rows > 0)
    }

    /// Clear all checkpoints for a thread
    fn clear_thread(&self, thread_id: String) -> PyResult<bool> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let rows = conn
            .execute(
                "DELETE FROM checkpoints WHERE thread_id = ?1",
                params![thread_id],
            )
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Delete error: {}", e)))?;

        Ok(rows > 0)
    }

    /// Get statistics about stored checkpoints
    fn stats(&self) -> PyResult<HashMap<String, usize>> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        let mut stats = HashMap::new();

        // Total threads
        let total_threads: usize = conn
            .query_row(
                "SELECT COUNT(DISTINCT thread_id) FROM checkpoints",
                [],
                |row| row.get(0),
            )
            .unwrap_or(0);

        // Total checkpoints
        let total_checkpoints: usize = conn
            .query_row("SELECT COUNT(*) FROM checkpoints", [], |row| row.get(0))
            .unwrap_or(0);

        // Total bytes
        let total_bytes: usize = conn
            .query_row("SELECT SUM(LENGTH(data)) FROM checkpoints", [], |row| {
                row.get(0)
            })
            .unwrap_or(0);

        stats.insert("total_threads".to_string(), total_threads);
        stats.insert("total_checkpoints".to_string(), total_checkpoints);
        stats.insert("total_bytes".to_string(), total_bytes);

        Ok(stats)
    }
}

#[cfg(feature = "sqlite")]
impl RustSQLiteCheckpointer {
    fn init_db(&self) -> PyResult<()> {
        let conn = Connection::open(&self.db_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Database error: {}", e)))?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                data BLOB NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (thread_id, checkpoint_id)
            )",
            [],
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Create table error: {}", e)))?;

        // Create index for faster lookups
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_thread_id ON checkpoints(thread_id)",
            [],
        )
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Create index error: {}", e)))?;

        Ok(())
    }

    // Helper methods (same as RustCheckpointer)
    fn extract_channel_values(
        &self,
        py: Python,
        checkpoint: &PyDict,
    ) -> PyResult<HashMap<String, Vec<u8>>> {
        let mut channel_values = HashMap::new();

        if let Ok(Some(channels)) = checkpoint.get_item("channel_values") {
            if let Ok(channels_dict) = channels.downcast::<PyDict>() {
                for (key, value) in channels_dict.iter() {
                    let key_str: String = key.extract()?;

                    // Serialize the value using pickle
                    let pickle = py.import("pickle")?;
                    let dumps = pickle.getattr("dumps")?;
                    let serialized: &PyBytes = dumps.call1((value,))?.downcast()?;

                    channel_values.insert(key_str, serialized.as_bytes().to_vec());
                }
            }
        }

        Ok(channel_values)
    }

    fn extract_versions(&self, checkpoint: &PyDict, key: &str) -> PyResult<HashMap<String, usize>> {
        let mut versions = HashMap::new();

        if let Ok(Some(versions_obj)) = checkpoint.get_item(key) {
            if let Ok(versions_dict) = versions_obj.downcast::<PyDict>() {
                for (k, v) in versions_dict.iter() {
                    let key_str: String = k.extract()?;
                    let version: usize = v.extract()?;
                    versions.insert(key_str, version);
                }
            }
        }

        Ok(versions)
    }

    fn extract_versions_seen(
        &self,
        checkpoint: &PyDict,
    ) -> PyResult<HashMap<String, HashMap<String, usize>>> {
        let mut versions_seen = HashMap::new();

        if let Ok(Some(vs_obj)) = checkpoint.get_item("versions_seen") {
            if let Ok(vs_dict) = vs_obj.downcast::<PyDict>() {
                for (task, channels) in vs_dict.iter() {
                    let task_str: String = task.extract()?;
                    let mut channel_versions = HashMap::new();

                    if let Ok(channels_dict) = channels.downcast::<PyDict>() {
                        for (chan, ver) in channels_dict.iter() {
                            let chan_str: String = chan.extract()?;
                            let version: usize = ver.extract()?;
                            channel_versions.insert(chan_str, version);
                        }
                    }

                    versions_seen.insert(task_str, channel_versions);
                }
            }
        }

        Ok(versions_seen)
    }

    fn checkpoint_data_to_py(&self, py: Python, data: &CheckpointData) -> PyResult<PyObject> {
        let result = PyDict::new(py);

        // Deserialize channel values
        let channel_values_dict = PyDict::new(py);
        let pickle = py.import("pickle")?;
        let loads = pickle.getattr("loads")?;

        for (key, value_bytes) in &data.channel_values {
            let py_bytes = PyBytes::new(py, value_bytes);
            let value = loads.call1((py_bytes,))?;
            channel_values_dict.set_item(key, value)?;
        }
        result.set_item("channel_values", channel_values_dict)?;

        // Convert channel versions
        let channel_versions_dict = PyDict::new(py);
        for (key, version) in &data.channel_versions {
            channel_versions_dict.set_item(key, version)?;
        }
        result.set_item("channel_versions", channel_versions_dict)?;

        // Convert versions_seen
        let versions_seen_dict = PyDict::new(py);
        for (task, channels) in &data.versions_seen {
            let channels_dict = PyDict::new(py);
            for (chan, ver) in channels {
                channels_dict.set_item(chan, ver)?;
            }
            versions_seen_dict.set_item(task, channels_dict)?;
        }
        result.set_item("versions_seen", versions_seen_dict)?;

        // Add step
        result.set_item("step", data.step)?;

        Ok(result.into())
    }
}

/// Register SQLite checkpoint module
#[cfg(feature = "sqlite")]
pub fn register_sqlite_checkpoint(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustSQLiteCheckpointer>()?;
    Ok(())
}

/// Stub for when SQLite feature is not enabled
#[cfg(not(feature = "sqlite"))]
pub fn register_sqlite_checkpoint(_py: Python, _m: &PyModule) -> PyResult<()> {
    Ok(())
}
