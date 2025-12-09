//! Pregel Node - wraps runnables with metadata and execution context
//!
//! This module implements the PregelNode structure that wraps Python runnables
//! and provides the execution context needed for the Pregel algorithm.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use std::collections::HashMap;

/// PregelNode wraps a Python runnable with execution metadata
#[derive(Clone)]
pub struct PregelNode {
    /// The Python runnable (Runnable protocol)
    pub runnable: PyObject,
    /// Node name
    pub name: String,
    /// Input channels that trigger this node
    pub triggers: Vec<String>,
    /// Output channels this node writes to
    pub channels: Vec<String>,
    /// Whether this node writes to specific channels or returns a dict
    pub mapper: Option<PyObject>,
    /// Retry policy configuration
    pub retry_policy: Option<RetryPolicyConfig>,
    /// Additional configuration
    pub config: Option<PyObject>,
}

#[derive(Clone, Debug)]
pub struct RetryPolicyConfig {
    pub initial_interval: f64,
    pub backoff_factor: f64,
    pub max_interval: f64,
    pub max_attempts: usize,
    pub jitter: bool,
}

impl RetryPolicyConfig {
    /// Create from Python retry policy object
    pub fn from_py_object(py: Python, obj: &PyObject) -> PyResult<Self> {
        let initial_interval = obj
            .getattr(py, "initial_interval")
            .and_then(|v| v.extract::<f64>(py))
            .unwrap_or(1.0);

        let backoff_factor = obj
            .getattr(py, "backoff_factor")
            .and_then(|v| v.extract::<f64>(py))
            .unwrap_or(2.0);

        let max_interval = obj
            .getattr(py, "max_interval")
            .and_then(|v| v.extract::<f64>(py))
            .unwrap_or(60.0);

        let max_attempts = obj
            .getattr(py, "max_attempts")
            .and_then(|v| v.extract::<usize>(py))
            .unwrap_or(3);

        let jitter = obj
            .getattr(py, "jitter")
            .and_then(|v| v.extract::<bool>(py))
            .unwrap_or(false);

        Ok(Self {
            initial_interval,
            backoff_factor,
            max_interval,
            max_attempts,
            jitter,
        })
    }
}

impl PregelNode {
    /// Create a new PregelNode
    pub fn new(
        runnable: PyObject,
        name: String,
        triggers: Vec<String>,
        channels: Vec<String>,
    ) -> Self {
        Self {
            runnable,
            name,
            triggers,
            channels,
            mapper: None,
            retry_policy: None,
            config: None,
        }
    }

    /// Get the actual runnable to execute
    pub fn get_runnable(&self, py: Python) -> PyResult<PyObject> {
        // Check if this is a ChannelWrite or similar wrapper
        if let Ok(build_method) = self.runnable.getattr(py, "build") {
            // It has a build() method - call it to get the actual runnable
            build_method.call0(py)
        } else {
            // It's already a runnable
            Ok(self.runnable.clone_ref(py))
        }
    }

    /// Check if this node should run based on channel versions
    pub fn should_run(
        &self,
        checkpoint_versions: &HashMap<String, usize>,
        versions_seen: &HashMap<String, HashMap<String, usize>>,
    ) -> bool {
        // Node should run if any of its trigger channels have been updated
        // since the last time this node executed

        let last_seen = versions_seen.get(&self.name);

        for trigger in &self.triggers {
            if let Some(&current_version) = checkpoint_versions.get(trigger) {
                if let Some(seen_versions) = last_seen {
                    if let Some(&seen_version) = seen_versions.get(trigger) {
                        if current_version > seen_version {
                            return true;
                        }
                    } else {
                        // Channel exists but we haven't seen it - should run
                        return true;
                    }
                } else {
                    // First time running this node - should run
                    return true;
                }
            }
        }

        false
    }
}

/// PregelExecutableTask represents a task ready for execution
pub struct PregelExecutableTask {
    /// Task name (usually node name)
    pub name: String,
    /// Input to the task
    pub input: PyObject,
    /// The runnable to execute
    pub proc: PyObject,
    /// Writes accumulated during execution
    pub writes: Vec<(String, PyObject)>,
    /// Configuration for this execution
    pub config: PyObject,
    /// Channels that triggered this task
    pub triggers: Vec<String>,
    /// Retry policy
    pub retry_policy: Option<RetryPolicyConfig>,
    /// Unique task ID
    pub id: String,
}

impl PregelExecutableTask {
    /// Execute this task
    pub fn execute(&mut self, py: Python) -> PyResult<PyObject> {
        // Try multiple calling conventions to support different node types

        // 1. Try Runnable.invoke(input, config=config)
        if let Ok(invoke_method) = self.proc.getattr(py, "invoke") {
            let args = PyTuple::new(py, &[self.input.clone_ref(py)]);
            let kwargs = PyDict::new(py);
            kwargs.set_item("config", self.config.clone_ref(py))?;

            if let Ok(result) = invoke_method.call(py, args, Some(kwargs)) {
                return Ok(result);
            }

            // 2. Try invoke(input) without config
            if let Ok(result) = invoke_method.call1(py, (self.input.clone_ref(py),)) {
                return Ok(result);
            }
        }

        // 3. Try calling directly as __call__(input)
        let result = self.proc.call1(py, (self.input.clone_ref(py),))?;
        Ok(result)
    }

    /// Execute with retry logic
    pub fn execute_with_retry(&mut self, py: Python) -> PyResult<PyObject> {
        if let Some(retry_policy) = self.retry_policy.clone() {
            let mut attempts = 0;
            let mut last_error = None;

            while attempts < retry_policy.max_attempts {
                attempts += 1;

                match self.execute(py) {
                    Ok(result) => return Ok(result),
                    Err(e) => {
                        // Check if we should retry this error
                        if attempts < retry_policy.max_attempts {
                            // Calculate backoff delay
                            let delay_ms = retry_policy.initial_interval
                                * retry_policy.backoff_factor.powi(attempts as i32 - 1);
                            let delay_ms = delay_ms.min(retry_policy.max_interval);

                            // Sleep
                            std::thread::sleep(std::time::Duration::from_millis(delay_ms as u64));

                            last_error = Some(e);
                        } else {
                            return Err(e);
                        }
                    }
                }
            }

            if let Some(e) = last_error {
                Err(e)
            } else {
                // Shouldn't happen, but just in case
                Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Max retry attempts exceeded",
                ))
            }
        } else {
            // No retry policy - execute once
            self.execute(py)
        }
    }
}

/// PregelTaskDescription is a lightweight description of a task to be executed
#[derive(Clone)]
pub struct PregelTaskDescription {
    pub name: String,
    pub input: PyObject,
}
