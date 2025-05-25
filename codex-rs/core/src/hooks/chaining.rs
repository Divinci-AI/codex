//! Hook result chaining and data passing system.

use std::collections::HashMap;
use std::sync::Arc;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::hooks::types::{HookError, HookResult};

/// Context for passing data between chained hooks.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainContext {
    /// Data passed from previous hooks in the chain.
    pub data: HashMap<String, Value>,
    /// Metadata about the chain execution.
    pub metadata: ChainMetadata,
    /// Results from previous hooks (for reference).
    pub previous_results: Vec<ChainedHookResult>,
}

/// Metadata about the chain execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainMetadata {
    /// Unique identifier for this chain execution.
    pub chain_id: String,
    /// Total number of hooks in the chain.
    pub total_hooks: usize,
    /// Current hook index in the chain.
    pub current_index: usize,
    /// Timestamp when the chain started.
    pub started_at: chrono::DateTime<chrono::Utc>,
    /// Whether the chain should continue on hook failures.
    pub continue_on_failure: bool,
}

/// Result from a hook in a chain, including data for the next hook.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainedHookResult {
    /// The hook ID that produced this result.
    pub hook_id: String,
    /// The original hook result.
    pub result: HookResult,
    /// Data to pass to the next hook in the chain.
    pub output_data: HashMap<String, Value>,
    /// Whether this hook wants to terminate the chain.
    pub terminate_chain: bool,
}

/// Configuration for hook chaining behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainConfig {
    /// Whether to continue the chain if a hook fails.
    pub continue_on_failure: bool,
    /// Maximum number of hooks that can be chained.
    pub max_chain_length: usize,
    /// Timeout for the entire chain execution.
    pub chain_timeout: std::time::Duration,
    /// Whether to preserve all intermediate results.
    pub preserve_intermediate_results: bool,
}

impl Default for ChainConfig {
    fn default() -> Self {
        Self {
            continue_on_failure: false,
            max_chain_length: 50,
            chain_timeout: std::time::Duration::from_secs(300), // 5 minutes
            preserve_intermediate_results: true,
        }
    }
}

/// Manager for executing chained hooks.
#[derive(Debug)]
pub struct ChainExecutor {
    config: ChainConfig,
}

impl ChainExecutor {
    /// Create a new chain executor with the given configuration.
    pub fn new(config: ChainConfig) -> Self {
        Self { config }
    }

    /// Create a new chain executor with default configuration.
    pub fn default() -> Self {
        Self::new(ChainConfig::default())
    }

    /// Execute a chain of hooks with data passing.
    pub async fn execute_chain(
        &self,
        hooks: Vec<Arc<dyn ChainableHook>>,
        initial_data: HashMap<String, Value>,
    ) -> Result<ChainExecutionResult, HookError> {
        if hooks.len() > self.config.max_chain_length {
            return Err(HookError::Configuration(format!(
                "Chain length {} exceeds maximum allowed length {}",
                hooks.len(),
                self.config.max_chain_length
            )));
        }

        let chain_id = uuid::Uuid::new_v4().to_string();
        let started_at = chrono::Utc::now();

        let mut context = ChainContext {
            data: initial_data,
            metadata: ChainMetadata {
                chain_id: chain_id.clone(),
                total_hooks: hooks.len(),
                current_index: 0,
                started_at,
                continue_on_failure: self.config.continue_on_failure,
            },
            previous_results: Vec::new(),
        };

        let mut results = Vec::new();
        let mut terminated_early = false;

        for (index, hook) in hooks.iter().enumerate() {
            context.metadata.current_index = index;

            tracing::info!(
                "Executing hook {} of {} in chain {}",
                index + 1,
                hooks.len(),
                chain_id
            );

            // Execute the hook with the current context
            let hook_result = match hook.execute_with_chain_context(&context).await {
                Ok(result) => result,
                Err(e) => {
                    tracing::error!("Hook {} failed in chain {}: {}", index, chain_id, e);
                    
                    if !self.config.continue_on_failure {
                        return Err(e);
                    }

                    // Create a failure result and continue
                    ChainedHookResult {
                        hook_id: hook.get_id(),
                        result: HookResult::failure(e.to_string(), std::time::Duration::ZERO),
                        output_data: HashMap::new(),
                        terminate_chain: false,
                    }
                }
            };

            // Check if the hook wants to terminate the chain
            if hook_result.terminate_chain {
                tracing::info!("Hook {} requested chain termination", hook.get_id());
                terminated_early = true;
            }

            // Update context with the hook's output data
            for (key, value) in &hook_result.output_data {
                context.data.insert(key.clone(), value.clone());
            }

            // Store the result
            if self.config.preserve_intermediate_results {
                context.previous_results.push(hook_result.clone());
            }
            results.push(hook_result.clone());

            // Check if we should terminate the chain
            if terminated_early {
                break;
            }
        }

        let total_duration = started_at.signed_duration_since(chrono::Utc::now()).to_std()
            .unwrap_or(std::time::Duration::ZERO);

        Ok(ChainExecutionResult {
            chain_id,
            results,
            final_data: context.data,
            total_duration,
            terminated_early,
            success: results.iter().all(|r| r.result.success),
        })
    }

