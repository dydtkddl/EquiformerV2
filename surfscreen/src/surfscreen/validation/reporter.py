"""
Validation Reporter - generates comprehensive validation reports.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

from .physics import ValidationResult, ValidationStatus


class ValidationReporter:
    """Generates validation reports in various formats."""
    
    def __init__(self, title: str = "SurfScreen Scientific Validation"):
        self.title = title
        self.results: List[ValidationResult] = []
        self.metadata: Dict = {
            'timestamp': datetime.now().isoformat(),
            'version': '0.8.0'
        }
    
    def add_result(self, result: ValidationResult):
        """Add a validation result."""
        self.results.append(result)
    
    def add_results(self, results: List[ValidationResult]):
        """Add multiple validation results."""
        self.results.extend(results)
    
    def get_summary(self) -> Dict[str, int]:
        """Get count of each status."""
        summary = {
            'PASS': 0,
            'FAIL': 0,
            'WARNING': 0,
            'SKIPPED': 0
        }
        for result in self.results:
            summary[result.status.value] += 1
        return summary
    
    def is_valid(self) -> bool:
        """Check if all validations passed (no FAIL)."""
        return all(r.status != ValidationStatus.FAIL for r in self.results)
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            'title': self.title,
            'metadata': self.metadata,
            'summary': self.get_summary(),
            'is_valid': self.is_valid(),
            'results': [
                {
                    'name': r.name,
                    'status': r.status.value,
                    'message': r.message,
                    'expected': str(r.expected) if r.expected is not None else None,
                    'actual': str(r.actual) if r.actual is not None else None,
                    'tolerance': r.tolerance
                }
                for r in self.results
            ]
        }
    
    def to_json(self, path: Optional[Path] = None) -> str:
        """Export report as JSON."""
        content = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        if path:
            Path(path).write_text(content, encoding='utf-8')
        return content
    
    def to_markdown(self, path: Optional[Path] = None) -> str:
        """Export report as Markdown."""
        summary = self.get_summary()
        
        lines = [
            f"# {self.title}",
            "",
            f"**Generated:** {self.metadata['timestamp']}",
            f"**Version:** {self.metadata['version']}",
            "",
            "## Summary",
            "",
            f"| Status | Count |",
            f"|--------|-------|",
            f"| ✅ PASS | {summary['PASS']} |",
            f"| ❌ FAIL | {summary['FAIL']} |",
            f"| ⚠️ WARNING | {summary['WARNING']} |",
            f"| ⏭️ SKIPPED | {summary['SKIPPED']} |",
            "",
            f"**Overall:** {'✅ VALID' if self.is_valid() else '❌ INVALID'}",
            "",
            "## Detailed Results",
            ""
        ]
        
        status_icons = {
            ValidationStatus.PASS: "✅",
            ValidationStatus.FAIL: "❌",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.SKIPPED: "⏭️"
        }
        
        for result in self.results:
            icon = status_icons[result.status]
            lines.append(f"### {icon} {result.name}")
            lines.append("")
            lines.append(f"**Status:** {result.status.value}")
            lines.append("")
            lines.append(f"**Message:** {result.message}")
            lines.append("")
            if result.expected is not None:
                lines.append(f"- **Expected:** {result.expected}")
            if result.actual is not None:
                lines.append(f"- **Actual:** {result.actual}")
            if result.tolerance is not None:
                lines.append(f"- **Tolerance:** {result.tolerance}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        content = "\n".join(lines)
        if path:
            Path(path).write_text(content, encoding='utf-8')
        return content
    
    def to_html(self, path: Optional[Path] = None) -> str:
        """Export report as HTML."""
        summary = self.get_summary()
        
        status_colors = {
            ValidationStatus.PASS: "#22c55e",
            ValidationStatus.FAIL: "#ef4444",
            ValidationStatus.WARNING: "#f59e0b",
            ValidationStatus.SKIPPED: "#6b7280"
        }
        
        rows = ""
        for result in self.results:
            color = status_colors[result.status]
            rows += f"""
            <tr>
                <td style="color: {color}; font-weight: bold;">{result.status.value}</td>
                <td>{result.name}</td>
                <td>{result.message}</td>
                <td>{result.expected if result.expected else '-'}</td>
                <td>{result.actual if result.actual else '-'}</td>
            </tr>
            """
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f3f4f6; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h1 {{ color: #1f2937; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-pass {{ background: #dcfce7; color: #166534; }}
        .stat-fail {{ background: #fee2e2; color: #991b1b; }}
        .stat-warning {{ background: #fef3c7; color: #92400e; }}
        .stat-skipped {{ background: #f3f4f6; color: #4b5563; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .overall {{ padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; font-size: 1.2em; font-weight: bold; }}
        .valid {{ background: #dcfce7; color: #166534; }}
        .invalid {{ background: #fee2e2; color: #991b1b; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
        tr:hover {{ background: #f9fafb; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{self.title}</h1>
        <p><strong>Generated:</strong> {self.metadata['timestamp']}</p>
        
        <div class="summary">
            <div class="stat stat-pass"><div class="stat-value">{summary['PASS']}</div>PASS</div>
            <div class="stat stat-fail"><div class="stat-value">{summary['FAIL']}</div>FAIL</div>
            <div class="stat stat-warning"><div class="stat-value">{summary['WARNING']}</div>WARNING</div>
            <div class="stat stat-skipped"><div class="stat-value">{summary['SKIPPED']}</div>SKIPPED</div>
        </div>
        
        <div class="overall {'valid' if self.is_valid() else 'invalid'}">
            {'✅ ALL VALIDATIONS PASSED' if self.is_valid() else '❌ VALIDATION FAILED'}
        </div>
        
        <h2>Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Status</th>
                    <th>Check</th>
                    <th>Message</th>
                    <th>Expected</th>
                    <th>Actual</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        if path:
            Path(path).write_text(html, encoding='utf-8')
        return html
    
    def print_console(self):
        """Print report to console."""
        summary = self.get_summary()
        
        print(f"\n{'='*60}")
        print(f"  {self.title}")
        print(f"{'='*60}\n")
        
        print(f"Summary: PASS={summary['PASS']} | FAIL={summary['FAIL']} | WARNING={summary['WARNING']} | SKIPPED={summary['SKIPPED']}")
        print(f"Overall: {'✅ VALID' if self.is_valid() else '❌ INVALID'}\n")
        
        status_symbols = {
            ValidationStatus.PASS: "✅",
            ValidationStatus.FAIL: "❌",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.SKIPPED: "⏭️"
        }
        
        for result in self.results:
            symbol = status_symbols[result.status]
            print(f"{symbol} {result.name}: {result.message}")
        
        print(f"\n{'='*60}\n")
