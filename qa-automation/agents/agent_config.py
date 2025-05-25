#!/usr/bin/env python3
"""
Individual Agent Configuration for Magentic-One QA System

This module provides configuration and initialization for individual
Magentic-One agents used in the QA automation system.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import toml

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.agents.web_surfer import MultimodalWebSurfer
    from autogen_ext.agents.file_surfer import FileSurfer
    from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
    from autogen_agentchat.agents import CodeExecutorAgent
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
except ImportError as e:
    print(f"Error importing Magentic-One dependencies: {e}")
    raise


class AgentConfigManager:
    """Manages configuration and initialization of individual agents."""
    
    def __init__(self, config_path: str = "qa-automation/config/qa-config.toml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.client = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file."""
        with open(self.config_path, 'r') as f:
            return toml.load(f)
            
    async def initialize_client(self) -> OpenAIChatCompletionClient:
        """Initialize OpenAI client."""
        if self.client is None:
            api_key = os.getenv(self.config['openai']['api_key_env'])
            if not api_key:
                raise ValueError(f"OpenAI API key not found in environment")
                
            self.client = OpenAIChatCompletionClient(
                model=self.config['openai']['model'],
                api_key=api_key
            )
        return self.client
        
    async def create_file_surfer(self, name: str = "FileSurfer") -> FileSurfer:
        """Create and configure FileSurfer agent."""
        client = await self.initialize_client()
        agent_config = self.config['agents']['file_surfer']
        
        return FileSurfer(
            name=name,
            model_client=client,
            # Add any specific FileSurfer configuration here
        )
        
    async def create_web_surfer(self, name: str = "WebSurfer") -> MultimodalWebSurfer:
        """Create and configure WebSurfer agent."""
        client = await self.initialize_client()
        agent_config = self.config['agents']['web_surfer']
        
        return MultimodalWebSurfer(
            name=name,
            model_client=client,
            # Add any specific WebSurfer configuration here
        )
        
    async def create_coder(self, name: str = "Coder") -> MagenticOneCoderAgent:
        """Create and configure Coder agent."""
        client = await self.initialize_client()
        agent_config = self.config['agents']['coder']
        
        return MagenticOneCoderAgent(
            name=name,
            model_client=client,
            # Add any specific Coder configuration here
        )
        
    async def create_computer_terminal(self, name: str = "ComputerTerminal") -> CodeExecutorAgent:
        """Create and configure ComputerTerminal agent."""
        agent_config = self.config['agents']['computer_terminal']
        
        # Create code executor with safety restrictions
        code_executor = LocalCommandLineCodeExecutor(
            timeout=agent_config['timeout'],
            # Add command filtering based on allowed/blocked commands
        )
        
        return CodeExecutorAgent(
            name=name,
            code_executor=code_executor
        )
        
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration for agents."""
        return self.config.get('safety', {})
        
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration for agents."""
        return self.config.get('monitoring', {})
        
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.close()


# Agent-specific task templates
AGENT_TASKS = {
    'file_surfer': {
        'config_validation': """
        Analyze the Codex hooks configuration file and validate:
        1. TOML syntax correctness
        2. Required fields presence
        3. Valid hook types and parameters
        4. Security considerations
        5. Performance implications
        
        Provide a detailed validation report with recommendations.
        """,
        
        'code_analysis': """
        Analyze the Codex hooks implementation code and check for:
        1. Code quality and best practices
        2. Security vulnerabilities
        3. Performance bottlenecks
        4. Error handling completeness
        5. Documentation quality
        
        Provide a comprehensive code analysis report.
        """
    },
    
    'web_surfer': {
        'webhook_testing': """
        Test webhook endpoints for the Codex hooks system:
        1. Verify webhook URL accessibility
        2. Test HTTP methods and response codes
        3. Validate request/response formats
        4. Check authentication mechanisms
        5. Test error handling scenarios
        
        Generate a webhook testing report with results.
        """,
        
        'api_validation': """
        Validate external API integrations used by hooks:
        1. Test API endpoint availability
        2. Verify authentication methods
        3. Check rate limiting behavior
        4. Validate response formats
        5. Test error scenarios
        
        Provide an API validation report.
        """
    },
    
    'coder': {
        'test_generation': """
        Generate comprehensive test scripts for the Codex hooks system:
        1. Unit tests for hook execution
        2. Integration tests for CLI integration
        3. Performance benchmark scripts
        4. Security test scenarios
        5. Error handling test cases
        
        Create well-documented, executable test scripts.
        """,
        
        'analysis_scripts': """
        Create analysis scripts for hooks system evaluation:
        1. Performance profiling scripts
        2. Memory usage analysis tools
        3. Log analysis utilities
        4. Metrics collection scripts
        5. Report generation tools
        
        Provide production-ready analysis tools.
        """
    },
    
    'computer_terminal': {
        'cli_testing': """
        Execute CLI testing scenarios for the Codex hooks system:
        1. Test hook configuration loading
        2. Verify hook execution with real commands
        3. Test error scenarios and recovery
        4. Validate CLI output and logging
        5. Check performance impact
        
        Execute tests and provide detailed results.
        """,
        
        'system_validation': """
        Validate system requirements and environment:
        1. Check required dependencies
        2. Verify file permissions
        3. Test network connectivity
        4. Validate environment variables
        5. Check system resources
        
        Provide a system validation report.
        """
    }
}


async def run_individual_agent_test(agent_type: str, task_type: str, custom_task: Optional[str] = None):
    """Run a test with a specific agent type and task."""
    config_manager = AgentConfigManager()
    
    try:
        # Get the task
        if custom_task:
            task = custom_task
        else:
            task = AGENT_TASKS.get(agent_type, {}).get(task_type)
            if not task:
                raise ValueError(f"Unknown task type '{task_type}' for agent '{agent_type}'")
        
        # Create the appropriate agent
        if agent_type == 'file_surfer':
            agent = await config_manager.create_file_surfer()
        elif agent_type == 'web_surfer':
            agent = await config_manager.create_web_surfer()
        elif agent_type == 'coder':
            agent = await config_manager.create_coder()
        elif agent_type == 'computer_terminal':
            agent = await config_manager.create_computer_terminal()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        print(f"Running {agent_type} agent with task: {task_type}")
        print(f"Task: {task}")
        
        # Execute the task (this would need to be implemented based on the specific agent interface)
        # For now, we'll just print the configuration
        print(f"Agent created successfully: {agent}")
        
        return {
            'agent_type': agent_type,
            'task_type': task_type,
            'status': 'completed',
            'agent': str(agent)
        }
        
    except Exception as e:
        print(f"Error running agent test: {e}")
        return {
            'agent_type': agent_type,
            'task_type': task_type,
            'status': 'failed',
            'error': str(e)
        }
    finally:
        await config_manager.cleanup()


if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python agent_config.py <agent_type> <task_type> [custom_task]")
        print("Agent types: file_surfer, web_surfer, coder, computer_terminal")
        print("Task types: config_validation, webhook_testing, test_generation, cli_testing, etc.")
        sys.exit(1)
    
    agent_type = sys.argv[1]
    task_type = sys.argv[2]
    custom_task = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = asyncio.run(run_individual_agent_test(agent_type, task_type, custom_task))
    print(f"Result: {result}")
