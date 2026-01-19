"""
Executive Summary Template

A concise template for executive-level briefings with:
- Key Findings
- Strategic Implications
- Recommendations
- Action Items
"""

from app.reports.templates.base import (
    ReportTemplate, ReportSection, SectionType, ReportType
)


class ExecutiveSummaryTemplate(ReportTemplate):
    """Template for executive summary briefings."""

    def __init__(self):
        super().__init__()
        self.report_type = ReportType.EXECUTIVE
        self.name = "Executive Summary"
        self.description = "Concise executive briefing with key insights and recommendations"

    def get_sections(self) -> list[ReportSection]:
        """Define sections for an executive summary."""
        return [
            ReportSection(
                section_type=SectionType.TITLE,
                title="Title",
                order=1,
                is_required=True,
                word_count_target=30,
                notes="Brief, impactful title"
            ),
            ReportSection(
                section_type=SectionType.EXECUTIVE_SUMMARY,
                title="Overview",
                order=2,
                is_required=True,
                word_count_target=150,
                notes="One-paragraph situation summary"
            ),
            ReportSection(
                section_type=SectionType.FINDINGS,
                title="Key Findings",
                order=3,
                is_required=True,
                word_count_target=300,
                notes="3-5 critical findings in bullet format"
            ),
            ReportSection(
                section_type=SectionType.ANALYSIS,
                title="Strategic Implications",
                order=4,
                is_required=True,
                word_count_target=250,
                notes="Business impact and strategic considerations"
            ),
            ReportSection(
                section_type=SectionType.RECOMMENDATIONS,
                title="Recommendations",
                order=5,
                is_required=True,
                word_count_target=250,
                notes="Prioritized action recommendations"
            ),
            ReportSection(
                section_type=SectionType.CONCLUSION,
                title="Next Steps",
                order=6,
                is_required=True,
                word_count_target=150,
                notes="Immediate action items and timeline"
            )
        ]

    def get_section_instructions(self, section_type: SectionType) -> str:
        """Get writing instructions for each section type."""
        instructions = {
            SectionType.TITLE: """
Create a brief, impactful title that:
- Captures the core topic in 5-8 words
- Uses action-oriented language
- Is appropriate for executive audience
Example: "Market Expansion Strategy: Q4 Opportunities"
""",
            SectionType.EXECUTIVE_SUMMARY: """
Write a one-paragraph overview that:
- States the situation in 1-2 sentences
- Highlights the most critical finding
- Indicates the primary recommendation
- Can be understood in 30 seconds
Write for busy executives who may only read this section.
""",
            SectionType.FINDINGS: """
Present 3-5 key findings:
- Use bullet points for clarity
- Lead with the most important finding
- Include supporting data points
- Keep each finding to 1-2 sentences
- Focus on what matters for decisions
Format: "• [Finding]: [Brief supporting evidence]"
""",
            SectionType.ANALYSIS: """
Discuss strategic implications:
- Business impact (revenue, costs, risk)
- Competitive positioning
- Opportunity costs of inaction
- Timeline considerations
- Resource implications
Focus on what this means for the organization.
""",
            SectionType.RECOMMENDATIONS: """
Provide prioritized recommendations:
- List 2-4 clear recommendations
- Prioritize by impact and urgency
- Include expected outcomes
- Note resource requirements
- Consider quick wins vs. long-term plays
Format: "1. [Action] - [Expected Outcome] - [Priority]"
""",
            SectionType.CONCLUSION: """
Define concrete next steps:
- List 2-3 immediate actions
- Assign ownership if known
- Include timeline targets
- Note decision points needed
- Specify follow-up schedule
Be specific and actionable.
"""
        }

        return instructions.get(section_type, "Write concisely for executive audience.")
