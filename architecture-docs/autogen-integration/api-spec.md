# API Specification: Codex-AutoGen-Claude Integration

## Overview

This document defines the API interfaces and communication protocols for the integrated multi-agent system comprising Codex CLI, Microsoft AutoGen, and Claude Computer Use.

## AutoGen Server API

### Base Configuration
- **Base URL**: `http://localhost:5000` (configurable)
- **Content-Type**: `application/json`
- **Authentication**: API Key (optional, for production)
- **Timeout**: 30 seconds (configurable)

### 1. Webhook Endpoints

#### POST /webhook/codex
Receives lifecycle events from Codex CLI.

**Request Body:**
```json
{
  "eventType": "task_start" | "task_complete" | "task_error" | 
               "command_start" | "command_complete" | "patch_apply" |
               "agent_message" | "agent_reasoning" | "mcp_tool_call",
  "sessionId": "string",
  "timestamp": "string (ISO 8601)",
  "context": {
    "model": "string",
    "workingDirectory": "string",
    "eventData": "object",
    "task": "string (optional)",
    "files": ["string"] (optional),
    "success": "boolean (optional)",
    "duration": "number (optional)"
  },
  "metadata": {
    "linesAdded": "number (optional)",
    "linesDeleted": "number (optional)",
    "testsAdded": "number (optional)",
    "complexity": "low | medium | high (optional)",
    "riskLevel": "low | medium | high (optional)"
  }
}
```

**Response:**
```json
{
  "status": "accepted" | "rejected" | "processing",
  "requestId": "string",
  "estimatedDuration": "number (milliseconds)",
  "workflow": "string",
  "message": "string (optional)"
}
```

**Status Codes:**
- `200 OK`: Event accepted and processing
- `400 Bad Request`: Invalid event format
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

#### POST /webhook/claude-response
Receives responses from Claude Computer Use operations.

**Request Body:**
```json
{
  "requestId": "string",
  "status": "completed" | "failed" | "timeout",
  "timestamp": "string (ISO 8601)",
  "results": {
    "actions_performed": [
      {
        "action": "string",
        "timestamp": "string",
        "description": "string",
        "coordinates": [number, number] (optional),
        "text": "string (optional)"
      }
    ],
    "analysis": "object",
    "evidence": [
      {
        "type": "screenshot" | "log" | "file",
        "base64": "string (optional)",
        "content": "string (optional)",
        "description": "string"
      }
    ]
  },
  "error": "string (optional)"
}
```

