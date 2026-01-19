"""
Markdown Formatter

Formats reports as clean, professional Markdown documents.
"""

from datetime import datetime
from typing import Optional
from app.reports.templates.base import ReportOutline, ReportSection, SectionType
from app.reports.citation_manager import CitationManager


class MarkdownFormatter:
    """Formats reports as Markdown documents."""

    def __init__(self, citation_manager: Optional[CitationManager] = None):
        self.citation_manager = citation_manager

    def format(self, outline: ReportOutline) -> str:
        """
        Format a complete report outline as Markdown.

        Args:
            outline: The report outline with content

        Returns:
            Formatted Markdown string
        """
        lines = []

        # Add metadata header
        lines.append(self._format_frontmatter(outline))
        lines.append("")

        # Process each section
        for section in sorted(outline.sections, key=lambda s: s.order):
            section_md = self._format_section(section, level=1)
            lines.append(section_md)
            lines.append("")

        # Add bibliography if citation manager provided
        if self.citation_manager:
            lines.append(self._format_bibliography())

        return "\n".join(lines)

    def _format_frontmatter(self, outline: ReportOutline) -> str:
        """Generate YAML frontmatter."""
        lines = [
            "---",
            f"title: \"{outline.title}\"",
            f"type: {outline.report_type.value}",
            f"date: {outline.created_at.strftime('%Y-%m-%d')}",
            f"author: Research Agent",
        ]

        if outline.metadata.get("keywords"):
            keywords = ", ".join(outline.metadata["keywords"])
            lines.append(f"keywords: [{keywords}]")

        lines.append("---")
        return "\n".join(lines)

    def _format_section(self, section: ReportSection, level: int = 1) -> str:
        """Format a single section as Markdown."""
        lines = []

        # Section header (skip for title section)
        if section.section_type != SectionType.TITLE:
            header_prefix = "#" * min(level, 6)
            lines.append(f"{header_prefix} {section.title}")
            lines.append("")

        # Section content
        if section.content:
            # Process content for citations
            content = self._process_citations(section.content)
            lines.append(content)
            lines.append("")

        # Subsections
        for subsection in sorted(section.subsections, key=lambda s: s.order):
            subsection_md = self._format_section(subsection, level=level + 1)
            lines.append(subsection_md)

        return "\n".join(lines)

    def _process_citations(self, content: str) -> str:
        """Process inline citations in content."""
        if not self.citation_manager:
            return content

        # Citations are marked as [cite_X] in content
        import re

        def replace_citation(match):
            cite_id = match.group(1)
            citation = self.citation_manager.get_citation(cite_id)
            if citation:
                self.citation_manager.mark_used(cite_id)
                return self.citation_manager.format_inline_citation(citation)
            return match.group(0)

        return re.sub(r'\[(cite_\d+)\]', replace_citation, content)

    def _format_bibliography(self) -> str:
        """Format the bibliography section."""
        lines = [
            "## References",
            "",
            self.citation_manager.generate_bibliography(used_only=True)
        ]
        return "\n".join(lines)

    def format_section_only(self, section: ReportSection) -> str:
        """Format just a single section (for preview)."""
        return self._format_section(section, level=1)

    def format_toc(self, outline: ReportOutline) -> str:
        """Generate a table of contents."""
        lines = ["## Table of Contents", ""]

        for section in sorted(outline.sections, key=lambda s: s.order):
            if section.section_type != SectionType.TITLE:
                # Create anchor link
                anchor = section.title.lower().replace(" ", "-").replace("&", "and")
                lines.append(f"- [{section.title}](#{anchor})")

                for subsection in section.subsections:
                    sub_anchor = subsection.title.lower().replace(" ", "-")
                    lines.append(f"  - [{subsection.title}](#{sub_anchor})")

        return "\n".join(lines)


def format_report_as_markdown(
    outline: ReportOutline,
    citation_manager: Optional[CitationManager] = None,
    include_toc: bool = True
) -> str:
    """
    Convenience function to format a report as Markdown.

    Args:
        outline: The report outline
        citation_manager: Optional citation manager
        include_toc: Whether to include table of contents

    Returns:
        Formatted Markdown string
    """
    formatter = MarkdownFormatter(citation_manager)

    lines = []

    # Frontmatter
    lines.append(formatter._format_frontmatter(outline))
    lines.append("")

    # Title (from first section if it's a title section)
    title_section = outline.get_section(SectionType.TITLE)
    if title_section and title_section.content:
        lines.append(title_section.content)
        lines.append("")
    else:
        lines.append(f"# {outline.title}")
        lines.append("")

    # Table of contents
    if include_toc:
        lines.append(formatter.format_toc(outline))
        lines.append("")
        lines.append("---")
        lines.append("")

    # Main content
    for section in sorted(outline.sections, key=lambda s: s.order):
        if section.section_type != SectionType.TITLE:
            lines.append(formatter._format_section(section))
            lines.append("")

    # Bibliography
    if citation_manager:
        lines.append(formatter._format_bibliography())

    return "\n".join(lines)
