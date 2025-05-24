"""
WebSurfer Agent
Specialized agent for web testing and webhook endpoint validation
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import aiohttp
import requests
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class WebSurferAgent:
    """
    WebSurfer agent responsible for testing web endpoints, webhook functionality,
    and web-based integrations for the QA system.
    """
    
    def __init__(self, config: Dict, client):
        self.config = config
        self.client = client
        self.restrictions = config.get('restrictions', {})
        self.capabilities = config.get('capabilities', [])
        
        # Network restrictions
        self.allowed_domains = set(self.restrictions.get('allowed_domains', []))
        self.allowed_ports = set(self.restrictions.get('allowed_ports', []))
        self.max_requests_per_minute = self.restrictions.get('max_requests_per_minute', 60)
        self.timeout = self.restrictions.get('timeout', 30)
        self.follow_redirects = self.restrictions.get('follow_redirects', False)
        self.verify_ssl = self.restrictions.get('verify_ssl', False)
        
        # Browser automation
        self.playwright = None
        self.browser = None
        
        # Request tracking
        self.request_history = []
        self.rate_limiter = {}
        
    async def initialize(self) -> bool:
        """Initialize the WebSurfer agent"""
        try:
            logger.info("Initializing WebSurfer agent...")
            
            # Validate configuration
            if not await self._validate_config():
                return False
            
            # Initialize browser automation
            if 'web_interface_testing' in self.capabilities:
                await self._initialize_browser()
            
            # Test network connectivity
            if not await self._test_network_access():
                return False
            
            logger.info("WebSurfer agent initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSurfer agent: {e}")
            return False
    
    async def _validate_config(self) -> bool:
        """Validate agent configuration"""
        required_capabilities = ['http_requests', 'webhook_testing']
        missing_capabilities = [cap for cap in required_capabilities if cap not in self.capabilities]
        
        if missing_capabilities:
            logger.error(f"Missing required capabilities: {missing_capabilities}")
            return False
        
        return True
    
    async def _initialize_browser(self):
        """Initialize Playwright browser for web interface testing"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            logger.info("Browser automation initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize browser automation: {e}")
    
    async def _test_network_access(self) -> bool:
        """Test basic network connectivity"""
        try:
            # Test connection to localhost
            test_url = "http://localhost:8080/health"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                try:
                    async with session.get(test_url) as response:
                        logger.info(f"Network test successful: {response.status}")
                except aiohttp.ClientError:
                    logger.info("Network test: localhost not responding (expected in some environments)")
            
            return True
            
        except Exception as e:
            logger.error(f"Network access test failed: {e}")
            return False
    
    def _check_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed based on restrictions"""
        try:
            parsed = urlparse(url)
            
            # Check domain restrictions
            if self.allowed_domains and parsed.hostname not in self.allowed_domains:
                logger.warning(f"Domain not allowed: {parsed.hostname}")
                return False
            
            # Check port restrictions
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            if self.allowed_ports and port not in self.allowed_ports:
                logger.warning(f"Port not allowed: {port}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return False
    
    def _check_rate_limit(self, domain: str) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()
        
        if domain not in self.rate_limiter:
            self.rate_limiter[domain] = []
        
        # Clean old requests (older than 1 minute)
        self.rate_limiter[domain] = [
            req_time for req_time in self.rate_limiter[domain]
            if current_time - req_time < 60
        ]
        
        # Check if under rate limit
        if len(self.rate_limiter[domain]) >= self.max_requests_per_minute:
            logger.warning(f"Rate limit exceeded for domain: {domain}")
            return False
        
        # Add current request
        self.rate_limiter[domain].append(current_time)
        return True
    
    async def test_webhook_endpoint(self, webhook_config: Dict) -> Dict:
        """Test a webhook endpoint configuration"""
        try:
            logger.info(f"Testing webhook endpoint: {webhook_config.get('url')}")
            
            url = webhook_config.get('url')
            method = webhook_config.get('method', 'POST').upper()
            headers = webhook_config.get('headers', {})
            payload = webhook_config.get('payload', {})
            
            # Validate URL
            if not self._check_url_allowed(url):
                return {'success': False, 'error': 'URL not allowed by security restrictions'}
            
            # Check rate limits
            parsed_url = urlparse(url)
            if not self._check_rate_limit(parsed_url.hostname):
                return {'success': False, 'error': 'Rate limit exceeded'}
            
            # Perform HTTP request
            result = await self._make_http_request(url, method, headers, payload)
            
            # Log request
            self.request_history.append({
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'method': method,
                'status_code': result.get('status_code'),
                'success': result.get('success', False)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Webhook endpoint test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _make_http_request(self, url: str, method: str, headers: Dict, payload: Any) -> Dict:
        """Make HTTP request with proper error handling"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(verify_ssl=self.verify_ssl)
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': 'Codex-QA-WebSurfer/1.0'}
            ) as session:
                
                # Prepare request parameters
                kwargs = {
                    'headers': headers,
                    'allow_redirects': self.follow_redirects
                }
                
                if method in ['POST', 'PUT', 'PATCH'] and payload:
                    if isinstance(payload, dict):
                        kwargs['json'] = payload
                    else:
                        kwargs['data'] = payload
                
                # Make request
                start_time = time.time()
                async with session.request(method, url, **kwargs) as response:
                    response_time = time.time() - start_time
                    
                    # Read response
                    try:
                        response_text = await response.text()
                        try:
                            response_json = json.loads(response_text)
                        except json.JSONDecodeError:
                            response_json = None
                    except Exception:
                        response_text = ""
                        response_json = None
                    
                    return {
                        'success': 200 <= response.status < 400,
                        'status_code': response.status,
                        'response_time': response_time,
                        'headers': dict(response.headers),
                        'text': response_text[:1000],  # Limit response text
                        'json': response_json,
                        'size': len(response_text)
                    }
                    
        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Request timeout'}
        except aiohttp.ClientError as e:
            return {'success': False, 'error': f'Client error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
    async def test_webhook_integration(self, hook_config: Dict, test_payload: Dict) -> Dict:
        """Test webhook integration with specific payload"""
        try:
            logger.info("Testing webhook integration with test payload")
            
            # Prepare webhook configuration
            webhook_config = {
                'url': hook_config.get('url'),
                'method': hook_config.get('method', 'POST'),
                'headers': hook_config.get('headers', {}),
                'payload': test_payload
            }
            
            # Add content-type header if not specified
            if 'Content-Type' not in webhook_config['headers']:
                webhook_config['headers']['Content-Type'] = 'application/json'
            
            # Test the webhook
            result = await self.test_webhook_endpoint(webhook_config)
            
            # Additional integration-specific validation
            if result.get('success'):
                result['integration_tests'] = await self._validate_webhook_response(
                    result, hook_config
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Webhook integration test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _validate_webhook_response(self, response_result: Dict, hook_config: Dict) -> Dict:
        """Validate webhook response for integration requirements"""
        validation_result = {
            'response_format_valid': True,
            'expected_fields_present': True,
            'response_time_acceptable': True,
            'errors': [],
            'warnings': []
        }
        
        # Check response time
        response_time = response_result.get('response_time', 0)
        max_response_time = hook_config.get('max_response_time', 5.0)
        if response_time > max_response_time:
            validation_result['response_time_acceptable'] = False
            validation_result['warnings'].append(f"Response time {response_time:.2f}s exceeds maximum {max_response_time}s")
        
        # Check expected response format
        expected_format = hook_config.get('expected_response_format')
        if expected_format == 'json':
            if not response_result.get('json'):
                validation_result['response_format_valid'] = False
                validation_result['errors'].append("Expected JSON response but received non-JSON")
        
        # Check for expected fields in response
        expected_fields = hook_config.get('expected_response_fields', [])
        response_json = response_result.get('json', {})
        if expected_fields and isinstance(response_json, dict):
            missing_fields = [field for field in expected_fields if field not in response_json]
            if missing_fields:
                validation_result['expected_fields_present'] = False
                validation_result['errors'].append(f"Missing expected fields: {missing_fields}")
        
        return validation_result
    
    async def test_web_interface(self, url: str, test_scenarios: List[Dict]) -> Dict:
        """Test web interface using browser automation"""
        if not self.browser:
            return {'success': False, 'error': 'Browser automation not available'}
        
        try:
            logger.info(f"Testing web interface: {url}")
            
            # Validate URL
            if not self._check_url_allowed(url):
                return {'success': False, 'error': 'URL not allowed by security restrictions'}
            
            page = await self.browser.new_page()
            
            try:
                # Navigate to page
                await page.goto(url, timeout=self.timeout * 1000)
                
                # Run test scenarios
                scenario_results = []
                for scenario in test_scenarios:
                    scenario_result = await self._run_web_scenario(page, scenario)
                    scenario_results.append(scenario_result)
                
                # Take screenshot for debugging
                screenshot = await page.screenshot()
                
                return {
                    'success': all(result.get('success', False) for result in scenario_results),
                    'scenario_results': scenario_results,
                    'screenshot_size': len(screenshot),
                    'page_title': await page.title(),
                    'page_url': page.url
                }
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Web interface test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_web_scenario(self, page: Page, scenario: Dict) -> Dict:
        """Run a single web test scenario"""
        try:
            scenario_name = scenario.get('name', 'unnamed_scenario')
            logger.info(f"Running web scenario: {scenario_name}")
            
            actions = scenario.get('actions', [])
            
            for action in actions:
                action_type = action.get('type')
                
                if action_type == 'click':
                    selector = action.get('selector')
                    await page.click(selector)
                elif action_type == 'fill':
                    selector = action.get('selector')
                    value = action.get('value')
                    await page.fill(selector, value)
                elif action_type == 'wait':
                    timeout = action.get('timeout', 1000)
                    await page.wait_for_timeout(timeout)
                elif action_type == 'wait_for_selector':
                    selector = action.get('selector')
                    await page.wait_for_selector(selector)
                elif action_type == 'assert_text':
                    selector = action.get('selector')
                    expected_text = action.get('text')
                    element = await page.query_selector(selector)
                    if element:
                        actual_text = await element.text_content()
                        if expected_text not in actual_text:
                            raise AssertionError(f"Expected text '{expected_text}' not found in '{actual_text}'")
                    else:
                        raise AssertionError(f"Element not found: {selector}")
            
            return {'success': True, 'scenario': scenario_name}
            
        except Exception as e:
            logger.error(f"Web scenario '{scenario_name}' failed: {e}")
            return {'success': False, 'scenario': scenario_name, 'error': str(e)}
    
    async def monitor_webhook_performance(self, webhook_configs: List[Dict], duration: int = 60) -> Dict:
        """Monitor webhook performance over time"""
        try:
            logger.info(f"Starting webhook performance monitoring for {duration} seconds")
            
            start_time = time.time()
            results = []
            
            while time.time() - start_time < duration:
                for config in webhook_configs:
                    result = await self.test_webhook_endpoint(config)
                    result['timestamp'] = time.time()
                    results.append(result)
                
                # Wait before next round
                await asyncio.sleep(5)
            
            # Analyze results
            analysis = self._analyze_performance_results(results)
            
            return {
                'success': True,
                'duration': duration,
                'total_requests': len(results),
                'results': results,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Webhook performance monitoring failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_performance_results(self, results: List[Dict]) -> Dict:
        """Analyze webhook performance results"""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.get('success')]
        response_times = [r.get('response_time', 0) for r in successful_results]
        
        analysis = {
            'total_requests': len(results),
            'successful_requests': len(successful_results),
            'failed_requests': len(results) - len(successful_results),
            'success_rate': len(successful_results) / len(results) if results else 0,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0
        }
        
        return analysis
    
    async def get_request_history(self) -> List[Dict]:
        """Get history of HTTP requests made by this agent"""
        return self.request_history.copy()
    
    async def shutdown(self):
        """Shutdown the WebSurfer agent"""
        logger.info("Shutting down WebSurfer agent...")
        
        # Close browser
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        # Clear state
        self.request_history.clear()
        self.rate_limiter.clear()
        
        logger.info("WebSurfer agent shutdown complete")
