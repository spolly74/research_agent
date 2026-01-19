"""
Tests for Report Scope Configuration
"""

import pytest
from app.reports.scope_config import (
    ReportScope,
    ScopeConfig,
    ScopeParameters,
    SCOPE_DEFAULTS,
    detect_scope_from_query,
    create_scope_config,
    WORDS_PER_PAGE
)


class TestReportScope:
    """Test ReportScope enum."""

    def test_scope_values(self):
        """Test that all expected scope values exist."""
        assert ReportScope.BRIEF.value == "brief"
        assert ReportScope.STANDARD.value == "standard"
        assert ReportScope.COMPREHENSIVE.value == "comprehensive"
        assert ReportScope.CUSTOM.value == "custom"


class TestScopeDefaults:
    """Test default scope parameters."""

    def test_brief_defaults(self):
        """Test brief scope default parameters."""
        params = SCOPE_DEFAULTS[ReportScope.BRIEF]
        assert params.target_pages == 2
        assert params.target_word_count == 750
        assert params.min_sources == 3
        assert params.max_sources == 5
        assert params.section_depth == "minimal"

    def test_standard_defaults(self):
        """Test standard scope default parameters."""
        params = SCOPE_DEFAULTS[ReportScope.STANDARD]
        assert params.target_pages == 4
        assert params.target_word_count == 2000
        assert params.min_sources == 5
        assert params.max_sources == 10
        assert params.section_depth == "balanced"

    def test_comprehensive_defaults(self):
        """Test comprehensive scope default parameters."""
        params = SCOPE_DEFAULTS[ReportScope.COMPREHENSIVE]
        assert params.target_pages == 12
        assert params.target_word_count == 6000
        assert params.min_sources == 15
        assert params.max_sources == 25
        assert params.section_depth == "detailed"


class TestScopeConfig:
    """Test ScopeConfig class."""

    def test_brief_scope_config(self):
        """Test creating brief scope config."""
        config = ScopeConfig(scope=ReportScope.BRIEF)
        assert config.scope == ReportScope.BRIEF
        assert config.parameters.target_pages == 2
        assert config.parameters.target_word_count == 750

    def test_standard_scope_config(self):
        """Test creating standard scope config."""
        config = ScopeConfig(scope=ReportScope.STANDARD)
        assert config.scope == ReportScope.STANDARD
        assert config.parameters.target_pages == 4

    def test_comprehensive_scope_config(self):
        """Test creating comprehensive scope config."""
        config = ScopeConfig(scope=ReportScope.COMPREHENSIVE)
        assert config.scope == ReportScope.COMPREHENSIVE
        assert config.parameters.target_pages == 12

    def test_custom_scope_with_pages(self):
        """Test custom scope with page count."""
        config = ScopeConfig(scope=ReportScope.CUSTOM, custom_pages=10)
        assert config.scope == ReportScope.CUSTOM
        assert config.parameters.target_pages == 10
        assert config.parameters.target_word_count == 10 * WORDS_PER_PAGE

    def test_custom_scope_with_word_count(self):
        """Test custom scope with word count."""
        config = ScopeConfig(scope=ReportScope.CUSTOM, custom_word_count=3000)
        assert config.scope == ReportScope.CUSTOM
        assert config.parameters.target_word_count == 3000
        assert config.parameters.target_pages == 6  # 3000 / 500

    def test_word_count_multiplier_brief(self):
        """Test word count multiplier for brief scope."""
        config = ScopeConfig(scope=ReportScope.BRIEF)
        multiplier = config.get_word_count_multiplier()
        # Brief is 750 words, standard is 2000, so multiplier = 0.375
        assert multiplier == 750 / 2000

    def test_word_count_multiplier_comprehensive(self):
        """Test word count multiplier for comprehensive scope."""
        config = ScopeConfig(scope=ReportScope.COMPREHENSIVE)
        multiplier = config.get_word_count_multiplier()
        # Comprehensive is 6000 words, standard is 2000, so multiplier = 3.0
        assert multiplier == 6000 / 2000

    def test_scale_section_word_count(self):
        """Test scaling section word counts."""
        config = ScopeConfig(scope=ReportScope.COMPREHENSIVE)
        original = 200
        scaled = config.scale_section_word_count(original)
        # Should scale by 3x
        assert scaled == 600

    def test_scale_section_word_count_minimum(self):
        """Test that scaled word count has minimum of 50."""
        config = ScopeConfig(scope=ReportScope.BRIEF)
        original = 100
        scaled = config.scale_section_word_count(original)
        # 100 * 0.375 = 37.5, but minimum is 50
        assert scaled == 50

    def test_research_parameters(self):
        """Test getting research parameters."""
        config = ScopeConfig(scope=ReportScope.COMPREHENSIVE)
        params = config.get_research_parameters()
        assert params["min_sources"] == 15
        assert params["max_sources"] == 25
        assert params["depth"] == "detailed"
        assert params["focus"] == "comprehensive"

    def test_editor_instructions_brief(self):
        """Test editor instructions for brief scope."""
        config = ScopeConfig(scope=ReportScope.BRIEF)
        instructions = config.get_editor_instructions()
        assert "Brief" in instructions
        assert "1-2 pages" in instructions
        assert "750" in instructions

    def test_editor_instructions_comprehensive(self):
        """Test editor instructions for comprehensive scope."""
        config = ScopeConfig(scope=ReportScope.COMPREHENSIVE)
        instructions = config.get_editor_instructions()
        assert "Comprehensive" in instructions
        assert "10+ pages" in instructions

    def test_should_include_section_always(self):
        """Test sections that are always included."""
        config = ScopeConfig(scope=ReportScope.BRIEF)
        assert config.should_include_section("title") == True
        assert config.should_include_section("executive_summary") == True
        assert config.should_include_section("findings") == True
        assert config.should_include_section("conclusion") == True

    def test_should_include_section_brief_excludes(self):
        """Test that brief scope excludes methodology."""
        config = ScopeConfig(scope=ReportScope.BRIEF)
        # Brief excludes methodology and background
        assert config.should_include_section("methodology") == False
        assert config.should_include_section("background") == False

    def test_should_include_section_comprehensive_includes_all(self):
        """Test that comprehensive scope includes all sections."""
        config = ScopeConfig(scope=ReportScope.COMPREHENSIVE)
        assert config.should_include_section("methodology") == True
        assert config.should_include_section("background") == True
        assert config.should_include_section("appendix") == True

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = ScopeConfig(scope=ReportScope.STANDARD)
        d = config.to_dict()
        assert d["scope"] == "standard"
        assert d["target_pages"] == 4
        assert d["target_word_count"] == 2000
        assert "word_count_multiplier" in d


