"""
Report Generator

Orchestrates the complete report generation process:
1. Template selection
2. Outline creation
3. Section-by-section content generation
4. Citation management
5. Formatting and output
"""

from typing import Optional, Callable
from datetime import datetime
import structlog

from app.reports.templates.base import (
    ReportTemplate, ReportOutline, ReportSection, SectionType, ReportType
)
from app.reports.templates.research_report import ResearchReportTemplate
from app.reports.templates.technical_analysis import TechnicalAnalysisTemplate
from app.reports.templates.executive_summary import ExecutiveSummaryTemplate
from app.reports.citation_manager import CitationManager, CitationStyle
from app.reports.formatters.markdown import MarkdownFormatter, format_report_as_markdown
from app.reports.formatters.html import HTMLFormatter, format_report_as_html

logger = structlog.get_logger(__name__)


class ReportGenerator:
    """
    Generates professional reports from research data.

    Usage:
        generator = ReportGenerator()
        outline = generator.create_outline("Report Title", research_data, ReportType.RESEARCH)
        # Generate content for each section using LLM
        markdown = generator.format_as_markdown(outline)
    """

    # Available templates
    TEMPLATES = {
        ReportType.RESEARCH: ResearchReportTemplate,
        ReportType.TECHNICAL: TechnicalAnalysisTemplate,
        ReportType.EXECUTIVE: ExecutiveSummaryTemplate,
    }

    def __init__(self, citation_style: CitationStyle = CitationStyle.APA):
        self.citation_manager = CitationManager(style=citation_style)
        self._templates: dict[ReportType, ReportTemplate] = {}

    def get_template(self, report_type: ReportType) -> ReportTemplate:
        """Get or create a template instance."""
        if report_type not in self._templates:
            template_class = self.TEMPLATES.get(report_type, ResearchReportTemplate)
            self._templates[report_type] = template_class()
        return self._templates[report_type]

    def select_template(self, query: str, research_data: list[str]) -> ReportType:
        """
        Automatically select the best template based on content.

        Args:
            query: The original research query
            research_data: The gathered research data

        Returns:
            The recommended ReportType
        """
        query_lower = query.lower()

        # Keywords for technical reports
        technical_keywords = [
            'technical', 'architecture', 'implementation', 'performance',
            'security', 'infrastructure', 'system', 'code', 'api', 'database'
        ]

        # Keywords for executive summaries
        executive_keywords = [
            'executive', 'summary', 'brief', 'overview', 'quick',
            'decision', 'stakeholder', 'recommendation'
        ]

        # Check for technical
        if any(kw in query_lower for kw in technical_keywords):
            return ReportType.TECHNICAL

        # Check for executive
        if any(kw in query_lower for kw in executive_keywords):
            return ReportType.EXECUTIVE

        # Check content length for executive vs research
        total_content = " ".join(research_data)
        if len(total_content) < 2000:
            return ReportType.EXECUTIVE

        # Default to research report
        return ReportType.RESEARCH

    def create_outline(
        self,
        title: str,
        research_data: list[str],
        report_type: Optional[ReportType] = None,
        metadata: Optional[dict] = None
    ) -> ReportOutline:
        """
        Create a report outline from research data.

        Args:
            title: Report title
            research_data: List of research findings
            report_type: Type of report (auto-detected if None)
            metadata: Additional metadata

        Returns:
            ReportOutline ready for content generation
        """
        # Auto-select template if not specified
        if report_type is None:
            report_type = self.select_template(title, research_data)
            logger.info("Auto-selected report type", report_type=report_type.value)

        template = self.get_template(report_type)
        outline = template.create_outline(title, research_data, metadata)

        # Extract citations from research data
        self._extract_citations_from_data(research_data)

        logger.info(
            "Report outline created",
            title=title,
            report_type=report_type.value,
            sections=len(outline.sections),
            citations=len(self.citation_manager.get_all_citations())
        )

        return outline

    def _extract_citations_from_data(self, research_data: list[str]) -> None:
        """Extract and register citations from research data."""
        import re

        for data in research_data:
            # Look for URLs in the data
            urls = re.findall(r'https?://[^\s\]\)]+', data)
            for url in urls:
                # Clean URL
                url = url.rstrip('.,;:')
                self.citation_manager.create_citation_from_url(url, data)

    def get_writing_prompt(
        self,
        outline: ReportOutline,
        section: ReportSection,
        research_data: list[str],
        previous_sections: list[ReportSection]
    ) -> str:
        """
        Generate an LLM prompt for writing a section.

        Args:
            outline: The report outline
            section: The section to write
            research_data: Original research data
            previous_sections: Previously written sections

        Returns:
            A prompt string for the LLM
        """
        template = self.get_template(outline.report_type)

        # Summarize previous sections
        previous_summary = ""
        if previous_sections:
            summaries = []
            for prev in previous_sections:
                if prev.content:
                    # Take first 200 chars as summary
                    summary = prev.content[:200] + "..." if len(prev.content) > 200 else prev.content
                    summaries.append(f"**{prev.title}**: {summary}")
            previous_summary = "\n".join(summaries)
        else:
            previous_summary = "This is the first section."

        context = {
            "title": outline.title,
            "report_type": outline.report_type.value,
            "research_data": research_data,
            "previous_sections_summary": previous_summary,
            "citations": [c.to_dict() for c in self.citation_manager.get_all_citations()]
        }

        return template.get_writing_prompt(section, context)

    def update_section_content(
        self,
        outline: ReportOutline,
        section_type: SectionType,
        content: str
    ) -> bool:
        """
        Update the content of a section in the outline.

        Args:
            outline: The report outline
            section_type: The section to update
            content: The new content

        Returns:
            True if section was found and updated
        """
        section = outline.get_section(section_type)
        if section:
            section.content = content
            logger.debug(
                "Section content updated",
                section=section_type.value,
                word_count=len(content.split())
            )
            return True
        return False

    def format_as_markdown(self, outline: ReportOutline, include_toc: bool = True) -> str:
        """Format the report as Markdown."""
        return format_report_as_markdown(outline, self.citation_manager, include_toc)

    def format_as_html(self, outline: ReportOutline, include_toc: bool = True) -> str:
        """Format the report as HTML."""
        return format_report_as_html(outline, self.citation_manager, include_toc)

    def get_bibliography(self) -> str:
        """Get the formatted bibliography."""
        return self.citation_manager.generate_bibliography(used_only=False)

    def get_status(self) -> dict:
        """Get generator status."""
        return {
            "citation_count": len(self.citation_manager.get_all_citations()),
            "citation_style": self.citation_manager.style.value,
            "available_templates": [t.value for t in self.TEMPLATES.keys()]
        }


def create_report_from_research(
    title: str,
    research_data: list[str],
    report_type: Optional[ReportType] = None,
    format_type: str = "markdown"
) -> tuple[ReportOutline, str]:
    """
    Convenience function to create a report structure from research.

    Note: This creates the outline but doesn't generate content.
    Content must be generated section-by-section using an LLM.

    Args:
        title: Report title
        research_data: Research findings
        report_type: Type of report
        format_type: Output format ("markdown" or "html")

    Returns:
        Tuple of (outline, formatted_structure)
    """
    generator = ReportGenerator()
    outline = generator.create_outline(title, research_data, report_type)

    if format_type == "html":
        formatted = generator.format_as_html(outline)
    else:
        formatted = generator.format_as_markdown(outline)

    return outline, formatted
