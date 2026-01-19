"""
LLM Manager - Centralized LLM access with multiple providers and intelligent routing.

This module provides:
- Multiple Ollama endpoint support with health checking and load balancing
- Claude API integration with Sonnet (default) and Opus (powerful) models
- Task-based routing to select the appropriate LLM
- Retry logic with exponential backoff
- Configurable via YAML
"""

import os
import re
import asyncio
import threading
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime, timedelta

import yaml
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel

# Re-export complexity analyzer for convenience
from app.core.complexity_analyzer import analyze_complexity, ComplexityScore, get_complexity_analyzer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class Provider(str, Enum):
    """LLM Provider types."""
    OLLAMA = "ollama"
    CLAUDE = "claude"


class TaskType(str, Enum):
    """Task types for routing decisions."""
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    CODER = "coder"
    EDITOR = "editor"
    APPROVAL = "approval"
    GENERAL = "general"


@dataclass
class EndpointStatus:
    """Health status for an Ollama endpoint."""
    url: str
    is_healthy: bool = False
    last_check: Optional[datetime] = None
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None
    available_models: list[str] = field(default_factory=list)


@dataclass
class OllamaEndpoint:
    """Configuration for a single Ollama endpoint."""
    url: str
    models: list[str]
    priority: int = 1
    enabled: bool = True
    status: EndpointStatus = field(default_factory=lambda: EndpointStatus(url=""))

    def __post_init__(self):
        self.status = EndpointStatus(url=self.url)


@dataclass
class LLMConfig:
    """Complete LLM configuration loaded from YAML."""
    ollama_endpoints: list[OllamaEndpoint]
    ollama_default_model: str
    ollama_health_check_interval: int
    ollama_request_timeout: int

    claude_enabled: bool
    claude_default_model: str
    claude_powerful_model: str
    claude_max_tokens: int
    claude_temperature: float
    claude_request_timeout: int

    complexity_threshold: float
    task_rules: dict[str, dict]
    complexity_keywords: dict[str, list[str]]
    force_claude_patterns: list[str]

    retry_max_attempts: int
    retry_initial_delay: float
    retry_max_delay: float

    log_level: str
    log_prompts: bool
    log_responses: bool
    log_token_usage: bool


