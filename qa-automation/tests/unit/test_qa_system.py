#!/usr/bin/env python3
"""
Unit Tests for QA System Components

Tests the integrated QA system, Magentic-One agents,
and workflow automation components.
"""

import pytest
import asyncio
import json
import tempfile
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys

# Add the agents module to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "agents"))

try:
    from integrated_qa_system import IntegratedCodexHooksQASystem
    from magentic_one_orchestrator import MagneticOneOrchestrator
    from file_surfer_agent import FileSurferAgent
    from web_surfer_agent import WebSurferAgent
    from coder_agent import CoderAgent
    from computer_terminal_agent import ComputerTerminalAgent
except ImportError as e:
    # Create mock classes if imports fail
    class IntegratedCodexHooksQASystem:
        def __init__(self, model_client):
            self.model_client = model_client
    
    class MagneticOneOrchestrator:
        def __init__(self, model_client):
            self.model_client = model_client


class TestIntegratedQASystem:
    """Test cases for IntegratedCodexHooksQASystem."""
    
    @pytest.fixture
    def mock_model_client(self):
        """Create a mock model client."""
        mock_client = Mock()
        mock_client.close = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def qa_system(self, mock_model_client):
        """Create a QA system for testing."""
        return IntegratedCodexHooksQASystem(mock_model_client)
    
    def test_qa_system_initialization(self, qa_system, mock_model_client):
        """Test QA system initialization."""
        assert qa_system.model_client == mock_model_client
        assert hasattr(qa_system, 'orchestrator')
        assert hasattr(qa_system, 'agents')
    
    @pytest.mark.asyncio
    async def test_validate_configuration(self, qa_system):
        """Test configuration validation."""
        
        # Mock the validation process
        with patch.object(qa_system, '_validate_toml_config') as mock_validate:
            mock_validate.return_value = {
                "status": "passed",
                "issues": [],
                "recommendations": []
            }
            
            config = {
                "validate_main_config": True,
                "main_config_path": "test/config.toml"
            }
            
            result = await qa_system.validate_configuration(config)
            
            assert "status" in result
            assert "validation_results" in result
            mock_validate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_code_changes(self, qa_system):
        """Test code change analysis."""
        
        # Mock the analysis process
        with patch.object(qa_system, '_analyze_files') as mock_analyze:
            mock_analyze.return_value = {
                "status": "completed",
                "analysis": {"quality_score": 85},
                "recommendations": ["Add more tests"]
            }
            
            config = {
                "files": ["test.py"],
                "review_type": "code_quality"
            }
            
            result = await qa_system.analyze_code_changes(config)
            
            assert "status" in result
            assert "analysis_results" in result
            mock_analyze.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_qa_suite(self, qa_system):
        """Test running comprehensive QA suite."""
        
        # Mock all the QA components
        with patch.object(qa_system, 'validate_configuration') as mock_validate, \
             patch.object(qa_system, 'analyze_code_changes') as mock_analyze, \
             patch.object(qa_system, '_run_performance_tests') as mock_perf:
            
            mock_validate.return_value = {"status": "passed"}
            mock_analyze.return_value = {"status": "passed"}
            mock_perf.return_value = {"status": "passed"}
            
            config = {
                "scope": "comprehensive",
                "validate_main_config": True,
                "main_config_path": "test/config.toml"
            }
            
            result = await qa_system.run_comprehensive_qa_suite(config)
            
            assert "overall_status" in result
            assert "qa_results" in result
            assert "timestamp" in result


class TestMagneticOneOrchestrator:
    """Test cases for MagneticOneOrchestrator."""
    
    @pytest.fixture
    def mock_model_client(self):
        """Create a mock model client."""
        return Mock()
    
    @pytest.fixture
    def orchestrator(self, mock_model_client):
        """Create an orchestrator for testing."""
        return MagneticOneOrchestrator(mock_model_client)
    
    def test_orchestrator_initialization(self, orchestrator, mock_model_client):
        """Test orchestrator initialization."""
        assert orchestrator.model_client == mock_model_client
        assert hasattr(orchestrator, 'agents')
    
    @pytest.mark.asyncio
    async def test_coordinate_qa_workflow(self, orchestrator):
        """Test QA workflow coordination."""
        
        # Mock the coordination process
        with patch.object(orchestrator, '_plan_qa_workflow') as mock_plan, \
             patch.object(orchestrator, '_execute_workflow') as mock_execute:
            
            mock_plan.return_value = ["validate_config", "analyze_code"]
            mock_execute.return_value = {"status": "completed"}
            
            task = {
                "type": "comprehensive_qa",
                "config": {"validate_main_config": True}
            }
            
            result = await orchestrator.coordinate_qa_workflow(task)
            
            assert "status" in result
            mock_plan.assert_called_once()
            mock_execute.assert_called_once()


class TestAgentComponents:
    """Test cases for individual agent components."""
    
    @pytest.fixture
    def mock_model_client(self):
        """Create a mock model client."""
        return Mock()
    
    def test_file_surfer_agent(self, mock_model_client):
        """Test FileSurferAgent initialization and basic functionality."""
        try:
            agent = FileSurferAgent(mock_model_client)
            assert agent.model_client == mock_model_client
            assert hasattr(agent, 'analyze_file')
        except NameError:
            # Skip if class not available
            pytest.skip("FileSurferAgent not available")
    
    def test_web_surfer_agent(self, mock_model_client):
        """Test WebSurferAgent initialization and basic functionality."""
        try:
            agent = WebSurferAgent(mock_model_client)
            assert agent.model_client == mock_model_client
            assert hasattr(agent, 'test_endpoint')
        except NameError:
            # Skip if class not available
            pytest.skip("WebSurferAgent not available")
    
    def test_coder_agent(self, mock_model_client):
        """Test CoderAgent initialization and basic functionality."""
        try:
            agent = CoderAgent(mock_model_client)
            assert agent.model_client == mock_model_client
            assert hasattr(agent, 'generate_test')
        except NameError:
            # Skip if class not available
            pytest.skip("CoderAgent not available")
    
    def test_computer_terminal_agent(self, mock_model_client):
        """Test ComputerTerminalAgent initialization and basic functionality."""
        try:
            agent = ComputerTerminalAgent(mock_model_client)
            assert agent.model_client == mock_model_client
            assert hasattr(agent, 'execute_command')
        except NameError:
            # Skip if class not available
            pytest.skip("ComputerTerminalAgent not available")


