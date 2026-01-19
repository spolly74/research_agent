"""
Base Report Template

Provides the foundation for all report templates with:
- Standard section structure
- Outline generation
- Content organization
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any
import structlog

logger = structlog.get_logger(__name__)


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    RESEARCH = "research"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    COMPARISON = "comparison"
    CUSTOM = "custom"


class SectionType(str, Enum):
    """Standard section types for reports."""
    TITLE = "title"
    ABSTRACT = "abstract"
    EXECUTIVE_SUMMARY = "executive_summary"
    INTRODUCTION = "introduction"
    BACKGROUND = "background"
    METHODOLOGY = "methodology"
    FINDINGS = "findings"
    ANALYSIS = "analysis"
    DISCUSSION = "discussion"
    RECOMMENDATIONS = "recommendations"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    APPENDIX = "appendix"
    CUSTOM = "custom"


@dataclass
class ReportSection:
    """A section within a report."""
    section_type: SectionType
    title: str
    content: str = ""
    subsections: list['ReportSection'] = field(default_factory=list)
    order: int = 0
    is_required: bool = True
    word_count_target: Optional[int] = None
    notes: str = ""  # Instructions for content generation

    def to_dict(self) -> dict:
        """Convert section to dictionary."""
        return {
            "type": self.section_type.value,
            "title": self.title,
            "content": self.content,
            "subsections": [s.to_dict() for s in self.subsections],
            "order": self.order,
            "is_required": self.is_required,
            "word_count_target": self.word_count_target
        }

    def word_count(self) -> int:
        """Get word count of content."""
        count = len(self.content.split())
        for sub in self.subsections:
            count += sub.word_count()
        return count


@dataclass
class ReportOutline:
    """Complete outline for a report."""
    title: str
    report_type: ReportType
    sections: list[ReportSection] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert outline to dictionary."""
        return {
            "title": self.title,
            "report_type": self.report_type.value,
            "sections": [s.to_dict() for s in self.sections],
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }

    def get_section(self, section_type: SectionType) -> Optional[ReportSection]:
        """Get a specific section by type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None

    def total_word_count(self) -> int:
        """Get total word count across all sections."""
        return sum(s.word_count() for s in self.sections)


@dataclass
class ReportMetadata:
    """Metadata for a generated report."""
    title: str
    author: str = "Research Agent"
    date: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    keywords: list[str] = field(default_factory=list)
    abstract: str = ""
    report_type: ReportType = ReportType.RESEARCH


class ReportTemplate(ABC):
    """
    Abstract base class for report templates.

    Subclasses should implement:
    - get_sections(): Define the sections for this report type
    - get_section_instructions(): Provide writing instructions for each section
    """

    def __init__(self):
        self.report_type: ReportType = ReportType.CUSTOM
        self.name: str = "Base Template"
        self.description: str = "Base report template"

    @abstractmethod
    def get_sections(self) -> list[ReportSection]:
        """
        Get the list of sections for this report type.

        Returns:
            List of ReportSection objects defining the report structure
        """
        pass

    @abstractmethod
    def get_section_instructions(self, section_type: SectionType) -> str:
        """
        Get writing instructions for a specific section.

        Args:
            section_type: The type of section

        Returns:
            Instructions for generating content for this section
        """
        pass

    def create_outline(self, title: str, research_data: list[str], metadata: Optional[dict] = None) -> ReportOutline:
        """
        Create a report outline from research data.

        Args:
            title: Report title
            research_data: List of research findings/data
            metadata: Optional additional metadata

        Returns:
            ReportOutline ready for content generation
        """
        sections = self.get_sections()

        outline = ReportOutline(
            title=title,
            report_type=self.report_type,
            sections=sections,
            metadata=metadata or {}
        )

        # Add research context to metadata
        outline.metadata["research_data_count"] = len(research_data)
        outline.metadata["template"] = self.name

        logger.info(
            "Report outline created",
            title=title,
            report_type=self.report_type.value,
            sections=len(sections)
        )

        return outline

    def get_writing_prompt(self, section: ReportSection, context: dict) -> str:
        """
        Generate a writing prompt for a section.

        Args:
            section: The section to write
            context: Context including research data, previous sections, etc.

        Returns:
            A prompt for the LLM to generate section content
        """
        instructions = self.get_section_instructions(section.section_type)

        prompt = f"""Write the "{section.title}" section for a professional report.

## Section Instructions
{instructions}

## Section Requirements
- Section Type: {section.section_type.value}
- Target Word Count: {section.word_count_target or 'No specific target'}
- Required: {'Yes' if section.is_required else 'No'}

## Context
Report Title: {context.get('title', 'Untitled')}
Report Type: {context.get('report_type', 'research')}

## Research Data
{self._format_research_data(context.get('research_data', []))}

## Previous Sections Summary
{context.get('previous_sections_summary', 'This is the first section.')}

## Writing Guidelines
1. Write in a professional, academic tone
2. Use clear, concise language
3. Support claims with evidence from the research data
4. Include specific examples and data points where relevant
5. Maintain logical flow and coherence
6. Use appropriate transitions between paragraphs

Please write the section content now:
"""
        return prompt

    def _format_research_data(self, research_data: list[str]) -> str:
        """Format research data for inclusion in prompts."""
        if not research_data:
            return "No research data available."

        formatted = []
        for i, data in enumerate(research_data[:10], 1):  # Limit to 10 items
            # Truncate very long data
            if len(data) > 2000:
                data = data[:2000] + "... [truncated]"
            formatted.append(f"[Source {i}]\n{data}\n")

        return "\n".join(formatted)

    def validate_outline(self, outline: ReportOutline) -> tuple[bool, list[str]]:
        """
        Validate a report outline.

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Check for required sections
        required_types = {s.section_type for s in self.get_sections() if s.is_required}
        present_types = {s.section_type for s in outline.sections}
        missing = required_types - present_types

        if missing:
            issues.append(f"Missing required sections: {[m.value for m in missing]}")

        # Check for empty title
        if not outline.title:
            issues.append("Report title is empty")

        return len(issues) == 0, issues

    def estimate_completion_time(self, outline: ReportOutline) -> int:
        """
        Estimate time to generate report in seconds.

        Args:
            outline: The report outline

        Returns:
            Estimated seconds to complete
        """
        # Rough estimate: 30 seconds per section
        base_time = len(outline.sections) * 30

        # Add time for longer sections
        for section in outline.sections:
            if section.word_count_target and section.word_count_target > 500:
                base_time += 20

        return base_time
