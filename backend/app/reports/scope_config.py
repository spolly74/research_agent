"""
Report Scope Configuration

Allows users to specify desired report length/scope and adjusts:
1. Section word count targets
2. Research depth (number of sources, detail level)
3. Editor instructions for content generation
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import re
import structlog

logger = structlog.get_logger(__name__)


class ReportScope(str, Enum):
    """Available report scope levels."""
    BRIEF = "brief"                 # 1-2 pages, key points only
    STANDARD = "standard"           # 3-5 pages, balanced coverage
    COMPREHENSIVE = "comprehensive" # 10-15 pages, detailed analysis
    CUSTOM = "custom"               # User-specified page count


@dataclass
class ScopeParameters:
    """Parameters derived from scope selection."""
    target_pages: int
    target_word_count: int
    min_sources: int
    max_sources: int
    section_depth: str  # "minimal", "balanced", "detailed"
    include_appendix: bool
    include_methodology: bool
    citation_detail: str  # "inline", "footnote", "full"


# Default parameters for each scope level
SCOPE_DEFAULTS = {
    ReportScope.BRIEF: ScopeParameters(
        target_pages=2,
        target_word_count=750,
        min_sources=3,
        max_sources=5,
        section_depth="minimal",
        include_appendix=False,
        include_methodology=False,
        citation_detail="inline"
    ),
    ReportScope.STANDARD: ScopeParameters(
        target_pages=4,
        target_word_count=2000,
        min_sources=5,
        max_sources=10,
        section_depth="balanced",
        include_appendix=False,
        include_methodology=True,
        citation_detail="inline"
    ),
    ReportScope.COMPREHENSIVE: ScopeParameters(
        target_pages=12,
        target_word_count=6000,
        min_sources=15,
        max_sources=25,
        section_depth="detailed",
        include_appendix=True,
        include_methodology=True,
        citation_detail="full"
    ),
}

# Words per page estimate (standard formatting)
WORDS_PER_PAGE = 500


@dataclass
class ScopeConfig:
    """
    Configures report generation based on desired scope.

    Usage:
        config = ScopeConfig(ReportScope.COMPREHENSIVE)
        scaled_template = config.scale_template(template)
        research_params = config.get_research_parameters()
        editor_instructions = config.get_editor_instructions()
    """
    scope: ReportScope
    custom_pages: Optional[int] = None
    custom_word_count: Optional[int] = None
    parameters: ScopeParameters = field(init=False)

    def __post_init__(self):
        """Initialize parameters based on scope."""
        if self.scope == ReportScope.CUSTOM:
            if self.custom_pages:
                word_count = self.custom_pages * WORDS_PER_PAGE
            elif self.custom_word_count:
                word_count = self.custom_word_count
            else:
                # Default to standard if no custom value provided
                word_count = SCOPE_DEFAULTS[ReportScope.STANDARD].target_word_count

            self.parameters = self._create_custom_parameters(word_count)
        else:
            self.parameters = SCOPE_DEFAULTS[self.scope]

        logger.info(
            "Scope configuration initialized",
            scope=self.scope.value,
            target_pages=self.parameters.target_pages,
            target_words=self.parameters.target_word_count
        )

    def _create_custom_parameters(self, word_count: int) -> ScopeParameters:
        """Create parameters for custom word count."""
        pages = max(1, word_count // WORDS_PER_PAGE)

        # Scale sources based on length
        if pages <= 2:
            min_sources, max_sources = 3, 5
            depth = "minimal"
        elif pages <= 5:
            min_sources, max_sources = 5, 10
            depth = "balanced"
        elif pages <= 10:
            min_sources, max_sources = 10, 15
            depth = "balanced"
        else:
            min_sources, max_sources = 15, 25
            depth = "detailed"

        return ScopeParameters(
            target_pages=pages,
            target_word_count=word_count,
            min_sources=min_sources,
            max_sources=max_sources,
            section_depth=depth,
            include_appendix=pages > 8,
            include_methodology=pages > 2,
            citation_detail="full" if pages > 8 else "inline"
        )

    def get_word_count_multiplier(self) -> float:
        """
        Get multiplier to apply to template word counts.

        Based on standard template targeting ~2000 words.
        """
        standard_words = SCOPE_DEFAULTS[ReportScope.STANDARD].target_word_count
        return self.parameters.target_word_count / standard_words

    def scale_section_word_count(self, original_count: Optional[int]) -> Optional[int]:
        """Scale a section's word count target based on scope."""
        if original_count is None:
            return None

        multiplier = self.get_word_count_multiplier()
        scaled = int(original_count * multiplier)

        # Ensure minimum reasonable word count
        return max(50, scaled)

    def get_research_parameters(self) -> dict:
        """
        Get parameters to guide research depth.

        Returns dict with:
        - min_sources: Minimum sources to gather
        - max_sources: Maximum sources to gather
        - depth: Level of detail to extract from each source
        - focus: What to prioritize in research
        """
        return {
            "min_sources": self.parameters.min_sources,
            "max_sources": self.parameters.max_sources,
            "depth": self.parameters.section_depth,
            "focus": self._get_research_focus()
        }

    def _get_research_focus(self) -> str:
        """Get research focus based on scope."""
        if self.scope == ReportScope.BRIEF:
            return "key_facts"  # Just the essential facts
        elif self.scope == ReportScope.STANDARD:
            return "balanced"   # Facts + some analysis
        else:
            return "comprehensive"  # Facts, analysis, context, examples

    def get_editor_instructions(self) -> str:
        """
        Get scope-specific instructions for the editor agent.

        These instructions guide content generation style and depth.
        """
        if self.scope == ReportScope.BRIEF:
            return """
## Scope: Brief Report (1-2 pages)

Write a concise executive summary style report:
- Focus only on the most critical findings
- Use bullet points for key takeaways
- Limit each section to 1-2 short paragraphs
- Skip detailed methodology and background
- Include only essential citations
- Target approximately {word_count} words total

Prioritize clarity and actionable insights over comprehensive coverage.
""".format(word_count=self.parameters.target_word_count)

        elif self.scope == ReportScope.STANDARD:
            return """
## Scope: Standard Report (3-5 pages)

Write a balanced professional report:
- Cover all key findings with supporting evidence
- Include brief methodology section
- Provide context for each major point
- Use a mix of paragraphs and bullet points
- Include relevant citations throughout
- Target approximately {word_count} words total

Balance thoroughness with readability.
""".format(word_count=self.parameters.target_word_count)

        else:  # COMPREHENSIVE or CUSTOM with high word count
            return """
## Scope: Comprehensive Report (10+ pages)

Write a detailed, in-depth research report:
- Provide thorough coverage of all aspects
- Include detailed methodology and background
- Analyze findings from multiple perspectives
- Include examples and case studies where relevant
- Provide detailed citations with context
- Include appendix for supplementary data
- Target approximately {word_count} words total

Aim for academic-level depth and rigor.
""".format(word_count=self.parameters.target_word_count)

    def should_include_section(self, section_type: str) -> bool:
        """Determine if a section should be included based on scope."""
        # Sections that are always included
        always_include = {"title", "executive_summary", "findings", "conclusion"}

        # Sections that require at least standard scope
        standard_sections = {"introduction", "analysis", "recommendations"}

        # Sections that require comprehensive scope
        comprehensive_sections = {"methodology", "background", "appendix", "discussion"}

        section_lower = section_type.lower()

        if section_lower in always_include:
            return True

        if section_lower in comprehensive_sections:
            return self.scope in [ReportScope.COMPREHENSIVE, ReportScope.CUSTOM] and \
                   self.parameters.target_pages > 5

        if section_lower in standard_sections:
            return self.scope != ReportScope.BRIEF

        return True  # Include unknown sections by default

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "scope": self.scope.value,
            "target_pages": self.parameters.target_pages,
            "target_word_count": self.parameters.target_word_count,
            "min_sources": self.parameters.min_sources,
            "max_sources": self.parameters.max_sources,
            "section_depth": self.parameters.section_depth,
            "include_appendix": self.parameters.include_appendix,
            "include_methodology": self.parameters.include_methodology,
            "word_count_multiplier": self.get_word_count_multiplier()
        }