class LLMManager:
    """
    Centralized manager for LLM access with multiple providers.

    Handles:
    - Multiple Ollama endpoints with health checking and load balancing
    - Claude API with Sonnet/Opus model selection
    - Task-based routing
    - Automatic failover
    - Retry logic
    """

    _instance: Optional['LLMManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for LLM Manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the LLM Manager."""
        if self._initialized:
            return

        self._initialized = True
        self.config: Optional[LLMConfig] = None
        self._claude_client: Optional[ChatAnthropic] = None
        self._claude_powerful_client: Optional[ChatAnthropic] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._current_endpoint_index: int = 0

        # Load configuration
        self._load_config()

        # Initialize Claude client if enabled
        if self.config.claude_enabled:
            self._init_claude_clients()

        logger.info(
            "LLM Manager initialized",
            ollama_endpoints=len(self.config.ollama_endpoints),
            claude_enabled=self.config.claude_enabled
        )

    def _load_config(self):
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent.parent.parent / "config" / "llm_config.yaml"

        if not config_path.exists():
            logger.warning("Config file not found, using defaults", path=str(config_path))
            self._use_default_config()
            return

        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)

        # Parse Ollama endpoints
        ollama_endpoints = []
        for ep in raw_config.get('ollama', {}).get('endpoints', []):
            if ep.get('enabled', True):
                ollama_endpoints.append(OllamaEndpoint(
                    url=ep['url'],
                    models=ep.get('models', ['llama3.2']),
                    priority=ep.get('priority', 1),
                    enabled=ep.get('enabled', True)
                ))

        # Sort by priority
        ollama_endpoints.sort(key=lambda x: x.priority)

        # Build config object
        ollama_cfg = raw_config.get('ollama', {})
        claude_cfg = raw_config.get('claude', {})
        routing_cfg = raw_config.get('routing', {})
        retry_cfg = raw_config.get('retry', {})
        log_cfg = raw_config.get('logging', {})

        self.config = LLMConfig(
            ollama_endpoints=ollama_endpoints,
            ollama_default_model=ollama_cfg.get('default_model', 'llama3.2'),
            ollama_health_check_interval=ollama_cfg.get('health_check_interval', 30),
            ollama_request_timeout=ollama_cfg.get('request_timeout', 120),

            claude_enabled=claude_cfg.get('enabled', False),
            claude_default_model=claude_cfg.get('models', {}).get('default', 'claude-sonnet-4-20250514'),
            claude_powerful_model=claude_cfg.get('models', {}).get('powerful', 'claude-opus-4-5-20251101'),
            claude_max_tokens=claude_cfg.get('max_tokens', 4096),
            claude_temperature=claude_cfg.get('temperature', 0),
            claude_request_timeout=claude_cfg.get('request_timeout', 300),

            complexity_threshold=routing_cfg.get('complexity_threshold', 0.7),
            task_rules=routing_cfg.get('task_rules', {}),
            complexity_keywords=routing_cfg.get('complexity_keywords', {}),
            force_claude_patterns=routing_cfg.get('force_claude_patterns', []),

            retry_max_attempts=retry_cfg.get('max_attempts', 3),
            retry_initial_delay=retry_cfg.get('initial_delay', 1.0),
            retry_max_delay=retry_cfg.get('max_delay', 30.0),

            log_level=log_cfg.get('level', 'INFO'),
            log_prompts=log_cfg.get('log_prompts', False),
            log_responses=log_cfg.get('log_responses', False),
            log_token_usage=log_cfg.get('log_token_usage', True)
        )

        logger.info(
            "Configuration loaded",
            config_path=str(config_path),
            endpoints=len(self.config.ollama_endpoints),
            claude_enabled=self.config.claude_enabled
        )

    def _use_default_config(self):
        """Use default configuration when YAML is not available."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        self.config = LLMConfig(
            ollama_endpoints=[OllamaEndpoint(url=base_url, models=['llama3.2'], priority=1)],
            ollama_default_model='llama3.2',
            ollama_health_check_interval=30,
            ollama_request_timeout=120,

            claude_enabled=bool(os.getenv("ANTHROPIC_API_KEY")),
            claude_default_model='claude-sonnet-4-20250514',
            claude_powerful_model='claude-opus-4-5-20251101',
            claude_max_tokens=4096,
            claude_temperature=0,
            claude_request_timeout=300,

            complexity_threshold=0.7,
            task_rules={},
            complexity_keywords={'high': [], 'medium': []},
            force_claude_patterns=[],

            retry_max_attempts=3,
            retry_initial_delay=1.0,
            retry_max_delay=30.0,

            log_level='INFO',
            log_prompts=False,
            log_responses=False,
            log_token_usage=True
        )

    def _init_claude_clients(self):
        """Initialize Claude API clients."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, Claude will be unavailable")
            self.config.claude_enabled = False
            return

        try:
            # Default model (Sonnet)
            self._claude_client = ChatAnthropic(
                model=self.config.claude_default_model,
                max_tokens=self.config.claude_max_tokens,
                temperature=self.config.claude_temperature,
                api_key=api_key,
                timeout=self.config.claude_request_timeout
            )

            # Powerful model (Opus)
            self._claude_powerful_client = ChatAnthropic(
                model=self.config.claude_powerful_model,
                max_tokens=self.config.claude_max_tokens,
                temperature=self.config.claude_temperature,
                api_key=api_key,
                timeout=self.config.claude_request_timeout
            )

            logger.info(
                "Claude clients initialized",
                default_model=self.config.claude_default_model,
                powerful_model=self.config.claude_powerful_model
            )
        except Exception as e:
            logger.error("Failed to initialize Claude clients", error=str(e))
            self.config.claude_enabled = False

    async def check_endpoint_health(self, endpoint: OllamaEndpoint) -> EndpointStatus:
        """Check health of a single Ollama endpoint."""
        start_time = datetime.now()
        try:
            async with httpx.AsyncClient(timeout=self.config.ollama_health_check_interval) as client:
                # Check if Ollama is responding
                response = await client.get(f"{endpoint.url}/api/tags")
                response.raise_for_status()

                # Parse available models
                data = response.json()
                available_models = [m['name'].split(':')[0] for m in data.get('models', [])]

                response_time = (datetime.now() - start_time).total_seconds() * 1000

                endpoint.status = EndpointStatus(
                    url=endpoint.url,
                    is_healthy=True,
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    available_models=available_models
                )

                logger.debug(
                    "Endpoint health check passed",
                    url=endpoint.url,
                    response_time_ms=response_time,
                    models=available_models
                )

        except Exception as e:
            endpoint.status = EndpointStatus(
                url=endpoint.url,
                is_healthy=False,
                last_check=datetime.now(),
                last_error=str(e)
            )
            logger.warning(
                "Endpoint health check failed",
                url=endpoint.url,
                error=str(e)
            )

        return endpoint.status

    async def check_all_endpoints(self) -> dict[str, EndpointStatus]:
        """Check health of all Ollama endpoints."""
        tasks = [self.check_endpoint_health(ep) for ep in self.config.ollama_endpoints]
        await asyncio.gather(*tasks)
        return {ep.url: ep.status for ep in self.config.ollama_endpoints}

    def check_endpoint_health_sync(self, endpoint: OllamaEndpoint) -> EndpointStatus:
        """Synchronous health check for a single endpoint."""
        start_time = datetime.now()
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{endpoint.url}/api/tags")
                response.raise_for_status()

                data = response.json()
                available_models = [m['name'].split(':')[0] for m in data.get('models', [])]

                response_time = (datetime.now() - start_time).total_seconds() * 1000

                endpoint.status = EndpointStatus(
                    url=endpoint.url,
                    is_healthy=True,
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    available_models=available_models
                )

        except Exception as e:
            endpoint.status = EndpointStatus(
                url=endpoint.url,
                is_healthy=False,
                last_check=datetime.now(),
                last_error=str(e)
            )

        return endpoint.status

    def _get_healthy_ollama_endpoint(self, model: Optional[str] = None) -> Optional[OllamaEndpoint]:
        """Get a healthy Ollama endpoint that supports the requested model."""
        model = model or self.config.ollama_default_model

        # Filter to healthy endpoints with the requested model
        candidates = [
            ep for ep in self.config.ollama_endpoints
            if ep.enabled and ep.status.is_healthy and model in ep.models
        ]

        if not candidates:
            # Try checking health of all endpoints
            for ep in self.config.ollama_endpoints:
                if ep.enabled and model in ep.models:
                    self.check_endpoint_health_sync(ep)
                    if ep.status.is_healthy:
                        candidates.append(ep)

        if not candidates:
            # Last resort: try any enabled endpoint
            for ep in self.config.ollama_endpoints:
                if ep.enabled:
                    self.check_endpoint_health_sync(ep)
                    if ep.status.is_healthy:
                        return ep

        if not candidates:
            return None

        # Round-robin selection among healthy endpoints
        self._current_endpoint_index = (self._current_endpoint_index + 1) % len(candidates)
        return candidates[self._current_endpoint_index]

    def _should_use_claude(
        self,
        task_type: TaskType,
        prompt: Optional[str] = None,
        complexity_score: Optional[float] = None,
        force_claude: bool = False
    ) -> tuple[bool, str]:
        """
        Determine if Claude should be used for this task.

        Returns:
            Tuple of (should_use_claude, reason)
        """
        if force_claude:
            return True, "forced by caller"

        if not self.config.claude_enabled:
            return False, "Claude not enabled"

        # Check task rules
        task_rules = self.config.task_rules.get(task_type.value, {})
        default_provider = task_rules.get('default_provider', 'ollama')

        if default_provider == 'claude':
            return True, f"task type {task_type.value} defaults to Claude"

        # Check complexity threshold
        if complexity_score is not None and complexity_score > self.config.complexity_threshold:
            return True, f"complexity {complexity_score:.2f} exceeds threshold {self.config.complexity_threshold}"

        # Check force patterns
        if prompt:
            for pattern in self.config.force_claude_patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    return True, f"prompt matches pattern '{pattern}'"

        return False, "default to Ollama"

    def get_llm(
        self,
        task_type: TaskType = TaskType.GENERAL,
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        complexity_score: Optional[float] = None,
        force_provider: Optional[Provider] = None,
        use_powerful: bool = False
    ) -> BaseChatModel:
        """
        Get an appropriate LLM based on task type, complexity, and availability.

        Args:
            task_type: The type of task (orchestrator, researcher, etc.)
            model: Specific Ollama model to use (optional)
            prompt: The prompt text for complexity analysis (optional)
            complexity_score: Pre-computed complexity score (optional)
            force_provider: Force a specific provider (optional)
            use_powerful: Use the powerful Claude model (Opus) if using Claude

        Returns:
            A LangChain chat model instance
        """
        # Determine provider
        if force_provider == Provider.CLAUDE:
            use_claude = True
            reason = "forced by caller"
        elif force_provider == Provider.OLLAMA:
            use_claude = False
            reason = "forced by caller"
        else:
            use_claude, reason = self._should_use_claude(
                task_type, prompt, complexity_score
            )

        logger.info(
            "Selecting LLM",
            task_type=task_type.value,
            use_claude=use_claude,
            reason=reason,
            use_powerful=use_powerful
        )

        if use_claude and self.config.claude_enabled:
            if use_powerful and self._claude_powerful_client:
                logger.info("Using Claude Opus (powerful)")
                return self._claude_powerful_client
            elif self._claude_client:
                logger.info("Using Claude Sonnet (default)")
                return self._claude_client

        # Fall back to Ollama
        endpoint = self._get_healthy_ollama_endpoint(model)
        if endpoint is None:
            # Last resort: try Claude if available
            if self.config.claude_enabled and self._claude_client:
                logger.warning("No healthy Ollama endpoints, falling back to Claude")
                return self._claude_client

            # Create Ollama client anyway, it will fail on invoke
            logger.error("No healthy LLM endpoints available")
            endpoint = self.config.ollama_endpoints[0] if self.config.ollama_endpoints else None
            base_url = endpoint.url if endpoint else "http://localhost:11434"
        else:
            base_url = endpoint.url

        model_name = model or self.config.ollama_default_model
        logger.info("Using Ollama", url=base_url, model=model_name)

        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=0,
            timeout=self.config.ollama_request_timeout
        )

    def get_ollama(self, model: Optional[str] = None) -> ChatOllama:
        """Get an Ollama client directly (bypasses routing)."""
        return self.get_llm(force_provider=Provider.OLLAMA, model=model)

    def get_claude(self, use_powerful: bool = False) -> Optional[ChatAnthropic]:
        """Get a Claude client directly (bypasses routing)."""
        if not self.config.claude_enabled:
            return None
        return self._claude_powerful_client if use_powerful else self._claude_client

    def get_status(self) -> dict[str, Any]:
        """Get current status of all LLM providers."""
        return {
            "ollama": {
                "endpoints": [
                    {
                        "url": ep.url,
                        "enabled": ep.enabled,
                        "priority": ep.priority,
                        "models": ep.models,
                        "status": {
                            "is_healthy": ep.status.is_healthy,
                            "last_check": ep.status.last_check.isoformat() if ep.status.last_check else None,
                            "last_error": ep.status.last_error,
                            "response_time_ms": ep.status.response_time_ms,
                            "available_models": ep.status.available_models
                        }
                    }
                    for ep in self.config.ollama_endpoints
                ],
                "default_model": self.config.ollama_default_model
            },
            "claude": {
                "enabled": self.config.claude_enabled,
                "default_model": self.config.claude_default_model,
                "powerful_model": self.config.claude_powerful_model
            },
            "routing": {
                "complexity_threshold": self.config.complexity_threshold
            }
        }


# Singleton instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get the singleton LLM Manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def get_llm(
    task_type: TaskType = TaskType.GENERAL,
    model: Optional[str] = None,
    prompt: Optional[str] = None,
    complexity_score: Optional[float] = None,
    force_provider: Optional[Provider] = None,
    use_powerful: bool = False
) -> BaseChatModel:
    """
    Convenience function to get an LLM through the manager.

    This is the primary interface for agents to obtain LLM instances.
    """
    manager = get_llm_manager()
    return manager.get_llm(
        task_type=task_type,
        model=model,
        prompt=prompt,
        complexity_score=complexity_score,
        force_provider=force_provider,
        use_powerful=use_powerful
    )
