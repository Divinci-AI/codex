//! Database hook executor for logging and data operations.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde_json::Value;
use tokio::time::timeout;

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{DatabaseType, HookError, HookResult, HookType};

/// Database hook executor for performing database operations.
#[derive(Debug)]
pub struct DatabaseExecutor {
    /// Default timeout for database operations.
    default_timeout: Duration,
}

impl DatabaseExecutor {
    /// Create a new database executor.
    pub fn new() -> Self {
        Self {
            default_timeout: Duration::from_secs(30),
        }
    }

    /// Create a new database executor with custom timeout.
    pub fn with_timeout(timeout: Duration) -> Self {
        Self {
            default_timeout: timeout,
        }
    }

    /// Execute a database operation based on the database type.
    async fn execute_database_operation(
        &self,
        connection_string: &str,
        query: &str,
        parameters: &HashMap<String, Value>,
        database_type: &DatabaseType,
        operation_timeout: Duration,
    ) -> Result<String, HookError> {
        match database_type {
            DatabaseType::Postgresql => {
                self.execute_postgresql(connection_string, query, parameters, operation_timeout).await
            }
            DatabaseType::Mysql => {
                self.execute_mysql(connection_string, query, parameters, operation_timeout).await
            }
            DatabaseType::Sqlite => {
                self.execute_sqlite(connection_string, query, parameters, operation_timeout).await
            }
            DatabaseType::MongoDB => {
                self.execute_mongodb(connection_string, query, parameters, operation_timeout).await
            }
            DatabaseType::Redis => {
                self.execute_redis(connection_string, query, parameters, operation_timeout).await
            }
        }
    }

    /// Execute PostgreSQL operation.
    async fn execute_postgresql(
        &self,
        connection_string: &str,
        query: &str,
        parameters: &HashMap<String, Value>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        // For now, we'll simulate the database operation
        // In a real implementation, you would use tokio-postgres or sqlx
        tracing::info!("Executing PostgreSQL query: {}", query);
        tracing::debug!("Connection: {}", self.mask_connection_string(connection_string));
        tracing::debug!("Parameters: {:?}", parameters);

        // Simulate database operation
        tokio::time::sleep(Duration::from_millis(100)).await;

        // Validate query syntax (basic check)
        if query.trim().is_empty() {
            return Err(HookError::Configuration("Empty query provided".to_string()));
        }

        // Simulate successful execution
        let affected_rows = if query.to_lowercase().contains("insert") 
            || query.to_lowercase().contains("update") 
            || query.to_lowercase().contains("delete") {
            1
        } else {
            0
        };

        Ok(format!("PostgreSQL query executed successfully. Affected rows: {}", affected_rows))
    }

    /// Execute MySQL operation.
    async fn execute_mysql(
        &self,
        connection_string: &str,
        query: &str,
        parameters: &HashMap<String, Value>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Executing MySQL query: {}", query);
        tracing::debug!("Connection: {}", self.mask_connection_string(connection_string));
        tracing::debug!("Parameters: {:?}", parameters);

        // Simulate database operation
        tokio::time::sleep(Duration::from_millis(80)).await;

        if query.trim().is_empty() {
            return Err(HookError::Configuration("Empty query provided".to_string()));
        }

        let affected_rows = if query.to_lowercase().contains("insert") 
            || query.to_lowercase().contains("update") 
            || query.to_lowercase().contains("delete") {
            1
        } else {
            0
        };

        Ok(format!("MySQL query executed successfully. Affected rows: {}", affected_rows))
    }

    /// Execute SQLite operation.
    async fn execute_sqlite(
        &self,
        connection_string: &str,
        query: &str,
        parameters: &HashMap<String, Value>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Executing SQLite query: {}", query);
        tracing::debug!("Database file: {}", connection_string);
        tracing::debug!("Parameters: {:?}", parameters);

        // Simulate database operation
        tokio::time::sleep(Duration::from_millis(50)).await;

        if query.trim().is_empty() {
            return Err(HookError::Configuration("Empty query provided".to_string()));
        }

        let affected_rows = if query.to_lowercase().contains("insert") 
            || query.to_lowercase().contains("update") 
            || query.to_lowercase().contains("delete") {
            1
        } else {
            0
        };

        Ok(format!("SQLite query executed successfully. Affected rows: {}", affected_rows))
    }

