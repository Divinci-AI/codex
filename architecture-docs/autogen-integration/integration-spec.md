# Integration Specification: Codex-AutoGen-Claude

## Technical Implementation Details

This document provides detailed technical specifications for implementing the integration between Codex CLI, Microsoft AutoGen, and Claude Computer Use.

## System Components

### 1. AutoGen Server Setup

#### Server Configuration
```python
# autogen_server.py
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from flask import Flask, request, jsonify
import asyncio
import logging
from typing import Dict, List, Any

class CodexAutoGenServer:
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.app = Flask(__name__)
        self.setup_agents()
        self.setup_routes()
        
    def setup_agents(self):
        """Initialize AutoGen agents with specific roles"""
        
        # Manager Agent - Orchestrates workflows
        self.manager = AssistantAgent(
            name="CodexManager",
            system_message="""You are a code review manager that coordinates between 
            different specialist agents. Your role is to:
            1. Analyze incoming Codex events
            2. Determine appropriate review workflows
            3. Orchestrate specialist agents
            4. Aggregate results and provide feedback
            5. Escalate complex issues when needed""",
            llm_config=self.config["llm_config"]
        )
        
        # Code Reviewer Agent
        self.code_reviewer = AssistantAgent(
            name="CodeReviewer",
            system_message="""You are a senior code reviewer specializing in:
            1. Code quality and best practices
            2. Security vulnerability detection
            3. Performance optimization opportunities
            4. Maintainability and readability
            5. Documentation completeness
            
            Provide specific, actionable feedback with examples.""",
            llm_config=self.config["llm_config"]
        )
        
        # Test Validator Agent
        self.test_validator = AssistantAgent(
            name="TestValidator",
            system_message="""You are a testing specialist responsible for:
            1. Analyzing test coverage and quality
            2. Suggesting additional test cases
            3. Validating test implementation
            4. Identifying edge cases
            5. Ensuring proper test structure
            
            Focus on comprehensive testing strategies.""",
            llm_config=self.config["llm_config"]
        )
        
        # Claude Computer Use Proxy
        self.claude_proxy = UserProxyAgent(
            name="ClaudeProxy",
            system_message="""You coordinate with Claude Computer Use for:
            1. Desktop application testing
            2. IDE integration and analysis
            3. Browser-based validation
            4. Screenshot capture and analysis
            5. Complex interaction workflows""",
            human_input_mode="NEVER",
            code_execution_config={"use_docker": False}
        )
        
    def setup_routes(self):
        """Setup Flask routes for Codex integration"""
        
        @self.app.route('/webhook/codex', methods=['POST'])
        def handle_codex_event():
            return asyncio.run(self.process_codex_event(request.json))
            
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({"status": "healthy", "agents": len(self.get_active_agents())})
            
        @self.app.route('/agents', methods=['GET'])
        def list_agents():
            return jsonify({"agents": [agent.name for agent in self.get_active_agents()]})
```

#### Agent Workflow Configuration
```python
async def process_codex_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process incoming Codex lifecycle events"""
    
    event_type = event_data.get("eventType")
    context = event_data.get("context", {})
    
    # Determine workflow based on event type
    workflow = self.determine_workflow(event_type, context)
    
    # Execute appropriate workflow
    if workflow == "code_review":
        return await self.execute_code_review_workflow(event_data)
    elif workflow == "test_validation":
        return await self.execute_test_validation_workflow(event_data)
    elif workflow == "full_validation":
        return await self.execute_full_validation_workflow(event_data)
    else:
        return {"status": "skipped", "reason": "No applicable workflow"}

async def execute_code_review_workflow(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute code review workflow with multiple agents"""
    
    # Create group chat for collaborative review
    groupchat = GroupChat(
        agents=[self.manager, self.code_reviewer, self.claude_proxy],
        messages=[],
        max_round=10
    )
    
    manager = GroupChatManager(groupchat=groupchat, llm_config=self.config["llm_config"])
    
    # Prepare review context
    review_prompt = self.prepare_review_prompt(event_data)
    
    # Execute collaborative review
    result = await manager.a_initiate_chat(
        self.code_reviewer,
        message=review_prompt
    )
    
    # Process and format results
    return self.format_review_results(result)
```

### 2. Claude Computer Use Integration

