#!/usr/bin/env python3
"""
Enhanced QA Orchestrator Agent for Codex Lifecycle Hooks Testing

This module provides a specialized orchestrator agent that coordinates
comprehensive testing of the Codex lifecycle hooks system using advanced
planning and coordination capabilities.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.teams import MagenticOneGroupChat
    from autogen_agentchat.ui import Console
    from autogen_agentchat.messages import TextMessage
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

logger = logging.getLogger(__name__)


class CodexHooksQAOrchestratorAgent:
    """
    Specialized QA Orchestrator Agent for Codex Lifecycle Hooks Testing.
    
    This agent provides enhanced coordination capabilities specifically designed
    for testing the Codex hooks system, including intelligent test planning,
    execution coordination, and result analysis.
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient, name: str = "QAOrchestrator"):
        self.model_client = model_client
        self.name = name
        self.test_plans = {}
        self.execution_history = []
        self.current_test_session = None
        
        # Create the underlying assistant agent with specialized system prompt
        self.agent = AssistantAgent(
            name=self.name,
            model_client=self.model_client,
            system_message=self._get_system_message()
        )
        
    def _get_system_message(self) -> str:
        """Get the specialized system message for the QA Orchestrator."""
        return """
You are the QA Orchestrator Agent for the Codex Lifecycle Hooks Testing System.

Your primary responsibilities:
1. Create comprehensive test plans for lifecycle hooks validation
2. Coordinate multiple specialized agents (FileSurfer, WebSurfer, Coder, ComputerTerminal)
3. Analyze test results and identify issues
4. Generate detailed QA reports with actionable recommendations
5. Ensure thorough coverage of all hook types and scenarios

Key areas of focus for Codex hooks testing:
- Configuration validation (TOML syntax, semantic correctness)
- Hook execution testing (script, webhook, MCP tool hooks)
- Performance analysis (execution time, resource usage)
- Security assessment (input validation, sandbox isolation)
- Integration testing (CLI integration, event triggering)
- Error handling (failure scenarios, recovery mechanisms)

When creating test plans:
- Break down complex testing into manageable phases
- Assign appropriate agents based on their specializations
- Define clear success criteria for each test
- Include both positive and negative test scenarios
- Consider edge cases and error conditions
- Plan for performance and security testing

When coordinating agents:
- Provide clear, specific instructions to each agent
- Ensure proper sequencing of dependent tests
- Collect and analyze results from all agents
- Identify patterns and correlations across test results
- Escalate critical issues that require immediate attention

Always maintain a focus on quality, thoroughness, and actionable insights.
"""

    async def create_comprehensive_test_plan(self, test_scope: str = "full") -> Dict[str, Any]:
        """
        Create a comprehensive test plan for Codex hooks testing.
        
        Args:
            test_scope: Scope of testing ("full", "config", "functional", "performance", "security")
            
        Returns:
            Detailed test plan with phases, tasks, and agent assignments
        """
        logger.info(f"Creating comprehensive test plan with scope: {test_scope}")
        
        planning_prompt = f"""
Create a detailed test plan for comprehensive Codex lifecycle hooks testing.

Test Scope: {test_scope}

Please create a structured test plan that includes:

1. **Test Phases**: Break down testing into logical phases
2. **Agent Assignments**: Assign specific tasks to appropriate agents
3. **Test Scenarios**: Define specific test cases for each area
4. **Success Criteria**: Clear criteria for determining test success
5. **Dependencies**: Identify dependencies between test phases
6. **Risk Assessment**: Identify potential risks and mitigation strategies

Focus Areas:
- Configuration validation (hooks.toml files, syntax, semantics)
- Hook execution testing (all hook types: script, webhook, MCP)
- Performance benchmarking (execution time, resource usage)
- Security testing (input validation, sandbox isolation, privilege escalation)
- Integration testing (CLI integration, event triggering, error handling)
- Regression testing (ensure existing functionality still works)

Available Agents:
- FileSurfer: File analysis, configuration validation, code review
- WebSurfer: Webhook testing, API validation, web-based integrations
- Coder: Test script generation, analysis tools, performance scripts
- ComputerTerminal: CLI testing, command execution, system validation

Please provide a detailed, actionable test plan in JSON format.
"""

        try:
            # Use the agent to generate the test plan
            response = await self.agent.on_messages(
                [TextMessage(content=planning_prompt, source="user")],
                cancellation_token=None
            )
            
            # Extract the test plan from the response
            test_plan = {
                "plan_id": f"test-plan-{int(datetime.now().timestamp())}",
                "created_at": datetime.now().isoformat(),
                "scope": test_scope,
                "orchestrator": self.name,
                "plan_content": response.chat_message.content if response.chat_message else str(response),
                "status": "created"
            }
            
            # Store the test plan
            self.test_plans[test_plan["plan_id"]] = test_plan
            
            logger.info(f"Created test plan: {test_plan['plan_id']}")
            return test_plan
            
        except Exception as e:
            logger.error(f"Failed to create test plan: {e}")
            raise
            
    async def coordinate_agent_testing(self, test_plan: Dict[str, Any], agents: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate testing across multiple specialized agents.
        
        Args:
            test_plan: The test plan to execute
            agents: Dictionary of available agents
            
        Returns:
            Consolidated test results from all agents
        """
        logger.info(f"Coordinating agent testing for plan: {test_plan['plan_id']}")
        
        coordination_prompt = f"""
Based on the following test plan, coordinate the execution of tests across multiple specialized agents.

Test Plan: {json.dumps(test_plan, indent=2)}

Available Agents: {list(agents.keys())}

Your tasks:
1. Analyze the test plan and break it down into agent-specific tasks
2. Determine the optimal execution order considering dependencies
3. Create specific instructions for each agent
4. Monitor progress and collect results
5. Identify any issues or failures that need attention
6. Provide a comprehensive summary of all test results

For each agent, provide:
- Specific tasks to execute
- Expected deliverables
- Success criteria
- Any special considerations or constraints

Please coordinate the testing execution and provide detailed results.
"""

        try:
            # Start a new test session
            session_id = f"session-{int(datetime.now().timestamp())}"
            self.current_test_session = {
                "session_id": session_id,
                "test_plan_id": test_plan["plan_id"],
                "start_time": datetime.now().isoformat(),
                "agents": list(agents.keys()),
                "status": "running",
                "results": {}
            }
            
            # Use the agent to coordinate testing
            response = await self.agent.on_messages(
                [TextMessage(content=coordination_prompt, source="user")],
                cancellation_token=None
            )
            
            # Update session with results
            self.current_test_session.update({
                "end_time": datetime.now().isoformat(),
                "status": "completed",
                "coordination_result": response.chat_message.content if response.chat_message else str(response)
            })
            
            # Add to execution history
            self.execution_history.append(self.current_test_session.copy())
            
            logger.info(f"Completed agent coordination for session: {session_id}")
            return self.current_test_session
            
        except Exception as e:
            logger.error(f"Failed to coordinate agent testing: {e}")
            if self.current_test_session:
                self.current_test_session.update({
                    "status": "failed",
                    "error": str(e),
                    "end_time": datetime.now().isoformat()
                })
            raise
            
    async def analyze_test_results(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze comprehensive test results and generate insights.
        
        Args:
            test_results: Consolidated test results from all agents
            
        Returns:
            Analysis report with insights and recommendations
        """
        logger.info("Analyzing comprehensive test results")
        
        analysis_prompt = f"""
Analyze the following comprehensive test results from the Codex lifecycle hooks testing:

Test Results: {json.dumps(test_results, indent=2)}

Please provide a thorough analysis that includes:

1. **Overall Assessment**: Summary of test execution and outcomes
2. **Success Rate**: Percentage of tests that passed vs failed
3. **Critical Issues**: Any critical failures or security vulnerabilities
4. **Performance Analysis**: Performance metrics and bottlenecks
5. **Configuration Issues**: Problems with hook configurations
6. **Integration Problems**: Issues with CLI integration or event handling
7. **Recommendations**: Specific actions to address identified issues
8. **Risk Assessment**: Potential risks and their impact
9. **Quality Score**: Overall quality rating for the hooks system
10. **Next Steps**: Recommended follow-up actions

Focus on:
- Actionable insights that developers can use
- Prioritization of issues by severity and impact
- Specific code or configuration changes needed
- Performance optimization opportunities
- Security improvements required

Provide a comprehensive analysis report in a structured format.
"""

        try:
            # Use the agent to analyze results
            response = await self.agent.on_messages(
                [TextMessage(content=analysis_prompt, source="user")],
                cancellation_token=None
            )
            
            analysis_report = {
                "analysis_id": f"analysis-{int(datetime.now().timestamp())}",
                "created_at": datetime.now().isoformat(),
                "test_session_id": test_results.get("session_id"),
                "orchestrator": self.name,
                "analysis_content": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            logger.info(f"Completed test results analysis: {analysis_report['analysis_id']}")
            return analysis_report
            
        except Exception as e:
            logger.error(f"Failed to analyze test results: {e}")
            raise
            
    async def generate_qa_report(self, test_plan: Dict[str, Any], test_results: Dict[str, Any], 
                                analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive QA report.
        
        Args:
            test_plan: The original test plan
            test_results: Test execution results
            analysis: Test results analysis
            
        Returns:
            Comprehensive QA report
        """
        logger.info("Generating comprehensive QA report")
        
        report_prompt = f"""
Generate a comprehensive QA report for the Codex lifecycle hooks testing.

Test Plan: {json.dumps(test_plan, indent=2)}
Test Results: {json.dumps(test_results, indent=2)}
Analysis: {json.dumps(analysis, indent=2)}

Please create a professional QA report that includes:

1. **Executive Summary**: High-level overview for stakeholders
2. **Test Execution Summary**: What was tested and how
3. **Results Overview**: Key findings and metrics
4. **Detailed Findings**: Specific issues and observations
5. **Performance Report**: Performance metrics and analysis
6. **Security Assessment**: Security findings and recommendations
7. **Configuration Review**: Configuration issues and suggestions
8. **Integration Status**: CLI integration and event handling status
9. **Recommendations**: Prioritized action items
10. **Appendices**: Detailed logs and supporting data

The report should be:
- Professional and well-structured
- Actionable with specific recommendations
- Include severity ratings for issues
- Provide clear next steps
- Be suitable for both technical and non-technical stakeholders

Format the report in a clear, professional manner.
"""

        try:
            # Use the agent to generate the report
            response = await self.agent.on_messages(
                [TextMessage(content=report_prompt, source="user")],
                cancellation_token=None
            )
            
            qa_report = {
                "report_id": f"qa-report-{int(datetime.now().timestamp())}",
                "created_at": datetime.now().isoformat(),
                "test_plan_id": test_plan["plan_id"],
                "test_session_id": test_results.get("session_id"),
                "analysis_id": analysis["analysis_id"],
                "orchestrator": self.name,
                "report_content": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Save report to file
            await self._save_report(qa_report)
            
            logger.info(f"Generated QA report: {qa_report['report_id']}")
            return qa_report
            
        except Exception as e:
            logger.error(f"Failed to generate QA report: {e}")
            raise
            
    async def _save_report(self, report: Dict[str, Any]):
        """Save QA report to file."""
        try:
            reports_dir = Path("qa-automation/reports")
            reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"qa_report_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Saved QA report to: {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            
    def get_test_history(self) -> List[Dict[str, Any]]:
        """Get the execution history."""
        return self.execution_history.copy()
        
    def get_test_plans(self) -> Dict[str, Any]:
        """Get all created test plans."""
        return self.test_plans.copy()
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("QA Orchestrator agent cleanup completed")


# Example usage and testing functions
async def test_qa_orchestrator():
    """Test the QA Orchestrator agent."""
    import os
    
    # Initialize client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create orchestrator
        orchestrator = CodexHooksQAOrchestratorAgent(client)
        
        # Create test plan
        test_plan = await orchestrator.create_comprehensive_test_plan("config")
        print(f"Created test plan: {test_plan['plan_id']}")
        
        # Mock agents for testing
        mock_agents = {
            "file_surfer": "FileSurfer agent",
            "web_surfer": "WebSurfer agent", 
            "coder": "Coder agent",
            "computer_terminal": "ComputerTerminal agent"
        }
        
        # Coordinate testing
        test_results = await orchestrator.coordinate_agent_testing(test_plan, mock_agents)
        print(f"Completed test session: {test_results['session_id']}")
        
        # Analyze results
        analysis = await orchestrator.analyze_test_results(test_results)
        print(f"Completed analysis: {analysis['analysis_id']}")
        
        # Generate report
        report = await orchestrator.generate_qa_report(test_plan, test_results, analysis)
        print(f"Generated report: {report['report_id']}")
        
        # Cleanup
        await orchestrator.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_qa_orchestrator())
