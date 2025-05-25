#!/usr/bin/env python3
"""
Specialized FileSurfer Agent for Codex Hooks Configuration Validation

This module provides an enhanced FileSurfer agent specifically designed for
validating Codex lifecycle hooks configurations, analyzing code quality,
and performing comprehensive file-based testing.
"""

import asyncio
import logging
import json
import toml
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import re

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.agents.file_surfer import FileSurfer
    from autogen_agentchat.messages import TextMessage
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

logger = logging.getLogger(__name__)


class CodexHooksFileSurferAgent:
    """
    Specialized FileSurfer Agent for Codex Hooks Configuration Validation.
    
    This agent provides enhanced file analysis capabilities specifically designed
    for validating Codex hooks configurations, analyzing implementation code,
    and performing comprehensive file-based quality assurance.
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient, name: str = "HooksFileSurfer"):
        self.model_client = model_client
        self.name = name
        self.validation_results = []
        self.analysis_cache = {}
        
        # Create the underlying FileSurfer agent with specialized system message
        self.agent = FileSurfer(
            name=self.name,
            model_client=self.model_client,
            # Note: FileSurfer may not support custom system messages directly
            # We'll handle specialization through our wrapper methods
        )
        
    async def validate_hooks_configuration(self, config_path: str) -> Dict[str, Any]:
        """
        Comprehensive validation of hooks configuration files.
        
        Args:
            config_path: Path to the hooks configuration file
            
        Returns:
            Detailed validation report
        """
        logger.info(f"Validating hooks configuration: {config_path}")
        
        validation_prompt = f"""
Perform comprehensive validation of the Codex lifecycle hooks configuration file: {config_path}

Please analyze the following aspects:

1. **Syntax Validation**:
   - TOML syntax correctness
   - Proper structure and formatting
   - Valid data types and values

2. **Semantic Validation**:
   - Required sections and fields
   - Valid hook types (script, webhook, mcp_tool)
   - Proper event type definitions
   - Correct parameter formats

3. **Security Analysis**:
   - No dangerous commands in script hooks
   - Secure webhook URLs (HTTPS preferred)
   - Proper file path restrictions
   - Environment variable handling

4. **Performance Considerations**:
   - Reasonable timeout values
   - Appropriate priority settings
   - Resource usage implications
   - Execution mode optimization

5. **Best Practices**:
   - Clear descriptions and documentation
   - Logical hook organization
   - Proper error handling configuration
   - Maintainability considerations

6. **Compatibility Check**:
   - Version compatibility
   - Platform-specific considerations
   - Dependency requirements

Please provide a detailed validation report with:
- Overall validation status (PASS/FAIL/WARNING)
- Specific issues found with line numbers
- Severity ratings (CRITICAL/HIGH/MEDIUM/LOW)
- Recommended fixes for each issue
- Best practice suggestions
"""

        try:
            # First, perform basic file analysis
            file_analysis = await self._analyze_file_structure(config_path)
            
            # Then use the FileSurfer agent for detailed analysis
            response = await self.agent.on_messages(
                [TextMessage(content=validation_prompt, source="user")],
                cancellation_token=None
            )
            
            # Combine results
            validation_result = {
                "validation_id": f"config-validation-{int(datetime.now().timestamp())}",
                "file_path": config_path,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "file_analysis": file_analysis,
                "detailed_validation": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Store result
            self.validation_results.append(validation_result)
            
            logger.info(f"Completed configuration validation: {validation_result['validation_id']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            error_result = {
                "validation_id": f"config-validation-error-{int(datetime.now().timestamp())}",
                "file_path": config_path,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            self.validation_results.append(error_result)
            return error_result
            
    async def analyze_hooks_implementation(self, code_paths: List[str]) -> Dict[str, Any]:
        """
        Analyze hooks implementation code for quality and correctness.
        
        Args:
            code_paths: List of paths to analyze (Rust and TypeScript files)
            
        Returns:
            Code analysis report
        """
        logger.info(f"Analyzing hooks implementation code: {len(code_paths)} files")
        
        analysis_prompt = f"""
Perform comprehensive code analysis of the Codex lifecycle hooks implementation.

Files to analyze: {code_paths}

Please analyze the following aspects:

1. **Code Quality**:
   - Code structure and organization
   - Naming conventions and clarity
   - Documentation and comments
   - Error handling patterns

2. **Security Analysis**:
   - Input validation and sanitization
   - Privilege escalation prevention
   - Resource access controls
   - Injection attack prevention

3. **Performance Analysis**:
   - Execution efficiency
   - Memory usage patterns
   - Async/await usage
   - Resource cleanup

4. **Correctness Analysis**:
   - Logic correctness
   - Edge case handling
   - Error propagation
   - State management

5. **Maintainability**:
   - Code modularity
   - Testability
   - Extensibility
   - Technical debt

