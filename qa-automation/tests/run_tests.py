#!/usr/bin/env python3
"""
Test Runner for AutoAgent Framework

Comprehensive test runner that executes unit tests, integration tests,
and end-to-end tests for the AutoAgent framework.
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any
import json

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "qa-automation"))
sys.path.append(str(project_root / "qa-automation" / "agents"))
sys.path.append(str(project_root / "qa-automation" / "safety"))
sys.path.append(str(project_root / "qa-automation" / "server"))

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color


class TestRunner:
    """Comprehensive test runner for AutoAgent framework."""
    
    def __init__(self, verbose: bool = False, coverage: bool = False):
        self.verbose = verbose
        self.coverage = coverage
        self.test_results = {}
        self.start_time = time.time()
        
        # Test directories
        self.test_dir = Path(__file__).parent
        self.unit_test_dir = self.test_dir / "unit"
        self.e2e_test_dir = self.test_dir / "e2e"
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Log a message with color."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"{color}[{timestamp}]{Colors.NC} {message}")
    
    def run_command(self, command: List[str], cwd: Path = None) -> Dict[str, Any]:
        """Run a command and return results."""
        
        self.log(f"Running: {' '.join(command)}", Colors.CYAN)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.test_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration
            }
            
        except subprocess.TimeoutExpired:
            self.log("Command timed out", Colors.RED)
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "duration": 300
            }
        except Exception as e:
            self.log(f"Command failed: {e}", Colors.RED)
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0
            }
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed."""
        
        self.log("Checking dependencies...", Colors.BLUE)
        
        required_packages = [
            "pytest",
            "requests",
            "fastapi",
            "uvicorn"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                self.log(f"✓ {package}", Colors.GREEN)
            except ImportError:
                self.log(f"✗ {package} (missing)", Colors.RED)
                missing_packages.append(package)
        
        if missing_packages:
            self.log(f"Missing packages: {', '.join(missing_packages)}", Colors.RED)
            self.log("Install with: pip install " + " ".join(missing_packages), Colors.YELLOW)
            return False
        
        self.log("All dependencies available", Colors.GREEN)
        return True
    
    def run_unit_tests(self) -> bool:
        """Run unit tests."""
        
        self.log("Running Unit Tests", Colors.PURPLE)
        self.log("=" * 50, Colors.PURPLE)
        
        if not self.unit_test_dir.exists():
            self.log("Unit test directory not found", Colors.RED)
            return False
        
        # Build pytest command
        pytest_cmd = ["python", "-m", "pytest"]
        
        if self.verbose:
            pytest_cmd.append("-v")
        
        if self.coverage:
            pytest_cmd.extend([
                "--cov=qa-automation",
                "--cov-report=html",
                "--cov-report=term"
            ])
        
        pytest_cmd.extend([
            str(self.unit_test_dir),
            "--tb=short",
            "-x"  # Stop on first failure
        ])
        
        result = self.run_command(pytest_cmd)
        
        self.test_results["unit_tests"] = result
        
        if result["success"]:
            self.log("Unit tests PASSED", Colors.GREEN)
        else:
            self.log("Unit tests FAILED", Colors.RED)
            if self.verbose:
                self.log("STDOUT:", Colors.YELLOW)
                print(result["stdout"])
                self.log("STDERR:", Colors.YELLOW)
                print(result["stderr"])
        
        return result["success"]
    
    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        
        self.log("Running Integration Tests", Colors.PURPLE)
        self.log("=" * 50, Colors.PURPLE)
        
        # Check if AutoGen server is available
        server_available = self.check_autogen_server()
        
        if not server_available:
            self.log("AutoGen server not available - skipping integration tests", Colors.YELLOW)
            return True  # Don't fail the entire test suite
        
        # Run integration test script
        integration_script = self.test_dir.parent / "scripts" / "test-integration.sh"
        
        if not integration_script.exists():
            self.log("Integration test script not found", Colors.RED)
            return False
        
        result = self.run_command([str(integration_script)])
        
        self.test_results["integration_tests"] = result
        
        if result["success"]:
            self.log("Integration tests PASSED", Colors.GREEN)
        else:
            self.log("Integration tests FAILED", Colors.RED)
            if self.verbose:
                self.log("STDOUT:", Colors.YELLOW)
                print(result["stdout"])
                self.log("STDERR:", Colors.YELLOW)
                print(result["stderr"])
        
        return result["success"]
    
    def run_e2e_tests(self) -> bool:
        """Run end-to-end tests."""
        
        self.log("Running End-to-End Tests", Colors.PURPLE)
        self.log("=" * 50, Colors.PURPLE)
        
        if not self.e2e_test_dir.exists():
            self.log("E2E test directory not found", Colors.RED)
            return False
        
        # Check if OpenAI API key is available
        if not os.getenv("OPENAI_API_KEY"):
            self.log("OPENAI_API_KEY not set - some E2E tests will be skipped", Colors.YELLOW)
        
        # Build pytest command for E2E tests
        pytest_cmd = ["python", "-m", "pytest"]
        
        if self.verbose:
            pytest_cmd.append("-v")
        
        pytest_cmd.extend([
            str(self.e2e_test_dir),
            "--tb=short",
            "-s"  # Don't capture output for E2E tests
        ])
        
        result = self.run_command(pytest_cmd)
        
        self.test_results["e2e_tests"] = result
        
        if result["success"]:
            self.log("E2E tests PASSED", Colors.GREEN)
        else:
            self.log("E2E tests FAILED", Colors.RED)
            if self.verbose:
                self.log("STDOUT:", Colors.YELLOW)
                print(result["stdout"])
                self.log("STDERR:", Colors.YELLOW)
                print(result["stderr"])
        
        return result["success"]
    
    def check_autogen_server(self) -> bool:
        """Check if AutoGen server is running."""
        
        try:
            import requests
            response = requests.get("http://localhost:5000/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def run_linting(self) -> bool:
        """Run code linting."""
        
        self.log("Running Code Linting", Colors.PURPLE)
        self.log("=" * 50, Colors.PURPLE)
        
        # Check if flake8 is available
        try:
            import flake8
        except ImportError:
            self.log("flake8 not available - skipping linting", Colors.YELLOW)
            return True
        
        # Run flake8 on the codebase
        flake8_cmd = [
            "python", "-m", "flake8",
            str(self.test_dir.parent),
            "--max-line-length=100",
            "--ignore=E501,W503",
            "--exclude=__pycache__,*.pyc,.git"
        ]
        
        result = self.run_command(flake8_cmd)
        
        self.test_results["linting"] = result
        
        if result["success"]:
            self.log("Linting PASSED", Colors.GREEN)
        else:
            self.log("Linting FAILED", Colors.RED)
            if self.verbose:
                print(result["stdout"])
        
        return result["success"]
    
    def run_type_checking(self) -> bool:
        """Run type checking with mypy."""
        
        self.log("Running Type Checking", Colors.PURPLE)
        self.log("=" * 50, Colors.PURPLE)
        
        # Check if mypy is available
        try:
            import mypy
        except ImportError:
            self.log("mypy not available - skipping type checking", Colors.YELLOW)
            return True
        
        # Run mypy on the codebase
        mypy_cmd = [
            "python", "-m", "mypy",
            str(self.test_dir.parent),
            "--ignore-missing-imports",
            "--no-strict-optional"
        ]
        
        result = self.run_command(mypy_cmd)
        
        self.test_results["type_checking"] = result
        
        if result["success"]:
            self.log("Type checking PASSED", Colors.GREEN)
        else:
            self.log("Type checking FAILED", Colors.RED)
            if self.verbose:
                print(result["stdout"])
        
        return result["success"]
    
    def generate_test_report(self) -> None:
        """Generate a comprehensive test report."""
        
        self.log("Generating Test Report", Colors.BLUE)
        self.log("=" * 50, Colors.BLUE)
        
        total_duration = time.time() - self.start_time
        
        # Calculate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        # Print summary
        print(f"\n{Colors.WHITE}{'='*60}{Colors.NC}")
        print(f"{Colors.WHITE}TEST SUMMARY{Colors.NC}")
        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")
        
        for test_name, result in self.test_results.items():
            status = f"{Colors.GREEN}PASSED{Colors.NC}" if result["success"] else f"{Colors.RED}FAILED{Colors.NC}"
            duration = f"{result['duration']:.2f}s"
            print(f"{test_name.replace('_', ' ').title():<30} {status} ({duration})")
        
        print(f"\n{Colors.WHITE}Overall Results:{Colors.NC}")
        print(f"Total test suites: {total_tests}")
        print(f"Passed: {Colors.GREEN}{passed_tests}{Colors.NC}")
        print(f"Failed: {Colors.RED}{failed_tests}{Colors.NC}")
        print(f"Total duration: {total_duration:.2f}s")
        
        # Save detailed report
        report_file = self.test_dir / "test_report.json"
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration": total_duration,
            "summary": {
                "total_suites": total_tests,
                "passed_suites": passed_tests,
                "failed_suites": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "results": self.test_results
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.log(f"Detailed report saved to: {report_file}", Colors.BLUE)
        
        # Overall result
        if failed_tests == 0:
            self.log("ALL TESTS PASSED! 🎉", Colors.GREEN)
            return True
        else:
            self.log(f"{failed_tests} test suite(s) failed", Colors.RED)
            return False
    
    def run_all_tests(self, test_types: List[str] = None) -> bool:
        """Run all specified test types."""
        
        if test_types is None:
            test_types = ["unit", "integration", "e2e", "lint", "type"]
        
        self.log("Starting AutoAgent Framework Test Suite", Colors.WHITE)
        self.log("=" * 60, Colors.WHITE)
        
        # Check dependencies first
        if not self.check_dependencies():
            return False
        
        success = True
        
        # Run each test type
        if "unit" in test_types:
            success &= self.run_unit_tests()
        
        if "integration" in test_types:
            success &= self.run_integration_tests()
        
        if "e2e" in test_types:
            success &= self.run_e2e_tests()
        
        if "lint" in test_types:
            success &= self.run_linting()
        
        if "type" in test_types:
            success &= self.run_type_checking()
        
        # Generate report
        self.generate_test_report()
        
        return success


def main():
    """Main entry point."""
    
    parser = argparse.ArgumentParser(description="AutoAgent Framework Test Runner")
    
    parser.add_argument(
        "--test-types",
        nargs="+",
        choices=["unit", "integration", "e2e", "lint", "type"],
        default=["unit", "integration", "e2e"],
        help="Types of tests to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only unit tests (quick check)"
    )
    
    args = parser.parse_args()
    
    # Quick mode - only unit tests
    if args.quick:
        args.test_types = ["unit"]
    
    # Create and run test runner
    runner = TestRunner(verbose=args.verbose, coverage=args.coverage)
    success = runner.run_all_tests(args.test_types)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