### 2. Management Endpoints

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "string (ISO 8601)",
  "agents": {
    "total": "number",
    "active": "number",
    "inactive": "number"
  },
  "services": {
    "claude_api": "healthy | unhealthy",
    "database": "healthy | unhealthy (optional)"
  },
  "metrics": {
    "requests_per_minute": "number",
    "average_response_time": "number",
    "error_rate": "number"
  }
}
```

#### GET /agents
List active agents and their status.

**Response:**
```json
{
  "agents": [
    {
      "name": "string",
      "type": "manager" | "specialist" | "proxy",
      "status": "active" | "idle" | "busy" | "error",
      "capabilities": ["string"],
      "current_tasks": "number",
      "last_activity": "string (ISO 8601)"
    }
  ]
}
```

#### GET /workflows
List available workflows and their configurations.

**Response:**
```json
{
  "workflows": [
    {
      "name": "string",
      "description": "string",
      "trigger_events": ["string"],
      "required_agents": ["string"],
      "optional_agents": ["string"],
      "estimated_duration": "number",
      "success_rate": "number"
    }
  ]
}
```

### 3. Control Endpoints

#### POST /workflows/{workflow_name}/execute
Manually trigger a workflow.

**Request Body:**
```json
{
  "sessionId": "string",
  "context": "object",
  "priority": "low" | "normal" | "high",
  "options": {
    "async": "boolean",
    "timeout": "number",
    "agents": ["string"] (optional)
  }
}
```

**Response:**
```json
{
  "executionId": "string",
  "status": "started" | "queued",
  "estimatedCompletion": "string (ISO 8601)",
  "assignedAgents": ["string"]
}
```

#### GET /executions/{execution_id}
Get execution status and results.

**Response:**
```json
{
  "executionId": "string",
  "status": "running" | "completed" | "failed" | "cancelled",
  "startTime": "string (ISO 8601)",
  "endTime": "string (ISO 8601, optional)",
  "duration": "number (optional)",
  "results": "object (optional)",
  "error": "string (optional)",
  "progress": {
    "current_step": "string",
    "total_steps": "number",
    "completed_steps": "number"
  }
}
```

#### DELETE /executions/{execution_id}
Cancel a running execution.

**Response:**
```json
{
  "status": "cancelled",
  "message": "string"
}
```

## Claude Computer Use API Integration

### 1. Computer Use Request Format

#### Code Review Request
```json
{
  "action": "review_code_in_ide",
  "requestId": "string",
  "parameters": {
    "files": ["string"],
    "ide": "vscode" | "intellij" | "vim" | "emacs",
    "reviewCriteria": {
      "security": "boolean",
      "performance": "boolean",
      "bestPractices": "boolean",
      "documentation": "boolean"
    },
    "tasks": [
      "open_file",
      "analyze_structure",
      "check_imports",
      "validate_types",
      "capture_screenshots",
      "run_linter",
      "check_tests"
    ]
  },
  "context": {
    "workingDirectory": "string",
    "language": "string",
    "framework": "string (optional)",
    "expectedIdeState": "string"
  },
  "options": {
    "captureScreenshots": "boolean",
    "generateReport": "boolean",
    "timeout": "number"
  }
}
```

#### Test Validation Request
```json
{
  "action": "validate_tests",
  "requestId": "string",
  "parameters": {
    "testCommands": ["string"],
    "testFiles": ["string"],
    "coverageThreshold": "number",
    "tasks": [
      "run_tests",
      "check_coverage",
      "validate_ui",
      "capture_results",
      "analyze_failures"
    ]
  },
  "context": {
    "workingDirectory": "string",
    "testFramework": "string",
    "applicationUrl": "string (optional)"
  }
}
```

#### UI Testing Request
```json
{
  "action": "test_user_interface",
  "requestId": "string",
  "parameters": {
    "applicationUrl": "string",
    "testScenarios": [
      {
        "name": "string",
        "steps": [
          {
            "action": "navigate" | "click" | "type" | "wait" | "verify",
            "target": "string",
            "value": "string (optional)",
            "timeout": "number (optional)"
          }
        ],
        "expectedOutcome": "string"
      }
    ]
  },
  "context": {
    "browser": "chrome" | "firefox" | "safari",
    "viewport": {
      "width": "number",
      "height": "number"
    }
  }
}
```

### 2. Computer Use Response Format

#### Standard Response
```json
{
  "requestId": "string",
  "status": "completed" | "failed" | "timeout" | "cancelled",
  "timestamp": "string (ISO 8601)",
  "duration": "number",
  "results": {
    "summary": "string",
    "actions_performed": [
      {
        "action": "string",
        "timestamp": "string",
        "description": "string",
        "success": "boolean",
        "coordinates": [number, number] (optional),
        "text": "string (optional)",
        "screenshot": "string (base64, optional)"
      }
    ],
    "analysis": {
      "overall_assessment": "string",
      "findings": [
        {
          "type": "issue" | "suggestion" | "improvement",
          "severity": "low" | "medium" | "high" | "critical",
          "category": "string",
          "description": "string",
          "location": "string (optional)",
          "suggestion": "string (optional)"
        }
      ],
      "metrics": {
        "code_quality_score": "number (0-10)",
        "security_score": "number (0-10)",
        "performance_score": "number (0-10)",
        "test_coverage": "number (0-100)"
      }
    },
    "evidence": [
      {
        "type": "screenshot" | "log" | "file" | "video",
        "base64": "string (optional)",
        "content": "string (optional)",
        "description": "string",
        "timestamp": "string"
      }
    ]
  },
  "error": {
    "code": "string",
    "message": "string",
    "details": "object (optional)"
  } (optional)
}
```

## Codex Integration API

### 1. Feedback Reception

#### POST /codex/feedback
Endpoint for AutoGen to send feedback to Codex.

**Request Body:**
```json
{
  "sessionId": "string",
  "feedbackType": "code_review" | "test_validation" | "general",
  "priority": "low" | "normal" | "high" | "critical",
  "feedback": {
    "summary": "string",
    "recommendations": [
      {
        "type": "fix" | "improvement" | "suggestion",
        "description": "string",
        "file": "string (optional)",
        "line": "number (optional)",
        "code": "string (optional)",
        "suggestion": "string (optional)"
      }
    ],
    "metrics": {
      "overall_score": "number",
      "confidence": "number"
    }
  },
  "evidence": [
    {
      "type": "screenshot" | "log" | "analysis",
      "description": "string",
      "data": "string"
    }
  ]
}
```

**Response:**
```json
{
  "status": "accepted" | "rejected",
  "message": "string",
  "actions": [
    {
      "action": "apply_fix" | "schedule_review" | "ignore",
      "description": "string"
    }
  ]
}
```

### 2. Status Updates

#### GET /codex/status/{session_id}
Get current status of a Codex session.

**Response:**
```json
{
  "sessionId": "string",
  "status": "active" | "completed" | "error" | "paused",
  "currentTask": "string",
  "progress": {
    "completed_steps": "number",
    "total_steps": "number",
    "current_step": "string"
  },
  "integrations": {
    "autogen": {
      "enabled": "boolean",
      "status": "connected" | "disconnected" | "error",
      "last_interaction": "string (ISO 8601)"
    }
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object (optional)",
    "timestamp": "string (ISO 8601)",
    "requestId": "string (optional)"
  }
}
```

### Error Codes

#### AutoGen Server Errors
- `AGENT_UNAVAILABLE`: Required agent is not available
- `WORKFLOW_NOT_FOUND`: Requested workflow doesn't exist
- `INVALID_EVENT`: Event format is invalid
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `CLAUDE_API_ERROR`: Claude Computer Use API error
- `TIMEOUT`: Operation timed out

#### Claude Computer Use Errors
- `DESKTOP_ACCESS_DENIED`: Cannot access desktop
- `APPLICATION_NOT_FOUND`: Target application not available
- `SCREENSHOT_FAILED`: Cannot capture screenshot
- `INTERACTION_FAILED`: UI interaction failed
- `ANALYSIS_ERROR`: Code analysis failed

#### Integration Errors
- `CODEX_UNREACHABLE`: Cannot connect to Codex
- `INVALID_FEEDBACK`: Feedback format is invalid
- `SESSION_NOT_FOUND`: Codex session doesn't exist
- `PERMISSION_DENIED`: Insufficient permissions

## Rate Limiting

### Default Limits
- **Webhook events**: 100 requests per minute per session
- **Manual workflows**: 10 requests per minute per user
- **Status queries**: 1000 requests per minute
- **Claude Computer Use**: 5 concurrent sessions

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 60
```

## Authentication (Optional)

### API Key Authentication
```
Authorization: Bearer <api_key>
```

### Request Signing (Production)
```
X-Signature: sha256=<hmac_signature>
X-Timestamp: <unix_timestamp>
```

## Monitoring and Observability

### Metrics Endpoints

#### GET /metrics
Prometheus-compatible metrics.

#### GET /metrics/summary
Human-readable metrics summary.

**Response:**
```json
{
  "requests": {
    "total": "number",
    "success_rate": "number",
    "average_duration": "number"
  },
  "agents": {
    "active_count": "number",
    "utilization": "number"
  },
  "claude": {
    "api_calls": "number",
    "success_rate": "number",
    "average_duration": "number"
  }
}
```

This API specification provides a comprehensive interface for all components to communicate effectively while maintaining reliability, security, and observability.
