"""
Enhanced Editor Agent - Generates professional long-form reports.

This agent can:
1. Analyze research data and determine report type
2. Generate structured reports with sections
3. Include proper citations
4. Output in multiple formats (Markdown, HTML)
5. Respect scope configuration for report length
"""

import structlog
from langchain_core.messages import SystemMessage, AIMessage
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType
from app.reports.generator import ReportGenerator
from app.reports.templates.base import ReportType, SectionType
from app.reports.scope_config import ScopeConfig, ReportScope, create_scope_config

logger = structlog.get_logger(__name__)


EDITOR_SYSTEM_PROMPT = """You are a Professional Editor Agent. Your job is to synthesize research findings into well-structured, professional reports.

## Your Responsibilities
1. Analyze the research data and context
2. Determine the appropriate response format (brief answer vs. full report)
3. Write clear, well-organized content
4. Include citations where appropriate
5. Ensure professional tone and quality

## Response Guidelines

### For Simple Questions (brief answers)
If the user asked a simple, direct question, provide a clear, concise answer.
- Focus on directly answering the question
- Include key facts and figures
- Keep it under 300 words unless more detail is needed

### For Research Tasks (detailed reports)
If the user requested research or analysis, create a structured report with:

**Required Sections:**
1. **Executive Summary** (2-3 sentences)
2. **Key Findings** (bullet points)
3. **Detailed Analysis** (organized by topic)
4. **Conclusion**

**Formatting Rules:**
- Use Markdown formatting
- Use headers (##, ###) to organize sections
- Use bullet points for lists
- Bold key terms and findings
- Include source attributions when possible

## Quality Standards
- Be accurate and factual
- Support claims with evidence from the research
- Acknowledge limitations or gaps in information
- Write in clear, professional language
- Avoid speculation without labeling it as such

## Citation Format
When citing sources, use this format: [Source: domain.com]

Now synthesize the research into a high-quality response:
"""


LONG_FORM_REPORT_PROMPT = """You are writing a specific section of a professional research report.

## Section: {section_title}
## Section Type: {section_type}
## Word Count Target: {word_count}

## Writing Instructions
{instructions}

## Research Data
{research_data}

## Previous Sections Summary
{previous_summary}

## Guidelines
1. Write only the content for this section
2. Maintain professional academic tone
3. Use evidence from the research data
4. Include citations as [cite_X] where X is the source number
5. Stay focused on this section's purpose
6. Target the specified word count

Write the section content now:
"""


def determine_report_format(query: str, research_data: list[str]) -> str:
    """Determine if we need a brief answer or full report."""
    query_lower = query.lower()

    # Keywords suggesting full report
    report_keywords = [
        'research', 'report', 'analysis', 'comprehensive', 'detailed',
        'investigate', 'study', 'compare', 'evaluate', 'assess',
        'in-depth', 'thorough', 'full'
    ]

    # Keywords suggesting brief answer
    brief_keywords = [
        'what is', 'who is', 'when', 'where', 'how much', 'how many',
        'quick', 'brief', 'simple', 'just tell me'
    ]

    # Check for report indicators
    for kw in report_keywords:
        if kw in query_lower:
            return "full_report"

    # Check for brief indicators
    for kw in brief_keywords:
        if kw in query_lower:
            return "brief"

    # Based on research data volume
    total_content = " ".join(research_data)
    if len(total_content) > 5000:
        return "full_report"

    return "brief"


