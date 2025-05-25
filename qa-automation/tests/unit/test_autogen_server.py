#!/usr/bin/env python3
"""
Unit Tests for AutoGen Server

Tests the AutoGen server components including webhook handling,
session management, and QA coordination.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add the server module to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "server"))

try:
    from autogen_server import CodexAutoGenServer
except ImportError:
    # Create mock class if import fails
    class CodexAutoGenServer:
        def __init__(self, config=None):
            self.config = config or {}
            self.app = Mock()


class TestCodexAutoGenServer:
    """Test cases for CodexAutoGenServer."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "server": {
                "host": "localhost",
                "port": 5000,
                "debug": True,
                "workers": 1
            },
            "openai": {
                "api_key": "test-api-key",
                "model": "gpt-4o",
                "timeout": 30
            },
            "qa_system": {
                "enabled": True,
                "auto_run": True,
                "safety_level": "standard"
            }
        }
    
    @pytest.fixture
    def server(self, mock_config):
        """Create a server instance for testing."""
        with patch('autogen_server.OpenAIChatCompletionClient'), \
             patch('autogen_server.IntegratedCodexHooksQASystem'), \
             patch('autogen_server.SafetyIntegrationSystem'):
            return CodexAutoGenServer(mock_config)
    
    def test_server_initialization(self, server, mock_config):
        """Test server initialization."""
        assert server.config == mock_config
        assert hasattr(server, 'app')
        assert hasattr(server, 'active_sessions')
        assert hasattr(server, 'event_queue')
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        server = CodexAutoGenServer()
        
        assert "server" in server.config
        assert "openai" in server.config
        assert "qa_system" in server.config
        assert "webhook" in server.config
    
    @pytest.mark.asyncio
    async def test_validate_event_data(self, server):
        """Test event data validation."""
        
        # Valid event data
        valid_event = {
            "eventType": "session_start",
            "sessionId": "test-session",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        assert server._validate_event_data(valid_event) is True
        
        # Invalid event data (missing required field)
        invalid_event = {
            "eventType": "session_start",
            "timestamp": "2024-01-01T00:00:00Z"
            # Missing sessionId
        }
        
        assert server._validate_event_data(invalid_event) is False
    
    def test_determine_qa_action(self, server):
        """Test determining QA action based on event type."""
        
        test_cases = [
            ("session_start", "configuration_validation"),
            ("session_end", "comprehensive_analysis"),
            ("task_start", "pre_task_validation"),
            ("task_end", "post_task_analysis"),
            ("error", "error_analysis"),
            ("unknown_event", None)
        ]
        
        for event_type, expected_action in test_cases:
            action = server._determine_qa_action(event_type, {})
            assert action == expected_action
    
    def test_build_qa_config(self, server):
        """Test building QA configuration."""
        
        event_data = {
            "eventType": "comprehensive_analysis",
            "context": {
                "config_path": "test/config.toml",
                "files": ["test.py"]
            }
        }
        
        config = server._build_qa_config("comprehensive_analysis", event_data)
        
        assert config["scope"] == "comprehensive_analysis"
        assert config["event_data"] == event_data
        assert "timestamp" in config
        assert config["validate_main_config"] is True


class TestWebhookEndpoints:
    """Test cases for webhook endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        with patch('autogen_server.OpenAIChatCompletionClient'), \
             patch('autogen_server.IntegratedCodexHooksQASystem'), \
             patch('autogen_server.SafetyIntegrationSystem'):
            
            server = CodexAutoGenServer()
            server.is_running = True
            server.model_client = Mock()
            server.qa_system = Mock()
            server.safety_system = Mock()
            
            return TestClient(server.app)
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Codex AutoGen Server"
        assert data["version"] == "1.0.0"
    
    def test_health_endpoint_healthy(self, client):
        """Test health endpoint when server is healthy."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "active_sessions" in data
    
    def test_health_endpoint_unhealthy(self):
        """Test health endpoint when server is unhealthy."""
        with patch('autogen_server.OpenAIChatCompletionClient'), \
             patch('autogen_server.IntegratedCodexHooksQASystem'), \
             patch('autogen_server.SafetyIntegrationSystem'):
            
            server = CodexAutoGenServer()
            server.is_running = False  # Server not ready
            
            client = TestClient(server.app)
            response = client.get("/health")
            
            assert response.status_code == 503
    
    def test_codex_webhook_valid_event(self, client):
        """Test Codex webhook with valid event data."""
        
        valid_event = {
            "eventType": "session_start",
            "sessionId": "test-session-123",
            "timestamp": "2024-01-01T00:00:00Z",
            "context": {
                "model": "test-model",
                "workingDirectory": "/tmp/test"
            }
        }
        
        response = client.post("/webhook/codex", json=valid_event)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "event_id" in data
        assert "timestamp" in data
    
    def test_codex_webhook_invalid_event(self, client):
        """Test Codex webhook with invalid event data."""
        
        invalid_event = {
            "eventType": "session_start",
            # Missing required fields
        }
        
        response = client.post("/webhook/codex", json=invalid_event)
        
        assert response.status_code == 400
    
    def test_codex_webhook_invalid_json(self, client):
        """Test Codex webhook with invalid JSON."""
        
        response = client.post(
            "/webhook/codex",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
    
    def test_qa_completion_webhook(self, client):
        """Test QA completion webhook."""
        
        completion_data = {
            "session_id": "test-session-123",
            "status": "completed",
            "results": {
                "overall_status": "passed",
                "quality_score": 85.0
            }
        }
        
        response = client.post("/webhook/qa-complete", json=completion_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["session_id"] == "test-session-123"


class TestSessionManagement:
    """Test cases for session management."""
    
    @pytest.fixture
    def server_with_sessions(self):
        """Create a server with test sessions."""
        with patch('autogen_server.OpenAIChatCompletionClient'), \
             patch('autogen_server.IntegratedCodexHooksQASystem'), \
             patch('autogen_server.SafetyIntegrationSystem'):
            
            server = CodexAutoGenServer()
            server.is_running = True
            
            # Add test sessions
            server.active_sessions = {
                "session-1": {
                    "session_id": "session-1",
                    "status": "active",
                    "event_type": "session_start",
                    "started_at": "2024-01-01T00:00:00Z"
                },
                "session-2": {
                    "session_id": "session-2",
                    "status": "qa_complete",
                    "event_type": "session_end",
                    "started_at": "2024-01-01T00:01:00Z"
                }
            }
            
            return server
    
    def test_get_active_sessions(self, server_with_sessions):
        """Test getting active sessions."""
        client = TestClient(server_with_sessions.app)
        response = client.get("/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_sessions"] == 2
        assert len(data["sessions"]) == 2
    
    def test_get_session_details(self, server_with_sessions):
        """Test getting session details."""
        client = TestClient(server_with_sessions.app)
        response = client.get("/sessions/session-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session-1"
        assert data["status"] == "active"
    
    def test_get_nonexistent_session(self, server_with_sessions):
        """Test getting details for nonexistent session."""
        client = TestClient(server_with_sessions.app)
        response = client.get("/sessions/nonexistent")
        
        assert response.status_code == 404
    
    def test_cleanup_session(self, server_with_sessions):
        """Test cleaning up a session."""
        client = TestClient(server_with_sessions.app)
        response = client.delete("/sessions/session-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleaned_up"
        assert data["session_id"] == "session-1"


class TestEventProcessing:
    """Test cases for event processing."""
    
    @pytest.fixture
    def server_with_mocks(self):
        """Create a server with mocked dependencies."""
        with patch('autogen_server.OpenAIChatCompletionClient') as mock_client, \
             patch('autogen_server.IntegratedCodexHooksQASystem') as mock_qa, \
             patch('autogen_server.SafetyIntegrationSystem') as mock_safety:
            
            server = CodexAutoGenServer()
            server.is_running = True
            server.model_client = mock_client.return_value
            server.qa_system = mock_qa.return_value
            server.safety_system = mock_safety.return_value
            
            # Mock QA system methods
            server.qa_system.run_comprehensive_qa_suite = AsyncMock(return_value={
                "overall_status": "passed",
                "qa_results": {"quality_score": 85.0}
            })
            
            return server
    
    @pytest.mark.asyncio
    async def test_process_codex_event(self, server_with_mocks):
        """Test processing a Codex event."""
        
        event_data = {
            "event_id": "test-event-123",
            "eventType": "session_end",
            "sessionId": "test-session",
            "timestamp": "2024-01-01T00:00:00Z",
            "context": {}
        }
        
        await server_with_mocks._process_codex_event(event_data)
        
        # Verify session was created
        assert "test-session" in server_with_mocks.active_sessions
        
        session = server_with_mocks.active_sessions["test-session"]
        assert session["session_id"] == "test-session"
        assert session["event_type"] == "session_end"
        assert len(session["events"]) == 1
    
    @pytest.mark.asyncio
    async def test_run_qa_analysis(self, server_with_mocks):
        """Test running QA analysis."""
        
        event_data = {
            "eventType": "comprehensive_analysis",
            "context": {}
        }
        
        result = await server_with_mocks._run_qa_analysis(
            "test-session",
            "comprehensive_analysis",
            event_data
        )
        
        assert result["overall_status"] == "passed"
        assert "qa_results" in result
        
        # Verify QA system was called
        server_with_mocks.qa_system.run_comprehensive_qa_suite.assert_called_once()


class TestErrorHandling:
    """Test cases for error handling."""
    
    @pytest.fixture
    def server_with_failing_qa(self):
        """Create a server with failing QA system."""
        with patch('autogen_server.OpenAIChatCompletionClient'), \
             patch('autogen_server.IntegratedCodexHooksQASystem') as mock_qa, \
             patch('autogen_server.SafetyIntegrationSystem'):
            
            server = CodexAutoGenServer()
            server.is_running = True
            server.qa_system = mock_qa.return_value
            
            # Mock QA system to raise exception
            server.qa_system.run_comprehensive_qa_suite = AsyncMock(
                side_effect=Exception("QA system error")
            )
            
            return server
    
    @pytest.mark.asyncio
    async def test_qa_analysis_error_handling(self, server_with_failing_qa):
        """Test error handling in QA analysis."""
        
        result = await server_with_failing_qa._run_qa_analysis(
            "test-session",
            "comprehensive_analysis",
            {}
        )
        
        assert result["status"] == "error"
        assert "error" in result
        assert result["error"] == "QA system error"
    
    @pytest.mark.asyncio
    async def test_event_processing_error_handling(self, server_with_failing_qa):
        """Test error handling in event processing."""
        
        event_data = {
            "event_id": "test-event-error",
            "eventType": "session_end",
            "sessionId": "test-session-error",
            "timestamp": "2024-01-01T00:00:00Z",
            "context": {}
        }
        
        # This should not raise an exception
        await server_with_failing_qa._process_codex_event(event_data)
        
        # Verify session was created with error status
        assert "test-session-error" in server_with_failing_qa.active_sessions
        session = server_with_failing_qa.active_sessions["test-session-error"]
        assert session["status"] == "error"
        assert "error" in session


# Test fixtures and utilities
@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return {
        "eventType": "session_start",
        "sessionId": "test-session-123",
        "timestamp": "2024-01-01T00:00:00Z",
        "context": {
            "model": "gpt-4o",
            "workingDirectory": "/tmp/test",
            "eventData": {
                "user_request": "Create a todo app",
                "files_modified": ["app.py", "requirements.txt"]
            }
        }
    }


@pytest.fixture
def sample_qa_results():
    """Create sample QA results for testing."""
    return {
        "overall_status": "passed",
        "timestamp": "2024-01-01T00:00:00Z",
        "qa_results": {
            "configuration_validation": {
                "status": "passed",
                "issues": [],
                "recommendations": []
            },
            "code_analysis": {
                "status": "passed",
                "quality_score": 85.0,
                "recommendations": ["Add more unit tests"]
            },
            "performance_tests": {
                "status": "passed",
                "metrics": {
                    "response_time": 0.15,
                    "memory_usage": 45.2
                }
            }
        },
        "recommendations": [
            "Consider adding integration tests",
            "Optimize database queries"
        ]
    }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