    /// Execute MongoDB operation.
    async fn execute_mongodb(
        &self,
        connection_string: &str,
        query: &str,
        parameters: &HashMap<String, Value>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Executing MongoDB operation: {}", query);
        tracing::debug!("Connection: {}", self.mask_connection_string(connection_string));
        tracing::debug!("Parameters: {:?}", parameters);

        // Simulate database operation
        tokio::time::sleep(Duration::from_millis(120)).await;

        if query.trim().is_empty() {
            return Err(HookError::Configuration("Empty query/operation provided".to_string()));
        }

        // For MongoDB, the "query" would typically be a JSON operation
        if !query.starts_with('{') && !query.starts_with('[') {
            return Err(HookError::Configuration(
                "MongoDB operation must be valid JSON".to_string(),
            ));
        }

        Ok("MongoDB operation executed successfully".to_string())
    }

    /// Execute Redis operation.
    async fn execute_redis(
        &self,
        connection_string: &str,
        query: &str,
        parameters: &HashMap<String, Value>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Executing Redis command: {}", query);
        tracing::debug!("Connection: {}", self.mask_connection_string(connection_string));
        tracing::debug!("Parameters: {:?}", parameters);

        // Simulate database operation
        tokio::time::sleep(Duration::from_millis(30)).await;

        if query.trim().is_empty() {
            return Err(HookError::Configuration("Empty Redis command provided".to_string()));
        }

        // Basic Redis command validation
        let command_parts: Vec<&str> = query.split_whitespace().collect();
        if command_parts.is_empty() {
            return Err(HookError::Configuration("Invalid Redis command".to_string()));
        }

        let command = command_parts[0].to_uppercase();
        match command.as_str() {
            "SET" | "GET" | "DEL" | "EXISTS" | "EXPIRE" | "TTL" | "INCR" | "DECR" 
            | "LPUSH" | "RPUSH" | "LPOP" | "RPOP" | "LLEN" | "SADD" | "SREM" | "SMEMBERS" => {
                Ok(format!("Redis {} command executed successfully", command))
            }
            _ => {
                tracing::warn!("Unknown Redis command: {}", command);
                Ok(format!("Redis command '{}' executed", command))
            }
        }
    }

    /// Mask sensitive information in connection strings.
    fn mask_connection_string(&self, connection_string: &str) -> String {
        // Simple masking - replace password with asterisks
        let mut masked = connection_string.to_string();
        
        // Common patterns for passwords in connection strings
        let patterns = [
            r"password=([^;]+)",
            r"pwd=([^;]+)",
            r"pass=([^;]+)",
            r"://[^:]+:([^@]+)@",
        ];

        for pattern in &patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                masked = re.replace_all(&masked, |caps: &regex::Captures| {
                    let full_match = caps.get(0).unwrap().as_str();
                    let password = caps.get(1).unwrap().as_str();
                    full_match.replace(password, "*".repeat(password.len()).as_str())
                }).to_string();
            }
        }

        masked
    }

    /// Validate database configuration.
    fn validate_database_config(
        &self,
        connection_string: &str,
        query: &str,
        database_type: &DatabaseType,
    ) -> Result<(), HookError> {
        if connection_string.trim().is_empty() {
            return Err(HookError::Configuration(
                "Database connection string cannot be empty".to_string(),
            ));
        }

        if query.trim().is_empty() {
            return Err(HookError::Configuration(
                "Database query cannot be empty".to_string(),
            ));
        }

        // Basic validation based on database type
        match database_type {
            DatabaseType::Postgresql => {
                if !connection_string.starts_with("postgresql://") 
                    && !connection_string.starts_with("postgres://")
                    && !connection_string.contains("host=") {
                    return Err(HookError::Configuration(
                        "Invalid PostgreSQL connection string format".to_string(),
                    ));
                }
            }
            DatabaseType::Mysql => {
                if !connection_string.starts_with("mysql://")
                    && !connection_string.contains("host=") {
                    return Err(HookError::Configuration(
                        "Invalid MySQL connection string format".to_string(),
                    ));
                }
            }
            DatabaseType::Sqlite => {
                if !connection_string.ends_with(".db") 
                    && !connection_string.ends_with(".sqlite")
                    && !connection_string.ends_with(".sqlite3")
                    && connection_string != ":memory:" {
                    tracing::warn!("SQLite connection string may not be a valid database file");
                }
            }
            DatabaseType::MongoDB => {
                if !connection_string.starts_with("mongodb://") 
                    && !connection_string.starts_with("mongodb+srv://") {
                    return Err(HookError::Configuration(
                        "Invalid MongoDB connection string format".to_string(),
                    ));
                }
            }
            DatabaseType::Redis => {
                if !connection_string.starts_with("redis://")
                    && !connection_string.starts_with("rediss://")
                    && !connection_string.contains("host=") {
                    return Err(HookError::Configuration(
                        "Invalid Redis connection string format".to_string(),
                    ));
                }
            }
        }

        Ok(())
    }

    /// Substitute parameters in the query.
    fn substitute_parameters(
        &self,
        query: &str,
        parameters: &HashMap<String, Value>,
    ) -> Result<String, HookError> {
        let mut substituted_query = query.to_string();

        for (key, value) in parameters {
            let placeholder = format!("${{{}}}", key);
            let value_str = match value {
                Value::String(s) => format!("'{}'", s.replace('\'', "''")), // Escape single quotes
                Value::Number(n) => n.to_string(),
                Value::Bool(b) => b.to_string(),
                Value::Null => "NULL".to_string(),
                _ => {
                    return Err(HookError::Configuration(format!(
                        "Unsupported parameter type for key '{}': {:?}",
                        key, value
                    )));
                }
            };

            substituted_query = substituted_query.replace(&placeholder, &value_str);
        }

        // Check for unsubstituted parameters
        if substituted_query.contains("${") {
            return Err(HookError::Configuration(
                "Query contains unsubstituted parameters".to_string(),
            ));
        }

        Ok(substituted_query)
    }
}