def editor_node(state: AgentState):
    """
    Enhanced Editor Agent node.

    Analyzes research data and generates appropriate response format.
    Uses scope configuration from state if available.
    """
    messages = state["messages"]
    research_data = state.get("research_data", [])
    scope_config_dict = state.get("scope_config")

    # Get original query from first user message
    original_query = ""
    for msg in messages:
        if hasattr(msg, 'type') and msg.type == 'human':
            original_query = msg.content
            break

    # Determine response format
    response_format = determine_report_format(original_query, research_data)

    # Get or create scope config
    if scope_config_dict:
        scope_config = ScopeConfig(
            scope=ReportScope(scope_config_dict.get("scope", "standard")),
            custom_pages=scope_config_dict.get("target_pages"),
            custom_word_count=scope_config_dict.get("target_word_count")
        )
    else:
        scope_config = create_scope_config(query=original_query)

    logger.info(
        "Editor node invoked",
        message_count=len(messages),
        research_data_count=len(research_data),
        response_format=response_format,
        scope=scope_config.scope.value,
        target_words=scope_config.parameters.target_word_count
    )

    # Get LLM
    llm = get_llm(task_type=TaskType.EDITOR)

    # Build context from research
    research_context = "\n\n".join([
        f"[Source {i+1}]\n{data[:2000]}..."
        if len(data) > 2000 else f"[Source {i+1}]\n{data}"
        for i, data in enumerate(research_data[:10])
    ]) if research_data else "No research data available."

    # Get scope-specific instructions
    scope_instructions = scope_config.get_editor_instructions()

    # Create enhanced system prompt
    enhanced_prompt = EDITOR_SYSTEM_PROMPT + f"""

{scope_instructions}

## Original Query
{original_query}

## Available Research Data
{research_context}

## Response Format
Generate a {'detailed research report' if response_format == 'full_report' else 'clear, concise answer'}.
Target approximately {scope_config.parameters.target_word_count} words ({scope_config.parameters.target_pages} pages).
"""

    system_msg = SystemMessage(content=enhanced_prompt)

    # Invoke LLM
    response = llm.invoke([system_msg] + messages)
    final_content = response.content

    # Fallback if empty
    if not final_content or len(final_content.strip()) == 0:
        if len(messages) > 0 and messages[-1].content:
            logger.warning("Editor LLM returned empty, using fallback")
            final_content = messages[-1].content
        else:
            final_content = "I apologize, but I couldn't generate a report from the available research. Please try refining your request."

    return {
        "messages": [AIMessage(content=final_content)],
        "final_report": final_content
    }


def editor_node_structured(state: AgentState):
    """
    Editor node that generates fully structured reports.

    Uses the ReportGenerator to create section-by-section reports.
    """
    messages = state["messages"]
    research_data = state.get("research_data", [])

    # Get original query
    original_query = ""
    for msg in messages:
        if hasattr(msg, 'type') and msg.type == 'human':
            original_query = msg.content
            break

    logger.info(
        "Structured editor node invoked",
        research_data_count=len(research_data)
    )

    # Initialize report generator
    generator = ReportGenerator()

    # Create outline (auto-selects template)
    outline = generator.create_outline(
        title=original_query[:100],
        research_data=research_data
    )

    # Get LLM for content generation
    llm = get_llm(task_type=TaskType.EDITOR, use_powerful=True)

    # Generate content for each section
    written_sections = []
    for section in sorted(outline.sections, key=lambda s: s.order):
        if section.section_type == SectionType.TITLE:
            section.content = original_query
            continue

        if section.section_type == SectionType.REFERENCES:
            section.content = generator.get_bibliography()
            continue

        # Get writing prompt
        prompt = generator.get_writing_prompt(
            outline=outline,
            section=section,
            research_data=research_data,
            previous_sections=written_sections
        )

        # Generate content
        try:
            response = llm.invoke([SystemMessage(content=prompt)])
            section.content = response.content
            written_sections.append(section)
            logger.debug(
                "Section generated",
                section=section.title,
                word_count=len(section.content.split())
            )
        except Exception as e:
            logger.error("Failed to generate section", section=section.title, error=str(e))
            section.content = f"[Content generation failed for this section: {str(e)}]"

    # Format final report
    final_content = generator.format_as_markdown(outline)

    return {
        "messages": [AIMessage(content=final_content)],
        "final_report": final_content
    }


# Export the default node
__all__ = ['editor_node', 'editor_node_structured']
