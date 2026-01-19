"""
Citation Manager

Handles citation tracking, formatting, and bibliography generation with:
- Multiple citation styles (APA, MLA, Chicago)
- URL and source extraction
- Automatic citation formatting
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger(__name__)


class CitationStyle(str, Enum):
    """Supported citation styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"


@dataclass
class Citation:
    """A single citation/source."""
    id: str  # Unique identifier
    url: Optional[str] = None
    title: str = ""
    author: str = ""
    date_published: Optional[datetime] = None
    date_accessed: datetime = field(default_factory=datetime.now)
    publisher: str = ""
    source_type: str = "web"  # web, book, journal, report
    page_numbers: str = ""
    volume: str = ""
    issue: str = ""
    doi: str = ""
    raw_content: str = ""  # Original content for reference

    def to_dict(self) -> dict:
        """Convert citation to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "date_published": self.date_published.isoformat() if self.date_published else None,
            "date_accessed": self.date_accessed.isoformat(),
            "publisher": self.publisher,
            "source_type": self.source_type,
            "doi": self.doi
        }


class CitationManager:
    """
    Manages citations throughout the research and report generation process.

    Features:
    - Extract citations from source content
    - Format citations in multiple styles
    - Generate bibliographies
    - Track citation usage
    """

    def __init__(self, style: CitationStyle = CitationStyle.APA):
        self.style = style
        self._citations: dict[str, Citation] = {}
        self._citation_count = 0
        self._usage: dict[str, int] = {}  # Citation ID -> usage count

    def add_citation(self, citation: Citation) -> str:
        """
        Add a citation to the manager.

        Args:
            citation: The citation to add

        Returns:
            The citation ID
        """
        if not citation.id:
            self._citation_count += 1
            citation.id = f"cite_{self._citation_count}"

        self._citations[citation.id] = citation
        self._usage[citation.id] = 0

        logger.debug("Citation added", citation_id=citation.id, title=citation.title[:50])
        return citation.id

    def create_citation_from_url(self, url: str, content: str = "", title: str = "") -> Citation:
        """
        Create a citation from a URL and optional content.

        Args:
            url: Source URL
            content: Page content for metadata extraction
            title: Optional title override

        Returns:
            Created Citation object
        """
        self._citation_count += 1
        citation_id = f"cite_{self._citation_count}"

        # Extract domain for publisher
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # Try to extract title from content if not provided
        if not title and content:
            title = self._extract_title(content)

        # Try to extract author
        author = self._extract_author(content) if content else ""

        # Try to extract date
        date_published = self._extract_date(content) if content else None

        citation = Citation(
            id=citation_id,
            url=url,
            title=title or f"Content from {domain}",
            author=author,
            date_published=date_published,
            publisher=domain,
            source_type="web",
            raw_content=content[:5000] if content else ""
        )

        self.add_citation(citation)
        return citation

    def _extract_title(self, content: str) -> str:
        """Extract title from content."""
        # Try to find a title pattern
        patterns = [
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'^#\s+(.+)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                title = match.group(1).strip()
                # Clean up HTML entities
                title = re.sub(r'&[a-z]+;', ' ', title)
                title = re.sub(r'\s+', ' ', title)
                return title[:200]  # Limit length

        # Fallback: use first line
        first_line = content.split('\n')[0].strip()
        return first_line[:100] if first_line else "Untitled"

    def _extract_author(self, content: str) -> str:
        """Extract author from content."""
        patterns = [
            r'(?:by|author|written by)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            r'"author":\s*"([^"]+)"',
            r'<meta[^>]+name="author"[^>]+content="([^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_date(self, content: str) -> Optional[datetime]:
        """Extract publication date from content."""
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # ISO date
            r'(?:published|posted|date)[:\s]+(\w+ \d{1,2},? \d{4})',
            r'"datePublished":\s*"([^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try ISO format first
                    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                        return datetime.strptime(date_str, '%Y-%m-%d')
                    # Try other formats
                    for fmt in ['%B %d, %Y', '%B %d %Y', '%b %d, %Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except:
                            continue
                except:
                    pass

        return None

    def get_citation(self, citation_id: str) -> Optional[Citation]:
        """Get a citation by ID."""
        return self._citations.get(citation_id)

    def get_all_citations(self) -> list[Citation]:
        """Get all citations."""
        return list(self._citations.values())

    def mark_used(self, citation_id: str) -> None:
        """Mark a citation as used in the document."""
        if citation_id in self._usage:
            self._usage[citation_id] += 1

    def format_citation(self, citation: Citation, style: Optional[CitationStyle] = None) -> str:
        """
        Format a citation in the specified style.

        Args:
            citation: The citation to format
            style: Citation style (defaults to manager's style)

        Returns:
            Formatted citation string
        """
        style = style or self.style

        if style == CitationStyle.APA:
            return self._format_apa(citation)
        elif style == CitationStyle.MLA:
            return self._format_mla(citation)
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago(citation)
        elif style == CitationStyle.IEEE:
            return self._format_ieee(citation)
        else:
            return self._format_apa(citation)

    def _format_apa(self, citation: Citation) -> str:
        """Format citation in APA style."""
        parts = []

        # Author
        if citation.author:
            parts.append(f"{citation.author}.")
        else:
            parts.append(f"{citation.publisher}.")

        # Date
        if citation.date_published:
            parts.append(f"({citation.date_published.year}).")
        else:
            parts.append("(n.d.).")

        # Title
        if citation.title:
            parts.append(f"*{citation.title}*.")

        # Source/Publisher
        if citation.publisher and citation.author:
            parts.append(f"{citation.publisher}.")

        # URL
        if citation.url:
            parts.append(f"Retrieved from {citation.url}")

        return " ".join(parts)

    def _format_mla(self, citation: Citation) -> str:
        """Format citation in MLA style."""
        parts = []

        # Author
        if citation.author:
            parts.append(f"{citation.author}.")

        # Title in quotes for web
        if citation.title:
            parts.append(f'"{citation.title}."')

        # Publisher/Website
        if citation.publisher:
            parts.append(f"*{citation.publisher}*,")

        # Date
        if citation.date_published:
            parts.append(f"{citation.date_published.strftime('%d %b. %Y')},")

        # URL
        if citation.url:
            parts.append(f"{citation.url}.")

        # Access date
        parts.append(f"Accessed {citation.date_accessed.strftime('%d %b. %Y')}.")

        return " ".join(parts)

    def _format_chicago(self, citation: Citation) -> str:
        """Format citation in Chicago style."""
        parts = []

        # Author
        if citation.author:
            parts.append(f"{citation.author}.")

        # Title in quotes
        if citation.title:
            parts.append(f'"{citation.title}."')

        # Publisher
        if citation.publisher:
            parts.append(f"{citation.publisher}.")

        # Date
        if citation.date_published:
            parts.append(f"{citation.date_published.strftime('%B %d, %Y')}.")

        # URL
        if citation.url:
            parts.append(f"{citation.url}.")

        return " ".join(parts)

    def _format_ieee(self, citation: Citation) -> str:
        """Format citation in IEEE style."""
        parts = []

        # Author
        if citation.author:
            # IEEE uses initials first
            parts.append(f"{citation.author},")

        # Title in quotes
        if citation.title:
            parts.append(f'"{citation.title},"')

        # Publisher
        if citation.publisher:
            parts.append(f"*{citation.publisher}*,")

        # Date
        if citation.date_published:
            parts.append(f"{citation.date_published.year}.")

        # URL with access date
        if citation.url:
            parts.append(f"[Online]. Available: {citation.url}.")
            parts.append(f"[Accessed: {citation.date_accessed.strftime('%b. %d, %Y')}].")

        return " ".join(parts)

    def format_inline_citation(self, citation: Citation, style: Optional[CitationStyle] = None) -> str:
        """
        Format an inline citation reference.

        Args:
            citation: The citation
            style: Citation style

        Returns:
            Inline citation (e.g., "(Smith, 2023)" or "[1]")
        """
        style = style or self.style

        if style == CitationStyle.APA:
            author = citation.author.split()[-1] if citation.author else citation.publisher
            year = citation.date_published.year if citation.date_published else "n.d."
            return f"({author}, {year})"

        elif style == CitationStyle.MLA:
            author = citation.author.split()[-1] if citation.author else citation.publisher
            return f"({author})"

        elif style == CitationStyle.IEEE:
            # Find citation number
            citation_list = list(self._citations.keys())
            idx = citation_list.index(citation.id) + 1 if citation.id in citation_list else 0
            return f"[{idx}]"

        else:
            return f"[{citation.id}]"

    def generate_bibliography(self, style: Optional[CitationStyle] = None, used_only: bool = True) -> str:
        """
        Generate a formatted bibliography.

        Args:
            style: Citation style
            used_only: Only include citations that were used

        Returns:
            Formatted bibliography as string
        """
        style = style or self.style
        citations = self.get_all_citations()

        if used_only:
            citations = [c for c in citations if self._usage.get(c.id, 0) > 0]

        if not citations:
            return "No citations."

        # Sort alphabetically by author/publisher
        citations.sort(key=lambda c: (c.author or c.publisher or "").lower())

        lines = []
        for i, citation in enumerate(citations, 1):
            formatted = self.format_citation(citation, style)

            if style == CitationStyle.IEEE:
                lines.append(f"[{i}] {formatted}")
            else:
                lines.append(formatted)

        return "\n\n".join(lines)

    def get_status(self) -> dict:
        """Get citation manager status."""
        return {
            "total_citations": len(self._citations),
            "used_citations": sum(1 for u in self._usage.values() if u > 0),
            "style": self.style.value,
            "citations": [c.to_dict() for c in self._citations.values()]
        }