    /// Validate a chain of hooks before execution.
    pub fn validate_chain(&self, hooks: &[Arc<dyn ChainableHook>]) -> Result<(), HookError> {
        if hooks.is_empty() {
            return Err(HookError::Configuration(
                "Cannot execute empty hook chain".to_string(),
            ));
        }

        if hooks.len() > self.config.max_chain_length {
            return Err(HookError::Configuration(format!(
                "Chain length {} exceeds maximum allowed length {}",
                hooks.len(),
                self.config.max_chain_length
            )));
        }

        // Validate that each hook can participate in chaining
        for (index, hook) in hooks.iter().enumerate() {
            if !hook.supports_chaining() {
                return Err(HookError::Configuration(format!(
                    "Hook at index {} does not support chaining",
                    index
                )));
            }
        }

        Ok(())
    }
}

/// Result of executing a hook chain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainExecutionResult {
    /// Unique identifier for this chain execution.
    pub chain_id: String,
    /// Results from all hooks in the chain.
    pub results: Vec<ChainedHookResult>,
    /// Final data after all hooks have executed.
    pub final_data: HashMap<String, Value>,
    /// Total duration of the chain execution.
    pub total_duration: std::time::Duration,
    /// Whether the chain was terminated early.
    pub terminated_early: bool,
    /// Whether all hooks in the chain succeeded.
    pub success: bool,
}

/// Trait for hooks that can participate in chaining.
#[async_trait::async_trait]
pub trait ChainableHook: Send + Sync {
    /// Get the unique identifier for this hook.
    fn get_id(&self) -> String;

    /// Check if this hook supports chaining.
    fn supports_chaining(&self) -> bool {
        true
    }

    /// Execute the hook with chain context.
    async fn execute_with_chain_context(
        &self,
        context: &ChainContext,
    ) -> Result<ChainedHookResult, HookError>;

    /// Get the expected input data schema for this hook.
    fn get_input_schema(&self) -> Option<serde_json::Value> {
        None
    }

    /// Get the output data schema that this hook produces.
    fn get_output_schema(&self) -> Option<serde_json::Value> {
        None
    }
}

/// Utility functions for working with chain data.
pub mod chain_utils {
    use super::*;

    /// Extract a typed value from chain data.
    pub fn get_typed_value<T>(data: &HashMap<String, Value>, key: &str) -> Result<T, HookError>
    where
        T: for<'de> Deserialize<'de>,
    {
        let value = data.get(key).ok_or_else(|| {
            HookError::Execution(format!("Required chain data key '{}' not found", key))
        })?;

        serde_json::from_value(value.clone()).map_err(|e| {
            HookError::Execution(format!("Failed to deserialize chain data '{}': {}", key, e))
        })
    }

    /// Set a typed value in chain data.
    pub fn set_typed_value<T>(
        data: &mut HashMap<String, Value>,
        key: &str,
        value: T,
    ) -> Result<(), HookError>
    where
        T: Serialize,
    {
        let json_value = serde_json::to_value(value).map_err(|e| {
            HookError::Execution(format!("Failed to serialize chain data '{}': {}", key, e))
        })?;

        data.insert(key.to_string(), json_value);
        Ok(())
    }

    /// Merge two data maps, with the second taking precedence.
    pub fn merge_data(
        base: &HashMap<String, Value>,
        overlay: &HashMap<String, Value>,
    ) -> HashMap<String, Value> {
        let mut result = base.clone();
        for (key, value) in overlay {
            result.insert(key.clone(), value.clone());
        }
        result
    }

    /// Filter data by key prefix.
    pub fn filter_data_by_prefix(
        data: &HashMap<String, Value>,
        prefix: &str,
    ) -> HashMap<String, Value> {
        data.iter()
            .filter(|(key, _)| key.starts_with(prefix))
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect()
    }

