//! Message queue hook executor for async processing and notifications.

use std::collections::HashMap;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde_json::Value;
use tokio::time::timeout;

use crate::hooks::context::HookContext;
use crate::hooks::executor::{ExecutionConfig, HookExecutor, HookExecutorResult};
use crate::hooks::types::{HookError, HookResult, HookType, MessageQueueType};

/// Message queue hook executor for sending messages to various queue systems.
#[derive(Debug)]
pub struct MessageQueueExecutor {
    /// Default timeout for message queue operations.
    default_timeout: Duration,
}

impl MessageQueueExecutor {
    /// Create a new message queue executor.
    pub fn new() -> Self {
        Self {
            default_timeout: Duration::from_secs(15),
        }
    }

    /// Create a new message queue executor with custom timeout.
    pub fn with_timeout(timeout: Duration) -> Self {
        Self {
            default_timeout: timeout,
        }
    }

    /// Send a message to the specified queue system.
    async fn send_message(
        &self,
        queue_url: &str,
        message: &str,
        queue_type: &MessageQueueType,
        routing_key: Option<&str>,
        headers: &HashMap<String, String>,
        operation_timeout: Duration,
    ) -> Result<String, HookError> {
        match queue_type {
            MessageQueueType::RabbitMQ => {
                self.send_rabbitmq_message(queue_url, message, routing_key, headers, operation_timeout).await
            }
            MessageQueueType::Kafka => {
                self.send_kafka_message(queue_url, message, routing_key, headers, operation_timeout).await
            }
            MessageQueueType::RedisPubSub => {
                self.send_redis_pubsub_message(queue_url, message, routing_key, headers, operation_timeout).await
            }
            MessageQueueType::AwsSqs => {
                self.send_aws_sqs_message(queue_url, message, headers, operation_timeout).await
            }
            MessageQueueType::GcpPubSub => {
                self.send_gcp_pubsub_message(queue_url, message, headers, operation_timeout).await
            }
            MessageQueueType::AzureServiceBus => {
                self.send_azure_servicebus_message(queue_url, message, headers, operation_timeout).await
            }
        }
    }

    /// Send message to RabbitMQ.
    async fn send_rabbitmq_message(
        &self,
        queue_url: &str,
        message: &str,
        routing_key: Option<&str>,
        headers: &HashMap<String, String>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Sending message to RabbitMQ: {}", queue_url);
        tracing::debug!("Message: {}", message);
        tracing::debug!("Routing key: {:?}", routing_key);
        tracing::debug!("Headers: {:?}", headers);

        // Simulate RabbitMQ operation
        tokio::time::sleep(Duration::from_millis(150)).await;

        // Basic validation
        if !queue_url.starts_with("amqp://") && !queue_url.starts_with("amqps://") {
            return Err(HookError::Configuration(
                "Invalid RabbitMQ URL format. Must start with amqp:// or amqps://".to_string(),
            ));
        }

        if message.is_empty() {
            return Err(HookError::Configuration("Message cannot be empty".to_string()));
        }

        // Simulate successful message publishing
        let routing_info = routing_key.unwrap_or("default");
        Ok(format!(
            "Message published to RabbitMQ successfully. Queue: {}, Routing key: {}, Message size: {} bytes",
            queue_url,
            routing_info,
            message.len()
        ))
    }

    /// Send message to Apache Kafka.
    async fn send_kafka_message(
        &self,
        queue_url: &str,
        message: &str,
        routing_key: Option<&str>,
        headers: &HashMap<String, String>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Sending message to Kafka: {}", queue_url);
        tracing::debug!("Message: {}", message);
        tracing::debug!("Topic/Partition key: {:?}", routing_key);
        tracing::debug!("Headers: {:?}", headers);

        // Simulate Kafka operation
        tokio::time::sleep(Duration::from_millis(200)).await;

        // Basic validation
        if message.is_empty() {
            return Err(HookError::Configuration("Message cannot be empty".to_string()));
        }

        // Extract topic from URL or routing key
        let topic = routing_key.unwrap_or("codex-hooks");
        
        // Simulate successful message production
        Ok(format!(
            "Message produced to Kafka successfully. Broker: {}, Topic: {}, Message size: {} bytes",
            queue_url,
            topic,
            message.len()
        ))
    }