#### Claude API Client
```python
# claude_computer_use.py
import anthropic
import base64
import subprocess
import json
from typing import Dict, List, Any, Optional
import pyautogui
import time

class ClaudeComputerUseClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.setup_computer_use()
        
    def setup_computer_use(self):
        """Initialize computer use capabilities"""
        # Enable screenshot capabilities
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
    async def review_code_in_ide(self, file_paths: List[str], review_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Use Claude to review code by interacting with IDE"""
        
        # Take initial screenshot
        screenshot = self.capture_screenshot()
        
        # Prepare Claude prompt for IDE interaction
        prompt = f"""
        I need you to review the following code files using the IDE interface:
        Files: {', '.join(file_paths)}
        
        Review criteria:
        {json.dumps(review_criteria, indent=2)}
        
        Please:
        1. Open each file in the IDE
        2. Analyze the code structure and quality
        3. Look for potential issues or improvements
        4. Take screenshots of any problems found
        5. Provide detailed feedback
        
        Current screen shows: [screenshot will be provided]
        """
        
        # Execute Claude Computer Use
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            tools=[
                {
                    "type": "computer_20241022",
                    "name": "computer",
                    "display_width_px": 1920,
                    "display_height_px": 1080,
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot
                            }
                        }
                    ]
                }
            ]
        )
        
        return self.process_claude_response(response)
        
    def capture_screenshot(self) -> str:
        """Capture and encode screenshot"""
        screenshot = pyautogui.screenshot()
        screenshot.save("/tmp/screenshot.png")
        
        with open("/tmp/screenshot.png", "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
            
    async def run_tests_with_validation(self, test_commands: List[str]) -> Dict[str, Any]:
        """Execute tests and validate results using computer use"""
        
        results = []
        
        for command in test_commands:
            # Take screenshot before test
            before_screenshot = self.capture_screenshot()
            
            # Execute test command
            process = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Take screenshot after test
            after_screenshot = self.capture_screenshot()
            
            # Use Claude to analyze test results
            analysis = await self.analyze_test_results(
                command, 
                process.stdout, 
                process.stderr,
                before_screenshot,
                after_screenshot
            )
            
            results.append({
                "command": command,
                "exit_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "analysis": analysis
            })
            
        return {"test_results": results}
```

### 3. Codex Lifecycle Hook Scripts

#### AutoGen Integration Hook
```bash
#!/bin/bash
# hooks/autogen-integration.sh

# Configuration
AUTOGEN_SERVER_URL="${AUTOGEN_SERVER_URL:-http://localhost:5000}"
WEBHOOK_ENDPOINT="/webhook/codex"
TIMEOUT="${AUTOGEN_TIMEOUT:-30}"

# Read event data from stdin
EVENT_DATA=$(cat)

# Prepare webhook payload
PAYLOAD=$(jq -n \
  --arg eventType "$CODEX_EVENT_TYPE" \
  --arg sessionId "$CODEX_SESSION_ID" \
  --arg model "$CODEX_MODEL" \
  --arg workingDir "$CODEX_WORKING_DIR" \
  --argjson eventData "$EVENT_DATA" \
  '{
    eventType: $eventType,
    sessionId: $sessionId,
    timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
    context: {
      model: $model,
      workingDirectory: $workingDir,
      eventData: $eventData
    }
  }'
)

# Send to AutoGen server
RESPONSE=$(curl -s \
  --max-time "$TIMEOUT" \
  --header "Content-Type: application/json" \
  --data "$PAYLOAD" \
  "$AUTOGEN_SERVER_URL$WEBHOOK_ENDPOINT"
)

# Process response
if [ $? -eq 0 ]; then
  echo "AutoGen integration successful"
  echo "Response: $RESPONSE"
  
  # Extract feedback if available
  FEEDBACK=$(echo "$RESPONSE" | jq -r '.feedback // empty')
  if [ -n "$FEEDBACK" ]; then
    echo "AutoGen Feedback:"
    echo "$FEEDBACK"
    
    # Optionally save feedback for Codex to process
    echo "$FEEDBACK" > "/tmp/autogen-feedback-$CODEX_SESSION_ID.json"
  fi
else
  echo "AutoGen integration failed"
  exit 1
fi

exit 0
```

#### Code Review Hook
```bash
#!/bin/bash
# hooks/autogen-code-review.sh

# Only trigger for code files
EVENT_DATA=$(cat)
FILES=$(echo "$EVENT_DATA" | jq -r '.files[]? // empty')

if [ -z "$FILES" ]; then
  echo "No files to review"
  exit 0
fi

# Check if files are code files
CODE_FILES=""
for file in $FILES; do
  case "$file" in
    *.ts|*.js|*.tsx|*.jsx|*.py|*.java|*.go|*.rs|*.cpp|*.c|*.h)
      CODE_FILES="$CODE_FILES $file"
      ;;
  esac
done

if [ -z "$CODE_FILES" ]; then
  echo "No code files to review"
  exit 0
fi

# Prepare review request
REVIEW_PAYLOAD=$(jq -n \
  --arg eventType "code_review" \
  --arg sessionId "$CODEX_SESSION_ID" \
  --argjson files "$(echo $CODE_FILES | jq -R 'split(" ") | map(select(length > 0))')" \
  --argjson eventData "$EVENT_DATA" \
  '{
    eventType: $eventType,
    sessionId: $sessionId,
    timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
    context: {
      files: $files,
      reviewType: "code_quality",
      eventData: $eventData
    }
  }'
)

# Send to AutoGen for review
curl -s \
  --header "Content-Type: application/json" \
  --data "$REVIEW_PAYLOAD" \
  "${AUTOGEN_SERVER_URL:-http://localhost:5000}/webhook/codex"

exit 0
```

