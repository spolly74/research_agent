"""
Report Generator

Orchestrates the complete report generation process:
1. Template selection
2. Outline creation with scope-based scaling
3. Section-by-section content generation
4. Citation management
5. Formatting and output
"""

from typing import Optional, Callable
from datetime import datetime
import structlog
from copy import deepcopy

from app.reports.templates.base import (
    ReportTemplate, ReportOutline, ReportSection, SectionType, ReportType
)
from app.reports.templates.research_report import ResearchReportTemplate
from app.reports.templates.technical_analysis import TechnicalAnalysisTemplate
from app.reports.templates.executive_summary import ExecutiveSummaryTemplate
from app.reports.citation_manager import CitationManager, CitationStyle
from app.reports.formatters.markdown import MarkdownFormatter, format_report_as_markdown
from app.reports.formatters.html import HTMLFormatter, format_report_as_html
from app.reports.scope_config import ScopeConfig, ReportScope, create_scope_config, detect_scope_from_query

logger = structlog.get_logger(__name__)


class ReportGenerator:
    """
    Generates professional reports from research data.

    Usage:
        generator = ReportGenerator()
        outline = generator.create_outline("Report Title", research_data, ReportType.RESEARCH)
        # Generate content for each section using LLM
        markdown = generator.format_as_markdown(outline)

    With scope configuration:
        generator = ReportGenerator()
        generator.set_scope(ReportScope.COMPREHENSIVE)
        outline = generator.create_outline(...)
    """

    # Available templates
    TEMPLATES = {
        ReportType.RESEARCH: ResearchReportTemplate,
        ReportType.TECHNICAL: TechnicalAnalysisTemplate,
        ReportType.EXECUTIVE: ExecutiveSummaryTemplate,
    }

    def __init__(
        self,
        citation_style: CitationStyle = CitationStyle.APA,
        scope: Optional[ScopeConfig] = None
    ):
        self.citation_manager = CitationManager(style=citation_style)
        self._templates: dict[ReportType, ReportTemplate] = {}
        self._scope: Optional[ScopeConfig] = scope

    def set_scope(
        self,
        scope: Optional[ReportScope] = None,
        pages: Optional[int] = None,
        word_count: Optional[int] = None,
        query: Optional[str] = None
    ) -> ScopeConfig:
        """
        Set the scope configuration for report generation.

        Args:
            scope: ReportScope enum value
            pages: Custom page count
            word_count: Custom word count
            query: Query to detect scope from

        Returns:
            The configured ScopeConfig
        """
        if scope:
            self._scope = ScopeConfig(scope=scope, custom_pages=pages, custom_word_count=word_count)
        elif pages or word_count:
            self._scope = ScopeConfig(scope=ReportScope.CUSTOM, custom_pages=pages, custom_word_count=word_count)
        elif query:
            self._scope = create_scope_config(query=query)
        else:
            self._scope = ScopeConfig(scope=ReportScope.STANDARD)

        logger.info(
            "Scope configuration set",
            scope=self._scope.scope.value,
            target_words=self._scope.parameters.target_word_count
        )
        return self._scope

    def get_scope(self) -> Optional[ScopeConfig]:
        """Get current scope configuration."""
        return self._scope

    def get_research_parameters(self) -> dict:
        """
        Get parameters to guide research depth based on scope.

        Returns dict with min/max sources, depth level, etc.
        """
        if self._scope:
            return self._scope.get_research_parameters()
        # Default parameters
        return {
            "min_sources": 5,
            "max_sources": 10,
            "depth": "balanced",
            "focus": "balanced"
        }

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
        metadata: Optional[dict] = None,
        scope: Optional[ScopeConfig] = None
    ) -> ReportOutline:
        """
        Create a report outline from research data.

        Args:
            title: Report title
            research_data: List of research findings
            report_type: Type of report (auto-detected if None)
            metadata: Additional metadata
            scope: Scope configuration (uses instance scope if not provided)

        Returns:
            ReportOutline ready for content generation
        """
        # Use provided scope or instance scope
        active_scope = scope or self._scope

        # Auto-detect scope from title if not set
        if active_scope is None:
            active_scope = create_scope_config(query=title)
            self._scope = active_scope

        # Auto-select template if not specified
        if report_type is None:
            report_type = self.select_template(title, research_data)
            logger.info("Auto-selected report type", report_type=report_type.value)

        template = self.get_template(report_type)
        outline = template.create_outline(title, research_data, metadata)

        # Apply scope-based scaling to sections
        outline = self._apply_scope_to_outline(outline, active_scope)

        # Extract citations from research data
        self._extract_citations_from_data(research_data)

        logger.info(
            "Report outline created",
            title=title,
            report_type=report_type.value,
            scope=active_scope.scope.value,
            sections=len(outline.sections),
            target_words=active_scope.parameters.target_word_count,
            citations=len(self.citation_manager.get_all_citations())
        )

        return outline

    def _apply_scope_to_outline(self, outline: ReportOutline, scope: ScopeConfig) -> ReportOutline:
        """
        Apply scope configuration to an outline.

        Adjusts word counts and filters sections based on scope.
        """
        filtered_sections = []

        for section in outline.sections:
            # Check if section should be included for this scope
            if not scope.should_include_section(section.section_type.value):
                logger.debug(
                    "Excluding section based on scope",
                    section=section.title,
                    scope=scope.scope.value
                )
                continue

            # Scale word count target
            if section.word_count_target:
                section.word_count_target = scope.scale_section_word_count(section.word_count_target)

            filtered_sections.append(section)

        # Re-number section order
        for i, section in enumerate(filtered_sections, 1):
            section.order = i

        outline.sections = filtered_sections

        # Add scope info to metadata
        outline.metadata["scope"] = scope.to_dict()

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

        # Get scope instructions if available
        scope_instructions = ""
        if self._scope:
            scope_instructions = self._scope.get_editor_instructions()

        context = {
            "title": outline.title,
            "report_type": outline.report_type.value,
            "research_data": research_data,
            "previous_sections_summary": previous_summary,
            "citations": [c.to_dict() for c in self.citation_manager.get_all_citations()],
            "scope_instructions": scope_instructions
        }

        base_prompt = template.get_writing_prompt(section, context)

        # Prepend scope instructions if available
        if scope_instructions:
            return f"{scope_instructions}\n\n{base_prompt}"

        return base_prompt

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
        status = {
            "citation_count": len(self.citation_manager.get_all_citations()),
            "citation_style": self.citation_manager.style.value,
            "available_templates": [t.value for t in self.TEMPLATES.keys()]
        }

        if self._scope:
            status["scope"] = self._scope.to_dict()

        return status


def create_report_from_research(
    title: str,
    research_data: list[str],
    report_type: Optional[ReportType] = None,
    format_type: str = "markdown",
    scope: Optional[str] = None,
    pages: Optional[int] = None,
    word_count: Optional[int] = None
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
        scope: Scope level ("brief", "standard", "comprehensive")
        pages: Custom page count
        word_count: Custom word count

    Returns:
        Tuple of (outline, formatted_structure)
    """
    # Create scope config
    scope_config = None
    if scope or pages or word_count:
        scope_config = create_scope_config(
            scope=scope,
            pages=pages,
            word_count=word_count,
            query=title
        )

    generator = ReportGenerator(scope=scope_config)
    outline = generator.create_outline(title, research_data, report_type)

    if format_type == "html":
        formatted = generator.format_as_html(outline)
    else:
        formatted = generator.format_as_markdown(outline)

    return outline, formatted
