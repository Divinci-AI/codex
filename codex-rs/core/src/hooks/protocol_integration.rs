//! Integration between hooks system and protocol events.

use std::time::Duration;

use uuid::Uuid;

use crate::hooks::types::{HookExecutionMode, HookPriority, HookResult, LifecycleEvent};
use crate::protocol::{
    Event, EventMsg, HookExecutionBeginEvent, HookExecutionEndEvent, SessionEndEvent,
    SessionStartEvent,
};

/// Converts hook lifecycle events to protocol events for client communication.
pub struct ProtocolEventConverter;

impl ProtocolEventConverter {
    /// Convert a lifecycle event to a protocol event (if applicable).
    pub fn convert_lifecycle_event(event: &LifecycleEvent) -> Option<Event> {
        match event {
            LifecycleEvent::SessionStart {
                session_id,
                model,
                cwd,
                timestamp,
            } => Some(Event {
                id: Uuid::new_v4().to_string(),
                msg: EventMsg::SessionStart(SessionStartEvent {
                    session_id: session_id.clone(),
                    model: model.clone(),
                    cwd: cwd.clone(),
                    timestamp: timestamp.to_rfc3339(),
                }),
            }),
            LifecycleEvent::SessionEnd {
                session_id,
                duration,
                timestamp,
            } => Some(Event {
                id: Uuid::new_v4().to_string(),
                msg: EventMsg::SessionEnd(SessionEndEvent {
                    session_id: session_id.clone(),
                    duration_ms: duration.as_millis() as u64,
                    timestamp: timestamp.to_rfc3339(),
                }),
            }),
            // Other lifecycle events don't need to be converted to protocol events
            // as they are internal to the hook system
            _ => None,
        }
    }

    /// Create a hook execution begin event for protocol communication.
    pub fn create_hook_execution_begin_event(
        execution_id: String,
        event_type: &LifecycleEvent,
        hook_type: &str,
        hook_description: Option<String>,
        execution_mode: HookExecutionMode,
        priority: HookPriority,
        required: bool,
    ) -> Event {
        Event {
            id: Uuid::new_v4().to_string(),
            msg: EventMsg::HookExecutionBegin(HookExecutionBeginEvent {
                execution_id,
                event_type: event_type.event_type().to_string(),
                hook_type: hook_type.to_string(),
                hook_description,
                execution_mode: match execution_mode {
                    HookExecutionMode::Async => "async".to_string(),
                    HookExecutionMode::Blocking => "blocking".to_string(),
                    HookExecutionMode::FireAndForget => "fire_and_forget".to_string(),
                },
                priority: priority.value(),
                required,
                timestamp: chrono::Utc::now().to_rfc3339(),
            }),
        }
    }

    /// Create a hook execution end event for protocol communication.
    pub fn create_hook_execution_end_event(
        execution_id: String,
        result: &HookResult,
        retry_attempts: u32,
        cancelled: bool,
    ) -> Event {
        Event {
            id: Uuid::new_v4().to_string(),
            msg: EventMsg::HookExecutionEnd(HookExecutionEndEvent {
                execution_id,
                success: result.success,
                output: result.output.clone(),
                error: result.error.clone(),
                duration_ms: result.duration.as_millis() as u64,
                retry_attempts,
                cancelled,
                timestamp: chrono::Utc::now().to_rfc3339(),
            }),
        }
    }

    /// Create a session start event from session information.
    pub fn create_session_start_event(
        session_id: String,
        model: String,
        cwd: std::path::PathBuf,
    ) -> Event {
        Event {
            id: Uuid::new_v4().to_string(),
            msg: EventMsg::SessionStart(SessionStartEvent {
                session_id,
                model,
                cwd,
                timestamp: chrono::Utc::now().to_rfc3339(),
            }),
        }
    }

    /// Create a session end event from session information.
    pub fn create_session_end_event(session_id: String, duration: Duration) -> Event {
        Event {
            id: Uuid::new_v4().to_string(),
            msg: EventMsg::SessionEnd(SessionEndEvent {
                session_id,
                duration_ms: duration.as_millis() as u64,
                timestamp: chrono::Utc::now().to_rfc3339(),
            }),
        }
    }
}

/// Trait for components that can emit protocol events.
pub trait ProtocolEventEmitter {
    /// Emit a protocol event to the client.
    fn emit_event(&self, event: Event);
}

/// Mock implementation for testing.
#[derive(Debug, Default)]
pub struct MockProtocolEventEmitter {
    pub events: std::sync::Mutex<Vec<Event>>,
}

impl MockProtocolEventEmitter {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get_events(&self) -> Vec<Event> {
        self.events.lock().unwrap().clone()
    }

