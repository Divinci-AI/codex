#!/usr/bin/env python3
"""
Specialized Coder Agent for Codex Hooks Test Script Generation

This module provides an enhanced Coder agent specifically designed for
generating test scripts, analysis tools, and automated testing utilities
for the Codex lifecycle hooks system.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import textwrap

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
    from autogen_agentchat.messages import TextMessage
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

logger = logging.getLogger(__name__)


class CodexHooksCoderAgent:
    """
    Specialized Coder Agent for Codex Hooks Test Script Generation.
    
    This agent provides enhanced code generation capabilities specifically designed
    for creating test scripts, analysis tools, performance benchmarks, and
    automated testing utilities for the hooks system.
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient, name: str = "HooksCoder"):
        self.model_client = model_client
        self.name = name
        self.generated_scripts = []
        self.script_cache = {}
        
        # Create the underlying Coder agent
        self.agent = MagenticOneCoderAgent(
            name=self.name,
            model_client=self.model_client
        )
        
    async def generate_hook_test_scripts(self, test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive test scripts for hook testing scenarios.
        
        Args:
            test_scenarios: List of test scenarios to generate scripts for
            
        Returns:
            Generated test scripts and documentation
        """
        logger.info(f"Generating test scripts for {len(test_scenarios)} scenarios")
        
        generation_prompt = f"""
Generate comprehensive test scripts for the Codex lifecycle hooks system.

Test Scenarios: {json.dumps(test_scenarios, indent=2)}

Please generate the following types of test scripts:

1. **Unit Test Scripts**:
   - Individual hook execution tests
   - Configuration validation tests
   - Event triggering tests
   - Error handling tests

2. **Integration Test Scripts**:
   - CLI integration tests
   - End-to-end workflow tests
   - Multi-hook coordination tests
   - Event chain tests

3. **Performance Test Scripts**:
   - Hook execution benchmarks
   - Memory usage profiling
   - Concurrent execution tests
   - Resource limit tests

4. **Security Test Scripts**:
   - Input validation tests
   - Privilege escalation tests
   - Sandbox isolation tests
   - Injection attack tests

5. **Stress Test Scripts**:
   - High-frequency event tests
   - Large payload tests
   - Long-running tests
   - Resource exhaustion tests

For each script, provide:
- Complete, executable code
- Clear documentation and comments
- Usage instructions
- Expected outputs
- Error handling
- Cleanup procedures

Languages to use:
- Python for general testing and automation
- Bash for CLI and system testing
- Rust for performance-critical tests
- TypeScript for CLI integration tests

Make sure all scripts are:
- Well-documented and maintainable
- Include proper error handling
- Have clear success/failure criteria
- Include logging and reporting
- Are safe to run in CI/CD environments
"""

        try:
            # Use the Coder agent to generate scripts
            response = await self.agent.on_messages(
                [TextMessage(content=generation_prompt, source="user")],
                cancellation_token=None
            )
            
            # Process and organize the generated scripts
            generation_result = {
                "generation_id": f"test-scripts-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "scenarios_count": len(test_scenarios),
                "generated_content": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Extract and save individual scripts
            scripts = await self._extract_and_save_scripts(generation_result["generated_content"])
            generation_result["extracted_scripts"] = scripts
            
            # Store result
            self.generated_scripts.append(generation_result)
            
            logger.info(f"Generated test scripts: {generation_result['generation_id']}")
            return generation_result
            
        except Exception as e:
            logger.error(f"Test script generation failed: {e}")
            error_result = {
                "generation_id": f"test-scripts-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            self.generated_scripts.append(error_result)
            return error_result
            
    async def generate_performance_analysis_tools(self, metrics_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate performance analysis and profiling tools.
        
        Args:
            metrics_requirements: Requirements for performance metrics
            
        Returns:
            Generated performance analysis tools
        """
        logger.info("Generating performance analysis tools")
        
        analysis_prompt = f"""
Generate comprehensive performance analysis tools for the Codex lifecycle hooks system.

Metrics Requirements: {json.dumps(metrics_requirements, indent=2)}

Please generate the following performance analysis tools:

1. **Hook Execution Profiler**:
   - Measure hook execution time
   - Track memory usage
   - Monitor CPU utilization
   - Analyze I/O operations

2. **Benchmark Suite**:
   - Standard performance benchmarks
   - Comparative analysis tools
   - Regression detection
   - Performance trend analysis

3. **Resource Monitor**:
   - Real-time resource monitoring
   - Resource limit enforcement
   - Resource usage reporting
   - Alert generation

4. **Load Testing Tools**:
   - Concurrent hook execution
   - High-frequency event generation
   - Stress testing scenarios
   - Capacity planning tools

5. **Performance Reporting**:
   - Metrics collection and aggregation
   - Performance dashboard generation
   - Report formatting and export
   - Historical trend analysis

6. **Optimization Tools**:
   - Performance bottleneck identification
   - Optimization recommendations
   - Configuration tuning
   - Resource optimization

For each tool, provide:
- Complete implementation
- Configuration options
- Usage documentation
- Output format specifications
- Integration instructions
- Maintenance procedures

Focus on:
- Accuracy and precision of measurements
- Low overhead monitoring
- Comprehensive coverage
- Easy integration with CI/CD
- Clear visualization and reporting
- Actionable insights and recommendations
"""

        try:
            # Use the Coder agent to generate analysis tools
            response = await self.agent.on_messages(
                [TextMessage(content=analysis_prompt, source="user")],
                cancellation_token=None
            )
            
            analysis_result = {
                "analysis_tools_id": f"perf-tools-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "generated_content": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Extract and save tools
            tools = await self._extract_and_save_tools(analysis_result["generated_content"], "performance")
            analysis_result["extracted_tools"] = tools
            
            logger.info(f"Generated performance analysis tools: {analysis_result['analysis_tools_id']}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Performance analysis tools generation failed: {e}")
            return {
                "analysis_tools_id": f"perf-tools-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def generate_security_testing_tools(self, security_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate security testing and validation tools.
        
        Args:
            security_requirements: Requirements for security testing
            
        Returns:
            Generated security testing tools
        """
        logger.info("Generating security testing tools")
        
        security_prompt = f"""
Generate comprehensive security testing tools for the Codex lifecycle hooks system.

Security Requirements: {json.dumps(security_requirements, indent=2)}

Please generate the following security testing tools:

1. **Input Validation Tester**:
   - Malformed input testing
   - Injection attack simulation
   - Boundary value testing
   - Character encoding tests

2. **Privilege Escalation Tester**:
   - Permission boundary testing
   - Sandbox escape attempts
   - File system access tests
   - Network access validation

3. **Authentication Tester**:
   - Authentication bypass attempts
   - Token validation testing
   - Session management tests
   - Credential security tests

4. **Configuration Security Scanner**:
   - Insecure configuration detection
   - Permission analysis
   - Credential exposure checks
   - Security best practice validation

5. **Network Security Tester**:
   - SSL/TLS validation
   - Certificate verification
   - Protocol security testing
   - Man-in-the-middle detection

6. **Code Security Analyzer**:
   - Static code analysis
   - Vulnerability pattern detection
   - Dependency security scanning
   - Security code review automation

For each tool, provide:
- Complete implementation with safety checks
- Comprehensive test coverage
- Clear security assessment criteria
- Risk rating and classification
- Remediation recommendations
- Compliance checking

Important considerations:
- All tools must be safe to run
- No actual exploitation or damage
- Clear documentation of what is tested
- Proper error handling and logging
- Integration with security frameworks
- Compliance with security standards
"""

        try:
            # Use the Coder agent to generate security tools
            response = await self.agent.on_messages(
                [TextMessage(content=security_prompt, source="user")],
                cancellation_token=None
            )
            
            security_result = {
                "security_tools_id": f"sec-tools-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "generated_content": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Extract and save tools
            tools = await self._extract_and_save_tools(security_result["generated_content"], "security")
            security_result["extracted_tools"] = tools
            
            logger.info(f"Generated security testing tools: {security_result['security_tools_id']}")
            return security_result
            
        except Exception as e:
            logger.error(f"Security testing tools generation failed: {e}")
            return {
                "security_tools_id": f"sec-tools-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def generate_automation_scripts(self, automation_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate automation scripts for CI/CD integration.
        
        Args:
            automation_requirements: Requirements for automation scripts
            
        Returns:
            Generated automation scripts
        """
        logger.info("Generating automation scripts")
        
        automation_prompt = f"""
Generate comprehensive automation scripts for CI/CD integration of the Codex hooks testing.

Automation Requirements: {json.dumps(automation_requirements, indent=2)}

Please generate the following automation scripts:

1. **CI/CD Pipeline Scripts**:
   - GitHub Actions workflows
   - GitLab CI configurations
   - Jenkins pipeline scripts
   - Azure DevOps pipelines

2. **Test Automation Scripts**:
   - Automated test execution
   - Test result collection
   - Test report generation
   - Test failure notification

3. **Deployment Automation**:
   - Environment setup scripts
   - Configuration deployment
   - Service health checks
   - Rollback procedures

4. **Monitoring Automation**:
   - Health check scripts
   - Performance monitoring
   - Alert generation
   - Log aggregation

5. **Quality Gate Scripts**:
   - Quality threshold checking
   - Performance regression detection
   - Security vulnerability scanning
   - Code quality assessment

6. **Maintenance Scripts**:
   - Cleanup procedures
   - Log rotation
   - Backup automation
   - System maintenance

For each script, provide:
- Complete implementation
- Configuration parameters
- Error handling and recovery
- Logging and monitoring
- Documentation and usage
- Integration instructions

Focus on:
- Reliability and robustness
- Clear success/failure criteria
- Comprehensive error handling
- Proper logging and monitoring
- Easy maintenance and updates
- Integration with existing tools
"""

        try:
            # Use the Coder agent to generate automation scripts
            response = await self.agent.on_messages(
                [TextMessage(content=automation_prompt, source="user")],
                cancellation_token=None
            )
            
            automation_result = {
                "automation_id": f"automation-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "generated_content": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Extract and save scripts
            scripts = await self._extract_and_save_tools(automation_result["generated_content"], "automation")
            automation_result["extracted_scripts"] = scripts
            
            logger.info(f"Generated automation scripts: {automation_result['automation_id']}")
            return automation_result
            
        except Exception as e:
            logger.error(f"Automation scripts generation failed: {e}")
            return {
                "automation_id": f"automation-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def _extract_and_save_scripts(self, generated_content: str) -> List[Dict[str, Any]]:
        """Extract individual scripts from generated content and save them."""
        scripts = []
        
        try:
            # Create scripts directory
            scripts_dir = Path("qa-automation/generated-scripts")
            scripts_dir.mkdir(exist_ok=True)
            
            # Simple extraction logic - look for code blocks
            import re
            
            # Pattern to match code blocks with language specification
            code_pattern = r'```(\w+)?\n(.*?)\n```'
            matches = re.findall(code_pattern, generated_content, re.DOTALL)
            
            for i, (language, code) in enumerate(matches):
                if not code.strip():
                    continue
                    
                # Determine file extension
                ext_map = {
                    'python': '.py',
                    'bash': '.sh',
                    'shell': '.sh',
                    'rust': '.rs',
                    'typescript': '.ts',
                    'javascript': '.js',
                    'yaml': '.yml',
                    'json': '.json'
                }
                
                extension = ext_map.get(language.lower(), '.txt')
                filename = f"test_script_{i+1}{extension}"
                filepath = scripts_dir / filename
                
                # Save script
                with open(filepath, 'w') as f:
                    f.write(code.strip())
                
                # Make executable if it's a script
                if extension in ['.sh', '.py']:
                    filepath.chmod(0o755)
                
                scripts.append({
                    "filename": filename,
                    "filepath": str(filepath),
                    "language": language,
                    "size_bytes": len(code),
                    "executable": extension in ['.sh', '.py']
                })
                
            logger.info(f"Extracted and saved {len(scripts)} scripts")
            return scripts
            
        except Exception as e:
            logger.error(f"Failed to extract scripts: {e}")
            return []
            
    async def _extract_and_save_tools(self, generated_content: str, tool_type: str) -> List[Dict[str, Any]]:
        """Extract individual tools from generated content and save them."""
        tools = []
        
        try:
            # Create tools directory
            tools_dir = Path(f"qa-automation/generated-tools/{tool_type}")
            tools_dir.mkdir(parents=True, exist_ok=True)
            
            # Simple extraction logic - look for code blocks
            import re
            
            # Pattern to match code blocks with language specification
            code_pattern = r'```(\w+)?\n(.*?)\n```'
            matches = re.findall(code_pattern, generated_content, re.DOTALL)
            
            for i, (language, code) in enumerate(matches):
                if not code.strip():
                    continue
                    
                # Determine file extension
                ext_map = {
                    'python': '.py',
                    'bash': '.sh',
                    'shell': '.sh',
                    'rust': '.rs',
                    'typescript': '.ts',
                    'javascript': '.js',
                    'yaml': '.yml',
                    'json': '.json'
                }
                
                extension = ext_map.get(language.lower(), '.txt')
                filename = f"{tool_type}_tool_{i+1}{extension}"
                filepath = tools_dir / filename
                
                # Save tool
                with open(filepath, 'w') as f:
                    f.write(code.strip())
                
                # Make executable if it's a script
                if extension in ['.sh', '.py']:
                    filepath.chmod(0o755)
                
                tools.append({
                    "filename": filename,
                    "filepath": str(filepath),
                    "language": language,
                    "tool_type": tool_type,
                    "size_bytes": len(code),
                    "executable": extension in ['.sh', '.py']
                })
                
            logger.info(f"Extracted and saved {len(tools)} {tool_type} tools")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to extract {tool_type} tools: {e}")
            return []
            
    def get_generation_history(self) -> List[Dict[str, Any]]:
        """Get script generation history."""
        return self.generated_scripts.copy()
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Coder agent cleanup completed")


# Example usage and testing
async def test_coder_agent():
    """Test the Coder agent."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create Coder agent
        coder = CodexHooksCoderAgent(client)
        
        # Test script generation
        test_scenarios = [
            {
                "name": "Basic hook execution",
                "type": "unit",
                "description": "Test basic script hook execution"
            },
            {
                "name": "Webhook integration",
                "type": "integration",
                "description": "Test webhook hook integration"
            }
        ]
        
        scripts_result = await coder.generate_hook_test_scripts(test_scenarios)
        print(f"Generated test scripts: {scripts_result['generation_id']}")
        
        # Test performance tools generation
        metrics_requirements = {
            "execution_time": True,
            "memory_usage": True,
            "cpu_utilization": True
        }
        
        perf_result = await coder.generate_performance_analysis_tools(metrics_requirements)
        print(f"Generated performance tools: {perf_result['analysis_tools_id']}")
        
        # Test security tools generation
        security_requirements = {
            "input_validation": True,
            "privilege_escalation": True,
            "authentication": True
        }
        
        sec_result = await coder.generate_security_testing_tools(security_requirements)
        print(f"Generated security tools: {sec_result['security_tools_id']}")
        
        # Cleanup
        await coder.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_coder_agent())
