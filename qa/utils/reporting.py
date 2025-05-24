"""
Report Generator
Comprehensive reporting system for QA results and analysis
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Report generator responsible for creating comprehensive reports
    in multiple formats for QA workflow results.
    """
    
    def __init__(self):
        self.reports_dir = Path('/workspace/qa/reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Report templates
        self.templates = {
            'html': self._get_html_template(),
            'markdown': self._get_markdown_template()
        }
    
    async def generate_reports(self, report_data: Dict) -> List[str]:
        """Generate reports in multiple formats"""
        try:
            logger.info("Generating QA reports")
            
            generated_files = []
            
            # Generate JSON report
            json_file = await self._generate_json_report(report_data)
            if json_file:
                generated_files.append(json_file)
            
            # Generate HTML report
            html_file = await self._generate_html_report(report_data)
            if html_file:
                generated_files.append(html_file)
            
            # Generate Markdown report
            markdown_file = await self._generate_markdown_report(report_data)
            if markdown_file:
                generated_files.append(markdown_file)
            
            logger.info(f"Generated {len(generated_files)} report files")
            return generated_files
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return []
    
    async def _generate_json_report(self, report_data: Dict) -> Optional[str]:
        """Generate JSON format report"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qa_report_{timestamp}.json"
            filepath = self.reports_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"JSON report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"JSON report generation failed: {e}")
            return None
    
    async def _generate_html_report(self, report_data: Dict) -> Optional[str]:
        """Generate HTML format report"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qa_report_{timestamp}.html"
            filepath = self.reports_dir / filename
            
            # Generate HTML content
            html_content = self._render_html_report(report_data)
            
            with open(filepath, 'w') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"HTML report generation failed: {e}")
            return None
    
    async def _generate_markdown_report(self, report_data: Dict) -> Optional[str]:
        """Generate Markdown format report"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qa_report_{timestamp}.md"
            filepath = self.reports_dir / filename
            
            # Generate Markdown content
            markdown_content = self._render_markdown_report(report_data)
            
            with open(filepath, 'w') as f:
                f.write(markdown_content)
            
            logger.info(f"Markdown report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Markdown report generation failed: {e}")
            return None
    
    def _render_html_report(self, report_data: Dict) -> str:
        """Render HTML report content"""
        suite_name = report_data.get('suite_name', 'Unknown')
        timestamp = report_data.get('timestamp', datetime.now().isoformat())
        execution_time = report_data.get('execution_time', 0)
        results = report_data.get('results', {})
        summary = report_data.get('summary', {})
        
        # Generate results table
        results_rows = ""
        for workflow_name, result in results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            exec_time = f"{result.get('execution_time', 0):.2f}s"
            details = result.get('summary', 'No details available')
            
            results_rows += f"""
            <tr>
                <td>{workflow_name}</td>
                <td>{status}</td>
                <td>{exec_time}</td>
                <td>{details}</td>
            </tr>
            """
        
        # Generate summary cards
        total_workflows = summary.get('total_workflows', 0)
        successful_workflows = summary.get('successful_workflows', 0)
        failed_workflows = summary.get('failed_workflows', 0)
        overall_success = summary.get('overall_success', False)
        
        overall_status = "✅ PASS" if overall_success else "❌ FAIL"
        success_rate = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Codex QA Report - {suite_name}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
                .header h1 {{ margin: 0; font-size: 2.5em; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; }}
                .card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; border-left: 4px solid #007bff; }}
                .card.success {{ border-left-color: #28a745; }}
                .card.failure {{ border-left-color: #dc3545; }}
                .card h3 {{ margin: 0 0 10px 0; color: #333; }}
                .card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .card.success .value {{ color: #28a745; }}
                .card.failure .value {{ color: #dc3545; }}
                .results {{ padding: 0 30px 30px 30px; }}
                .results h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f8f9fa; font-weight: 600; }}
                .status-pass {{ color: #28a745; font-weight: bold; }}
                .status-fail {{ color: #dc3545; font-weight: bold; }}
                .footer {{ padding: 20px 30px; background: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Codex QA Report</h1>
                    <p>Suite: {suite_name} | Generated: {timestamp}</p>
                </div>
                
                <div class="summary">
                    <div class="card {'success' if overall_success else 'failure'}">
                        <h3>Overall Status</h3>
                        <div class="value">{overall_status}</div>
                    </div>
                    <div class="card">
                        <h3>Total Workflows</h3>
                        <div class="value">{total_workflows}</div>
                    </div>
                    <div class="card success">
                        <h3>Successful</h3>
                        <div class="value">{successful_workflows}</div>
                    </div>
                    <div class="card failure">
                        <h3>Failed</h3>
                        <div class="value">{failed_workflows}</div>
                    </div>
                    <div class="card">
                        <h3>Success Rate</h3>
                        <div class="value">{success_rate:.1f}%</div>
                    </div>
                    <div class="card">
                        <h3>Execution Time</h3>
                        <div class="value">{execution_time:.1f}s</div>
                    </div>
                </div>
                
                <div class="results">
                    <h2>📊 Workflow Results</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Workflow</th>
                                <th>Status</th>
                                <th>Duration</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results_rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="footer">
                    <p>Generated by Codex QA Automation System | Powered by Magentic-One</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _render_markdown_report(self, report_data: Dict) -> str:
        """Render Markdown report content"""
        suite_name = report_data.get('suite_name', 'Unknown')
        timestamp = report_data.get('timestamp', datetime.now().isoformat())
        execution_time = report_data.get('execution_time', 0)
        results = report_data.get('results', {})
        summary = report_data.get('summary', {})
        
        # Generate results table
        results_table = "| Workflow | Status | Duration | Details |\n|----------|--------|----------|----------|\n"
        
        for workflow_name, result in results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            exec_time = f"{result.get('execution_time', 0):.2f}s"
            details = result.get('summary', 'No details available')
            
            results_table += f"| {workflow_name} | {status} | {exec_time} | {details} |\n"
        
        # Generate summary
        total_workflows = summary.get('total_workflows', 0)
        successful_workflows = summary.get('successful_workflows', 0)
        failed_workflows = summary.get('failed_workflows', 0)
        overall_success = summary.get('overall_success', False)
        
        overall_status = "✅ PASS" if overall_success else "❌ FAIL"
        success_rate = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0
        
        markdown_content = f"""# 🤖 Codex QA Report

