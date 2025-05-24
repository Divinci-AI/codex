#!/usr/bin/env python3
"""
Codex QA Automation Runner
Main entry point for running Magentic-One QA workflows
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Load environment variables
load_dotenv()

# Set up rich console
console = Console()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('QA_LOG_LEVEL', 'INFO')),
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger("qa_runner")

# Import QA modules
try:
    from agents.orchestrator import QAOrchestrator
    from workflows.hooks_validation import HooksValidationWorkflow
    from workflows.e2e_testing import E2ETestingWorkflow
    from workflows.performance import PerformanceWorkflow
    from workflows.security import SecurityWorkflow
    from utils.safety import SafetyManager
    from utils.reporting import ReportGenerator
except ImportError as e:
    logger.error(f"Failed to import QA modules: {e}")
    logger.error("Make sure you're running from the qa/ directory and all dependencies are installed")
    sys.exit(1)


class QARunner:
    """Main QA runner that orchestrates all testing workflows"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "configs/agent_config.json"
        self.config = self._load_config()
        self.safety_manager = SafetyManager()
        self.report_generator = ReportGenerator()
        self.orchestrator = None
        self.start_time = None
        
    def _load_config(self) -> Dict:
        """Load QA configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            sys.exit(1)
    
    async def initialize(self) -> bool:
        """Initialize the QA system"""
        try:
            console.print("[bold blue]Initializing Codex QA System...[/bold blue]")
            
            # Initialize safety manager
            await self.safety_manager.initialize()
            
            # Initialize orchestrator
            self.orchestrator = QAOrchestrator(self.config)
            await self.orchestrator.initialize()
            
            # Validate environment
            if not await self._validate_environment():
                return False
                
            console.print("[bold green]✓ QA System initialized successfully[/bold green]")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize QA system: {e}")
            return False
    
    async def _validate_environment(self) -> bool:
        """Validate the QA environment"""
        checks = [
            ("OpenAI API Key", self._check_openai_key),
            ("Docker Access", self._check_docker_access),
            ("Workspace Access", self._check_workspace_access),
            ("Safety Protocols", self._check_safety_protocols),
        ]
        
        console.print("[bold yellow]Validating environment...[/bold yellow]")
        
        for check_name, check_func in checks:
            try:
                result = await check_func()
                status = "[green]✓[/green]" if result else "[red]✗[/red]"
                console.print(f"  {status} {check_name}")
                if not result:
                    return False
            except Exception as e:
                console.print(f"  [red]✗[/red] {check_name}: {e}")
                return False
        
        return True
    
    async def _check_openai_key(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(os.getenv('OPENAI_API_KEY'))
    
    async def _check_docker_access(self) -> bool:
        """Check if Docker is accessible"""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False
    
    async def _check_workspace_access(self) -> bool:
        """Check if workspace is accessible"""
        workspace_path = Path("/workspace")
        return workspace_path.exists() and workspace_path.is_dir()
    
    async def _check_safety_protocols(self) -> bool:
        """Check if safety protocols are active"""
        return await self.safety_manager.validate_safety_protocols()
    
    async def run_suite(self, suite_name: str, **kwargs) -> Dict:
        """Run a specific test suite"""
        self.start_time = time.time()
        
        console.print(f"[bold blue]Running QA Suite: {suite_name}[/bold blue]")
        
        # Map suite names to workflow classes
        workflows = {
            'full': [HooksValidationWorkflow, E2ETestingWorkflow, PerformanceWorkflow, SecurityWorkflow],
            'hooks-validation': [HooksValidationWorkflow],
            'e2e-testing': [E2ETestingWorkflow],
            'performance-benchmarks': [PerformanceWorkflow],
            'security-tests': [SecurityWorkflow],
        }
        
        if suite_name not in workflows:
            logger.error(f"Unknown test suite: {suite_name}")
            return {'success': False, 'error': f'Unknown suite: {suite_name}'}
        
        results = {}
        total_workflows = len(workflows[suite_name])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for i, workflow_class in enumerate(workflows[suite_name]):
                workflow_name = workflow_class.__name__
                task = progress.add_task(f"Running {workflow_name}...", total=1)
                
                try:
                    # Initialize workflow
                    workflow = workflow_class(self.orchestrator, self.config)
                    
                    # Run workflow with safety checks
                    workflow_result = await self.safety_manager.run_with_safety_checks(
                        workflow.run, **kwargs
                    )
                    
                    results[workflow_name] = workflow_result
                    progress.update(task, completed=1)
                    
                    # Log progress
                    status = "✓" if workflow_result.get('success', False) else "✗"
                    console.print(f"  {status} {workflow_name} completed")
                    
                except Exception as e:
                    logger.error(f"Workflow {workflow_name} failed: {e}")
                    results[workflow_name] = {'success': False, 'error': str(e)}
                    progress.update(task, completed=1)
        
        # Generate comprehensive report
        execution_time = time.time() - self.start_time
        report = await self._generate_report(suite_name, results, execution_time)
        
        return {
            'success': all(r.get('success', False) for r in results.values()),
            'results': results,
            'report': report,
            'execution_time': execution_time
        }
    
    async def _generate_report(self, suite_name: str, results: Dict, execution_time: float) -> Dict:
        """Generate a comprehensive test report"""
        report_data = {
            'suite_name': suite_name,
            'timestamp': datetime.now().isoformat(),
            'execution_time': execution_time,
            'results': results,
            'summary': {
                'total_workflows': len(results),
                'successful_workflows': sum(1 for r in results.values() if r.get('success', False)),
                'failed_workflows': sum(1 for r in results.values() if not r.get('success', False)),
                'overall_success': all(r.get('success', False) for r in results.values())
            }
        }
        
        # Generate reports in multiple formats
        report_files = await self.report_generator.generate_reports(report_data)
        report_data['report_files'] = report_files
        
        return report_data
    
    def display_summary(self, results: Dict):
        """Display a summary of test results"""
        table = Table(title="QA Test Results Summary")
        table.add_column("Workflow", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Duration", style="magenta")
        table.add_column("Details", style="dim")
        
        for workflow_name, result in results['results'].items():
            status = "[green]PASS[/green]" if result.get('success', False) else "[red]FAIL[/red]"
            duration = f"{result.get('execution_time', 0):.2f}s"
            details = result.get('summary', 'No details available')
            
            table.add_row(workflow_name, status, duration, str(details))
        
        console.print(table)
        
        # Overall summary
        summary = results['summary']
        overall_status = "[green]PASS[/green]" if summary['overall_success'] else "[red]FAIL[/red]"
        
        console.print(f"\n[bold]Overall Status: {overall_status}[/bold]")
        console.print(f"Total Execution Time: {results['execution_time']:.2f}s")
        console.print(f"Workflows: {summary['successful_workflows']}/{summary['total_workflows']} passed")
        
        if results.get('report', {}).get('report_files'):
            console.print(f"\nReports generated:")
            for report_file in results['report']['report_files']:
                console.print(f"  • {report_file}")


@click.command()
@click.option('--suite', default='full', help='Test suite to run (full, hooks-validation, e2e-testing, performance-benchmarks, security-tests)')
@click.option('--config', help='Path to configuration file')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--verbose', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Perform a dry run without executing tests')
@click.option('--parallel', default=1, help='Number of parallel test workers')
@click.option('--timeout', default=600, help='Test timeout in seconds')
@click.option('--report-format', default='json,html', help='Report formats (comma-separated)')
def main(suite, config, debug, verbose, dry_run, parallel, timeout, report_format):
    """Codex QA Automation Runner"""
    
    # Set log level based on flags
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Create QA runner
    runner = QARunner(config)
    
    async def run_qa():
        # Initialize QA system
        if not await runner.initialize():
            console.print("[bold red]Failed to initialize QA system[/bold red]")
            sys.exit(1)
        
        if dry_run:
            console.print("[bold yellow]Dry run mode - no tests will be executed[/bold yellow]")
            return
        
        # Run the specified test suite
        results = await runner.run_suite(
            suite,
            parallel=parallel,
            timeout=timeout,
            report_format=report_format.split(',')
        )
        
        # Display results
        runner.display_summary(results)
        
        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)
    
    # Run the async main function
    try:
        asyncio.run(run_qa())
    except KeyboardInterrupt:
        console.print("\n[bold red]QA execution interrupted by user[/bold red]")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
