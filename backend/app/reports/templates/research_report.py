"""
Research Report Template

A comprehensive template for in-depth research reports with:
- Abstract
- Introduction
- Methodology
- Findings
- Analysis
- Conclusion
- References
"""

from app.reports.templates.base import (
    ReportTemplate, ReportSection, SectionType, ReportType
)


class ResearchReportTemplate(ReportTemplate):
    """Template for comprehensive research reports."""

    def __init__(self):
        super().__init__()
        self.report_type = ReportType.RESEARCH
        self.name = "Research Report"
        self.description = "Comprehensive research report with methodology, findings, and analysis"

    def get_sections(self) -> list[ReportSection]:
        """Define sections for a research report."""
        return [
            ReportSection(
                section_type=SectionType.TITLE,
                title="Title Page",
                order=1,
                is_required=True,
                word_count_target=50,
                notes="Include title, author, date, and brief subtitle"
            ),
            ReportSection(
                section_type=SectionType.ABSTRACT,
                title="Abstract",
                order=2,
                is_required=True,
                word_count_target=250,
                notes="Concise summary of the entire report including key findings"
            ),
            ReportSection(
                section_type=SectionType.INTRODUCTION,
                title="Introduction",
                order=3,
                is_required=True,
                word_count_target=400,
                notes="Background, research questions, and scope of the study"
            ),
            ReportSection(
                section_type=SectionType.BACKGROUND,
                title="Background & Literature Review",
                order=4,
                is_required=True,
                word_count_target=600,
                notes="Existing knowledge, related work, and theoretical framework"
            ),
            ReportSection(
                section_type=SectionType.METHODOLOGY,
                title="Methodology",
                order=5,
                is_required=True,
                word_count_target=400,
                notes="Research methods, data sources, and analytical approach"
            ),
            ReportSection(
                section_type=SectionType.FINDINGS,
                title="Findings",
                order=6,
                is_required=True,
                word_count_target=800,
                notes="Detailed presentation of research results with evidence"
            ),
            ReportSection(
                section_type=SectionType.ANALYSIS,
                title="Analysis & Discussion",
                order=7,
                is_required=True,
                word_count_target=600,
                notes="Interpretation of findings, implications, and connections"
            ),
            ReportSection(
                section_type=SectionType.CONCLUSION,
                title="Conclusion",
                order=8,
                is_required=True,
                word_count_target=300,
                notes="Summary of key insights and final thoughts"
            ),
            ReportSection(
                section_type=SectionType.RECOMMENDATIONS,
                title="Recommendations",
                order=9,
                is_required=False,
                word_count_target=300,
                notes="Actionable recommendations based on findings"
            ),
            ReportSection(
                section_type=SectionType.REFERENCES,
                title="References",
                order=10,
                is_required=True,
                word_count_target=None,
                notes="Bibliography of all sources cited"
            )
        ]

    def get_section_instructions(self, section_type: SectionType) -> str:
        """Get writing instructions for each section type."""
        instructions = {
            SectionType.TITLE: """
Create a compelling title page that includes:
- A clear, descriptive title that captures the research focus
- A subtitle if appropriate to clarify scope
- Author attribution (Research Agent)
- Date of report
Keep it professional and informative.
""",
            SectionType.ABSTRACT: """
Write a concise abstract (200-300 words) that:
- States the research problem or question
- Briefly describes the methodology
- Summarizes the key findings
- Highlights the main conclusions
- Uses clear, accessible language
The abstract should stand alone as a complete summary.
""",
            SectionType.INTRODUCTION: """
Write an introduction that:
- Provides context for the research topic
- States the research questions or objectives
- Explains why this topic is important or relevant
- Outlines the scope and limitations
- Previews the structure of the report
Engage the reader while setting clear expectations.
""",
            SectionType.BACKGROUND: """
Write a background section that:
- Reviews existing knowledge on the topic
- Identifies key concepts and definitions
- Discusses relevant theories or frameworks
- Highlights gaps in current understanding
- Establishes the foundation for your research
Cite sources appropriately and maintain academic rigor.
""",
            SectionType.METHODOLOGY: """
Describe the research methodology including:
- Research approach and design
- Data sources and collection methods
- Tools and technologies used
- Analytical techniques applied
- Any limitations of the methodology
Be specific and transparent about how the research was conducted.
""",
            SectionType.FINDINGS: """
Present the research findings by:
- Organizing results logically by theme or question
- Using specific data and evidence
- Including relevant examples and quotes
- Presenting information objectively
- Using subheadings for clarity
Focus on what was discovered, not interpretation.
""",
            SectionType.ANALYSIS: """
Analyze and discuss the findings by:
- Interpreting what the results mean
- Connecting findings to research questions
- Comparing with existing knowledge
- Identifying patterns and relationships
- Discussing implications and significance
Provide thoughtful, evidence-based analysis.
""",
            SectionType.CONCLUSION: """
Write a conclusion that:
- Summarizes the main findings
- Addresses the research questions
- Discusses broader implications
- Acknowledges limitations
- Suggests areas for future research
End with a strong, memorable closing statement.
""",
            SectionType.RECOMMENDATIONS: """
Provide actionable recommendations that:
- Flow logically from the findings
- Are specific and practical
- Include implementation considerations
- Prioritize by impact or urgency
- Consider constraints and feasibility
Make recommendations clear and actionable.
""",
            SectionType.REFERENCES: """
Compile a complete reference list:
- Include all sources cited in the report
- Use consistent citation format (APA style preferred)
- Organize alphabetically by author
- Include URLs for web sources with access dates
- Verify all citations are accurate
"""
        }

        return instructions.get(section_type, "Write this section professionally and thoroughly.")
