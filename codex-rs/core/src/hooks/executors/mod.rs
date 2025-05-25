//! Hook executor implementations for different hook types.

pub mod custom_plugin;
pub mod database;
pub mod filesystem;
pub mod mcp;
pub mod message_queue;
pub mod script;
pub mod webhook;

pub use custom_plugin::CustomPluginExecutor;
pub use database::DatabaseExecutor;
pub use filesystem::FileSystemExecutor;
pub use mcp::McpToolExecutor;
pub use message_queue::MessageQueueExecutor;
pub use script::ScriptExecutor;
pub use webhook::WebhookExecutor;

// Re-export the ExecutableExecutor from the executor module
pub use crate::hooks::executor::ExecutableExecutor;

#[cfg(test)]
mod tests;