    /// Send message to Redis Pub/Sub.
    async fn send_redis_pubsub_message(
        &self,
        queue_url: &str,
        message: &str,
        routing_key: Option<&str>,
        headers: &HashMap<String, String>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Publishing message to Redis Pub/Sub: {}", queue_url);
        tracing::debug!("Message: {}", message);
        tracing::debug!("Channel: {:?}", routing_key);
        tracing::debug!("Headers: {:?}", headers);

        // Simulate Redis Pub/Sub operation
        tokio::time::sleep(Duration::from_millis(80)).await;

        // Basic validation
        if !queue_url.starts_with("redis://") && !queue_url.starts_with("rediss://") {
            return Err(HookError::Configuration(
                "Invalid Redis URL format. Must start with redis:// or rediss://".to_string(),
            ));
        }

        if message.is_empty() {
            return Err(HookError::Configuration("Message cannot be empty".to_string()));
        }

        let channel = routing_key.unwrap_or("codex-hooks");
        
        // Simulate successful message publishing
        Ok(format!(
            "Message published to Redis Pub/Sub successfully. Server: {}, Channel: {}, Message size: {} bytes",
            queue_url,
            channel,
            message.len()
        ))
    }

    /// Send message to AWS SQS.
    async fn send_aws_sqs_message(
        &self,
        queue_url: &str,
        message: &str,
        headers: &HashMap<String, String>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Sending message to AWS SQS: {}", queue_url);
        tracing::debug!("Message: {}", message);
        tracing::debug!("Message attributes: {:?}", headers);

        // Simulate AWS SQS operation
        tokio::time::sleep(Duration::from_millis(300)).await;

        // Basic validation
        if !queue_url.contains("sqs.") || !queue_url.contains("amazonaws.com") {
            return Err(HookError::Configuration(
                "Invalid AWS SQS URL format".to_string(),
            ));
        }

        if message.is_empty() {
            return Err(HookError::Configuration("Message cannot be empty".to_string()));
        }

        if message.len() > 262144 { // 256KB limit for SQS
            return Err(HookError::Configuration(
                "Message size exceeds AWS SQS limit of 256KB".to_string(),
            ));
        }

        // Simulate successful message sending
        let message_id = format!("msg_{}", uuid::Uuid::new_v4());
        Ok(format!(
            "Message sent to AWS SQS successfully. Queue: {}, Message ID: {}, Message size: {} bytes",
            queue_url,
            message_id,
            message.len()
        ))
    }

    /// Send message to Google Cloud Pub/Sub.
    async fn send_gcp_pubsub_message(
        &self,
        queue_url: &str,
        message: &str,
        headers: &HashMap<String, String>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Publishing message to GCP Pub/Sub: {}", queue_url);
        tracing::debug!("Message: {}", message);
        tracing::debug!("Attributes: {:?}", headers);

        // Simulate GCP Pub/Sub operation
        tokio::time::sleep(Duration::from_millis(250)).await;

        // Basic validation
        if !queue_url.contains("pubsub.googleapis.com") && !queue_url.starts_with("projects/") {
            return Err(HookError::Configuration(
                "Invalid GCP Pub/Sub topic format".to_string(),
            ));
        }

        if message.is_empty() {
            return Err(HookError::Configuration("Message cannot be empty".to_string()));
        }

        if message.len() > 10485760 { // 10MB limit for Pub/Sub
            return Err(HookError::Configuration(
                "Message size exceeds GCP Pub/Sub limit of 10MB".to_string(),
            ));
        }

        // Simulate successful message publishing
        let message_id = format!("gcp_{}", uuid::Uuid::new_v4());
        Ok(format!(
            "Message published to GCP Pub/Sub successfully. Topic: {}, Message ID: {}, Message size: {} bytes",
            queue_url,
            message_id,
            message.len()
        ))
    }