6. **Best Practices**:
   - Language-specific best practices
   - Design patterns usage
   - Code reusability
   - Configuration management

For each file, provide:
- Overall quality score (1-10)
- Specific issues with line numbers
- Security vulnerabilities
- Performance bottlenecks
- Recommended improvements
"""

        try:
            # Analyze each file
            file_analyses = []
            for code_path in code_paths:
                file_analysis = await self._analyze_code_file(code_path)
                file_analyses.append(file_analysis)
            
            # Use FileSurfer for detailed analysis
            response = await self.agent.on_messages(
                [TextMessage(content=analysis_prompt, source="user")],
                cancellation_token=None
            )
            
            analysis_result = {
                "analysis_id": f"code-analysis-{int(datetime.now().timestamp())}",
                "code_paths": code_paths,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "file_analyses": file_analyses,
                "detailed_analysis": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            logger.info(f"Completed code analysis: {analysis_result['analysis_id']}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {
                "analysis_id": f"code-analysis-error-{int(datetime.now().timestamp())}",
                "code_paths": code_paths,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def validate_example_configurations(self, examples_dir: str) -> Dict[str, Any]:
        """
        Validate all example hook configurations.
        
        Args:
            examples_dir: Directory containing example configurations
            
        Returns:
            Validation report for all examples
        """
        logger.info(f"Validating example configurations in: {examples_dir}")
        
        try:
            examples_path = Path(examples_dir)
            if not examples_path.exists():
                raise FileNotFoundError(f"Examples directory not found: {examples_dir}")
            
            # Find all configuration files
            config_files = []
            for pattern in ["*.toml", "*.yaml", "*.yml", "*.json"]:
                config_files.extend(examples_path.rglob(pattern))
            
            validation_results = []
            for config_file in config_files:
                try:
                    result = await self.validate_hooks_configuration(str(config_file))
                    validation_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to validate {config_file}: {e}")
                    validation_results.append({
                        "file_path": str(config_file),
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Generate summary report
            summary_prompt = f"""
Generate a summary report for the validation of {len(config_files)} example configurations.

Validation Results: {json.dumps(validation_results, indent=2)}

