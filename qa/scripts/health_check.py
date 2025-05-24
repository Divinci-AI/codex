#!/usr/bin/env python3
"""
Health Check Script
Validates that the QA system is properly configured and operational
"""

import json
import os
import sys
from pathlib import Path


def check_python_dependencies():
    """Check if required Python packages are available"""
    required_packages = [
        'autogen_agentchat',
        'autogen_ext',
        'openai',
        'aiohttp',
        'toml',
        'yaml',
        'rich'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages


def check_environment_variables():
    """Check if required environment variables are set"""
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['QA_LOG_LEVEL', 'QA_DEBUG']
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def check_file_structure():
    """Check if required files and directories exist"""
    base_path = Path('/workspace/qa')
    required_paths = [
        'agents/__init__.py',
        'agents/orchestrator.py',
        'agents/file_surfer.py',
        'agents/web_surfer.py',
        'agents/coder.py',
        'agents/terminal.py',
        'workflows/__init__.py',
        'workflows/hooks_validation.py',
        'configs/agent_config.json',
        'configs/safety_config.json',
        'configs/test_scenarios.json',
        'utils/__init__.py',
        'utils/safety.py',
        'utils/reporting.py',
        'run_qa.py'
    ]
    
    missing_paths = []
    for path_str in required_paths:
        path = base_path / path_str
        if not path.exists():
            missing_paths.append(str(path))
    
    return len(missing_paths) == 0, missing_paths


def check_docker_availability():
    """Check if Docker is available"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True, None
    except Exception as e:
        return False, str(e)


def check_permissions():
    """Check file permissions"""
    base_path = Path('/workspace/qa')
    
    # Check if we can write to logs and reports directories
    logs_dir = base_path / 'logs'
    reports_dir = base_path / 'reports'
    
    try:
        logs_dir.mkdir(exist_ok=True)
        reports_dir.mkdir(exist_ok=True)
        
        # Test write access
        test_file = logs_dir / 'health_check_test.txt'
        test_file.write_text('test')
        test_file.unlink()
        
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    """Run health checks"""
    print("🔍 Codex QA System Health Check")
    print("=" * 40)
    
    checks = [
        ("Python Dependencies", check_python_dependencies),
        ("Environment Variables", check_environment_variables),
        ("File Structure", check_file_structure),
        ("Docker Availability", check_docker_availability),
        ("Permissions", check_permissions)
    ]
    
    all_passed = True
    results = {}
    
    for check_name, check_func in checks:
        try:
            passed, details = check_func()
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {check_name}")
            
            if not passed:
                all_passed = False
                if details:
                    print(f"   Details: {details}")
            
            results[check_name] = {
                'passed': passed,
                'details': details
            }
            
        except Exception as e:
            print(f"❌ FAIL {check_name}")
            print(f"   Error: {e}")
            all_passed = False
            results[check_name] = {
                'passed': False,
                'error': str(e)
            }
    
    print("=" * 40)
    
    if all_passed:
        print("🎉 All health checks passed! QA system is ready.")
        exit_code = 0
    else:
        print("⚠️  Some health checks failed. Please review the issues above.")
        exit_code = 1
    
    # Save results to file
    try:
        results_file = Path('/workspace/qa/logs/health_check_results.json')
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': str(Path(__file__).stat().st_mtime),
                'overall_status': 'pass' if all_passed else 'fail',
                'checks': results
            }, f, indent=2)
        
        print(f"📄 Health check results saved to: {results_file}")
        
    except Exception as e:
        print(f"⚠️  Could not save health check results: {e}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
