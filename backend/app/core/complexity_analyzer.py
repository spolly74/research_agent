"""
Complexity Analyzer - Analyzes task complexity to inform LLM routing decisions.

This module provides heuristics to determine task complexity based on:
- Keyword analysis
- Task length and structure
- Domain-specific indicators
- Multi-step requirements
"""

import re
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

import yaml
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ComplexityScore:
    """Result of complexity analysis."""
    score: float  # 0.0 to 1.0
    factors: dict[str, float]  # Breakdown of contributing factors
    recommendation: str  # "ollama" or "claude"
    reasoning: str  # Human-readable explanation


class ComplexityAnalyzer:
    """
    Analyzes task complexity to help route to appropriate LLM.

    Complexity is scored from 0.0 (simple) to 1.0 (complex).
    Scores above the threshold (default 0.7) recommend Claude.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the analyzer with optional config."""
        self.high_complexity_keywords: list[str] = []
        self.medium_complexity_keywords: list[str] = []
        self.complexity_threshold: float = 0.7

        # Load config
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "llm_config.yaml"

        self._load_config(config_path)

    def _load_config(self, config_path: Path):
        """Load complexity keywords from config."""
        if not config_path.exists():
            self._use_defaults()
            return

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            routing = config.get('routing', {})
            keywords = routing.get('complexity_keywords', {})

            self.high_complexity_keywords = keywords.get('high', [])
            self.medium_complexity_keywords = keywords.get('medium', [])
            self.complexity_threshold = routing.get('complexity_threshold', 0.7)

            logger.debug(
                "Complexity analyzer config loaded",
                high_keywords=len(self.high_complexity_keywords),
                medium_keywords=len(self.medium_complexity_keywords),
                threshold=self.complexity_threshold
            )
        except Exception as e:
            logger.warning("Failed to load complexity config", error=str(e))
            self._use_defaults()

    def _use_defaults(self):
        """Use default complexity keywords."""
        self.high_complexity_keywords = [
            "analyze", "compare", "evaluate", "synthesize", "comprehensive",
            "detailed", "professional", "technical", "complex", "multi-step",
            "in-depth", "thorough", "research", "investigate", "assess"
        ]
        self.medium_complexity_keywords = [
            "explain", "describe", "summarize", "list", "outline",
            "define", "identify", "clarify"
        ]
        self.complexity_threshold = 0.7

    def analyze(self, prompt: str, context: Optional[dict] = None) -> ComplexityScore:
        """
        Analyze the complexity of a task prompt.

        Args:
            prompt: The task or query text
            context: Optional additional context (e.g., conversation history)

        Returns:
            ComplexityScore with score, factors, and recommendation
        """
        factors = {}
        prompt_lower = prompt.lower()

        # Factor 1: Length (longer prompts tend to be more complex)
        length_score = self._analyze_length(prompt)
        factors['length'] = length_score

        # Factor 2: High complexity keywords
        high_keyword_score = self._analyze_keywords(prompt_lower, self.high_complexity_keywords)
        factors['high_keywords'] = high_keyword_score

        # Factor 3: Medium complexity keywords
        medium_keyword_score = self._analyze_keywords(prompt_lower, self.medium_complexity_keywords)
        factors['medium_keywords'] = medium_keyword_score

        # Factor 4: Question complexity (multiple questions, nested requirements)
        question_score = self._analyze_questions(prompt)
        factors['questions'] = question_score

        # Factor 5: Technical indicators
        technical_score = self._analyze_technical(prompt_lower)
        factors['technical'] = technical_score

        # Factor 6: Code-related content
        code_score = self._analyze_code(prompt)
        factors['code'] = code_score

        # Factor 7: Multi-step indicators
        multistep_score = self._analyze_multistep(prompt_lower)
        factors['multistep'] = multistep_score

        # Calculate weighted average
        weights = {
            'length': 0.10,
            'high_keywords': 0.25,
            'medium_keywords': 0.10,
            'questions': 0.15,
            'technical': 0.15,
            'code': 0.10,
            'multistep': 0.15
        }

        total_score = sum(factors[k] * weights[k] for k in factors)

        # Clamp to 0-1
        total_score = max(0.0, min(1.0, total_score))

        # Determine recommendation
        if total_score > self.complexity_threshold:
            recommendation = "claude"
            reasoning = f"Complexity score {total_score:.2f} exceeds threshold {self.complexity_threshold}"
        else:
            recommendation = "ollama"
            reasoning = f"Complexity score {total_score:.2f} below threshold {self.complexity_threshold}"

        # Add top contributing factors to reasoning
        top_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)[:3]
        factor_str = ", ".join([f"{k}={v:.2f}" for k, v in top_factors])
        reasoning += f". Top factors: {factor_str}"

        logger.debug(
            "Complexity analysis complete",
            score=total_score,
            recommendation=recommendation,
            factors=factors
        )

        return ComplexityScore(
            score=total_score,
            factors=factors,
            recommendation=recommendation,
            reasoning=reasoning
        )

    def _analyze_length(self, prompt: str) -> float:
        """Analyze prompt length complexity."""
        word_count = len(prompt.split())

        # Simple scaling: 0-50 words = 0.0-0.3, 50-200 = 0.3-0.7, 200+ = 0.7-1.0
        if word_count <= 50:
            return word_count / 50 * 0.3
        elif word_count <= 200:
            return 0.3 + (word_count - 50) / 150 * 0.4
        else:
            return min(1.0, 0.7 + (word_count - 200) / 300 * 0.3)

    def _analyze_keywords(self, prompt_lower: str, keywords: list[str]) -> float:
        """Count keyword matches and return normalized score."""
        if not keywords:
            return 0.0

        matches = sum(1 for kw in keywords if kw in prompt_lower)
        # Normalize: 1 match = 0.3, 2 = 0.5, 3+ = 0.7+
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.5
        elif matches == 3:
            return 0.7
        else:
            return min(1.0, 0.7 + (matches - 3) * 0.1)

    def _analyze_questions(self, prompt: str) -> float:
        """Analyze question complexity."""
        # Count question marks
        question_count = prompt.count('?')

        # Look for question words
        question_words = ['what', 'why', 'how', 'when', 'where', 'which', 'who']
        question_word_count = sum(
            1 for word in question_words
            if re.search(rf'\b{word}\b', prompt.lower())
        )

        # Look for nested requirements
        nested_patterns = [
            r'and\s+also',
            r'as\s+well\s+as',
            r'in\s+addition',
            r'furthermore',
            r'moreover',
            r'\d+\.',  # Numbered lists
            r'first.*then.*finally',
            r'step\s+\d+'
        ]
        nested_count = sum(
            1 for pattern in nested_patterns
            if re.search(pattern, prompt.lower())
        )

        # Calculate score
        score = 0.0
        score += min(0.4, question_count * 0.15)
        score += min(0.3, question_word_count * 0.1)
        score += min(0.3, nested_count * 0.15)

        return min(1.0, score)

    def _analyze_technical(self, prompt_lower: str) -> float:
        """Analyze technical complexity indicators."""
        technical_patterns = [
            r'\b(api|sdk|library|framework|database)\b',
            r'\b(algorithm|architecture|infrastructure)\b',
            r'\b(deploy|kubernetes|docker|aws|azure|gcp)\b',
            r'\b(machine learning|ml|ai|neural|model)\b',
            r'\b(security|authentication|encryption)\b',
            r'\b(performance|optimization|scaling)\b',
            r'\b(debug|troubleshoot|diagnose)\b',
            r'\b(integration|migration|refactor)\b'
        ]

        matches = sum(
            1 for pattern in technical_patterns
            if re.search(pattern, prompt_lower)
        )

        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.5
        else:
            return min(1.0, 0.5 + matches * 0.1)

    def _analyze_code(self, prompt: str) -> float:
        """Analyze code-related content."""
        # Check for code blocks
        code_block_count = len(re.findall(r'```', prompt))

        # Check for code-related keywords
        code_keywords = [
            'function', 'class', 'method', 'variable', 'import',
            'code', 'script', 'program', 'implement', 'debug',
            'error', 'exception', 'bug', 'fix'
        ]
        code_keyword_count = sum(
            1 for kw in code_keywords
            if kw in prompt.lower()
        )

        # Check for programming language mentions
        languages = [
            'python', 'javascript', 'typescript', 'java', 'rust',
            'go', 'c++', 'ruby', 'php', 'sql'
        ]
        language_count = sum(
            1 for lang in languages
            if lang in prompt.lower()
        )

        score = 0.0
        score += min(0.4, code_block_count * 0.2)
        score += min(0.4, code_keyword_count * 0.1)
        score += min(0.2, language_count * 0.1)

        return min(1.0, score)

    def _analyze_multistep(self, prompt_lower: str) -> float:
        """Analyze multi-step task indicators."""
        multistep_patterns = [
            r'step\s*\d+',
            r'first.*second.*third',
            r'begin.*then.*end',
            r'\d+\)\s+',  # Numbered items
            r'phase\s*\d+',
            r'stage\s*\d+',
            r'multiple\s+(steps|tasks|phases)',
            r'several\s+(steps|tasks|phases)',
            r'workflow',
            r'pipeline',
            r'process'
        ]

        matches = sum(
            1 for pattern in multistep_patterns
            if re.search(pattern, prompt_lower)
        )

        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.4
        elif matches == 2:
            return 0.6
        else:
            return min(1.0, 0.6 + matches * 0.1)


# Singleton instance
_analyzer: Optional[ComplexityAnalyzer] = None


def get_complexity_analyzer() -> ComplexityAnalyzer:
    """Get the singleton complexity analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ComplexityAnalyzer()
    return _analyzer


def analyze_complexity(prompt: str, context: Optional[dict] = None) -> ComplexityScore:
    """Convenience function to analyze prompt complexity."""
    analyzer = get_complexity_analyzer()
    return analyzer.analyze(prompt, context)