def detect_scope_from_query(query: str) -> tuple[ReportScope, Optional[int]]:
    """
    Detect desired scope from natural language query.

    Args:
        query: The user's research query

    Returns:
        Tuple of (ReportScope, optional custom page count)

    Examples:
        "Give me a brief overview of..." -> (BRIEF, None)
        "I need a comprehensive analysis..." -> (COMPREHENSIVE, None)
        "Write a 10 page report on..." -> (CUSTOM, 10)
        "Research topic X" -> (STANDARD, None)
    """
    query_lower = query.lower()

    # Check for page ranges first (e.g., "4-5 page", "4 to 5 pages")
    range_patterns = [
        r'(\d+)\s*[-–—]\s*(\d+)\s*page',  # 4-5 page, 4–5 pages
        r'(\d+)\s*to\s*(\d+)\s*page',      # 4 to 5 pages
    ]

    for pattern in range_patterns:
        match = re.search(pattern, query_lower)
        if match:
            # Use the higher number in the range as target
            pages = max(int(match.group(1)), int(match.group(2)))
            logger.info("Detected page range from query", pages=pages)
            return ReportScope.CUSTOM, pages

    # Check for explicit page count (single number)
    page_patterns = [
        r'(\d+)\s*page',
        r'(\d+)-page',
        r'(\d+)\s*pg',
    ]

    for pattern in page_patterns:
        match = re.search(pattern, query_lower)
        if match:
            pages = int(match.group(1))
            logger.info("Detected custom page count from query", pages=pages)
            return ReportScope.CUSTOM, pages

    # Check for explicit word count
    word_patterns = [
        r'(\d+)\s*words?',
        r'(\d+)\s*word',
    ]

    for pattern in word_patterns:
        match = re.search(pattern, query_lower)
        if match:
            words = int(match.group(1))
            pages = max(1, words // WORDS_PER_PAGE)
            logger.info("Detected custom word count from query", words=words)
            return ReportScope.CUSTOM, pages

    # Check for brief indicators
    brief_keywords = [
        'brief', 'short', 'quick', 'summary', 'overview',
        'concise', 'succinct', 'highlights', 'key points',
        'tldr', 'tl;dr', '1-2 page', 'one page', 'two page'
    ]

    if any(kw in query_lower for kw in brief_keywords):
        logger.info("Detected brief scope from keywords")
        return ReportScope.BRIEF, None

    # Check for comprehensive indicators
    comprehensive_keywords = [
        'comprehensive', 'detailed', 'in-depth', 'thorough',
        'extensive', 'complete', 'full', 'exhaustive',
        'deep dive', 'deep-dive', 'analysis', 'white paper',
        'whitepaper', 'long-form', 'long form'
    ]

    if any(kw in query_lower for kw in comprehensive_keywords):
        logger.info("Detected comprehensive scope from keywords")
        return ReportScope.COMPREHENSIVE, None

    # Default to standard
    logger.info("Using default standard scope")
    return ReportScope.STANDARD, None


def create_scope_config(
    scope: Optional[str] = None,
    pages: Optional[int] = None,
    word_count: Optional[int] = None,
    query: Optional[str] = None
) -> ScopeConfig:
    """
    Factory function to create a ScopeConfig.

    Args:
        scope: Explicit scope string ("brief", "standard", "comprehensive", "custom")
        pages: Custom page count (used with scope="custom" or alone)
        word_count: Custom word count (alternative to pages)
        query: If provided and no scope given, detect scope from query

    Returns:
        Configured ScopeConfig instance
    """
    # If explicit scope provided, use it
    if scope:
        scope_enum = ReportScope(scope.lower())
        return ScopeConfig(
            scope=scope_enum,
            custom_pages=pages,
            custom_word_count=word_count
        )

    # If custom pages/words provided without scope
    if pages or word_count:
        return ScopeConfig(
            scope=ReportScope.CUSTOM,
            custom_pages=pages,
            custom_word_count=word_count
        )

    # If query provided, detect from it
    if query:
        detected_scope, detected_pages = detect_scope_from_query(query)
        return ScopeConfig(
            scope=detected_scope,
            custom_pages=detected_pages
        )

    # Default to standard
    return ScopeConfig(scope=ReportScope.STANDARD)