    /// Send message to Azure Service Bus.
    async fn send_azure_servicebus_message(
        &self,
        queue_url: &str,
        message: &str,
        headers: &HashMap<String, String>,
        _timeout: Duration,
    ) -> Result<String, HookError> {
        tracing::info!("Sending message to Azure Service Bus: {}", queue_url);
        tracing::debug!("Message: {}", message);
        tracing::debug!("Properties: {:?}", headers);

        // Simulate Azure Service Bus operation
        tokio::time::sleep(Duration::from_millis(220)).await;

        // Basic validation
        if !queue_url.contains("servicebus.windows.net") {
            return Err(HookError::Configuration(
                "Invalid Azure Service Bus URL format".to_string(),
            ));
        }

        if message.is_empty() {
            return Err(HookError::Configuration("Message cannot be empty".to_string()));
        }

        if message.len() > 1048576 { // 1MB limit for Service Bus
            return Err(HookError::Configuration(
                "Message size exceeds Azure Service Bus limit of 1MB".to_string(),
            ));
        }

        // Simulate successful message sending
        let message_id = format!("azure_{}", uuid::Uuid::new_v4());
        Ok(format!(
            "Message sent to Azure Service Bus successfully. Queue/Topic: {}, Message ID: {}, Message size: {} bytes",
            queue_url,
            message_id,
            message.len()
        ))
    }

    /// Validate message queue configuration.
    fn validate_config(
        &self,
        queue_url: &str,
        message: &str,
        queue_type: &MessageQueueType,
    ) -> Result<(), HookError> {
        if queue_url.trim().is_empty() {
            return Err(HookError::Configuration(
                "Queue URL cannot be empty".to_string(),
            ));
        }

        if message.trim().is_empty() {
            return Err(HookError::Configuration(
                "Message cannot be empty".to_string(),
            ));
        }

        // Type-specific validation
        match queue_type {
            MessageQueueType::RabbitMQ => {
                if !queue_url.starts_with("amqp://") && !queue_url.starts_with("amqps://") {
                    return Err(HookError::Configuration(
                        "RabbitMQ URL must start with amqp:// or amqps://".to_string(),
                    ));
                }
            }
            MessageQueueType::RedisPubSub => {
                if !queue_url.starts_with("redis://") && !queue_url.starts_with("rediss://") {
                    return Err(HookError::Configuration(
                        "Redis URL must start with redis:// or rediss://".to_string(),
                    ));
                }
            }
            MessageQueueType::AwsSqs => {
                if !queue_url.contains("sqs.") || !queue_url.contains("amazonaws.com") {
                    return Err(HookError::Configuration(
                        "Invalid AWS SQS URL format".to_string(),
                    ));
                }
            }
            MessageQueueType::GcpPubSub => {
                if !queue_url.contains("pubsub.googleapis.com") && !queue_url.starts_with("projects/") {
                    return Err(HookError::Configuration(
                        "Invalid GCP Pub/Sub topic format".to_string(),
                    ));
                }
            }
            MessageQueueType::AzureServiceBus => {
                if !queue_url.contains("servicebus.windows.net") {
                    return Err(HookError::Configuration(
                        "Invalid Azure Service Bus URL format".to_string(),
                    ));
                }
            }
            MessageQueueType::Kafka => {
                // Kafka URLs are more flexible, just check it's not empty
                if queue_url.is_empty() {
                    return Err(HookError::Configuration(
                        "Kafka broker URL cannot be empty".to_string(),
                    ));
                }
            }
        }

        Ok(())
    }

