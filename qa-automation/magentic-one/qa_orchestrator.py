#!/usr/bin/env python3
"""
Magentic-One QA Orchestrator for Codex Lifecycle Hooks Testing

This module provides the main orchestrator for automated QA testing of the
Codex lifecycle hooks system using Magentic-One multi-agent architecture.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import toml
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.teams.magentic_one import MagenticOne
    from autogen_agentchat.ui import Console
    from autogen_ext.agents.web_surfer import MultimodalWebSurfer
    from autogen_ext.agents.file_surfer import FileSurfer
    from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
    from autogen_agentchat.agents import CodeExecutorAgent
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
    from autogen_agentchat.teams import MagenticOneGroupChat
except ImportError as e:
    print(f"Error importing Magentic-One dependencies: {e}")
    print("Please install required packages: pip install autogen-agentchat autogen-ext[magentic-one,openai]")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qa-automation/logs/qa-orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CodexHooksQAOrchestrator:
    """
    Main orchestrator for Codex lifecycle hooks QA testing using Magentic-One.
    
    This class coordinates multiple AI agents to perform comprehensive testing
    of the Codex hooks system, including configuration validation, execution
    testing, and performance analysis.
    """
    
    def __init__(self, config_path: str = "qa-automation/config/qa-config.toml"):
        """Initialize the QA orchestrator with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.client = None
        self.magentic_one = None
        self.agents = {}
        self.test_results = []
        self.execution_start_time = None
        
        # Ensure required directories exist
        self._setup_directories()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = toml.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
            
    def _setup_directories(self):
        """Create necessary directories for QA operations."""
        directories = [
            "qa-automation/logs",
            "qa-automation/output",
            "qa-automation/test-data",
            "qa-automation/reports"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
    async def initialize(self):
        """Initialize Magentic-One client and agents."""
        try:
            # Initialize OpenAI client
            api_key = os.getenv(self.config['openai']['api_key_env'])
            if not api_key:
                raise ValueError(f"OpenAI API key not found in environment variable: {self.config['openai']['api_key_env']}")
                
            self.client = OpenAIChatCompletionClient(
                model=self.config['openai']['model'],
                api_key=api_key
            )
            
            # Initialize Magentic-One with all agents
            self.magentic_one = MagenticOne(client=self.client)
            
            # Initialize individual agents for specific tasks
            await self._initialize_agents()
            
            logger.info("Magentic-One QA orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize QA orchestrator: {e}")
            raise
            
    async def _initialize_agents(self):
        """Initialize individual Magentic-One agents."""
        try:
            # File Surfer for configuration validation
            if self.config['agents']['file_surfer']['enabled']:
                self.agents['file_surfer'] = FileSurfer(
                    "FileSurfer",
                    model_client=self.client
                )
                
            # Web Surfer for webhook testing
            if self.config['agents']['web_surfer']['enabled']:
                self.agents['web_surfer'] = MultimodalWebSurfer(
                    "WebSurfer", 
                    model_client=self.client
                )
                
            # Coder for test script generation
            if self.config['agents']['coder']['enabled']:
                self.agents['coder'] = MagenticOneCoderAgent(
                    "Coder",
                    model_client=self.client
                )
                
            # Computer Terminal for CLI testing
            if self.config['agents']['computer_terminal']['enabled']:
                code_executor = LocalCommandLineCodeExecutor(
                    timeout=self.config['agents']['computer_terminal']['timeout']
                )
                self.agents['computer_terminal'] = CodeExecutorAgent(
                    "ComputerTerminal",
                    code_executor=code_executor
                )
                
            logger.info(f"Initialized {len(self.agents)} specialized agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise
            
    async def run_comprehensive_qa(self) -> Dict[str, Any]:
        """
        Run comprehensive QA testing of the Codex hooks system.
        
        Returns:
            Dict containing test results and metrics
        """
        self.execution_start_time = datetime.now()
        logger.info("Starting comprehensive QA testing of Codex hooks system")
        
        try:
            # Phase 1: Configuration Validation
            config_results = await self.validate_hooks_configuration()
            
            # Phase 2: Functional Testing
            functional_results = await self.test_hooks_functionality()
            
            # Phase 3: Performance Testing
            performance_results = await self.test_hooks_performance()
            
            # Phase 4: Security Testing
            security_results = await self.test_hooks_security()
            
            # Phase 5: Integration Testing
            integration_results = await self.test_hooks_integration()
            
            # Compile final results
            final_results = {
                "execution_id": f"qa-{int(self.execution_start_time.timestamp())}",
                "start_time": self.execution_start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "configuration_validation": config_results,
                "functional_testing": functional_results,
                "performance_testing": performance_results,
                "security_testing": security_results,
                "integration_testing": integration_results,
                "overall_status": self._determine_overall_status([
                    config_results, functional_results, performance_results,
                    security_results, integration_results
                ])
            }
            
            # Save results
            await self._save_results(final_results)
            
            logger.info("Comprehensive QA testing completed successfully")
            return final_results
            
        except Exception as e:
            logger.error(f"QA testing failed: {e}")
            raise
            
    async def validate_hooks_configuration(self) -> Dict[str, Any]:
        """Validate hooks configuration files using FileSurfer agent."""
        logger.info("Starting hooks configuration validation")
        
        task = """
        Analyze and validate the Codex lifecycle hooks configuration:
        
        1. Examine the main hooks.toml configuration file
        2. Check syntax and structure validity
        3. Validate hook types and parameters
        4. Test condition expressions and logic
        5. Verify file paths and permissions
        6. Check for security vulnerabilities in configurations
        7. Generate a detailed validation report
        
        Focus on:
        - TOML syntax correctness
        - Required fields presence
        - Valid hook types (script, webhook, mcp_tool)
        - Proper event type definitions
        - Security considerations (no dangerous commands)
        - Performance implications (timeouts, priorities)
        """
        
        try:
            # Create a team with FileSurfer for configuration analysis
            team = MagenticOneGroupChat([self.agents['file_surfer']], model_client=self.client)
            result = await Console(team.run_stream(task=task))
            
            return {
                "status": "completed",
                "agent": "file_surfer",
                "task": "configuration_validation",
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_hooks_functionality(self) -> Dict[str, Any]:
        """Test hooks functionality using multiple agents."""
        logger.info("Starting hooks functionality testing")
        
        task = """
        Perform comprehensive functional testing of the Codex lifecycle hooks system:
        
        1. Test basic hook execution for each event type:
           - session_start, session_end
           - task_start, task_end
           - command_start, command_end
           - error events
           
        2. Test different hook types:
           - Script hooks with various commands
           - Webhook hooks with test endpoints
           - MCP tool hooks
           
        3. Test hook execution modes:
           - Synchronous vs asynchronous execution
           - Priority ordering
           - Conditional execution
           
        4. Test error handling:
           - Hook failures and recovery
           - Timeout scenarios
           - Invalid configurations
           
        5. Generate test scripts and execute them
        6. Verify hook outputs and side effects
        7. Create a detailed functionality report
        """
        
        try:
            # Use the full Magentic-One team for comprehensive testing
            result = await Console(self.magentic_one.run_stream(task=task))
            
            return {
                "status": "completed",
                "agent": "magentic_one_team",
                "task": "functionality_testing",
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Functionality testing failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_hooks_performance(self) -> Dict[str, Any]:
        """Test hooks performance and benchmarking."""
        logger.info("Starting hooks performance testing")
        
        task = """
        Conduct performance testing and benchmarking of the Codex hooks system:
        
        1. Measure hook execution overhead:
           - Time to execute simple hooks
           - Memory usage during hook execution
           - CPU utilization patterns
           
        2. Test scalability:
           - Multiple concurrent hooks
           - Large number of hooks per event
           - High-frequency event triggering
           
        3. Benchmark different hook types:
           - Script execution performance
           - Webhook response times
           - MCP tool call latency
           
        4. Test resource limits:
           - Memory constraints
           - Timeout handling
           - CPU throttling effects
           
        5. Generate performance metrics and recommendations
        6. Create benchmark comparison reports
        7. Identify performance bottlenecks and optimization opportunities
        """
        
        try:
            # Use Coder and ComputerTerminal for performance testing
            agents = [self.agents['coder'], self.agents['computer_terminal']]
            team = MagenticOneGroupChat(agents, model_client=self.client)
            result = await Console(team.run_stream(task=task))
            
            return {
                "status": "completed",
                "agent": "performance_team",
                "task": "performance_testing",
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance testing failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_hooks_security(self) -> Dict[str, Any]:
        """Test hooks security and safety measures."""
        logger.info("Starting hooks security testing")
        
        task = """
        Perform security testing and vulnerability assessment of the hooks system:
        
        1. Test input validation:
           - Malicious hook configurations
           - Command injection attempts
           - Path traversal vulnerabilities
           
        2. Test execution safety:
           - Sandbox isolation effectiveness
           - Resource limit enforcement
           - Privilege escalation prevention
           
        3. Test webhook security:
           - HTTPS enforcement
           - Authentication mechanisms
           - Rate limiting
           
        4. Test configuration security:
           - Sensitive data exposure
           - File permission checks
           - Environment variable handling
           
        5. Generate security assessment report
        6. Identify potential vulnerabilities
        7. Recommend security improvements
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=task))
            
            return {
                "status": "completed",
                "agent": "security_team",
                "task": "security_testing",
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Security testing failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    async def test_hooks_integration(self) -> Dict[str, Any]:
        """Test hooks integration with Codex CLI."""
        logger.info("Starting hooks integration testing")
        
        task = """
        Test end-to-end integration of hooks with the Codex CLI system:
        
        1. Test CLI hook configuration:
           - Hook enable/disable flags
           - Configuration file discovery
           - Environment variable overrides
           
        2. Test real Codex workflows:
           - Start a Codex session with hooks enabled
           - Execute various Codex commands
           - Verify hook triggering and execution
           
        3. Test hook data flow:
           - Event context passing
           - Environment variable population
           - Hook result collection
           
        4. Test error scenarios:
           - Hook failures during Codex execution
           - Configuration errors
           - Network issues for webhooks
           
        5. Test user experience:
           - Hook status reporting
           - Error message clarity
           - Performance impact on CLI
           
        6. Generate integration test report
        7. Verify all lifecycle events are properly handled
        """
        
        try:
            result = await Console(self.magentic_one.run_stream(task=task))
            
            return {
                "status": "completed",
                "agent": "integration_team", 
                "task": "integration_testing",
                "result": str(result),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Integration testing failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
    def _determine_overall_status(self, results: List[Dict[str, Any]]) -> str:
        """Determine overall QA status based on individual test results."""
        failed_tests = [r for r in results if r.get('status') == 'failed']
        
        if not failed_tests:
            return "passed"
        elif len(failed_tests) < len(results) / 2:
            return "passed_with_warnings"
        else:
            return "failed"
            
    async def _save_results(self, results: Dict[str, Any]):
        """Save QA results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"qa-automation/reports/qa_results_{timestamp}.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"QA results saved to {results_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.close()
        logger.info("QA orchestrator cleanup completed")


async def main():
    """Main entry point for QA orchestrator."""
    orchestrator = CodexHooksQAOrchestrator()
    
    try:
        await orchestrator.initialize()
        results = await orchestrator.run_comprehensive_qa()
        
        print("\n" + "="*60)
        print("CODEX HOOKS QA TESTING COMPLETED")
        print("="*60)
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Execution ID: {results['execution_id']}")
        print(f"Duration: {results['end_time']} - {results['start_time']}")
        print("="*60)
        
        return results
        
    except Exception as e:
        logger.error(f"QA orchestrator failed: {e}")
        raise
    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