### 4. Configuration Management

#### AutoGen Server Configuration
```yaml
# autogen-config.yaml
server:
  host: "localhost"
  port: 5000
  debug: false
  
llm_config:
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.1
  max_tokens: 2000
  
claude_config:
  api_key: "${ANTHROPIC_API_KEY}"
  model: "claude-3-5-sonnet-20241022"
  computer_use_enabled: true
  
agents:
  manager:
    enabled: true
    max_rounds: 10
    
  code_reviewer:
    enabled: true
    specializations:
      - "security"
      - "performance"
      - "best_practices"
      
  test_validator:
    enabled: true
    test_frameworks:
      - "jest"
      - "pytest"
      - "go_test"
      
workflows:
  code_review:
    trigger_events: ["patch_apply", "task_complete"]
    required_agents: ["manager", "code_reviewer"]
    optional_agents: ["claude_proxy"]
    
  test_validation:
    trigger_events: ["command_complete"]
    command_filters: ["npm test", "pytest", "go test"]
    required_agents: ["manager", "test_validator", "claude_proxy"]
    
  full_validation:
    trigger_events: ["task_complete"]
    success_filter: true
    required_agents: ["manager", "code_reviewer", "test_validator", "claude_proxy"]
```

#### Codex Integration Configuration
```yaml
# ~/.codex/config.yaml (enhanced)
lifecycleHooks:
  enabled: true
  timeout: 60000
  
  environment:
    AUTOGEN_SERVER_URL: "http://localhost:5000"
    AUTOGEN_TIMEOUT: "30"
    
  hooks:
    # Code review on patch application
    onPatchApply:
      script: "./hooks/autogen-code-review.sh"
      async: true
      filter:
        fileExtensions: ["ts", "js", "tsx", "jsx", "py", "java", "go", "rs"]
        
    # Full validation on task completion
    onTaskComplete:
      script: "./hooks/autogen-full-validation.sh"
      async: false
      filter:
        customExpression: "eventData.success === true"
        
    # Test validation on test command completion
    onCommandComplete:
      script: "./hooks/autogen-test-validation.sh"
      async: true
      filter:
        commands: ["npm test", "pytest", "go test", "cargo test"]
        exitCodes: [0]
        
    # Task start notification
    onTaskStart:
      script: "./hooks/autogen-task-start.sh"
      async: true

# AutoGen integration settings
autogenIntegration:
  enabled: true
  serverUrl: "http://localhost:5000"
  timeout: 30000
  retryAttempts: 3
  
  # Feedback integration
  feedbackIntegration:
    enabled: true
    autoApply: false  # Require user confirmation for changes
    feedbackFile: "/tmp/autogen-feedback-{sessionId}.json"
```

### 5. Error Handling and Resilience

#### Retry Logic
```python
import asyncio
import aiohttp
from typing import Dict, Any, Optional
import logging

class ResilientAutoGenClient:
    def __init__(self, base_url: str, max_retries: int = 3):
        self.base_url = base_url
        self.max_retries = max_retries
        self.session = None
        
    async def send_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send event with retry logic and circuit breaker"""
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/webhook/codex",
                        json=event_data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logging.warning(f"AutoGen server returned {response.status}")
                            
            except asyncio.TimeoutError:
                logging.warning(f"Timeout on attempt {attempt + 1}")
            except aiohttp.ClientError as e:
                logging.warning(f"Client error on attempt {attempt + 1}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        logging.error("All retry attempts failed")
        return None
```

#### Fallback Mechanisms
```bash
#!/bin/bash
# hooks/autogen-with-fallback.sh

# Try AutoGen integration
if ! ./hooks/autogen-integration.sh; then
  echo "AutoGen integration failed, falling back to local validation"
  
  # Fallback to local tools
  if command -v eslint >/dev/null 2>&1; then
    echo "Running ESLint..."
    eslint . --ext .ts,.js,.tsx,.jsx
  fi
  
  if command -v pytest >/dev/null 2>&1; then
    echo "Running pytest..."
    pytest --tb=short
  fi
  
  echo "Local validation complete"
fi

exit 0
```

This integration specification provides the technical foundation for implementing a robust multi-agent system that enhances Codex CLI with sophisticated review and validation capabilities.
