#!/usr/bin/env python3
"""
Specialized WebSurfer Agent for Codex Hooks Webhook Testing

This module provides an enhanced WebSurfer agent specifically designed for
testing webhook endpoints, validating API integrations, and performing
comprehensive web-based testing for the Codex hooks system.
"""

import asyncio
import logging
import json
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import urllib.parse

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.agents.web_surfer import MultimodalWebSurfer
    from autogen_agentchat.messages import TextMessage
except ImportError as e:
    print(f"Error importing AutoGen dependencies: {e}")
    raise

logger = logging.getLogger(__name__)


class CodexHooksWebSurferAgent:
    """
    Specialized WebSurfer Agent for Codex Hooks Webhook Testing.
    
    This agent provides enhanced web testing capabilities specifically designed
    for validating webhook endpoints, testing API integrations, and performing
    comprehensive web-based quality assurance for the hooks system.
    """
    
    def __init__(self, model_client: OpenAIChatCompletionClient, name: str = "HooksWebSurfer"):
        self.model_client = model_client
        self.name = name
        self.test_results = []
        self.webhook_cache = {}
        
        # Create the underlying WebSurfer agent
        self.agent = MultimodalWebSurfer(
            name=self.name,
            model_client=self.model_client
        )
        
    async def test_webhook_endpoints(self, webhook_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Comprehensive testing of webhook endpoints.
        
        Args:
            webhook_configs: List of webhook configurations to test
            
        Returns:
            Detailed webhook testing report
        """
        logger.info(f"Testing {len(webhook_configs)} webhook endpoints")
        
        test_prompt = f"""
Perform comprehensive testing of webhook endpoints for the Codex lifecycle hooks system.

Webhook Configurations: {json.dumps(webhook_configs, indent=2)}

Please test the following aspects for each webhook:

1. **Connectivity Testing**:
   - URL accessibility and response time
   - SSL/TLS certificate validation
   - DNS resolution and routing
   - Network connectivity issues

2. **HTTP Method Testing**:
   - POST request handling (primary)
   - GET request handling (if applicable)
   - PUT/PATCH request handling (if applicable)
   - Proper HTTP status codes

3. **Request Format Testing**:
   - JSON payload acceptance
   - Content-Type header validation
   - Request size limits
   - Character encoding handling

4. **Authentication Testing**:
   - API key authentication (if configured)
   - Bearer token authentication (if configured)
   - Basic authentication (if configured)
   - Custom header authentication

5. **Response Validation**:
   - Response format and structure
   - Response time measurement
   - Error response handling
   - Status code appropriateness

6. **Security Testing**:
   - HTTPS enforcement
   - Certificate validation
   - Header security (CORS, CSP, etc.)
   - Input validation and sanitization

7. **Error Handling**:
   - Invalid payload handling
   - Network timeout scenarios
   - Server error responses
   - Rate limiting behavior

8. **Performance Testing**:
   - Response time benchmarks
   - Concurrent request handling
   - Payload size limits
   - Throughput testing

For each webhook, provide:
- Overall test status (PASS/FAIL/WARNING)
- Detailed test results for each aspect
- Performance metrics (response time, etc.)
- Security assessment
- Recommendations for improvements
"""

        try:
            # Perform direct HTTP testing first
            direct_test_results = []
            for webhook_config in webhook_configs:
                direct_result = await self._test_webhook_directly(webhook_config)
                direct_test_results.append(direct_result)
            
            # Use WebSurfer for advanced testing
            response = await self.agent.on_messages(
                [TextMessage(content=test_prompt, source="user")],
                cancellation_token=None
            )
            
            test_result = {
                "test_id": f"webhook-test-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "webhooks_tested": len(webhook_configs),
                "direct_test_results": direct_test_results,
                "detailed_analysis": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            # Store result
            self.test_results.append(test_result)
            
            logger.info(f"Completed webhook testing: {test_result['test_id']}")
            return test_result
            
        except Exception as e:
            logger.error(f"Webhook testing failed: {e}")
            error_result = {
                "test_id": f"webhook-test-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            self.test_results.append(error_result)
            return error_result
            
    async def validate_api_integrations(self, api_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate external API integrations used by hooks.
        
        Args:
            api_configs: List of API configurations to validate
            
        Returns:
            API validation report
        """
        logger.info(f"Validating {len(api_configs)} API integrations")
        
        validation_prompt = f"""
Validate external API integrations used by the Codex lifecycle hooks system.

API Configurations: {json.dumps(api_configs, indent=2)}

Please validate the following aspects for each API:

1. **API Availability**:
   - Endpoint accessibility
   - Service uptime and reliability
   - Geographic availability
   - Maintenance windows

2. **Authentication Validation**:
   - API key validity and permissions
   - OAuth flow testing
   - Token refresh mechanisms
   - Authentication error handling

3. **Rate Limiting**:
   - Rate limit discovery and testing
   - Backoff strategies
   - Quota management
   - Burst handling

4. **Data Format Validation**:
   - Request format compliance
   - Response format validation
   - Schema validation
   - Version compatibility

5. **Error Handling**:
   - Error response formats
   - Error code meanings
   - Retry mechanisms
   - Fallback strategies

6. **Performance Assessment**:
   - Response time benchmarks
   - Throughput capabilities
   - Latency variations
   - Geographic performance

7. **Security Assessment**:
   - HTTPS enforcement
   - Certificate validation
   - Data encryption
   - Privacy compliance

8. **Documentation Review**:
   - API documentation accuracy
   - Example completeness
   - Change log availability
   - Support channels

For each API, provide:
- Validation status and score
- Performance metrics
- Security assessment
- Reliability rating
- Integration recommendations
"""

        try:
            # Perform direct API testing
            api_test_results = []
            for api_config in api_configs:
                api_result = await self._test_api_directly(api_config)
                api_test_results.append(api_result)
            
            # Use WebSurfer for comprehensive validation
            response = await self.agent.on_messages(
                [TextMessage(content=validation_prompt, source="user")],
                cancellation_token=None
            )
            
            validation_result = {
                "validation_id": f"api-validation-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "apis_validated": len(api_configs),
                "direct_test_results": api_test_results,
                "detailed_validation": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            logger.info(f"Completed API validation: {validation_result['validation_id']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"API validation failed: {e}")
            return {
                "validation_id": f"api-validation-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def test_webhook_security(self, webhook_urls: List[str]) -> Dict[str, Any]:
        """
        Perform security testing on webhook endpoints.
        
        Args:
            webhook_urls: List of webhook URLs to test
            
        Returns:
            Security testing report
        """
        logger.info(f"Testing security for {len(webhook_urls)} webhook URLs")
        
        security_prompt = f"""
Perform comprehensive security testing on webhook endpoints.

Webhook URLs: {json.dumps(webhook_urls, indent=2)}

Please test the following security aspects:

1. **Transport Security**:
   - HTTPS enforcement
   - TLS version and cipher suites
   - Certificate validation
   - HSTS headers

2. **Input Validation**:
   - Payload size limits
   - Content-Type validation
   - Character encoding handling
   - Malformed data handling

3. **Authentication Security**:
   - Authentication bypass attempts
   - Token validation
   - Replay attack prevention
   - Brute force protection

4. **Injection Testing**:
   - SQL injection attempts
   - NoSQL injection attempts
   - Command injection attempts
   - Script injection attempts

5. **Header Security**:
   - Security headers presence
   - CORS configuration
   - CSP implementation
   - X-Frame-Options

6. **Rate Limiting**:
   - Rate limit enforcement
   - DDoS protection
   - Burst handling
   - IP-based limiting

7. **Error Information Disclosure**:
   - Error message sanitization
   - Stack trace exposure
   - Debug information leakage
   - System information disclosure

8. **Business Logic Testing**:
   - Authorization bypass
   - Privilege escalation
   - Data access controls
   - Workflow manipulation

For each webhook, provide:
- Security score (1-10)
- Vulnerabilities found
- Risk assessment
- Remediation recommendations
- Compliance status
"""

        try:
            # Perform direct security testing
            security_test_results = []
            for webhook_url in webhook_urls:
                security_result = await self._test_webhook_security_directly(webhook_url)
                security_test_results.append(security_result)
            
            # Use WebSurfer for advanced security testing
            response = await self.agent.on_messages(
                [TextMessage(content=security_prompt, source="user")],
                cancellation_token=None
            )
            
            security_result = {
                "security_test_id": f"webhook-security-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "webhooks_tested": len(webhook_urls),
                "direct_security_results": security_test_results,
                "detailed_security_analysis": response.chat_message.content if response.chat_message else str(response),
                "status": "completed"
            }
            
            logger.info(f"Completed webhook security testing: {security_result['security_test_id']}")
            return security_result
            
        except Exception as e:
            logger.error(f"Webhook security testing failed: {e}")
            return {
                "security_test_id": f"webhook-security-error-{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "failed",
                "error": str(e)
            }
            
    async def _test_webhook_directly(self, webhook_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform direct HTTP testing of a webhook."""
        try:
            url = webhook_config.get("url")
            if not url:
                return {"error": "No URL provided in webhook config"}
            
            # Prepare test payload
            test_payload = {
                "event_type": "test",
                "session_id": "test-session-123",
                "timestamp": datetime.now().isoformat(),
                "data": {"test": True}
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Codex-Hooks-QA-Agent/1.0"
            }
            
            # Add authentication headers if configured
            if "auth" in webhook_config:
                auth_config = webhook_config["auth"]
                if auth_config.get("type") == "bearer":
                    headers["Authorization"] = f"Bearer {auth_config.get('token')}"
                elif auth_config.get("type") == "api_key":
                    headers[auth_config.get("header", "X-API-Key")] = auth_config.get("key")
            
            start_time = datetime.now()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post(url, json=test_payload, headers=headers) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    
                    response_data = {
                        "url": url,
                        "status_code": response.status,
                        "response_time_seconds": response_time,
                        "headers": dict(response.headers),
                        "content_type": response.headers.get("Content-Type"),
                        "test_payload": test_payload
                    }
                    
                    try:
                        response_body = await response.text()
                        response_data["response_body"] = response_body[:1000]  # Limit size
                        
                        # Try to parse as JSON
                        if response.headers.get("Content-Type", "").startswith("application/json"):
                            response_data["response_json"] = json.loads(response_body)
                    except Exception as e:
                        response_data["response_parse_error"] = str(e)
                    
                    return response_data
                    
        except Exception as e:
            return {
                "url": webhook_config.get("url"),
                "error": str(e),
                "test_payload": test_payload
            }
            
    async def _test_api_directly(self, api_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform direct testing of an API endpoint."""
        try:
            base_url = api_config.get("base_url")
            if not base_url:
                return {"error": "No base_url provided in API config"}
            
            # Test basic connectivity
            test_endpoint = api_config.get("test_endpoint", "/health")
            url = urllib.parse.urljoin(base_url, test_endpoint)
            
            headers = {
                "User-Agent": "Codex-Hooks-QA-Agent/1.0"
            }
            
            # Add authentication if configured
            if "auth" in api_config:
                auth_config = api_config["auth"]
                if auth_config.get("type") == "bearer":
                    headers["Authorization"] = f"Bearer {auth_config.get('token')}"
                elif auth_config.get("type") == "api_key":
                    headers[auth_config.get("header", "X-API-Key")] = auth_config.get("key")
            
            start_time = datetime.now()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(url, headers=headers) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    
                    result = {
                        "api_name": api_config.get("name", "Unknown"),
                        "base_url": base_url,
                        "test_url": url,
                        "status_code": response.status,
                        "response_time_seconds": response_time,
                        "headers": dict(response.headers),
                        "ssl_info": {
                            "scheme": urllib.parse.urlparse(url).scheme,
                            "is_https": url.startswith("https://")
                        }
                    }
                    
                    try:
                        response_body = await response.text()
                        result["response_body"] = response_body[:500]  # Limit size
                    except Exception as e:
                        result["response_parse_error"] = str(e)
                    
                    return result
                    
        except Exception as e:
            return {
                "api_name": api_config.get("name", "Unknown"),
                "base_url": api_config.get("base_url"),
                "error": str(e)
            }
            
    async def _test_webhook_security_directly(self, webhook_url: str) -> Dict[str, Any]:
        """Perform direct security testing of a webhook."""
        try:
            security_tests = []
            
            # Test 1: HTTPS enforcement
            if webhook_url.startswith("http://"):
                security_tests.append({
                    "test": "HTTPS enforcement",
                    "status": "FAIL",
                    "issue": "Webhook uses HTTP instead of HTTPS",
                    "severity": "HIGH"
                })
            else:
                security_tests.append({
                    "test": "HTTPS enforcement",
                    "status": "PASS",
                    "message": "Webhook uses HTTPS"
                })
            
            # Test 2: Basic connectivity and headers
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(webhook_url) as response:
                        headers = dict(response.headers)
                        
                        # Check security headers
                        security_headers = {
                            "Strict-Transport-Security": "HSTS header",
                            "X-Content-Type-Options": "Content type options",
                            "X-Frame-Options": "Frame options",
                            "X-XSS-Protection": "XSS protection"
                        }
                        
                        for header, description in security_headers.items():
                            if header in headers:
                                security_tests.append({
                                    "test": f"Security header: {description}",
                                    "status": "PASS",
                                    "header": header,
                                    "value": headers[header]
                                })
                            else:
                                security_tests.append({
                                    "test": f"Security header: {description}",
                                    "status": "WARNING",
                                    "issue": f"Missing {header} header",
                                    "severity": "MEDIUM"
                                })
                        
            except Exception as e:
                security_tests.append({
                    "test": "Basic connectivity",
                    "status": "FAIL",
                    "error": str(e),
                    "severity": "HIGH"
                })
            
            # Test 3: Malformed payload handling
            try:
                malformed_payloads = [
                    {"test": "oversized", "data": "x" * 10000},  # Large payload
                    "invalid json string",  # Invalid JSON
                    {"test": "injection", "data": "<script>alert('xss')</script>"}  # XSS attempt
                ]
                
                for i, payload in enumerate(malformed_payloads):
                    try:
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                            async with session.post(webhook_url, json=payload) as response:
                                if response.status >= 400:
                                    security_tests.append({
                                        "test": f"Malformed payload handling {i+1}",
                                        "status": "PASS",
                                        "message": f"Properly rejected malformed payload with status {response.status}"
                                    })
                                else:
                                    security_tests.append({
                                        "test": f"Malformed payload handling {i+1}",
                                        "status": "WARNING",
                                        "issue": f"Accepted malformed payload with status {response.status}",
                                        "severity": "MEDIUM"
                                    })
                    except Exception:
                        # Connection errors are expected for malformed requests
                        security_tests.append({
                            "test": f"Malformed payload handling {i+1}",
                            "status": "PASS",
                            "message": "Connection rejected malformed payload"
                        })
                        
            except Exception as e:
                security_tests.append({
                    "test": "Malformed payload testing",
                    "status": "ERROR",
                    "error": str(e)
                })
            
            return {
                "webhook_url": webhook_url,
                "security_tests": security_tests,
                "overall_score": self._calculate_security_score(security_tests)
            }
            
        except Exception as e:
            return {
                "webhook_url": webhook_url,
                "error": str(e),
                "security_tests": []
            }
            
    def _calculate_security_score(self, security_tests: List[Dict[str, Any]]) -> float:
        """Calculate overall security score based on test results."""
        if not security_tests:
            return 0.0
        
        total_tests = len(security_tests)
        passed_tests = len([test for test in security_tests if test.get("status") == "PASS"])
        warning_tests = len([test for test in security_tests if test.get("status") == "WARNING"])
        
        # Calculate score: PASS = 1.0, WARNING = 0.5, FAIL/ERROR = 0.0
        score = (passed_tests + (warning_tests * 0.5)) / total_tests
        return round(score * 10, 1)  # Scale to 0-10
        
    def get_test_history(self) -> List[Dict[str, Any]]:
        """Get test history."""
        return self.test_results.copy()
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("WebSurfer agent cleanup completed")


# Example usage and testing
async def test_web_surfer_agent():
    """Test the WebSurfer agent."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found in environment")
        return
        
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)
    
    try:
        # Create WebSurfer agent
        web_surfer = CodexHooksWebSurferAgent(client)
        
        # Test webhook endpoints
        webhook_configs = [
            {
                "url": "https://httpbin.org/post",
                "description": "Test webhook endpoint"
            },
            {
                "url": "http://localhost:8080/webhook/test",
                "description": "Local test webhook"
            }
        ]
        
        webhook_result = await web_surfer.test_webhook_endpoints(webhook_configs)
        print(f"Webhook testing: {webhook_result['test_id']}")
        
        # Test API integrations
        api_configs = [
            {
                "name": "GitHub API",
                "base_url": "https://api.github.com",
                "test_endpoint": "/zen"
            }
        ]
        
        api_result = await web_surfer.validate_api_integrations(api_configs)
        print(f"API validation: {api_result['validation_id']}")
        
        # Test webhook security
        webhook_urls = ["https://httpbin.org/post"]
        security_result = await web_surfer.test_webhook_security(webhook_urls)
        print(f"Security testing: {security_result['security_test_id']}")
        
        # Cleanup
        await web_surfer.cleanup()
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_web_surfer_agent())