**Suite:** {suite_name}  
**Generated:** {timestamp}  
**Overall Status:** {overall_status}

## 📊 Summary

| Metric | Value |
|--------|-------|
| Total Workflows | {total_workflows} |
| Successful | {successful_workflows} |
| Failed | {failed_workflows} |
| Success Rate | {success_rate:.1f}% |
| Execution Time | {execution_time:.1f}s |

## 📋 Workflow Results

{results_table}

## 🔍 Detailed Analysis

### Successful Workflows
{chr(10).join([f"- **{name}**: {result.get('summary', 'Completed successfully')}" for name, result in results.items() if result.get('success', False)])}

### Failed Workflows
{chr(10).join([f"- **{name}**: {result.get('error', 'Unknown error')}" for name, result in results.items() if not result.get('success', False)])}

## 🚀 Recommendations

Based on the test results, consider the following actions:

1. **Review Failed Tests**: Investigate and address any failed workflow issues
2. **Performance Optimization**: Look for opportunities to improve execution time
3. **Test Coverage**: Ensure comprehensive coverage of all hook scenarios
4. **Documentation Updates**: Update documentation based on test findings

---

*Generated by Codex QA Automation System | Powered by Magentic-One*
"""
        
        return markdown_content
    
    def _get_html_template(self) -> str:
        """Get HTML report template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>QA Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                .summary { margin: 20px 0; }
                .results { margin: 20px 0; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """
    
    def _get_markdown_template(self) -> str:
        """Get Markdown report template"""
        return """# QA Report

{content}

---
*Generated by Codex QA System*
"""
    
    async def generate_performance_report(self, performance_data: Dict) -> str:
        """Generate specialized performance report"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"performance_report_{timestamp}.html"
            filepath = self.reports_dir / filename
            
            # Generate performance-specific HTML
            html_content = self._render_performance_html(performance_data)
            
            with open(filepath, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Performance report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Performance report generation failed: {e}")
            return ""
    
    def _render_performance_html(self, performance_data: Dict) -> str:
        """Render performance-specific HTML report"""
        # This would generate detailed performance charts and analysis
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>Performance Analysis Report</h1>
            <div id="performanceChart">
                <!-- Performance charts would be rendered here -->
            </div>
        </body>
        </html>
        """
    
    async def generate_security_report(self, security_data: Dict) -> str:
        """Generate specialized security report"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"security_report_{timestamp}.html"
            filepath = self.reports_dir / filename
            
            # Generate security-specific HTML
            html_content = self._render_security_html(security_data)
            
            with open(filepath, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Security report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Security report generation failed: {e}")
            return ""
    
    def _render_security_html(self, security_data: Dict) -> str:
        """Render security-specific HTML report"""
        # This would generate detailed security analysis
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Report</title>
        </head>
        <body>
            <h1>Security Analysis Report</h1>
            <div class="security-summary">
                <!-- Security analysis would be rendered here -->
            </div>
        </body>
        </html>
        """
    
    async def cleanup_old_reports(self, retention_days: int = 30):
        """Clean up old report files"""
        try:
            import time
            current_time = time.time()
            retention_seconds = retention_days * 24 * 60 * 60
            
            deleted_count = 0
            for report_file in self.reports_dir.glob('*'):
                if report_file.is_file():
                    file_age = current_time - report_file.stat().st_mtime
                    if file_age > retention_seconds:
                        report_file.unlink()
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old report files")
            
        except Exception as e:
            logger.error(f"Report cleanup failed: {e}")
    
    async def get_report_summary(self) -> Dict:
        """Get summary of generated reports"""
        try:
            reports = list(self.reports_dir.glob('*'))
            
            return {
                'total_reports': len(reports),
                'report_types': {
                    'json': len(list(self.reports_dir.glob('*.json'))),
                    'html': len(list(self.reports_dir.glob('*.html'))),
                    'markdown': len(list(self.reports_dir.glob('*.md')))
                },
                'latest_report': max(reports, key=lambda x: x.stat().st_mtime).name if reports else None,
                'reports_directory': str(self.reports_dir)
            }
            
        except Exception as e:
            logger.error(f"Failed to get report summary: {e}")
            return {'error': str(e)}
