"""Report templates module."""

from app.reports.templates.base import ReportTemplate, ReportSection, ReportOutline
from app.reports.templates.research_report import ResearchReportTemplate
from app.reports.templates.technical_analysis import TechnicalAnalysisTemplate
from app.reports.templates.executive_summary import ExecutiveSummaryTemplate

__all__ = [
    'ReportTemplate',
    'ReportSection',
    'ReportOutline',
    'ResearchReportTemplate',
    'TechnicalAnalysisTemplate',
    'ExecutiveSummaryTemplate'
]