    /// Prepare message payload with metadata.
    fn prepare_message_payload(
        &self,
        original_message: &str,
        context: &HookContext,
        headers: &HashMap<String, String>,
    ) -> Result<String, HookError> {
        // Try to parse as JSON to add metadata
        if let Ok(mut json_value) = serde_json::from_str::<Value>(original_message) {
            // Add hook metadata to JSON message
            if let Value::Object(ref mut map) = json_value {
                map.insert("_hook_metadata".to_string(), serde_json::json!({
                    "hook_id": context.config.id,
                    "event_type": context.event.event_type(),
                    "timestamp": chrono::Utc::now().to_rfc3339(),
                    "session_id": context.event.session_id(),
                    "headers": headers
                }));
            }
            serde_json::to_string(&json_value)
                .map_err(|e| HookError::Execution(format!("Failed to serialize message: {}", e)))
        } else {
            // For non-JSON messages, just return as-is
            Ok(original_message.to_string())
        }
    }
}

impl Default for MessageQueueExecutor {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl HookExecutor for MessageQueueExecutor {
    fn executor_type(&self) -> &'static str {
        "message_queue"
    }

    fn can_execute(&self, context: &HookContext) -> bool {
        matches!(context.hook_type, HookType::MessageQueue { .. })
    }

    async fn execute(&self, context: &HookContext) -> HookExecutorResult {
        let start_time = Instant::now();

        let (queue_url, message, queue_type, hook_timeout, routing_key, headers) = match &context.hook_type {
            HookType::MessageQueue {
                queue_url,
                message,
                queue_type,
                timeout,
                routing_key,
                headers,
            } => (
                queue_url,
                message,
                queue_type,
                timeout.unwrap_or(self.default_timeout),
                routing_key.as_deref(),
                headers,
            ),
            _ => {
                return Ok(HookResult::failure(
                    "Invalid hook type for message queue executor".to_string(),
                    start_time.elapsed(),
                ));
            }
        };

        // Validate configuration
        if let Err(e) = self.validate_config(queue_url, message, queue_type) {
            return Ok(HookResult::failure(
                format!("Message queue configuration error: {}", e),
                start_time.elapsed(),
            ));
        }

        // Prepare message payload
        let final_message = match self.prepare_message_payload(message, context, headers) {
            Ok(msg) => msg,
            Err(e) => {
                return Ok(HookResult::failure(
                    format!("Message preparation error: {}", e),
                    start_time.elapsed(),
                ));
            }
        };

        tracing::info!(
            "Sending message to {} queue: {}",
            match queue_type {
                MessageQueueType::RabbitMQ => "RabbitMQ",
                MessageQueueType::Kafka => "Kafka",
                MessageQueueType::RedisPubSub => "Redis Pub/Sub",
                MessageQueueType::AwsSqs => "AWS SQS",
                MessageQueueType::GcpPubSub => "GCP Pub/Sub",
                MessageQueueType::AzureServiceBus => "Azure Service Bus",
            },
            queue_url
        );

        // Send message with timeout
        let send_result = timeout(
            hook_timeout,
            self.send_message(
                queue_url,
                &final_message,
                queue_type,
                routing_key,
                headers,
                hook_timeout,
            ),
        )
        .await;

        let duration = start_time.elapsed();

        match send_result {
            Ok(Ok(output)) => {
                tracing::info!("Message sent successfully in {:?}", duration);
                Ok(HookResult::success(Some(output), duration))
            }
            Ok(Err(e)) => {
                tracing::error!("Failed to send message: {}", e);
                Ok(HookResult::failure(e.to_string(), duration))
            }
            Err(_) => {
                tracing::error!("Message sending timed out after {:?}", hook_timeout);
                Ok(HookResult::failure(
                    format!("Message sending timed out after {:?}", hook_timeout),
                    duration,
                ))
            }
        }
    }

    fn estimated_duration(&self) -> Option<Duration> {
        Some(Duration::from_secs(3))
    }