class TestDetectScopeFromQuery:
    """Test scope detection from natural language queries."""

    def test_detect_brief_keywords(self):
        """Test detection of brief scope keywords."""
        queries = [
            "Give me a brief overview",
            "Quick summary of AI",
            "Short report on climate change",
            "Just the highlights please"
        ]
        for query in queries:
            scope, pages = detect_scope_from_query(query)
            assert scope == ReportScope.BRIEF, f"Failed for: {query}"

    def test_detect_comprehensive_keywords(self):
        """Test detection of comprehensive scope keywords."""
        queries = [
            "Comprehensive analysis of market trends",
            "In-depth research on quantum computing",
            "Thorough investigation of security vulnerabilities",
            "Detailed white paper on blockchain"
        ]
        for query in queries:
            scope, pages = detect_scope_from_query(query)
            assert scope == ReportScope.COMPREHENSIVE, f"Failed for: {query}"

    def test_detect_custom_page_count(self):
        """Test detection of explicit page counts."""
        scope, pages = detect_scope_from_query("Write a 10 page report on AI")
        assert scope == ReportScope.CUSTOM
        assert pages == 10

        scope, pages = detect_scope_from_query("Need a 5-page summary")
        assert scope == ReportScope.CUSTOM
        assert pages == 5

    def test_detect_custom_word_count(self):
        """Test detection of explicit word counts."""
        scope, pages = detect_scope_from_query("Write 3000 words about machine learning")
        assert scope == ReportScope.CUSTOM
        assert pages == 6  # 3000 / 500

    def test_default_to_standard(self):
        """Test that ambiguous queries default to standard."""
        scope, pages = detect_scope_from_query("Tell me about renewable energy")
        assert scope == ReportScope.STANDARD
        assert pages is None


class TestCreateScopeConfig:
    """Test factory function for creating scope configs."""

    def test_create_with_explicit_scope(self):
        """Test creating config with explicit scope string."""
        config = create_scope_config(scope="comprehensive")
        assert config.scope == ReportScope.COMPREHENSIVE

    def test_create_with_pages(self):
        """Test creating config with page count."""
        config = create_scope_config(pages=8)
        assert config.scope == ReportScope.CUSTOM
        assert config.parameters.target_pages == 8

    def test_create_with_word_count(self):
        """Test creating config with word count."""
        config = create_scope_config(word_count=4000)
        assert config.scope == ReportScope.CUSTOM
        assert config.parameters.target_word_count == 4000

    def test_create_with_query(self):
        """Test creating config from query detection."""
        config = create_scope_config(query="Give me a brief summary")
        assert config.scope == ReportScope.BRIEF

    def test_create_default(self):
        """Test default config is standard."""
        config = create_scope_config()
        assert config.scope == ReportScope.STANDARD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
