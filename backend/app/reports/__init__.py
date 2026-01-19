"""
Report Generation Module

Provides professional report generation with:
- Multiple report templates (research, technical, executive)
- Citation management
- Multiple output formats (Markdown, HTML, PDF)
"""

from app.reports.templates.base import ReportTemplate, ReportSection, ReportOutline
from app.reports.citation_manager import CitationManager, Citation
from app.reports.generator import ReportGenerator

__all__ = [
    'ReportTemplate',
    'ReportSection',
    'ReportOutline',
    'CitationManager',
    'Citation',
    'ReportGenerator'
]
