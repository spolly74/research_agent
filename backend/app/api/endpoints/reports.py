"""
Report Generation API endpoints.

Provides endpoints for:
- Creating report outlines
- Listing available templates
- Generating formatted reports
- Managing citations
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

router = APIRouter()


class ReportOutlineRequest(BaseModel):
    """Request to create a report outline."""
    title: str = Field(..., description="Report title")
    research_data: list[str] = Field(..., description="List of research findings/data")
    report_type: Optional[str] = Field(default=None, description="Report type: research, technical, executive")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
    scope: Optional[str] = Field(default=None, description="Report scope: brief, standard, comprehensive")
    target_pages: Optional[int] = Field(default=None, description="Custom target page count")
    target_word_count: Optional[int] = Field(default=None, description="Custom target word count")


class ReportFormatRequest(BaseModel):
    """Request to format a report."""
    title: str = Field(..., description="Report title")
    research_data: list[str] = Field(..., description="List of research findings/data")
    report_type: Optional[str] = Field(default=None, description="Report type")
    format: str = Field(default="markdown", description="Output format: markdown or html")
    include_toc: bool = Field(default=True, description="Include table of contents")
    scope: Optional[str] = Field(default=None, description="Report scope: brief, standard, comprehensive")
    target_pages: Optional[int] = Field(default=None, description="Custom target page count")
    target_word_count: Optional[int] = Field(default=None, description="Custom target word count")


class CitationAddRequest(BaseModel):
    """Request to add a citation."""
    url: str = Field(..., description="Source URL")
    title: Optional[str] = Field(default=None, description="Source title")
    author: Optional[str] = Field(default=None, description="Author name")
    publication_date: Optional[str] = Field(default=None, description="Publication date")
    accessed_date: Optional[str] = Field(default=None, description="Date accessed")
    publisher: Optional[str] = Field(default=None, description="Publisher name")
    content_snippet: Optional[str] = Field(default=None, description="Content snippet for context")


class CitationStyleRequest(BaseModel):
    """Request to change citation style."""
    style: str = Field(..., description="Citation style: apa, mla, chicago, ieee")


@router.get("/scopes")
def list_scopes() -> dict[str, Any]:
    """
    List available report scope levels.

    Returns information about each scope including:
    - Target page count and word count
    - Number of sources expected
    - Section depth
    """
    from app.reports.scope_config import ReportScope, SCOPE_DEFAULTS

    scopes = {}
    for scope, params in SCOPE_DEFAULTS.items():
        scopes[scope.value] = {
            "name": scope.value.title(),
            "target_pages": params.target_pages,
            "target_word_count": params.target_word_count,
            "min_sources": params.min_sources,
            "max_sources": params.max_sources,
            "section_depth": params.section_depth,
            "description": _get_scope_description(scope)
        }

    return {
        "scopes": scopes,
        "count": len(scopes),
        "note": "Use 'custom' scope with target_pages or target_word_count for custom lengths"
    }


def _get_scope_description(scope) -> str:
    """Get description for a scope level."""
    from app.reports.scope_config import ReportScope

    descriptions = {
        ReportScope.BRIEF: "Quick 1-2 page summary with key points only",
        ReportScope.STANDARD: "Balanced 3-5 page report with full coverage",
        ReportScope.COMPREHENSIVE: "Detailed 10-15 page analysis with thorough research"
    }
    return descriptions.get(scope, "Custom scope")


@router.get("/templates")
def list_templates() -> dict[str, Any]:
    """
    List all available report templates.

    Returns information about each template including:
    - Template name and description
    - Sections included
    - Best use cases
    """
    from app.reports.templates.base import ReportType

    templates = {
        "research": {
            "name": "Research Report",
            "description": "Comprehensive research report with detailed analysis",
            "sections": [
                "Title", "Abstract", "Executive Summary", "Introduction",
                "Methodology", "Findings", "Analysis", "Discussion",
                "Conclusion", "References"
            ],
            "best_for": "In-depth research, academic papers, detailed analysis"
        },
        "technical": {
            "name": "Technical Analysis",
            "description": "Technical documentation with architecture and implementation details",
            "sections": [
                "Title", "Executive Summary", "Background", "Technical Overview",
                "Architecture Analysis", "Implementation Details", "Performance Analysis",
                "Security Considerations", "Recommendations", "References"
            ],
            "best_for": "Technical documentation, system analysis, architecture reviews"
        },
        "executive": {
            "name": "Executive Summary",
            "description": "Concise briefing for executive audience",
            "sections": [
                "Title", "Overview", "Key Findings", "Strategic Implications",
                "Recommendations", "Next Steps"
            ],
            "best_for": "Quick briefings, stakeholder updates, decision support"
        }
    }

    return {
        "templates": templates,
        "count": len(templates)
    }


@router.get("/templates/{template_type}")
def get_template(template_type: str) -> dict[str, Any]:
    """
    Get detailed information about a specific template.
    """
    from app.reports.templates.base import ReportType
    from app.reports.generator import ReportGenerator

    # Map string to enum
    type_map = {
        "research": ReportType.RESEARCH,
        "technical": ReportType.TECHNICAL,
        "executive": ReportType.EXECUTIVE,
    }

    if template_type.lower() not in type_map:
        raise HTTPException(status_code=404, detail=f"Template '{template_type}' not found")

    generator = ReportGenerator()
    template = generator.get_template(type_map[template_type.lower()])
    sections = template.get_sections()

    return {
        "name": template.name,
        "description": template.description,
        "report_type": template.report_type.value,
        "sections": [
            {
                "type": s.section_type.value,
                "title": s.title,
                "order": s.order,
                "is_required": s.is_required,
                "word_count_target": s.word_count_target,
                "notes": s.notes
            }
            for s in sections
        ]
    }


@router.post("/outline")
def create_outline(request: ReportOutlineRequest) -> dict[str, Any]:
    """
    Create a report outline from research data.

    Returns the outline structure without generated content.
    Content must be generated separately using the editor agent.

    Scope can be specified as:
    - "brief": 1-2 pages, key points only
    - "standard": 3-5 pages, balanced coverage
    - "comprehensive": 10-15 pages, detailed analysis
    - Or use target_pages/target_word_count for custom length
    """
    from app.reports.templates.base import ReportType
    from app.reports.generator import ReportGenerator
    from app.reports.scope_config import create_scope_config, ReportScope

    # Map string to enum if provided
    report_type = None
    if request.report_type:
        type_map = {
            "research": ReportType.RESEARCH,
            "technical": ReportType.TECHNICAL,
            "executive": ReportType.EXECUTIVE,
        }
        if request.report_type.lower() not in type_map:
            raise HTTPException(status_code=400, detail=f"Invalid report type '{request.report_type}'")
        report_type = type_map[request.report_type.lower()]

    # Create scope configuration
    scope_config = create_scope_config(
        scope=request.scope,
        pages=request.target_pages,
        word_count=request.target_word_count,
        query=request.title
    )

    generator = ReportGenerator(scope=scope_config)
    outline = generator.create_outline(
        title=request.title,
        research_data=request.research_data,
        report_type=report_type,
        metadata=request.metadata
    )

    return {
        "success": True,
        "outline": outline.to_dict(),
        "scope": scope_config.to_dict(),
        "generator_status": generator.get_status()
    }


@router.post("/format")
def format_report(request: ReportFormatRequest) -> dict[str, Any]:
    """
    Create and format a report structure.

    Note: This creates the outline structure but does NOT generate content.
    For full content generation, use the /api/chat endpoint with a report request.

    Supports scope configuration for controlling report length.
    """
    from app.reports.templates.base import ReportType
    from app.reports.generator import ReportGenerator
    from app.reports.scope_config import create_scope_config

    # Map string to enum if provided
    report_type = None
    if request.report_type:
        type_map = {
            "research": ReportType.RESEARCH,
            "technical": ReportType.TECHNICAL,
            "executive": ReportType.EXECUTIVE,
        }
        if request.report_type.lower() in type_map:
            report_type = type_map[request.report_type.lower()]

    # Create scope configuration
    scope_config = create_scope_config(
        scope=request.scope,
        pages=request.target_pages,
        word_count=request.target_word_count,
        query=request.title
    )

    generator = ReportGenerator(scope=scope_config)
    outline = generator.create_outline(
        title=request.title,
        research_data=request.research_data,
        report_type=report_type
    )

    # Format based on requested format
    if request.format.lower() == "html":
        formatted = generator.format_as_html(outline, include_toc=request.include_toc)
    else:
        formatted = generator.format_as_markdown(outline, include_toc=request.include_toc)

    return {
        "success": True,
        "format": request.format,
        "report_type": outline.report_type.value,
        "scope": scope_config.to_dict(),
        "content": formatted,
        "word_count": outline.total_word_count(),
        "sections": len(outline.sections)
    }


@router.get("/citation-styles")
def list_citation_styles() -> dict[str, Any]:
    """
    List available citation styles.
    """
    from app.reports.citation_manager import CitationStyle

    styles = {
        "apa": {
            "name": "APA (7th Edition)",
            "description": "American Psychological Association style",
            "example": "Author, A. A. (Year). Title of work. Publisher."
        },
        "mla": {
            "name": "MLA (9th Edition)",
            "description": "Modern Language Association style",
            "example": "Author. \"Title of Work.\" Publisher, Year."
        },
        "chicago": {
            "name": "Chicago Manual of Style",
            "description": "Chicago/Turabian style",
            "example": "Author. Title of Work. Publisher, Year."
        },
        "ieee": {
            "name": "IEEE",
            "description": "Institute of Electrical and Electronics Engineers style",
            "example": "[1] A. Author, \"Title,\" Publisher, Year."
        }
    }

    return {
        "styles": styles,
        "count": len(styles)
    }


@router.post("/citations")
def add_citation(request: CitationAddRequest) -> dict[str, Any]:
    """
    Add a citation to the citation manager.

    Returns the citation ID and formatted citation.
    """
    from app.reports.citation_manager import CitationManager, CitationStyle

    manager = CitationManager()

    # Create citation from URL
    citation_id = manager.create_citation_from_url(
        url=request.url,
        content_snippet=request.content_snippet or ""
    )

    # Update citation with additional info if provided
    citation = manager.get_citation(citation_id)
    if citation:
        if request.title:
            citation.title = request.title
        if request.author:
            citation.author = request.author
        if request.publisher:
            citation.publisher = request.publisher

    # Format the citation
    formatted = manager.format_citation(citation_id)

    return {
        "success": True,
        "citation_id": citation_id,
        "formatted": formatted,
        "citation": citation.to_dict() if citation else None
    }


@router.get("/citations")
def list_citations() -> dict[str, Any]:
    """
    List all citations in the current session.

    Note: Citations are session-specific and not persisted.
    """
    from app.reports.citation_manager import CitationManager

    manager = CitationManager()
    citations = manager.get_all_citations()

    return {
        "citations": [c.to_dict() for c in citations],
        "count": len(citations),
        "style": manager.style.value
    }


@router.post("/citations/style")
def set_citation_style(request: CitationStyleRequest) -> dict[str, Any]:
    """
    Set the citation formatting style.
    """
    from app.reports.citation_manager import CitationManager, CitationStyle

    style_map = {
        "apa": CitationStyle.APA,
        "mla": CitationStyle.MLA,
        "chicago": CitationStyle.CHICAGO,
        "ieee": CitationStyle.IEEE,
    }

    if request.style.lower() not in style_map:
        raise HTTPException(status_code=400, detail=f"Invalid citation style '{request.style}'")

    manager = CitationManager(style=style_map[request.style.lower()])

    return {
        "success": True,
        "style": request.style,
        "message": f"Citation style set to {request.style.upper()}"
    }


@router.post("/bibliography")
def generate_bibliography(request: CitationStyleRequest = None) -> dict[str, Any]:
    """
    Generate a formatted bibliography from all citations.
    """
    from app.reports.citation_manager import CitationManager, CitationStyle

    style = CitationStyle.APA
    if request and request.style:
        style_map = {
            "apa": CitationStyle.APA,
            "mla": CitationStyle.MLA,
            "chicago": CitationStyle.CHICAGO,
            "ieee": CitationStyle.IEEE,
        }
        style = style_map.get(request.style.lower(), CitationStyle.APA)

    manager = CitationManager(style=style)
    bibliography = manager.generate_bibliography(used_only=False)

    return {
        "success": True,
        "style": style.value,
        "bibliography": bibliography,
        "citation_count": len(manager.get_all_citations())
    }


@router.get("/analyze-query")
def analyze_query(query: str) -> dict[str, Any]:
    """
    Analyze a query to determine the best report type, format, and scope.
    """
    from app.reports.generator import ReportGenerator
    from app.agents.nodes.editor import determine_report_format
    from app.reports.scope_config import detect_scope_from_query, create_scope_config

    generator = ReportGenerator()

    # Determine report type
    report_type = generator.select_template(query, [])

    # Determine format (brief vs full report)
    response_format = determine_report_format(query, [])

    # Detect scope from query
    detected_scope, custom_pages = detect_scope_from_query(query)
    scope_config = create_scope_config(query=query)

    return {
        "query": query,
        "recommended_report_type": report_type.value,
        "recommended_format": response_format,
        "recommended_scope": {
            "scope": detected_scope.value,
            "custom_pages": custom_pages,
            "target_word_count": scope_config.parameters.target_word_count,
            "target_pages": scope_config.parameters.target_pages
        },
        "analysis": {
            "suggests_full_report": response_format == "full_report",
            "template_match": report_type.value,
            "scope_match": detected_scope.value,
            "reasoning": _get_recommendation_reasoning(query, report_type.value, response_format, detected_scope.value)
        }
    }


def _get_recommendation_reasoning(query: str, report_type: str, response_format: str, scope: str = "standard") -> str:
    """Generate reasoning for the recommendation."""
    reasons = []

    query_lower = query.lower()

    if response_format == "full_report":
        if any(kw in query_lower for kw in ['research', 'analysis', 'comprehensive']):
            reasons.append("Query contains keywords suggesting detailed research")
        else:
            reasons.append("Query complexity suggests full report format")

    if report_type == "technical":
        reasons.append("Query contains technical keywords (architecture, implementation, etc.)")
    elif report_type == "executive":
        reasons.append("Query suggests executive-level summary")
    else:
        reasons.append("Standard research report format recommended")

    # Add scope reasoning
    if scope == "brief":
        reasons.append("Brief scope detected from keywords like 'quick', 'summary', 'overview'")
    elif scope == "comprehensive":
        reasons.append("Comprehensive scope detected from keywords like 'detailed', 'in-depth', 'thorough'")
    elif scope == "custom":
        reasons.append("Custom scope detected from explicit page/word count in query")

    return "; ".join(reasons) if reasons else "Default recommendation based on query structure"