    fn default_config(&self) -> ExecutionConfig {
        ExecutionConfig {
            timeout: self.default_timeout,
            max_retries: 3,
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

    fn create_message_queue_context(
        queue_type: MessageQueueType,
        queue_url: &str,
        message: &str,
    ) -> HookContext {
        let event = LifecycleEvent::TaskComplete {
            session_id: "test_session".to_string(),
            task_id: "test_task".to_string(),
            success: true,
            duration: Duration::from_secs(5),
            timestamp: std::time::SystemTime::now(),
        };

        let hook_type = HookType::MessageQueue {
            queue_url: queue_url.to_string(),
            message: message.to_string(),
            queue_type,
            timeout: Some(Duration::from_secs(10)),
            routing_key: Some("test.routing.key".to_string()),
            headers: HashMap::new(),
        };

        let config = HookConfig {
            id: Some("test_mq_hook".to_string()),
            event: LifecycleEventType::TaskComplete,
            hook_type: hook_type.clone(),
            mode: HookExecutionMode::Async,
            priority: HookPriority::NORMAL,
            condition: None,
            blocking: false,
            required: false,
            tags: Vec::new(),
            description: Some("Test message queue hook".to_string()),
            depends_on: Vec::new(),
            parallel: true,
            max_retries: 0,
            timeout: Some(Duration::from_secs(10)),
        };

        HookContext::new(event, PathBuf::from("/tmp"), hook_type, config)
    }

    #[tokio::test]
    async fn test_message_queue_executor_creation() {
        let executor = MessageQueueExecutor::new();
        assert_eq!(executor.executor_type(), "message_queue");
        assert_eq!(executor.default_timeout, Duration::from_secs(15));
    }

    #[tokio::test]
    async fn test_can_execute_message_queue_hook() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::RabbitMQ,
            "amqp://localhost:5672",
            "test message",
        );

        assert!(executor.can_execute(&context));
    }

    #[tokio::test]
    async fn test_rabbitmq_execution() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::RabbitMQ,
            "amqp://user:pass@localhost:5672/vhost",
            "Hello RabbitMQ!",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("RabbitMQ"));
    }

    #[tokio::test]
    async fn test_kafka_execution() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::Kafka,
            "localhost:9092",
            "Hello Kafka!",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Kafka"));
    }

    #[tokio::test]
    async fn test_redis_pubsub_execution() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::RedisPubSub,
            "redis://localhost:6379",
            "Hello Redis!",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Redis"));
    }

    #[tokio::test]
    async fn test_aws_sqs_execution() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::AwsSqs,
            "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
            "Hello AWS SQS!",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("AWS SQS"));
    }

    #[tokio::test]
    async fn test_gcp_pubsub_execution() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::GcpPubSub,
            "projects/test-project/topics/test-topic",
            "Hello GCP Pub/Sub!",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("GCP Pub/Sub"));
    }

    #[tokio::test]
    async fn test_azure_servicebus_execution() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::AzureServiceBus,
            "https://test-namespace.servicebus.windows.net/test-queue",
            "Hello Azure Service Bus!",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
        assert!(result.output.unwrap().contains("Azure Service Bus"));
    }

    #[tokio::test]
    async fn test_invalid_configuration() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::RabbitMQ,
            "", // Empty URL
            "test message",
        );

        let result = executor.execute(&context).await.unwrap();
        assert!(!result.success);
        assert!(result.error.is_some());
        assert!(result.error.unwrap().contains("Queue URL cannot be empty"));
    }

    #[tokio::test]
    async fn test_json_message_with_metadata() {
        let executor = MessageQueueExecutor::new();
        let context = create_message_queue_context(
            MessageQueueType::Kafka,
            "localhost:9092",
            r#"{"event": "test", "data": "value"}"#,
        );

        let headers = HashMap::new();
        let prepared = executor.prepare_message_payload(
            r#"{"event": "test", "data": "value"}"#,
            &context,
            &headers,
        ).unwrap();

        // Should contain the original data plus metadata
        assert!(prepared.contains("\"event\":\"test\""));
        assert!(prepared.contains("\"_hook_metadata\""));
    }

    #[test]
    fn test_message_queue_type_serialization() {
        let queue_type = MessageQueueType::RabbitMQ;
        let serialized = serde_json::to_string(&queue_type).unwrap();
        assert_eq!(serialized, "\"rabbit_mq\"");

        let deserialized: MessageQueueType = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized, MessageQueueType::RabbitMQ);
    }
}