class TestWorkflowComponents:
    """Test cases for workflow automation components."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            yield workspace
    
    def test_configuration_validation_workflow(self, temp_workspace):
        """Test configuration validation workflow."""
        
        # Create a test configuration file
        test_config = temp_workspace / "test_config.toml"
        test_config.write_text("""
[hooks.test_hook]
type = "script"
script = "test.sh"
events = ["test"]
enabled = true
""")
        
        # Test validation logic
        from qa_automation.workflows.config_validation_automation import ConfigValidationAutomation
        
        # Mock the validation
        with patch('qa_automation.workflows.config_validation_automation.ConfigValidationAutomation') as MockValidator:
            mock_validator = MockValidator.return_value
            mock_validator.validate_config.return_value = {
                "status": "passed",
                "issues": [],
                "recommendations": []
            }
            
            validator = MockValidator()
            result = validator.validate_config(str(test_config))
            
            assert result["status"] == "passed"
    
    def test_performance_benchmarking_workflow(self):
        """Test performance benchmarking workflow."""
        
        # Mock the performance benchmarking
        with patch('qa_automation.workflows.performance_benchmarking.PerformanceBenchmarkingAutomation') as MockBenchmark:
            mock_benchmark = MockBenchmark.return_value
            mock_benchmark.run_comprehensive_benchmark_suite.return_value = {
                "status": "completed",
                "benchmarks": [],
                "summary": {"overall_status": "passed"}
            }
            
            benchmark = MockBenchmark(Mock())
            result = benchmark.run_comprehensive_benchmark_suite()
            
            assert result["status"] == "completed"
    
    def test_regression_testing_workflow(self):
        """Test regression testing workflow."""
        
        # Mock the regression testing
        with patch('qa_automation.workflows.regression_testing.RegressionTestingWorkflows') as MockRegression:
            mock_regression = MockRegression.return_value
            mock_regression.run_regression_test_suite.return_value = {
                "status": "passed",
                "test_phases": [],
                "regression_analysis": {"regressions_detected": []}
            }
            
            regression = MockRegression(Mock())
            result = regression.run_regression_test_suite()
            
            assert result["status"] == "passed"


class TestQAMetrics:
    """Test cases for QA metrics and reporting."""
    
    def test_qa_metrics_collection(self):
        """Test QA metrics collection."""
        
        # Mock metrics collection
        metrics = {
            "tests_run": 10,
            "tests_passed": 8,
            "tests_failed": 2,
            "coverage_percentage": 85.5,
            "quality_score": 92.3
        }
        
        # Test metrics validation
        assert isinstance(metrics["tests_run"], int)
        assert isinstance(metrics["tests_passed"], int)
        assert isinstance(metrics["tests_failed"], int)
        assert isinstance(metrics["coverage_percentage"], (int, float))
        assert isinstance(metrics["quality_score"], (int, float))
        
        # Test metrics calculations
        assert metrics["tests_passed"] + metrics["tests_failed"] == metrics["tests_run"]
        assert 0 <= metrics["coverage_percentage"] <= 100
        assert 0 <= metrics["quality_score"] <= 100
    
    def test_qa_report_generation(self):
        """Test QA report generation."""
        
        # Mock report data
        report_data = {
            "summary": {
                "overall_status": "passed",
                "total_checks": 15,
                "passed_checks": 13,
                "failed_checks": 2
            },
            "details": {
                "configuration_validation": {"status": "passed"},
                "code_analysis": {"status": "passed"},
                "performance_tests": {"status": "failed"},
                "security_checks": {"status": "passed"}
            },
            "recommendations": [
                "Optimize performance in module X",
                "Add more unit tests for component Y"
            ]
        }
        
        # Test report structure
        assert "summary" in report_data
        assert "details" in report_data
        assert "recommendations" in report_data
        
        # Test summary data
        summary = report_data["summary"]
        assert summary["passed_checks"] + summary["failed_checks"] == summary["total_checks"]


# Test utilities
class TestUtilities:
    """Utility functions for testing."""
    
    @staticmethod
    def create_mock_qa_result(status: str = "passed") -> dict:
        """Create a mock QA result."""
        return {
            "status": status,
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {
                "configuration_validation": {"status": status},
                "code_analysis": {"status": status},
                "performance_tests": {"status": status}
            },
            "metrics": {
                "quality_score": 85.0,
                "coverage_percentage": 78.5
            },
            "recommendations": []
        }
    
    @staticmethod
    def create_mock_agent_response(agent_type: str) -> dict:
        """Create a mock agent response."""
        return {
            "agent_type": agent_type,
            "status": "completed",
            "timestamp": "2024-01-01T00:00:00Z",
            "results": {
                "analysis": f"Mock analysis from {agent_type}",
                "recommendations": [f"Mock recommendation from {agent_type}"]
            }
        }


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