Please provide:
1. Overall validation summary
2. Common issues across examples
3. Best practices demonstrated
4. Recommendations for improvements
5. Quality assessment of examples
"""

            response = await self.agent.on_messages(
                [TextMessage(content=summary_prompt, source="user")],
                cancellation_token=None
            )
            
            summary_result = {
                "summary_id": f"examples-validation-{int(datetime.now().timestamp())}",
                "examples_dir": examples_dir,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "files_validated": len(config_files),
                "individual_results": validation_results,
                "summary_report": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            logger.info(f"Completed examples validation: {summary_result['summary_id']}")
            return summary_result
            
        except Exception as e:
            logger.error(f"Examples validation failed: {e}")
            return {
                "summary_id": f"examples-validation-error-{int(datetime.now().timestamp())}",
                "examples_dir": examples_dir,
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def _analyze_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze basic file structure and syntax."""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}
            
            # Get file info
            stat = path.stat()
            file_info = {
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": path.suffix.lower()
            }
            
            # Read and analyze content
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_info.update({
                "line_count": len(content.splitlines()),
                "char_count": len(content),
                "encoding": "utf-8"
            })
            
            # Parse based on file type
            if path.suffix.lower() == '.toml':
                try:
                    parsed = toml.loads(content)
                    file_info["syntax_valid"] = True
                    file_info["parsed_structure"] = self._summarize_toml_structure(parsed)
                except Exception as e:
                    file_info["syntax_valid"] = False
                    file_info["syntax_error"] = str(e)
            elif path.suffix.lower() in ['.yaml', '.yml']:
                try:
                    parsed = yaml.safe_load(content)
                    file_info["syntax_valid"] = True
                    file_info["parsed_structure"] = self._summarize_yaml_structure(parsed)
                except Exception as e:
                    file_info["syntax_valid"] = False
                    file_info["syntax_error"] = str(e)
            elif path.suffix.lower() == '.json':
                try:
                    parsed = json.loads(content)
                    file_info["syntax_valid"] = True
                    file_info["parsed_structure"] = self._summarize_json_structure(parsed)
                except Exception as e:
                    file_info["syntax_valid"] = False
                    file_info["syntax_error"] = str(e)
            
            return file_info
            
        except Exception as e:
            return {"error": f"Failed to analyze file structure: {e}"}
            
    async def _analyze_code_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze code file for basic metrics."""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            
            # Basic metrics
            metrics = {
                "file_path": str(path),
                "extension": path.suffix.lower(),
                "total_lines": len(lines),
                "non_empty_lines": len([line for line in lines if line.strip()]),
                "comment_lines": 0,
                "function_count": 0,
                "class_count": 0
            }
            
            # Language-specific analysis
            if path.suffix.lower() in ['.rs']:
                metrics.update(self._analyze_rust_code(content))
            elif path.suffix.lower() in ['.ts', '.js']:
                metrics.update(self._analyze_typescript_code(content))
            elif path.suffix.lower() in ['.py']:
                metrics.update(self._analyze_python_code(content))
            
            return metrics
            
        except Exception as e:
            return {"error": f"Failed to analyze code file: {e}"}
            
    def _summarize_toml_structure(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize TOML structure."""
        return {
            "top_level_keys": list(parsed.keys()),
            "section_count": len([k for k, v in parsed.items() if isinstance(v, dict)]),
            "array_count": len([k for k, v in parsed.items() if isinstance(v, list)])
        }
        
    def _summarize_yaml_structure(self, parsed: Any) -> Dict[str, Any]:
        """Summarize YAML structure."""
        if isinstance(parsed, dict):
            return {
                "type": "object",
                "keys": list(parsed.keys()),
                "key_count": len(parsed)
            }
        elif isinstance(parsed, list):
            return {
                "type": "array",
                "length": len(parsed)
            }
        else:
            return {
                "type": type(parsed).__name__,
                "value": str(parsed)[:100]
            }
            
    def _summarize_json_structure(self, parsed: Any) -> Dict[str, Any]:
        """Summarize JSON structure."""
        return self._summarize_yaml_structure(parsed)  # Same logic
        
    def _analyze_rust_code(self, content: str) -> Dict[str, Any]:
        """Analyze Rust code for basic metrics."""
        metrics = {}
        
        # Count functions
        fn_pattern = r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+\w+'
        metrics["function_count"] = len(re.findall(fn_pattern, content, re.MULTILINE))
        
        # Count structs
        struct_pattern = r'^\s*(?:pub\s+)?struct\s+\w+'
        metrics["struct_count"] = len(re.findall(struct_pattern, content, re.MULTILINE))
        
        # Count impl blocks
        impl_pattern = r'^\s*impl\s+'
        metrics["impl_count"] = len(re.findall(impl_pattern, content, re.MULTILINE))
        
        # Count comments
        comment_pattern = r'^\s*//'
        metrics["comment_lines"] = len(re.findall(comment_pattern, content, re.MULTILINE))
        
        return metrics
        
    def _analyze_typescript_code(self, content: str) -> Dict[str, Any]:
        """Analyze TypeScript/JavaScript code for basic metrics."""
        metrics = {}
        
        # Count functions
        fn_pattern = r'(?:function\s+\w+|(?:async\s+)?(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\(|(?:async\s+)?\w+\s*\()'
        metrics["function_count"] = len(re.findall(fn_pattern, content))
        
        # Count classes
        class_pattern = r'^\s*(?:export\s+)?class\s+\w+'
        metrics["class_count"] = len(re.findall(class_pattern, content, re.MULTILINE))
        
        # Count interfaces
        interface_pattern = r'^\s*(?:export\s+)?interface\s+\w+'
        metrics["interface_count"] = len(re.findall(interface_pattern, content, re.MULTILINE))
        
        # Count comments
        comment_pattern = r'^\s*//'
        metrics["comment_lines"] = len(re.findall(comment_pattern, content, re.MULTILINE))
        
        return metrics
        
    def _analyze_python_code(self, content: str) -> Dict[str, Any]:
        """Analyze Python code for basic metrics."""
        metrics = {}
        
        # Count functions
        fn_pattern = r'^\s*(?:async\s+)?def\s+\w+'
        metrics["function_count"] = len(re.findall(fn_pattern, content, re.MULTILINE))
        
        # Count classes
        class_pattern = r'^\s*class\s+\w+'
        metrics["class_count"] = len(re.findall(class_pattern, content, re.MULTILINE))
        
        # Count comments
        comment_pattern = r'^\s*#'
        metrics["comment_lines"] = len(re.findall(comment_pattern, content, re.MULTILINE))
        
        return metrics
        
    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Get validation history."""
        return self.validation_results.copy()
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("FileSurfer agent cleanup completed")


# Example usage and testing
async def test_file_surfer_agent():
    """Test the FileSurfer agent."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create FileSurfer agent
        file_surfer = CodexHooksFileSurferAgent(client)
        
        # Test configuration validation
        config_result = await file_surfer.validate_hooks_configuration("examples/hooks.toml")
        print(f"Configuration validation: {config_result['validation_id']}")
        
        # Test examples validation
        examples_result = await file_surfer.validate_example_configurations("examples/hooks")
        print(f"Examples validation: {examples_result['summary_id']}")
        
        # Test code analysis
        code_paths = [
            "codex-rs/core/src/hooks/mod.rs",
            "codex-cli/src/utils/hooks/events.ts"
        ]
        code_result = await file_surfer.analyze_hooks_implementation(code_paths)
        print(f"Code analysis: {code_result['analysis_id']}")
        
        # Cleanup
        await file_surfer.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_file_surfer_agent())
