"""
Technical Analysis Template

A template for technical reports and analyses with:
- Executive Summary
- Technical Overview
- Detailed Analysis
- Implementation Considerations
- Recommendations
"""

from app.reports.templates.base import (
    ReportTemplate, ReportSection, SectionType, ReportType
)


class TechnicalAnalysisTemplate(ReportTemplate):
    """Template for technical analysis reports."""

    def __init__(self):
        super().__init__()
        self.report_type = ReportType.TECHNICAL
        self.name = "Technical Analysis"
        self.description = "Technical report with detailed analysis and implementation guidance"

    def get_sections(self) -> list[ReportSection]:
        """Define sections for a technical analysis report."""
        return [
            ReportSection(
                section_type=SectionType.TITLE,
                title="Title Page",
                order=1,
                is_required=True,
                word_count_target=50,
                notes="Technical report title with version and date"
            ),
            ReportSection(
                section_type=SectionType.EXECUTIVE_SUMMARY,
                title="Executive Summary",
                order=2,
                is_required=True,
                word_count_target=300,
                notes="High-level overview for decision makers"
            ),
            ReportSection(
                section_type=SectionType.INTRODUCTION,
                title="Introduction & Scope",
                order=3,
                is_required=True,
                word_count_target=300,
                notes="Problem statement and analysis scope"
            ),
            ReportSection(
                section_type=SectionType.BACKGROUND,
                title="Technical Background",
                order=4,
                is_required=True,
                word_count_target=500,
                notes="Technical context, architecture, and key concepts"
            ),
            ReportSection(
                section_type=SectionType.METHODOLOGY,
                title="Analysis Methodology",
                order=5,
                is_required=True,
                word_count_target=300,
                notes="Tools, techniques, and evaluation criteria used"
            ),
            ReportSection(
                section_type=SectionType.FINDINGS,
                title="Technical Findings",
                order=6,
                is_required=True,
                word_count_target=800,
                notes="Detailed technical findings with data and evidence",
                subsections=[
                    ReportSection(
                        section_type=SectionType.CUSTOM,
                        title="Performance Analysis",
                        order=1,
                        word_count_target=250
                    ),
                    ReportSection(
                        section_type=SectionType.CUSTOM,
                        title="Security Considerations",
                        order=2,
                        word_count_target=250
                    ),
                    ReportSection(
                        section_type=SectionType.CUSTOM,
                        title="Scalability Assessment",
                        order=3,
                        word_count_target=250
                    )
                ]
            ),
            ReportSection(
                section_type=SectionType.ANALYSIS,
                title="Comparative Analysis",
                order=7,
                is_required=True,
                word_count_target=500,
                notes="Comparison with alternatives, trade-offs"
            ),
            ReportSection(
                section_type=SectionType.RECOMMENDATIONS,
                title="Recommendations",
                order=8,
                is_required=True,
                word_count_target=400,
                notes="Technical recommendations with implementation guidance"
            ),
            ReportSection(
                section_type=SectionType.CONCLUSION,
                title="Conclusion",
                order=9,
                is_required=True,
                word_count_target=200,
                notes="Summary and next steps"
            ),
            ReportSection(
                section_type=SectionType.APPENDIX,
                title="Technical Appendix",
                order=10,
                is_required=False,
                word_count_target=None,
                notes="Code samples, configurations, detailed data"
            ),
            ReportSection(
                section_type=SectionType.REFERENCES,
                title="References",
                order=11,
                is_required=True,
                word_count_target=None,
                notes="Technical documentation and sources"
            )
        ]

    def get_section_instructions(self, section_type: SectionType) -> str:
        """Get writing instructions for each section type."""
        instructions = {
            SectionType.TITLE: """
Create a technical title page that includes:
- Clear, specific technical title
- Version number (e.g., v1.0)
- Date of analysis
- Author/team attribution
Keep it precise and professional.
""",
            SectionType.EXECUTIVE_SUMMARY: """
Write an executive summary that:
- States the technical problem or question
- Summarizes key findings in business terms
- Highlights critical recommendations
- Notes any urgent concerns or risks
- Is accessible to non-technical stakeholders
Keep it concise but comprehensive (300 words max).
""",
            SectionType.INTRODUCTION: """
Write a technical introduction that:
- Clearly defines the problem or analysis objective
- Specifies the scope and boundaries
- Lists key requirements or constraints
- Identifies stakeholders and their needs
- Sets expectations for the analysis
Be precise and avoid ambiguity.
""",
            SectionType.BACKGROUND: """
Provide technical background including:
- Current system/architecture overview
- Key technologies and components
- Relevant technical standards
- Historical context if relevant
- Dependencies and integrations
Use diagrams conceptually and be technically accurate.
""",
            SectionType.METHODOLOGY: """
Describe the analysis methodology:
- Tools and technologies used
- Testing approaches and environments
- Evaluation criteria and metrics
- Data collection methods
- Limitations and assumptions
Be specific about how analysis was performed.
""",
            SectionType.FINDINGS: """
Present technical findings:
- Organize by category (performance, security, etc.)
- Include specific metrics and data
- Use technical detail appropriately
- Highlight critical issues
- Note both strengths and weaknesses
Support all findings with evidence.
""",
            SectionType.ANALYSIS: """
Provide comparative analysis:
- Compare with alternatives or standards
- Discuss trade-offs (cost, complexity, performance)
- Evaluate fit for requirements
- Consider future implications
- Risk assessment
Be objective and data-driven.
""",
            SectionType.RECOMMENDATIONS: """
Provide technical recommendations:
- Prioritize by impact and urgency
- Include implementation considerations
- Estimate effort/resources needed
- Address potential risks
- Suggest phased approach if appropriate
Make recommendations actionable and specific.
""",
            SectionType.CONCLUSION: """
Write a technical conclusion:
- Summarize key findings and recommendations
- State overall assessment
- Identify next steps
- Note any follow-up analysis needed
Keep it brief but complete.
""",
            SectionType.APPENDIX: """
Include technical appendix with:
- Code samples or configurations
- Detailed test results
- Raw data or metrics
- Architecture diagrams
- Additional technical documentation
Organize for easy reference.
""",
            SectionType.REFERENCES: """
List technical references:
- Official documentation
- Technical specifications
- Related analyses or reports
- Standards and guidelines
- Tools and libraries used
Include version numbers where applicable.
"""
        }

        return instructions.get(section_type, "Write this section with technical precision and clarity.")