    pub fn clear_events(&self) {
        self.events.lock().unwrap().clear();
    }
}

impl ProtocolEventEmitter for MockProtocolEventEmitter {
    fn emit_event(&self, event: Event) {
        self.events.lock().unwrap().push(event);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    use std::path::PathBuf;

    #[test]
    fn test_convert_session_start_event() {
        let lifecycle_event = LifecycleEvent::SessionStart {
            session_id: "test-session".to_string(),
            model: "test-model".to_string(),
            cwd: PathBuf::from("/test"),
            timestamp: chrono::Utc::now(),
        };

        let protocol_event = ProtocolEventConverter::convert_lifecycle_event(&lifecycle_event);
        assert!(protocol_event.is_some());

        let event = protocol_event.unwrap();
        match event.msg {
            EventMsg::SessionStart(session_start) => {
                assert_eq!(session_start.session_id, "test-session");
                assert_eq!(session_start.model, "test-model");
                assert_eq!(session_start.cwd, PathBuf::from("/test"));
            }
            _ => panic!("Expected SessionStart event"),
        }
    }

    #[test]
    fn test_convert_session_end_event() {
        let lifecycle_event = LifecycleEvent::SessionEnd {
            session_id: "test-session".to_string(),
            duration: Duration::from_secs(60),
            timestamp: chrono::Utc::now(),
        };

        let protocol_event = ProtocolEventConverter::convert_lifecycle_event(&lifecycle_event);
        assert!(protocol_event.is_some());

        let event = protocol_event.unwrap();
        match event.msg {
            EventMsg::SessionEnd(session_end) => {
                assert_eq!(session_end.session_id, "test-session");
                assert_eq!(session_end.duration_ms, 60000);
            }
            _ => panic!("Expected SessionEnd event"),
        }
    }

    #[test]
    fn test_convert_non_session_event_returns_none() {
        let lifecycle_event = LifecycleEvent::TaskStart {
            task_id: "test-task".to_string(),
            session_id: "test-session".to_string(),
            prompt: "test prompt".to_string(),
            timestamp: chrono::Utc::now(),
        };

        let protocol_event = ProtocolEventConverter::convert_lifecycle_event(&lifecycle_event);
        assert!(protocol_event.is_none());
    }

    #[test]
    fn test_create_hook_execution_begin_event() {
        let lifecycle_event = LifecycleEvent::TaskStart {
            task_id: "test-task".to_string(),
            session_id: "test-session".to_string(),
            prompt: "test prompt".to_string(),
            timestamp: chrono::Utc::now(),
        };

        let event = ProtocolEventConverter::create_hook_execution_begin_event(
            "exec-123".to_string(),
            &lifecycle_event,
            "script",
            Some("Test hook".to_string()),
            HookExecutionMode::Async,
            HookPriority::NORMAL,
            true,
        );

        match event.msg {
            EventMsg::HookExecutionBegin(begin_event) => {
                assert_eq!(begin_event.execution_id, "exec-123");
                assert_eq!(begin_event.event_type, "task_start");
                assert_eq!(begin_event.hook_type, "script");
                assert_eq!(begin_event.hook_description, Some("Test hook".to_string()));
                assert_eq!(begin_event.execution_mode, "async");
                assert_eq!(begin_event.priority, HookPriority::NORMAL.value());
                assert!(begin_event.required);
            }
            _ => panic!("Expected HookExecutionBegin event"),
        }
    }

    #[test]
    fn test_create_hook_execution_end_event() {
        let result = HookResult::success(Some("Hook completed".to_string()), Duration::from_millis(500));

        let event = ProtocolEventConverter::create_hook_execution_end_event(
            "exec-123".to_string(),
            &result,
            2,
            false,
        );

        match event.msg {
            EventMsg::HookExecutionEnd(end_event) => {
                assert_eq!(end_event.execution_id, "exec-123");
                assert!(end_event.success);
                assert_eq!(end_event.output, Some("Hook completed".to_string()));
                assert_eq!(end_event.error, None);
                assert_eq!(end_event.duration_ms, 500);
                assert_eq!(end_event.retry_attempts, 2);
                assert!(!end_event.cancelled);
            }
            _ => panic!("Expected HookExecutionEnd event"),
        }
    }

    #[test]
    fn test_mock_protocol_event_emitter() {
        let emitter = MockProtocolEventEmitter::new();

        let event = ProtocolEventConverter::create_session_start_event(
            "test-session".to_string(),
            "test-model".to_string(),
            PathBuf::from("/test"),
        );

        emitter.emit_event(event.clone());

        let events = emitter.get_events();
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].id, event.id);

        emitter.clear_events();
        let events = emitter.get_events();
        assert_eq!(events.len(), 0);
    }
}
