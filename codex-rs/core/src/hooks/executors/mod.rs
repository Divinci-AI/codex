//! Hook executor implementations for different hook types.

pub mod script;
pub mod webhook;
pub mod mcp;

pub use script::ScriptExecutor;
pub use webhook::WebhookExecutor;
pub use mcp::McpToolExecutor;

// Re-export the ExecutableExecutor from the executor module
pub use crate::hooks::executor::ExecutableExecutor;

#[cfg(test)]
mod tests;