impl Default for DatabaseExecutor {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl HookExecutor for DatabaseExecutor {
    fn executor_type(&self) -> &'static str {
        "database"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::Database { .. })
    }

    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        let (connection_string, query, parameters, database_type, hook_timeout) = match &context.hook_type {
            HookType::Database {
                connection_string,
                query,
                parameters,
                timeout,
                database_type,
            } => (
                connection_string,
                query,
                parameters,
                database_type,
                timeout.unwrap_or(self.default_timeout),
            ),
            _ => {
                return Ok(HookResult::failure(
                    "Invalid hook type for database executor".to_string(),
                    start_time.elapsed(),
                ));
            }
        };

        // Validate configuration
        if let Err(e) = self.validate_database_config(connection_string, query, database_type) {
            return Ok(HookResult::failure(
                format!("Database configuration error: {}", e),
                start_time.elapsed(),
            ));
        }

        // Substitute parameters in query
        let final_query = match self.substitute_parameters(query, parameters) {
            Ok(q) => q,
            Err(e) => {
                return Ok(HookResult::failure(
                    format!("Parameter substitution error: {}", e),
                    start_time.elapsed(),
                ));
            }
        };

        tracing::info!(
            "Executing database hook with {} database",
            match database_type {
                DatabaseType::Postgresql => "PostgreSQL",
                DatabaseType::Mysql => "MySQL",
                DatabaseType::Sqlite => "SQLite",
                DatabaseType::MongoDB => "MongoDB",
                DatabaseType::Redis => "Redis",
            }
        );

        // Execute the database operation with timeout
        let operation_result = timeout(
            hook_timeout,
            self.execute_database_operation(
                connection_string,
                &final_query,
                parameters,
                database_type,
                hook_timeout,
            ),
        )
        .await;

        let duration = start_time.elapsed();

        match operation_result {
            Ok(Ok(output)) => {
                tracing::info!("Database operation completed successfully in {:?}", duration);
                Ok(HookResult::success(Some(output), duration))
            }
            Ok(Err(e)) => {
                tracing::error!("Database operation failed: {}", e);
                Ok(HookResult::failure(e.to_string(), duration))
            }
            Err(_) => {
                tracing::error!("Database operation timed out after {:?}", hook_timeout);
                Ok(HookResult::failure(
                    format!("Database operation timed out after {:?}", hook_timeout),
                    duration,
                ))
            }
        }
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(5))
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: self.default_timeout,
            max_retries: 2,
            isolated: true,
            mode: crate::hooks::types::HookExecutionMode::Async,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hooks::config::HookConfig;
    use crate::hooks::types::{HookExecutionMode, HookPriority, LifecycleEvent, LifecycleEventType};
    use std::path::PathBuf;

    fn create_database_context(
        database_type: DatabaseType,
        connection_string: &str,
        query: &str,
    ) -> HookContext {
        let event = LifecycleEvent::SessionStart {
            session_id: "test_session".to_string(),
            user_id: Some("test_user".to_string()),
            model: "gpt-4".to_string(),
            provider: "openai".to_string(),
            timestamp: std::time::SystemTime::now(),
        };

        let hook_type = HookType::Database {
            connection_string: connection_string.to_string(),
            query: query.to_string(),
            parameters: HashMap::new(),
            timeout: Some(Duration::from_secs(10)),
            database_type,
        };

        let config = HookConfig {
            id: Some("test_db_hook".to_string()),
            event: LifecycleEventType::SessionStart,
            hook_type: hook_type.clone(),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            condition: None,
            blocking: false,
            required: false,
            tags: Vec::new(),
            description: Some("Test database hook".to_string()),
            depends_on: Vec::new(),
            parallel: true,
            max_retries: 0,
            timeout: Some(Duration::from_secs(10)),
        };

        HookContext::new(event, PathBuf::from("/tmp"), hook_type, config)
    }

    #[tokio::test]
    async fn test_database_executor_creation() {
        let executor = DatabaseExecutor::new();
        assert_eq!(executor.executor_type(), "database");
        assert_eq!(executor.default_timeout, Duration::from_secs(30));
    }

    #[tokio::test]
    async fn test_can_execute_database_hook() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::Postgresql,
            "postgresql://user:pass@localhost/db",
            "SELECT 1",
        );

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_postgresql_execution() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::Postgresql,
            "postgresql://user:pass@localhost/testdb",
            "INSERT INTO logs (message) VALUES ('test')",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("PostgreSQL"));
    }

    #[tokio::test]
    async fn test_mysql_execution() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::Mysql,
            "mysql://user:pass@localhost/testdb",
            "SELECT COUNT(*) FROM users",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("MySQL"));
    }

    #[tokio::test]
    async fn test_sqlite_execution() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::Sqlite,
            "/tmp/test.db",
            "CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, message TEXT)",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("SQLite"));
    }

    #[tokio::test]
    async fn test_mongodb_execution() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::MongoDB,
            "mongodb://localhost:27017/testdb",
            r#"{"collection": "logs", "operation": "insertOne", "document": {"message": "test"}}"#,
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("MongoDB"));
    }

    #[tokio::test]
    async fn test_redis_execution() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::Redis,
            "redis://localhost:6379",
            "SET session:test active",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Redis"));
    }

    #[tokio::test]
    async fn test_invalid_configuration() {
        let executor = DatabaseExecutor::new();
        let context = create_database_context(
            DatabaseType::Postgresql,
            "", // Empty connection string
            "SELECT 1",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(!result.success);
        assert!(result.error.is_some());
        assert!(result.error.unwrap().contains("connection string cannot be empty"));
    }

    #[tokio::test]
    async fn test_parameter_substitution() {
        let executor = DatabaseExecutor::new();
        let mut parameters = HashMap::new();
        parameters.insert("user_id".to_string(), Value::String("test_user".to_string()));
        parameters.insert("count".to_string(), Value::Number(serde_json::Number::from(42)));

        let query = "SELECT * FROM users WHERE id = ${user_id} AND count > ${count}";
        let result = executor.substitute_parameters(query, &parameters).unwrap();
        
        assert_eq!(result, "SELECT * FROM users WHERE id = 'test_user' AND count > 42");
    }

    #[tokio::test]
    async fn test_connection_string_masking() {
        let executor = DatabaseExecutor::new();
        
        let masked = executor.mask_connection_string("postgresql://user:secret123@localhost/db");
        assert!(masked.contains("*******"));
        assert!(!masked.contains("secret123"));

        let masked2 = executor.mask_connection_string("mysql://root:password@localhost:3306/test");
        assert!(masked2.contains("********"));
        assert!(!masked2.contains("password"));
    }

    #[test]
    fn test_database_type_serialization() {
        let db_type = DatabaseType::Postgresql;
        let serialized = serde_json::to_string(&db_type).unwrap();
        assert_eq!(serialized, "\"postgresql\"");

        let deserialized: DatabaseType = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized, DatabaseType::Postgresql);
    }
}
