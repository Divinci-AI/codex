"""
FileSurfer Agent
Specialized agent for file operations and configuration validation
"""

import asyncio
import json
import logging
import os
import stat
import toml
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


class FileSurferAgent:
    """
    FileSurfer agent responsible for file operations, configuration validation,
    and file system analysis for the QA system.
    """
    
    def __init__(self, config: Dict, client):
        self.config = config
        self.client = client
        self.restrictions = config.get('restrictions', {})
        self.capabilities = config.get('capabilities', [])
        
        # File operation limits
        self.max_file_size = self._parse_size(self.restrictions.get('max_file_size', '10MB'))
        self.allowed_extensions = set(self.restrictions.get('allowed_extensions', []))
        self.forbidden_paths = set(self.restrictions.get('forbidden_paths', []))
        self.read_only_mode = self.restrictions.get('read_only_mode', True)
        
        # Validation state
        self.validation_cache = {}
        self.file_access_log = []
        
    async def initialize(self) -> bool:
        """Initialize the FileSurfer agent"""
        try:
            logger.info("Initializing FileSurfer agent...")
            
            # Validate configuration
            if not await self._validate_config():
                return False
            
            # Test file system access
            if not await self._test_file_access():
                return False
            
            logger.info("FileSurfer agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize FileSurfer agent: {e}")
            return False
    
    async def _validate_config(self) -> bool:
        """Validate agent configuration"""
        required_capabilities = ['file_reading', 'configuration_validation']
        missing_capabilities = [cap for cap in required_capabilities if cap not in self.capabilities]
        
        if missing_capabilities:
            logger.error(f"Missing required capabilities: {missing_capabilities}")
            return False
        
        return True
    
    async def _test_file_access(self) -> bool:
        """Test basic file system access"""
        try:
            # Test read access to workspace
            workspace_path = Path("/workspace")
            if not workspace_path.exists():
                logger.error("Workspace directory not accessible")
                return False
            
            # Test write access to temp directory (if not read-only)
            if not self.read_only_mode:
                temp_path = Path("/workspace/qa/tmp")
                temp_path.mkdir(parents=True, exist_ok=True)
                test_file = temp_path / "file_surfer_test.txt"
                test_file.write_text("test")
                test_file.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"File access test failed: {e}")
            return False
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '10MB') to bytes"""
        if isinstance(size_str, int):
            return size_str
        
        size_str = size_str.upper()
        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                return int(size_str[:-len(suffix)]) * multiplier
        
        return int(size_str)  # Assume bytes if no suffix
    
    async def validate_hooks_config(self, config_path: str) -> Dict:
        """Validate a hooks configuration file"""
        try:
            logger.info(f"Validating hooks configuration: {config_path}")
            
            # Security checks
            if not await self._check_file_access(config_path):
                return {'valid': False, 'error': 'File access denied'}
            
            # Read and parse configuration
            config_data = await self._read_config_file(config_path)
            if config_data is None:
                return {'valid': False, 'error': 'Failed to read configuration file'}
            
            # Validate configuration structure
            validation_result = await self._validate_config_structure(config_data)
            
            # Validate hook definitions
            hooks_validation = await self._validate_hooks(config_data.get('hooks', {}))
            validation_result['hooks_validation'] = hooks_validation
            
            # Validate file references
            file_validation = await self._validate_file_references(config_data)
            validation_result['file_validation'] = file_validation
            
            # Overall validation status
            validation_result['valid'] = (
                validation_result.get('structure_valid', False) and
                hooks_validation.get('valid', False) and
                file_validation.get('valid', False)
            )
            
            # Cache result
            self.validation_cache[config_path] = validation_result
            
            logger.info(f"Configuration validation completed: {validation_result['valid']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {'valid': False, 'error': str(e)}
    
    async def _check_file_access(self, file_path: str) -> bool:
        """Check if file access is allowed"""
        path = Path(file_path).resolve()
        
        # Check forbidden paths
        for forbidden in self.forbidden_paths:
            if str(path).startswith(forbidden):
                logger.warning(f"Access denied to forbidden path: {path}")
                return False
        
        # Check file existence and readability
        if not path.exists():
            logger.warning(f"File does not exist: {path}")
            return False
        
        if not path.is_file():
            logger.warning(f"Path is not a file: {path}")
            return False
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            logger.warning(f"File too large: {file_size} > {self.max_file_size}")
            return False
        
        # Check file extension
        if self.allowed_extensions and path.suffix not in self.allowed_extensions:
            logger.warning(f"File extension not allowed: {path.suffix}")
            return False
        
        # Log access
        self.file_access_log.append({
            'path': str(path),
            'timestamp': asyncio.get_event_loop().time(),
            'operation': 'read'
        })
        
        return True
    
    async def _read_config_file(self, config_path: str) -> Optional[Dict]:
        """Read and parse configuration file"""
        try:
            path = Path(config_path)
            content = path.read_text(encoding='utf-8')
            
            # Parse based on file extension
            if path.suffix.lower() == '.toml':
                return toml.loads(content)
            elif path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            elif path.suffix.lower() == '.json':
                return json.loads(content)
            else:
                logger.error(f"Unsupported configuration format: {path.suffix}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read configuration file {config_path}: {e}")
            return None
    
    async def _validate_config_structure(self, config_data: Dict) -> Dict:
        """Validate the basic structure of configuration"""
        validation_result = {
            'structure_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required top-level sections
        required_sections = ['hooks']
        for section in required_sections:
            if section not in config_data:
                validation_result['errors'].append(f"Missing required section: {section}")
                validation_result['structure_valid'] = False
        
        # Validate hooks section structure
        if 'hooks' in config_data:
            hooks = config_data['hooks']
            if not isinstance(hooks, dict):
                validation_result['errors'].append("'hooks' section must be a dictionary")
                validation_result['structure_valid'] = False
            elif not hooks:
                validation_result['warnings'].append("'hooks' section is empty")
        
        return validation_result
    
    async def _validate_hooks(self, hooks_config: Dict) -> Dict:
        """Validate individual hook configurations"""
        validation_result = {
            'valid': True,
            'hook_results': {},
            'errors': [],
            'warnings': []
        }
        
        for hook_name, hook_config in hooks_config.items():
            hook_validation = await self._validate_single_hook(hook_name, hook_config)
            validation_result['hook_results'][hook_name] = hook_validation
            
            if not hook_validation.get('valid', False):
                validation_result['valid'] = False
                validation_result['errors'].extend(hook_validation.get('errors', []))
            
            validation_result['warnings'].extend(hook_validation.get('warnings', []))
        
        return validation_result
    
    async def _validate_single_hook(self, hook_name: str, hook_config: Dict) -> Dict:
        """Validate a single hook configuration"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['type']
        for field in required_fields:
            if field not in hook_config:
                validation_result['errors'].append(f"Hook '{hook_name}': Missing required field '{field}'")
                validation_result['valid'] = False
        
        # Validate hook type
        hook_type = hook_config.get('type')
        valid_types = ['script', 'webhook', 'mcp_tool', 'executable']
        if hook_type not in valid_types:
            validation_result['errors'].append(f"Hook '{hook_name}': Invalid type '{hook_type}'. Must be one of: {valid_types}")
            validation_result['valid'] = False
        
        # Type-specific validation
        if hook_type == 'script':
            await self._validate_script_hook(hook_name, hook_config, validation_result)
        elif hook_type == 'webhook':
            await self._validate_webhook_hook(hook_name, hook_config, validation_result)
        elif hook_type == 'mcp_tool':
            await self._validate_mcp_tool_hook(hook_name, hook_config, validation_result)
        elif hook_type == 'executable':
            await self._validate_executable_hook(hook_name, hook_config, validation_result)
        
        # Validate conditions
        if 'conditions' in hook_config:
            await self._validate_conditions(hook_name, hook_config['conditions'], validation_result)
        
        return validation_result
    
    async def _validate_script_hook(self, hook_name: str, hook_config: Dict, validation_result: Dict):
        """Validate script hook configuration"""
        script_path = hook_config.get('script')
        if not script_path:
            validation_result['errors'].append(f"Hook '{hook_name}': Script hooks must specify 'script' path")
            validation_result['valid'] = False
            return
        
        # Check if script file exists and is executable
        try:
            path = Path(script_path)
            if not path.exists():
                validation_result['errors'].append(f"Hook '{hook_name}': Script file not found: {script_path}")
                validation_result['valid'] = False
            elif not path.is_file():
                validation_result['errors'].append(f"Hook '{hook_name}': Script path is not a file: {script_path}")
                validation_result['valid'] = False
            else:
                # Check permissions
                file_stat = path.stat()
                if not (file_stat.st_mode & stat.S_IEXEC):
                    validation_result['warnings'].append(f"Hook '{hook_name}': Script file is not executable: {script_path}")
        
        except Exception as e:
            validation_result['errors'].append(f"Hook '{hook_name}': Error checking script file: {e}")
            validation_result['valid'] = False
    
    async def _validate_webhook_hook(self, hook_name: str, hook_config: Dict, validation_result: Dict):
        """Validate webhook hook configuration"""
        url = hook_config.get('url')
        if not url:
            validation_result['errors'].append(f"Hook '{hook_name}': Webhook hooks must specify 'url'")
            validation_result['valid'] = False
            return
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            validation_result['errors'].append(f"Hook '{hook_name}': Invalid webhook URL format: {url}")
            validation_result['valid'] = False
        
        # Validate HTTP method
        method = hook_config.get('method', 'POST').upper()
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        if method not in valid_methods:
            validation_result['errors'].append(f"Hook '{hook_name}': Invalid HTTP method '{method}'. Must be one of: {valid_methods}")
            validation_result['valid'] = False
    
    async def _validate_mcp_tool_hook(self, hook_name: str, hook_config: Dict, validation_result: Dict):
        """Validate MCP tool hook configuration"""
        tool_name = hook_config.get('tool')
        if not tool_name:
            validation_result['errors'].append(f"Hook '{hook_name}': MCP tool hooks must specify 'tool' name")
            validation_result['valid'] = False
    
    async def _validate_executable_hook(self, hook_name: str, hook_config: Dict, validation_result: Dict):
        """Validate executable hook configuration"""
        command = hook_config.get('command')
        if not command:
            validation_result['errors'].append(f"Hook '{hook_name}': Executable hooks must specify 'command'")
            validation_result['valid'] = False
    
    async def _validate_conditions(self, hook_name: str, conditions: Union[str, List[str]], validation_result: Dict):
        """Validate hook condition expressions"""
        if isinstance(conditions, str):
            conditions = [conditions]
        
        for condition in conditions:
            # Basic syntax validation for condition expressions
            # This is a simplified validation - in practice, you'd want more sophisticated parsing
            if not condition.strip():
                validation_result['warnings'].append(f"Hook '{hook_name}': Empty condition expression")
                continue
            
            # Check for potentially dangerous expressions
            dangerous_patterns = ['exec(', 'eval(', '__import__', 'open(', 'file(']
            for pattern in dangerous_patterns:
                if pattern in condition:
                    validation_result['errors'].append(f"Hook '{hook_name}': Potentially dangerous condition expression: {condition}")
                    validation_result['valid'] = False
    
    async def _validate_file_references(self, config_data: Dict) -> Dict:
        """Validate all file references in configuration"""
        validation_result = {
            'valid': True,
            'file_checks': {},
            'errors': [],
            'warnings': []
        }
        
        # Extract file references from hooks
        hooks = config_data.get('hooks', {})
        for hook_name, hook_config in hooks.items():
            if hook_config.get('type') == 'script':
                script_path = hook_config.get('script')
                if script_path:
                    file_check = await self._check_file_reference(script_path)
                    validation_result['file_checks'][script_path] = file_check
                    if not file_check['accessible']:
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Script file not accessible: {script_path}")
        
        return validation_result
    
    async def _check_file_reference(self, file_path: str) -> Dict:
        """Check if a file reference is valid and accessible"""
        try:
            path = Path(file_path)
            return {
                'accessible': await self._check_file_access(file_path),
                'exists': path.exists(),
                'is_file': path.is_file() if path.exists() else False,
                'readable': os.access(path, os.R_OK) if path.exists() else False,
                'executable': os.access(path, os.X_OK) if path.exists() else False,
                'size': path.stat().st_size if path.exists() else 0
            }
        except Exception as e:
            return {
                'accessible': False,
                'error': str(e)
            }
    
    async def get_file_info(self, file_path: str) -> Dict:
        """Get detailed information about a file"""
        if not await self._check_file_access(file_path):
            return {'error': 'File access denied'}
        
        try:
            path = Path(file_path)
            stat_info = path.stat()
            
            return {
                'path': str(path.resolve()),
                'size': stat_info.st_size,
                'modified': stat_info.st_mtime,
                'permissions': oct(stat_info.st_mode)[-3:],
                'is_executable': bool(stat_info.st_mode & stat.S_IEXEC),
                'extension': path.suffix,
                'mime_type': self._guess_mime_type(path)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _guess_mime_type(self, path: Path) -> str:
        """Guess MIME type based on file extension"""
        mime_types = {
            '.toml': 'application/toml',
            '.json': 'application/json',
            '.yaml': 'application/yaml',
            '.yml': 'application/yaml',
            '.py': 'text/x-python',
            '.sh': 'application/x-sh',
            '.js': 'application/javascript',
            '.ts': 'application/typescript',
            '.md': 'text/markdown',
            '.txt': 'text/plain'
        }
        return mime_types.get(path.suffix.lower(), 'application/octet-stream')
    
    async def shutdown(self):
        """Shutdown the FileSurfer agent"""
        logger.info("Shutting down FileSurfer agent...")
        
        # Clear caches
        self.validation_cache.clear()
        self.file_access_log.clear()
        
        logger.info("FileSurfer agent shutdown complete")
