"""
HTML Formatter

Formats reports as styled HTML documents suitable for web viewing or PDF conversion.
"""

import html
import re
from datetime import datetime
from typing import Optional
from app.reports.templates.base import ReportOutline, ReportSection, SectionType
from app.reports.citation_manager import CitationManager


# Professional HTML template with embedded CSS
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --text-color: #333;
            --light-gray: #f5f5f5;
            --border-color: #e0e0e0;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.8;
            color: var(--text-color);
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }}

        /* Title Page */
        .title-page {{
            text-align: center;
            padding: 60px 0;
            margin-bottom: 40px;
            border-bottom: 2px solid var(--primary-color);
        }}

        .title-page h1 {{
            font-size: 2.5em;
            color: var(--primary-color);
            margin-bottom: 20px;
            line-height: 1.3;
        }}

        .title-page .subtitle {{
            font-size: 1.2em;
            color: #666;
            font-style: italic;
        }}

        .title-page .meta {{
            margin-top: 40px;
            color: #888;
        }}

        /* Table of Contents */
        .toc {{
            background: var(--light-gray);
            padding: 30px;
            margin: 40px 0;
            border-radius: 8px;
        }}

        .toc h2 {{
            font-size: 1.3em;
            margin-bottom: 20px;
            color: var(--primary-color);
        }}

        .toc ul {{
            list-style: none;
        }}

        .toc li {{
            margin: 10px 0;
        }}

        .toc a {{
            color: var(--secondary-color);
            text-decoration: none;
        }}

        .toc a:hover {{
            text-decoration: underline;
        }}

        .toc .sub-item {{
            margin-left: 20px;
            font-size: 0.9em;
        }}

        /* Sections */
        section {{
            margin: 40px 0;
        }}

        h2 {{
            font-size: 1.8em;
            color: var(--primary-color);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}

        h3 {{
            font-size: 1.4em;
            color: var(--primary-color);
            margin: 30px 0 15px 0;
        }}

        h4 {{
            font-size: 1.2em;
            color: #444;
            margin: 25px 0 10px 0;
        }}

        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}

        /* Lists */
        ul, ol {{
            margin: 15px 0 15px 30px;
        }}

        li {{
            margin: 8px 0;
        }}

        /* Blockquotes */
        blockquote {{
            border-left: 4px solid var(--secondary-color);
            padding: 15px 20px;
            margin: 20px 0;
            background: var(--light-gray);
            font-style: italic;
        }}

        /* Code blocks */
        code {{
            font-family: 'Consolas', 'Monaco', monospace;
            background: var(--light-gray);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}

        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
        }}

        pre code {{
            background: none;
            padding: 0;
            color: inherit;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th, td {{
            border: 1px solid var(--border-color);
            padding: 12px;
            text-align: left;
        }}

        th {{
            background: var(--light-gray);
            font-weight: bold;
        }}

        /* Citations */
        .citation {{
            color: var(--secondary-color);
            cursor: pointer;
        }}

        .citation:hover {{
            text-decoration: underline;
        }}

        /* References */
        .references {{
            margin-top: 60px;
            padding-top: 30px;
            border-top: 2px solid var(--primary-color);
        }}

        .references h2 {{
            border-bottom: none;
        }}

        .reference-item {{
            margin: 15px 0;
            padding-left: 30px;
            text-indent: -30px;
            font-size: 0.95em;
        }}

        /* Abstract/Executive Summary Box */
        .abstract {{
            background: var(--light-gray);
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
            border-left: 4px solid var(--secondary-color);
        }}

        .abstract h2 {{
            font-size: 1.2em;
            margin-bottom: 15px;
            border-bottom: none;
        }}

        /* Key Findings Box */
        .key-findings {{
            background: #fff;
            border: 2px solid var(--secondary-color);
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
        }}

        .key-findings h3 {{
            color: var(--secondary-color);
            margin-top: 0;
        }}

        /* Footer */
        footer {{
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            text-align: center;
            color: #888;
            font-size: 0.9em;
        }}

        /* Print styles */
        @media print {{
            body {{
                max-width: none;
                padding: 0;
            }}

            .toc {{
                page-break-after: always;
            }}

            section {{
                page-break-inside: avoid;
            }}

            h2 {{
                page-break-after: avoid;
            }}
        }}
    </style>
</head>
<body>
{content}
<footer>
    <p>Generated by Research Agent on {date}</p>
</footer>
</body>
</html>
"""


class HTMLFormatter:
    """Formats reports as HTML documents."""

    def __init__(self, citation_manager: Optional[CitationManager] = None):
        self.citation_manager = citation_manager

    def format(self, outline: ReportOutline, include_toc: bool = True) -> str:
        """
        Format a complete report outline as HTML.

        Args:
            outline: The report outline with content
            include_toc: Whether to include table of contents

        Returns:
            Complete HTML document as string
        """
        content_parts = []

        # Title page
        content_parts.append(self._format_title_page(outline))

        # Table of contents
        if include_toc:
            content_parts.append(self._format_toc(outline))

        # Main content sections
        for section in sorted(outline.sections, key=lambda s: s.order):
            if section.section_type not in [SectionType.TITLE]:
                content_parts.append(self._format_section(section))

        # Combine into template
        content = "\n".join(content_parts)

        return HTML_TEMPLATE.format(
            title=html.escape(outline.title),
            content=content,
            date=datetime.now().strftime("%B %d, %Y")
        )

    def _format_title_page(self, outline: ReportOutline) -> str:
        """Format the title page."""
        title_section = outline.get_section(SectionType.TITLE)

        subtitle = ""
        if title_section and title_section.content:
            subtitle = f'<p class="subtitle">{html.escape(title_section.content)}</p>'

        return f"""
<div class="title-page">
    <h1>{html.escape(outline.title)}</h1>
    {subtitle}
    <div class="meta">
        <p>{outline.report_type.value.title()} Report</p>
        <p>{outline.created_at.strftime("%B %d, %Y")}</p>
        <p>Research Agent</p>
    </div>
</div>
"""

    def _format_toc(self, outline: ReportOutline) -> str:
        """Format table of contents."""
        items = []

        for section in sorted(outline.sections, key=lambda s: s.order):
            if section.section_type not in [SectionType.TITLE]:
                anchor = self._make_anchor(section.title)
                items.append(f'<li><a href="#{anchor}">{html.escape(section.title)}</a></li>')

                for sub in section.subsections:
                    sub_anchor = self._make_anchor(sub.title)
                    items.append(
                        f'<li class="sub-item"><a href="#{sub_anchor}">{html.escape(sub.title)}</a></li>'
                    )

        return f"""
<nav class="toc">
    <h2>Table of Contents</h2>
    <ul>
        {"".join(items)}
    </ul>
</nav>
"""

    def _format_section(self, section: ReportSection, level: int = 2) -> str:
        """Format a single section as HTML."""
        anchor = self._make_anchor(section.title)
        tag = f"h{min(level, 6)}"

        # Special styling for abstract/executive summary
        section_class = ""
        if section.section_type in [SectionType.ABSTRACT, SectionType.EXECUTIVE_SUMMARY]:
            section_class = " abstract"

        # Process content
        content_html = self._process_content(section.content) if section.content else ""

        # Subsections
        subsections_html = ""
        for sub in sorted(section.subsections, key=lambda s: s.order):
            subsections_html += self._format_section(sub, level=level + 1)

        return f"""
<section id="{anchor}" class="{section_class}">
    <{tag}>{html.escape(section.title)}</{tag}>
    {content_html}
    {subsections_html}
</section>
"""

    def _process_content(self, content: str) -> str:
        """Process content into HTML."""
        # Escape HTML
        content = html.escape(content)

        # Convert markdown-style formatting
        # Bold
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        # Italic
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        # Code
        content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)

        # Convert line breaks to paragraphs
        paragraphs = content.split('\n\n')
        html_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if it's a list
            if para.startswith('- ') or para.startswith('* '):
                items = re.split(r'\n[-*] ', para)
                items[0] = items[0][2:]  # Remove first bullet
                list_items = "".join(f"<li>{item.strip()}</li>" for item in items if item.strip())
                html_paragraphs.append(f"<ul>{list_items}</ul>")
            elif re.match(r'^\d+\. ', para):
                items = re.split(r'\n\d+\. ', para)
                items[0] = re.sub(r'^\d+\. ', '', items[0])
                list_items = "".join(f"<li>{item.strip()}</li>" for item in items if item.strip())
                html_paragraphs.append(f"<ol>{list_items}</ol>")
            elif para.startswith('>'):
                quote_content = para[1:].strip()
                html_paragraphs.append(f"<blockquote>{quote_content}</blockquote>")
            else:
                html_paragraphs.append(f"<p>{para}</p>")

        # Process citations
        content = "\n".join(html_paragraphs)
        content = self._process_citations(content)

        return content

    def _process_citations(self, content: str) -> str:
        """Convert citation markers to HTML."""
        if not self.citation_manager:
            return content

        def replace_citation(match):
            cite_id = match.group(1)
            citation = self.citation_manager.get_citation(cite_id)
            if citation:
                self.citation_manager.mark_used(cite_id)
                inline = self.citation_manager.format_inline_citation(citation)
                return f'<span class="citation" title="{html.escape(citation.title)}">{inline}</span>'
            return match.group(0)

        return re.sub(r'\[(cite_\d+)\]', replace_citation, content)

    def _make_anchor(self, title: str) -> str:
        """Create a URL-safe anchor from a title."""
        anchor = title.lower()
        anchor = re.sub(r'[^a-z0-9\s-]', '', anchor)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor


def format_report_as_html(
    outline: ReportOutline,
    citation_manager: Optional[CitationManager] = None,
    include_toc: bool = True
) -> str:
    """
    Convenience function to format a report as HTML.

    Args:
        outline: The report outline
        citation_manager: Optional citation manager
        include_toc: Whether to include table of contents

    Returns:
        Complete HTML document as string
    """
    formatter = HTMLFormatter(citation_manager)
    return formatter.format(outline, include_toc=include_toc)