    /// Transform data keys by removing a prefix.
    pub fn remove_prefix_from_keys(
        data: &HashMap<String, Value>,
        prefix: &str,
    ) -> HashMap<String, Value> {
        data.iter()
            .filter_map(|(key, value)| {
                if key.starts_with(prefix) {
                    let new_key = key.strip_prefix(prefix)?.trim_start_matches('.');
                    Some((new_key.to_string(), value.clone()))
                } else {
                    None
                }
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use async_trait::async_trait;
    use std::time::Duration;

    struct TestChainableHook {
        id: String,
        should_fail: bool,
        output_data: HashMap<String, Value>,
        terminate_chain: bool,
    }

    impl TestChainableHook {
        fn new(id: &str) -> Self {
            Self {
                id: id.to_string(),
                should_fail: false,
                output_data: HashMap::new(),
                terminate_chain: false,
            }
        }

        fn with_output_data(mut self, key: &str, value: Value) -> Self {
            self.output_data.insert(key.to_string(), value);
            self
        }

        fn with_failure(mut self) -> Self {
            self.should_fail = true;
            self
        }

        fn with_termination(mut self) -> Self {
            self.terminate_chain = true;
            self
        }
    }

    #[async_trait]
    impl ChainableHook for TestChainableHook {
        fn get_id(&self) -> String {
            self.id.clone()
        }

        async fn execute_with_chain_context(
            &self,
            _context: &ChainContext,
        ) -> Result<ChainedHookResult, HookError> {
            if self.should_fail {
                return Err(HookError::Execution("Test hook failure".to_string()));
            }

            Ok(ChainedHookResult {
                hook_id: self.id.clone(),
                result: HookResult::success(
                    Some(format!("Hook {} executed", self.id)),
                    Duration::from_millis(100),
                ),
                output_data: self.output_data.clone(),
                terminate_chain: self.terminate_chain,
            })
        }
    }

    #[tokio::test]
    async fn test_simple_chain_execution() {
        let executor = ChainExecutor::default();
        
        let hooks: Vec<Arc<dyn ChainableHook>> = vec![
            Arc::new(TestChainableHook::new("hook1").with_output_data("step1", Value::String("done".to_string()))),
            Arc::new(TestChainableHook::new("hook2").with_output_data("step2", Value::String("done".to_string()))),
        ];

        let initial_data = HashMap::new();
        let result = executor.execute_chain(hooks, initial_data).await.unwrap();

        assert!(result.success);
        assert_eq!(result.results.len(), 2);
        assert!(result.final_data.contains_key("step1"));
        assert!(result.final_data.contains_key("step2"));
        assert!(!result.terminated_early);
    }

    #[tokio::test]
    async fn test_chain_with_failure() {
        let mut config = ChainConfig::default();
        config.continue_on_failure = false;

        let executor = ChainExecutor::new(config);
        
        let hooks: Vec<Arc<dyn ChainableHook>> = vec![
            Arc::new(TestChainableHook::new("hook1")),
            Arc::new(TestChainableHook::new("hook2").with_failure()),
            Arc::new(TestChainableHook::new("hook3")),
        ];

        let initial_data = HashMap::new();
        let result = executor.execute_chain(hooks, initial_data).await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_chain_continue_on_failure() {
        let mut config = ChainConfig::default();
        config.continue_on_failure = true;

        let executor = ChainExecutor::new(config);
        
        let hooks: Vec<Arc<dyn ChainableHook>> = vec![
            Arc::new(TestChainableHook::new("hook1")),
            Arc::new(TestChainableHook::new("hook2").with_failure()),
            Arc::new(TestChainableHook::new("hook3")),
        ];

        let initial_data = HashMap::new();
        let result = executor.execute_chain(hooks, initial_data).await.unwrap();

        assert!(!result.success); // Overall failure due to hook2
        assert_eq!(result.results.len(), 3); // All hooks executed
        assert!(!result.terminated_early);
    }

    #[tokio::test]
    async fn test_chain_early_termination() {
        let executor = ChainExecutor::default();
        
        let hooks: Vec<Arc<dyn ChainableHook>> = vec![
            Arc::new(TestChainableHook::new("hook1")),
            Arc::new(TestChainableHook::new("hook2").with_termination()),
            Arc::new(TestChainableHook::new("hook3")),
        ];

        let initial_data = HashMap::new();
        let result = executor.execute_chain(hooks, initial_data).await.unwrap();

        assert!(result.success);
        assert_eq!(result.results.len(), 2); // Only first two hooks executed
        assert!(result.terminated_early);
    }

    #[test]
    fn test_chain_utils() {
        let mut data = HashMap::new();
        
        // Test setting and getting typed values
        chain_utils::set_typed_value(&mut data, "number", 42i32).unwrap();
        chain_utils::set_typed_value(&mut data, "text", "hello".to_string()).unwrap();

        let number: i32 = chain_utils::get_typed_value(&data, "number").unwrap();
        let text: String = chain_utils::get_typed_value(&data, "text").unwrap();

        assert_eq!(number, 42);
        assert_eq!(text, "hello");

        // Test data filtering
        let mut prefixed_data = HashMap::new();
        prefixed_data.insert("prefix.key1".to_string(), Value::String("value1".to_string()));
        prefixed_data.insert("prefix.key2".to_string(), Value::String("value2".to_string()));
        prefixed_data.insert("other.key".to_string(), Value::String("other".to_string()));

        let filtered = chain_utils::filter_data_by_prefix(&prefixed_data, "prefix");
        assert_eq!(filtered.len(), 2);
        assert!(filtered.contains_key("prefix.key1"));
        assert!(filtered.contains_key("prefix.key2"));

        let without_prefix = chain_utils::remove_prefix_from_keys(&prefixed_data, "prefix");
        assert_eq!(without_prefix.len(), 2);
        assert!(without_prefix.contains_key("key1"));
        assert!(without_prefix.contains_key("key2"));
    }
}
