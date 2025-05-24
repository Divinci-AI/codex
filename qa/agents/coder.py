"""
Coder Agent
Specialized agent for code generation, analysis, and test script creation
"""

import ast
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class CoderAgent:
    """
    Coder agent responsible for generating test scripts, analyzing code quality,
    and creating automation scripts for the QA system.
    """
    
    def __init__(self, config: Dict, client):
        self.config = config
        self.client = client
        self.restrictions = config.get('restrictions', {})
        self.capabilities = config.get('capabilities', [])
        
        # Code generation restrictions
        self.supported_languages = set(self.restrictions.get('supported_languages', []))
        self.max_script_length = self.restrictions.get('max_script_length', 1000)
        self.no_execution = self.restrictions.get('no_execution', True)
        self.safe_patterns_only = self.restrictions.get('safe_patterns_only', True)
        
        # Code analysis state
        self.generated_scripts = {}
        self.analysis_cache = {}
        
        # Dangerous patterns to avoid
        self.dangerous_patterns = [
            r'rm\s+-rf',
            r'sudo\s+',
            r'exec\s*\(',
            r'eval\s*\(',
            r'__import__',
            r'open\s*\(',
            r'file\s*\(',
            r'subprocess\.',
            r'os\.system',
            r'os\.popen',
            r'shell=True'
        ]
        
    async def initialize(self) -> bool:
        """Initialize the Coder agent"""
        try:
            logger.info("Initializing Coder agent...")
            
            # Validate configuration
            if not await self._validate_config():
                return False
            
            # Test code analysis capabilities
            if not await self._test_analysis_capabilities():
                return False
            
            logger.info("Coder agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Coder agent: {e}")
            return False
    
    async def _validate_config(self) -> bool:
        """Validate agent configuration"""
        required_capabilities = ['test_generation', 'code_analysis']
        missing_capabilities = [cap for cap in required_capabilities if cap not in self.capabilities]
        
        if missing_capabilities:
            logger.error(f"Missing required capabilities: {missing_capabilities}")
            return False
        
        if not self.supported_languages:
            logger.error("No supported programming languages configured")
            return False
        
        return True
    
    async def _test_analysis_capabilities(self) -> bool:
        """Test basic code analysis capabilities"""
        try:
            # Test Python AST parsing
            test_code = "def test_function(): return True"
            ast.parse(test_code)
            
            # Test regex compilation
            for pattern in self.dangerous_patterns:
                re.compile(pattern)
            
            return True
            
        except Exception as e:
            logger.error(f"Code analysis capability test failed: {e}")
            return False
    
    async def generate_test_script(self, test_scenario: Dict, language: str = 'python') -> Dict:
        """Generate a test script for a given scenario"""
        try:
            logger.info(f"Generating {language} test script for scenario: {test_scenario.get('name')}")
            
            # Validate language support
            if language not in self.supported_languages:
                return {'success': False, 'error': f'Language {language} not supported'}
            
            # Generate script based on language
            if language == 'python':
                script_result = await self._generate_python_test_script(test_scenario)
            elif language == 'bash':
                script_result = await self._generate_bash_test_script(test_scenario)
            elif language == 'javascript':
                script_result = await self._generate_javascript_test_script(test_scenario)
            else:
                return {'success': False, 'error': f'Script generation not implemented for {language}'}
            
            # Validate generated script
            if script_result.get('success'):
                validation_result = await self._validate_generated_script(
                    script_result['script'], language
                )
                script_result['validation'] = validation_result
                
                if not validation_result.get('safe', True):
                    script_result['success'] = False
                    script_result['error'] = 'Generated script failed safety validation'
            
            # Store generated script
            if script_result.get('success'):
                script_id = f"{test_scenario.get('name', 'unnamed')}_{language}"
                self.generated_scripts[script_id] = script_result
            
            return script_result
            
        except Exception as e:
            logger.error(f"Test script generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_python_test_script(self, test_scenario: Dict) -> Dict:
        """Generate Python test script"""
        try:
            scenario_name = test_scenario.get('name', 'test_scenario')
            scenario_type = test_scenario.get('type', 'generic')
            test_cases = test_scenario.get('test_cases', [])
            
            # Base script template
            script_lines = [
                "#!/usr/bin/env python3",
                '"""',
                f'Generated test script for scenario: {scenario_name}',
                f'Scenario type: {scenario_type}',
                '"""',
                '',
                'import json',
                'import sys',
                'import time',
                'from pathlib import Path',
                '',
                f'def test_{scenario_name.replace("-", "_").replace(" ", "_")}():',
                '    """Main test function"""',
                '    results = []',
                '    ',
            ]
            
            # Generate test cases
            for i, test_case in enumerate(test_cases):
                case_name = test_case.get('name', f'case_{i}')
                script_lines.extend([
                    f'    # Test case: {case_name}',
                    f'    try:',
                    f'        result = run_test_case_{i}()',
                    f'        results.append({{"case": "{case_name}", "success": result, "error": None}})',
                    f'    except Exception as e:',
                    f'        results.append({{"case": "{case_name}", "success": False, "error": str(e)}})',
                    '    ',
                ])
            
            script_lines.extend([
                '    return results',
                '',
            ])
            
            # Generate individual test case functions
            for i, test_case in enumerate(test_cases):
                case_function = await self._generate_python_test_case(i, test_case)
                script_lines.extend(case_function)
            
            # Add main execution block
            script_lines.extend([
                '',
                'if __name__ == "__main__":',
                f'    results = test_{scenario_name.replace("-", "_").replace(" ", "_")}()',
                '    ',
                '    # Print results',
                '    print(json.dumps(results, indent=2))',
                '    ',
                '    # Exit with appropriate code',
                '    failed_tests = [r for r in results if not r["success"]]',
                '    sys.exit(len(failed_tests))',
            ])
            
            script_content = '\n'.join(script_lines)
            
            # Check script length
            if len(script_content) > self.max_script_length * 100:  # Allow some flexibility
                return {'success': False, 'error': 'Generated script exceeds maximum length'}
            
            return {
                'success': True,
                'script': script_content,
                'language': 'python',
                'scenario': scenario_name,
                'test_cases_count': len(test_cases)
            }
            
        except Exception as e:
            logger.error(f"Python script generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _generate_python_test_case(self, case_index: int, test_case: Dict) -> List[str]:
        """Generate Python code for a single test case"""
        case_name = test_case.get('name', f'case_{case_index}')
        case_type = test_case.get('type', 'generic')
        
        lines = [
            f'def run_test_case_{case_index}():',
            f'    """Test case: {case_name}"""',
        ]
        
        if case_type == 'file_validation':
            file_path = test_case.get('file_path', '/dev/null')
            lines.extend([
                f'    file_path = Path("{file_path}")',
                '    if not file_path.exists():',
                '        raise FileNotFoundError(f"Test file not found: {file_path}")',
                '    ',
                '    # Validate file properties',
                '    if not file_path.is_file():',
                '        raise ValueError(f"Path is not a file: {file_path}")',
                '    ',
                '    return True',
            ])
        elif case_type == 'webhook_test':
            url = test_case.get('url', 'http://localhost:8080/test')
            lines.extend([
                '    import requests',
                f'    response = requests.get("{url}", timeout=10)',
                '    response.raise_for_status()',
                '    return response.status_code == 200',
            ])
        else:
            # Generic test case
            lines.extend([
                '    # Generic test case implementation',
                '    print(f"Running test case: {case_name}")',
                '    return True',
            ])
        
        lines.append('')
        return lines
    
    async def _generate_bash_test_script(self, test_scenario: Dict) -> Dict:
        """Generate Bash test script"""
        try:
            scenario_name = test_scenario.get('name', 'test_scenario')
            test_cases = test_scenario.get('test_cases', [])
            
            script_lines = [
                '#!/bin/bash',
                '# Generated test script for scenario: ' + scenario_name,
                '',
                'set -e  # Exit on error',
                'set -u  # Exit on undefined variable',
                '',
                'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
                'TEST_RESULTS=0',
                '',
                'log_test() {',
                '    echo "[$(date)] $1"',
                '}',
                '',
                'run_test_case() {',
                '    local case_name="$1"',
                '    local test_command="$2"',
                '    ',
                '    log_test "Running test case: $case_name"',
                '    if eval "$test_command"; then',
                '        log_test "✓ $case_name PASSED"',
                '        return 0',
                '    else',
                '        log_test "✗ $case_name FAILED"',
                '        TEST_RESULTS=$((TEST_RESULTS + 1))',
                '        return 1',
                '    fi',
                '}',
                '',
            ]
            
            # Generate test cases
            for i, test_case in enumerate(test_cases):
                case_name = test_case.get('name', f'case_{i}')
                case_command = self._generate_bash_test_command(test_case)
                script_lines.append(f'run_test_case "{case_name}" "{case_command}"')
            
            script_lines.extend([
                '',
                'log_test "Test execution completed"',
                'log_test "Failed tests: $TEST_RESULTS"',
                'exit $TEST_RESULTS',
            ])
            
            script_content = '\n'.join(script_lines)
            
            return {
                'success': True,
                'script': script_content,
                'language': 'bash',
                'scenario': scenario_name,
                'test_cases_count': len(test_cases)
            }
            
        except Exception as e:
            logger.error(f"Bash script generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_bash_test_command(self, test_case: Dict) -> str:
        """Generate Bash command for a test case"""
        case_type = test_case.get('type', 'generic')
        
        if case_type == 'file_validation':
            file_path = test_case.get('file_path', '/dev/null')
            return f'test -f "{file_path}"'
        elif case_type == 'command_execution':
            command = test_case.get('command', 'true')
            # Sanitize command for safety
            safe_command = re.sub(r'[;&|`$()]', '', command)
            return safe_command
        else:
            return 'true'  # Default success
    
    async def _generate_javascript_test_script(self, test_scenario: Dict) -> Dict:
        """Generate JavaScript test script"""
        try:
            scenario_name = test_scenario.get('name', 'test_scenario')
            test_cases = test_scenario.get('test_cases', [])
            
            script_lines = [
                '#!/usr/bin/env node',
                '/**',
                f' * Generated test script for scenario: {scenario_name}',
                ' */',
                '',
                'const fs = require("fs");',
                'const path = require("path");',
                '',
                'class TestRunner {',
                '    constructor() {',
                '        this.results = [];',
                '    }',
                '',
                '    async runTest(name, testFunction) {',
                '        try {',
                '            console.log(`Running test: ${name}`);',
                '            const result = await testFunction();',
                '            this.results.push({ name, success: true, result });',
                '            console.log(`✓ ${name} PASSED`);',
                '        } catch (error) {',
                '            this.results.push({ name, success: false, error: error.message });',
                '            console.log(`✗ ${name} FAILED: ${error.message}`);',
                '        }',
                '    }',
                '',
                '    getResults() {',
                '        return this.results;',
                '    }',
                '}',
                '',
                'async function main() {',
                '    const runner = new TestRunner();',
                '',
            ]
            
            # Generate test cases
            for i, test_case in enumerate(test_cases):
                case_name = test_case.get('name', f'case_{i}')
                case_function = self._generate_javascript_test_case(test_case)
                script_lines.extend([
                    f'    await runner.runTest("{case_name}", async () => {{',
                    f'        {case_function}',
                    '    });',
                    '',
                ])
            
            script_lines.extend([
                '    const results = runner.getResults();',
                '    console.log(JSON.stringify(results, null, 2));',
                '',
                '    const failedTests = results.filter(r => !r.success);',
                '    process.exit(failedTests.length);',
                '}',
                '',
                'main().catch(console.error);',
            ])
            
            script_content = '\n'.join(script_lines)
            
            return {
                'success': True,
                'script': script_content,
                'language': 'javascript',
                'scenario': scenario_name,
                'test_cases_count': len(test_cases)
            }
            
        except Exception as e:
            logger.error(f"JavaScript script generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_javascript_test_case(self, test_case: Dict) -> str:
        """Generate JavaScript code for a test case"""
        case_type = test_case.get('type', 'generic')
        
        if case_type == 'file_validation':
            file_path = test_case.get('file_path', '/dev/null')
            return f'return fs.existsSync("{file_path}");'
        elif case_type == 'api_test':
            url = test_case.get('url', 'http://localhost:8080/test')
            return f'''
        const response = await fetch("{url}");
        return response.ok;
            '''.strip()
        else:
            return 'return true;'
    
    async def _validate_generated_script(self, script_content: str, language: str) -> Dict:
        """Validate generated script for safety and correctness"""
        validation_result = {
            'safe': True,
            'syntax_valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check for dangerous patterns
            for pattern in self.dangerous_patterns:
                if re.search(pattern, script_content, re.IGNORECASE):
                    validation_result['safe'] = False
                    validation_result['errors'].append(f'Dangerous pattern detected: {pattern}')
            
            # Language-specific validation
            if language == 'python':
                try:
                    ast.parse(script_content)
                except SyntaxError as e:
                    validation_result['syntax_valid'] = False
                    validation_result['errors'].append(f'Python syntax error: {e}')
            
            # Check script length
            if len(script_content) > self.max_script_length * 100:
                validation_result['warnings'].append('Script is very long')
            
            # Check for hardcoded sensitive data
            sensitive_patterns = [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']'
            ]
            
            for pattern in sensitive_patterns:
                if re.search(pattern, script_content, re.IGNORECASE):
                    validation_result['warnings'].append('Potential hardcoded sensitive data detected')
            
        except Exception as e:
            validation_result['errors'].append(f'Validation error: {e}')
        
        return validation_result
    
    async def analyze_code_quality(self, code_content: str, language: str) -> Dict:
        """Analyze code quality and provide recommendations"""
        try:
            logger.info(f"Analyzing {language} code quality")
            
            analysis_result = {
                'language': language,
                'lines_of_code': len(code_content.splitlines()),
                'complexity_score': 0,
                'quality_score': 0,
                'issues': [],
                'recommendations': []
            }
            
            # Basic metrics
            lines = code_content.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]
            comment_lines = [line for line in lines if line.strip().startswith('#')]
            
            analysis_result['non_empty_lines'] = len(non_empty_lines)
            analysis_result['comment_lines'] = len(comment_lines)
            analysis_result['comment_ratio'] = len(comment_lines) / len(non_empty_lines) if non_empty_lines else 0
            
            # Language-specific analysis
            if language == 'python':
                python_analysis = await self._analyze_python_code(code_content)
                analysis_result.update(python_analysis)
            
            # Calculate quality score
            quality_factors = []
            
            # Comment ratio factor
            if analysis_result['comment_ratio'] > 0.1:
                quality_factors.append(0.2)
            
            # Complexity factor
            if analysis_result['complexity_score'] < 10:
                quality_factors.append(0.3)
            
            # Issue factor
            if len(analysis_result['issues']) == 0:
                quality_factors.append(0.5)
            
            analysis_result['quality_score'] = sum(quality_factors)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_python_code(self, code_content: str) -> Dict:
        """Analyze Python-specific code quality"""
        try:
            tree = ast.parse(code_content)
            
            analysis = {
                'functions': 0,
                'classes': 0,
                'complexity_score': 0,
                'issues': [],
                'recommendations': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis['functions'] += 1
                elif isinstance(node, ast.ClassDef):
                    analysis['classes'] += 1
                elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                    analysis['complexity_score'] += 1
            
            # Check for common issues
            if analysis['functions'] == 0 and analysis['classes'] == 0:
                analysis['issues'].append('No functions or classes defined')
            
            if analysis['complexity_score'] > 20:
                analysis['issues'].append('High complexity score')
                analysis['recommendations'].append('Consider breaking down complex functions')
            
            return analysis
            
        except SyntaxError as e:
            return {
                'issues': [f'Syntax error: {e}'],
                'recommendations': ['Fix syntax errors before analysis']
            }
    
    async def get_generated_scripts(self) -> Dict:
        """Get all generated scripts"""
        return self.generated_scripts.copy()
    
    async def shutdown(self):
        """Shutdown the Coder agent"""
        logger.info("Shutting down Coder agent...")
        
        # Clear caches
        self.generated_scripts.clear()
        self.analysis_cache.clear()
        
        logger.info("Coder agent shutdown complete")
