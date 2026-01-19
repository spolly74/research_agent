# Research Agent - Implementation Analysis & Plan

## Executive Summary

This document provides a comprehensive analysis of the current research agent implementation and a detailed plan to reach the final vision: a multi-agent research system with orchestrated LLM access across Ollama VMs, Claude API fallback, dynamic tool creation, and professional-grade report generation.

**Current Completion: ~95%**

---

## Part 1: Current State Analysis

### 1.1 Project Overview

The research agent is a full-stack application built with:
- **Backend**: Python/FastAPI (port 8000)
- **Frontend**: React/TypeScript with Vite (port 5173)
- **Database**: SQLite with SQLAlchemy ORM
- **LLM**: Ollama integration via LangChain
- **Orchestration**: LangGraph state machine

### 1.2 Directory Structure

```
research_agent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py          # LangGraph workflow definition
│   │   │   ├── state.py          # Shared agent state schema
│   │   │   ├── nodes/            # Individual agent implementations
│   │   │   │   ├── orchestrator.py
│   │   │   │   ├── researcher.py
│   │   │   │   ├── reviewer.py
│   │   │   │   ├── coder.py
│   │   │   │   ├── editor.py
│   │   │   │   └── approval.py
│   │   │   └── tools/
│   │   │       └── browser.py    # Web search & page visit tools
│   │   ├── api/endpoints/
│   │   │   └── chat.py           # FastAPI routes
│   │   ├── core/
│   │   │   ├── llm.py            # LLM client configuration
│   │   │   └── database.py       # SQLAlchemy setup
│   │   ├── models/               # ORM models
│   │   ├── schemas/              # Pydantic schemas
│   │   └── main.py               # FastAPI application
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Chat.tsx          # Main chat interface
│   │   ├── api.ts                # API client
│   │   └── App.tsx
│   └── package.json
├── SETUP.md
└── verify_orchestrator.py
```

### 1.3 Implemented Agents

| Agent | File | Purpose | Status |
|-------|------|---------|--------|
| **Orchestrator** | `nodes/orchestrator.py` | Breaks requests into structured task plans | ✅ Complete |
| **Researcher** | `nodes/researcher.py` | Web search and page exploration | ✅ Complete |
| **Reviewer** | `nodes/reviewer.py` | Critiques research findings | ✅ Complete |
| **Coder** | `nodes/coder.py` | Analyzes if custom code is needed | ⚠️ Partial |
| **Editor** | `nodes/editor.py` | Synthesizes final response | ✅ Complete |
| **Approval** | `nodes/approval.py` | Final quality check | ✅ Complete |
| **Tools** | `graph.py` (ToolNode) | Executes browser tools | ✅ Complete |

### 1.4 Current Workflow

```
                                    ┌─────────────┐
                                    │ Orchestrator│
                                    └──────┬──────┘
                                           │
                          ┌────────────────┴────────────────┐
                          │                                 │
                    [RESEARCH]                          [ANSWER]
                          │                                 │
                          ▼                                 │
                   ┌────────────┐                           │
                   │ Researcher │◄────────┐                 │
                   └─────┬──────┘         │                 │
                         │                │                 │
                    [tool_calls?]         │                 │
                         │                │                 │
                         ▼                │                 │
                   ┌──────────┐           │                 │
                   │  Tools   │───────────┘                 │
                   └──────────┘                             │
                         │                                  │
                         ▼                                  │
                   ┌──────────┐                             │
                   │ Reviewer │                             │
                   └────┬─────┘                             │
                        │                                   │
                        ▼                                   │
                   ┌──────────┐                             │
                   │  Coder   │                             │
                   └────┬─────┘                             │
                        │                                   │
                        ▼                                   │
                   ┌──────────┐◄────────────────────────────┘
                   │  Editor  │
                   └────┬─────┘
                        │
                        ▼
                   ┌──────────┐
                   │ Approval │
                   └────┬─────┘
                        │
                        ▼
                      [END]
```

### 1.5 Current LLM Configuration

**File**: `backend/app/core/llm.py`

```python
# Current implementation - single Ollama instance
def get_llm():
    return ChatOllama(
        model="llama3.2",
        base_url="http://localhost:11434",
        temperature=0
    )
```

**Limitations**:
- Single Ollama endpoint (no load balancing)
- No Claude API integration
- No task-based model selection
- No health checks or failover

### 1.6 Current Tools

| Tool | Function | Technology |
|------|----------|------------|
| `browser_search` | Web search queries | Linkup API |
| `visit_page` | Extract page content | Playwright + html2text |

### 1.7 Database Schema

```python
class ChatSession:
    id: int (PK)
    title: str
    created_at: datetime
    updated_at: datetime
    messages: relationship -> Message

class Message:
    id: int (PK)
    session_id: int (FK)
    role: str  # user/assistant/system
    content: str
    created_at: datetime
```

### 1.8 LangGraph State

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_step: str           # RESEARCH | ANSWER | etc.
    research_data: list[str]
    review_feedback: str
    code_output: str
    final_report: str
    plan: dict               # Orchestrator's task plan
```

---

## Part 2: Gap Analysis

### 2.1 What's Missing

| Feature | Current State | Target State | Priority |
|---------|---------------|--------------|----------|
| **Claude API Integration** | Not implemented | Fallback for complex tasks | High |
| **Multi-VM Ollama** | Single localhost | Pool of Ollama VMs with load balancing | High |
| **Automatic LLM Routing** | None | Task complexity → model selection | High |
| **Dynamic Tool Creation** | Coder only analyzes | Coder writes & registers tools | Medium |
| **Long-Form Reports** | Short summaries | Professional docs with structure | Medium |
| **State Persistence** | In-memory only | Database-backed checkpointing | Medium |
| **Progress Streaming** | Request/response | WebSocket real-time updates | Low |
| **Authentication** | None | API keys / user sessions | Low |

### 2.2 Technical Debt

- Print statements instead of structured logging
- Hardcoded configuration values
- Limited error handling and retry logic
- No unit tests for agents
- CORS set to allow all origins

---

## Part 3: Implementation Plan

### Phase 1: LLM Infrastructure (Priority: High)

#### 1.1 Create LLM Manager Service

**Goal**: Centralized LLM access with multiple providers and automatic routing.

**New File**: `backend/app/core/llm_manager.py`

```python
# Proposed structure
class LLMManager:
    """Manages multiple LLM providers with intelligent routing."""

    def __init__(self):
        self.ollama_pool: list[OllamaEndpoint] = []
        self.claude_client: Optional[ChatAnthropic] = None
        self.health_checker: HealthChecker
        self.router: TaskRouter

    async def get_llm(self, task_type: TaskType, complexity: Complexity) -> BaseLLM:
        """Select appropriate LLM based on task requirements."""
        pass

    async def health_check(self) -> dict[str, EndpointStatus]:
        """Check health of all LLM endpoints."""
        pass
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 1.1.1 | Install `langchain-anthropic` dependency | 5 min |
| 1.1.2 | Create `OllamaEndpoint` dataclass with URL, model, status | 30 min |
| 1.1.3 | Create `LLMManager` class with provider registration | 2 hr |
| 1.1.4 | Implement health check loop (async background task) | 1 hr |
| 1.1.5 | Implement round-robin load balancing for Ollama pool | 1 hr |
| 1.1.6 | Add Claude API client with API key from env | 30 min |
| 1.1.7 | Create `TaskRouter` for complexity-based model selection | 2 hr |
| 1.1.8 | Update all agent nodes to use `LLMManager` | 1 hr |
| 1.1.9 | Add configuration file for LLM endpoints | 1 hr |
| 1.1.10 | Write unit tests for LLM manager | 2 hr |

#### 1.2 Configuration System

**New File**: `backend/config/llm_config.yaml`

```yaml
# Proposed configuration structure
ollama_endpoints:
  - url: "http://ollama-vm-1:11434"
    models: ["llama3.2", "codellama"]
    priority: 1
  - url: "http://ollama-vm-2:11434"
    models: ["llama3.2", "mixtral"]
    priority: 2
  - url: "http://localhost:11434"
    models: ["llama3.2"]
    priority: 3  # Fallback

claude:
  enabled: true
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096
  use_for:
    - complex_reasoning
    - code_generation
    - long_form_writing

routing_rules:
  - task_type: "research"
    default_provider: "ollama"
    complexity_threshold: 0.7  # Use Claude if complexity > 0.7
  - task_type: "code_generation"
    default_provider: "claude"
  - task_type: "simple_qa"
    default_provider: "ollama"
    model: "llama3.2"
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 1.2.1 | Create config schema with Pydantic | 1 hr |
| 1.2.2 | Implement YAML config loader | 30 min |
| 1.2.3 | Add environment variable overrides | 30 min |
| 1.2.4 | Create config validation on startup | 30 min |
| 1.2.5 | Add API endpoint to view/update config | 1 hr |

#### 1.3 Task Complexity Analyzer

**New File**: `backend/app/core/complexity_analyzer.py`

```python
# Proposed structure
class ComplexityAnalyzer:
    """Analyzes task complexity to route to appropriate LLM."""

    def analyze(self, task: str, context: dict) -> ComplexityScore:
        """
        Returns complexity score (0.0 - 1.0) based on:
        - Task length and structure
        - Domain keywords (technical, medical, legal)
        - Required reasoning depth
        - Code generation requirements
        - Multi-step planning needs
        """
        pass
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 1.3.1 | Define `ComplexityScore` model | 30 min |
| 1.3.2 | Implement keyword-based complexity heuristics | 2 hr |
| 1.3.3 | Add task-type classification | 1 hr |
| 1.3.4 | Integrate with orchestrator for initial routing | 1 hr |
| 1.3.5 | Add dynamic re-routing if Ollama response is poor | 2 hr |

---

### Phase 2: Dynamic Tool System (Priority: Medium)

#### 2.1 Tool Registry

**Goal**: Runtime tool registration and management.

**New File**: `backend/app/agents/tools/registry.py`

```python
# Proposed structure
class ToolRegistry:
    """Central registry for all available tools."""

    _tools: dict[str, BaseTool] = {}
    _metadata: dict[str, ToolMetadata] = {}

    @classmethod
    def register(cls, tool: BaseTool, metadata: ToolMetadata):
        """Register a new tool."""
        pass

    @classmethod
    def get_tools_for_agent(cls, agent_type: str) -> list[BaseTool]:
        """Get tools available to a specific agent."""
        pass

    @classmethod
    def create_tool_from_code(cls, name: str, code: str, description: str) -> BaseTool:
        """Dynamically create a tool from Python code."""
        pass
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 2.1.1 | Create `ToolMetadata` schema | 30 min |
| 2.1.2 | Implement `ToolRegistry` singleton | 1 hr |
| 2.1.3 | Register existing tools on startup | 30 min |
| 2.1.4 | Add tool persistence to database | 1 hr |
| 2.1.5 | Create API endpoints for tool management | 1 hr |

#### 2.2 Enhanced Coder Agent

**Goal**: Coder agent can write, test, and register new tools.

**Updated File**: `backend/app/agents/nodes/coder.py`

```python
# Proposed enhancements
class CoderAgent:
    """Enhanced coder that can create and register tools."""

    async def analyze_tool_need(self, task: str, available_tools: list) -> ToolNeed:
        """Determine if a new tool is needed."""
        pass

    async def generate_tool_code(self, specification: ToolSpec) -> str:
        """Generate Python code for a new tool."""
        pass

    async def validate_tool(self, code: str) -> ValidationResult:
        """Validate tool code in sandbox."""
        pass

    async def register_tool(self, code: str, metadata: ToolMetadata):
        """Register validated tool in registry."""
        pass
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 2.2.1 | Create `ToolSpec` and `ToolNeed` schemas | 30 min |
| 2.2.2 | Implement tool need analysis with LLM | 2 hr |
| 2.2.3 | Create tool code generation prompts | 2 hr |
| 2.2.4 | Implement sandboxed code execution (Docker/subprocess) | 4 hr |
| 2.2.5 | Add tool validation tests | 2 hr |
| 2.2.6 | Integrate with ToolRegistry | 1 hr |
| 2.2.7 | Update graph to use dynamic tools | 1 hr |
| 2.2.8 | Add safety checks for generated code | 2 hr |

#### 2.3 Built-in Tool Library

**Goal**: Expand available tools beyond browser operations.

**New Tools to Implement**:

| Tool | Purpose | File |
|------|---------|------|
| `calculator` | Mathematical computations | `tools/math.py` |
| `file_reader` | Read local files | `tools/filesystem.py` |
| `file_writer` | Write local files | `tools/filesystem.py` |
| `code_executor` | Run Python code safely | `tools/executor.py` |
| `api_caller` | Make HTTP requests | `tools/http.py` |
| `database_query` | Query external databases | `tools/database.py` |
| `document_parser` | Parse PDF/DOCX files | `tools/documents.py` |

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 2.3.1 | Implement `calculator` tool | 1 hr |
| 2.3.2 | Implement `file_reader` tool with path validation | 1 hr |
| 2.3.3 | Implement `file_writer` tool with safety checks | 1 hr |
| 2.3.4 | Implement `code_executor` with Docker sandbox | 4 hr |
| 2.3.5 | Implement `api_caller` tool | 1 hr |
| 2.3.6 | Implement `document_parser` (PDF/DOCX) | 3 hr |
| 2.3.7 | Register all tools in ToolRegistry | 1 hr |

---

### Phase 3: Professional Report Generation (Priority: Medium)

#### 3.1 Report Templates

**Goal**: Structured templates for different report types.

**New Directory**: `backend/app/reports/`

```
reports/
├── templates/
│   ├── research_report.py
│   ├── technical_analysis.py
│   ├── executive_summary.py
│   └── comparison_report.py
├── formatters/
│   ├── markdown.py
│   ├── html.py
│   └── pdf.py
└── citation_manager.py
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 3.1.1 | Define `ReportTemplate` base class | 1 hr |
| 3.1.2 | Create research report template | 2 hr |
| 3.1.3 | Create technical analysis template | 2 hr |
| 3.1.4 | Create executive summary template | 1 hr |
| 3.1.5 | Implement Markdown formatter | 1 hr |
| 3.1.6 | Implement HTML formatter | 2 hr |
| 3.1.7 | Implement PDF export (WeasyPrint) | 3 hr |

#### 3.2 Enhanced Editor Agent

**Goal**: Editor produces professional long-form documents.

**Updated File**: `backend/app/agents/nodes/editor.py`

```python
# Proposed structure
class EditorAgent:
    """Enhanced editor for professional report generation."""

    async def select_template(self, task: str, research_data: list) -> ReportTemplate:
        """Select appropriate report template."""
        pass

    async def generate_outline(self, template: ReportTemplate, data: list) -> Outline:
        """Generate document outline."""
        pass

    async def write_section(self, section: Section, context: dict) -> str:
        """Write individual section with proper formatting."""
        pass

    async def compile_report(self, sections: list[str], citations: list) -> Report:
        """Compile final report with table of contents, citations."""
        pass

    async def format_output(self, report: Report, format: OutputFormat) -> bytes:
        """Format report to requested output format."""
        pass
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 3.2.1 | Create `Outline` and `Section` schemas | 30 min |
| 3.2.2 | Implement template selection logic | 1 hr |
| 3.2.3 | Create outline generation prompts | 2 hr |
| 3.2.4 | Implement section-by-section writing | 3 hr |
| 3.2.5 | Add citation extraction and formatting | 2 hr |
| 3.2.6 | Implement report compilation | 2 hr |
| 3.2.7 | Integrate with formatters | 1 hr |

#### 3.3 Citation Manager

**Goal**: Proper citation tracking and formatting.

**New File**: `backend/app/reports/citation_manager.py`

**Status**: ✅ Complete

#### 3.4 Report Scope Configuration

**Goal**: Allow users to specify desired report length/scope during prompts.

**New File**: `backend/app/reports/scope_config.py`

```python
# Proposed structure
class ReportScope(str, Enum):
    BRIEF = "brief"           # 1-2 pages, key points only
    STANDARD = "standard"     # 3-5 pages, balanced coverage
    COMPREHENSIVE = "comprehensive"  # 10-15 pages, detailed analysis
    CUSTOM = "custom"         # User-specified page count

class ScopeConfig:
    """Configures report generation based on desired scope."""

    def __init__(self, scope: ReportScope, custom_pages: int = None):
        self.scope = scope
        self.target_pages = self._calculate_target_pages(custom_pages)

    def scale_word_counts(self, template: ReportTemplate) -> ReportTemplate:
        """Adjust section word counts based on scope."""
        pass

    def adjust_research_depth(self) -> dict:
        """Configure research parameters (source count, detail level)."""
        pass

    def get_editor_instructions(self) -> str:
        """Get scope-specific instructions for the editor agent."""
        pass
```

**Scope Parameters**:

| Scope | Target Pages | Word Count | Sources | Section Depth |
|-------|--------------|------------|---------|---------------|
| Brief | 1-2 | ~500-1000 | 3-5 | Key points only |
| Standard | 3-5 | ~1500-2500 | 5-10 | Balanced coverage |
| Comprehensive | 10-15 | ~5000-7500 | 15-25 | Full analysis |
| Custom | User-defined | Calculated | Scaled | Adjusted |

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 3.4.1 | Create `ReportScope` enum and `ScopeConfig` class | 1 hr |
| 3.4.2 | Implement word count scaling for templates | 1 hr |
| 3.4.3 | Add research depth configuration | 1 hr |
| 3.4.4 | Update orchestrator to use scope in planning | 1 hr |
| 3.4.5 | Update editor prompts for scope awareness | 1 hr |
| 3.4.6 | Add scope parameter to API endpoints | 30 min |
| 3.4.7 | Add scope detection from natural language queries | 1 hr |
| 3.4.8 | Write tests for scope configuration | 1 hr |

```python
# Proposed structure
class CitationManager:
    """Manages citations throughout research and report generation."""

    def extract_citation(self, source_url: str, content: str) -> Citation:
        """Extract citation info from source."""
        pass

    def format_citations(self, citations: list, style: CitationStyle) -> str:
        """Format citations in specified style (APA, MLA, Chicago)."""
        pass

    def generate_bibliography(self, citations: list) -> str:
        """Generate formatted bibliography."""
        pass
```

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 3.3.1 | Create `Citation` and `CitationStyle` schemas | 30 min |
| 3.3.2 | Implement citation extraction from URLs | 2 hr |
| 3.3.3 | Implement APA formatting | 1 hr |
| 3.3.4 | Implement MLA formatting | 1 hr |
| 3.3.5 | Implement bibliography generation | 1 hr |
| 3.3.6 | Integrate with researcher tool outputs | 1 hr |

---

### Phase 4: Infrastructure Improvements (Priority: Medium-Low) ✅ COMPLETE

#### 4.1 State Persistence ✅

**Goal**: Persist LangGraph state to database for recovery.

**Status**: ✅ Complete

**Implemented**:
- `backend/app/models/graph_state.py` - GraphCheckpoint, GraphWrite, SessionRecovery models
- `backend/app/core/checkpointer.py` - DatabaseCheckpointer for LangGraph persistence
- Session recovery endpoints in status API
- Automatic checkpoint cleanup

**Tasks**:

| Task | Description | Status |
|------|-------------|--------|
| 4.1.1 | Create `GraphState` database model | ✅ Complete |
| 4.1.2 | Implement `DatabaseCheckpointer` for LangGraph | ✅ Complete |
| 4.1.3 | Add state recovery on session resume | ✅ Complete |
| 4.1.4 | Add state cleanup for old sessions | ✅ Complete |

#### 4.2 Structured Logging

**Goal**: Replace print statements with proper logging.

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 4.2.1 | Configure Python logging with structlog | 1 hr |
| 4.2.2 | Add request ID tracking | 30 min |
| 4.2.3 | Replace all print statements | 2 hr |
| 4.2.4 | Add log aggregation endpoint | 1 hr |

#### 4.3 Progress Streaming & Status Tracking

**Goal**: Real-time progress updates to frontend with detailed execution status.

**New File**: `backend/app/core/execution_tracker.py`

```python
# Proposed structure
class ExecutionPhase(str, Enum):
    PLANNING = "planning"
    RESEARCHING = "researching"
    REVIEWING = "reviewing"
    CODING = "coding"
    EDITING = "editing"
    FINALIZING = "finalizing"

class ExecutionStatus:
    """Tracks current execution state for a research session."""

    session_id: str
    current_phase: ExecutionPhase
    plan: dict                    # Orchestrator's plan
    active_agent: str             # Currently executing agent
    active_tools: list[str]       # Tools being used
    progress: float               # 0.0 - 1.0
    phase_details: dict           # Phase-specific info
    started_at: datetime
    estimated_completion: datetime

class ExecutionTracker:
    """Manages execution status across all sessions."""

    def start_session(self, session_id: str, plan: dict) -> None:
        """Initialize tracking for a new session."""
        pass

    def update_phase(self, session_id: str, phase: ExecutionPhase) -> None:
        """Update current execution phase."""
        pass

    def set_active_agent(self, session_id: str, agent: str, tools: list[str]) -> None:
        """Update active agent and tools."""
        pass

    def update_progress(self, session_id: str, progress: float, details: dict) -> None:
        """Update progress and emit WebSocket event."""
        pass

    def get_status(self, session_id: str) -> ExecutionStatus:
        """Get current execution status."""
        pass
```

**WebSocket Events**:

| Event | Payload | Description |
|-------|---------|-------------|
| `session.started` | `{session_id, plan}` | Research session initiated |
| `phase.changed` | `{session_id, phase, agent}` | Execution phase changed |
| `agent.started` | `{session_id, agent, tools}` | Agent began processing |
| `agent.progress` | `{session_id, agent, progress, detail}` | Agent progress update |
| `tool.invoked` | `{session_id, tool, args}` | Tool being executed |
| `tool.completed` | `{session_id, tool, result_summary}` | Tool finished |
| `session.completed` | `{session_id, report_summary}` | Session finished |
| `session.error` | `{session_id, error, recoverable}` | Error occurred |

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 4.3.1 | Create `ExecutionStatus` and `ExecutionTracker` classes | 2 hr |
| 4.3.2 | Add WebSocket endpoint with connection management | 2 hr |
| 4.3.3 | Implement event emission in ExecutionTracker | 1 hr |
| 4.3.4 | Add tracking hooks to orchestrator node | 1 hr |
| 4.3.5 | Add tracking hooks to all agent nodes | 2 hr |
| 4.3.6 | Add tracking hooks to tool execution | 1 hr |
| 4.3.7 | Implement progress estimation algorithm | 1 hr |
| 4.3.8 | Add REST endpoint for status polling (fallback) | 30 min |
| 4.3.9 | Write tests for execution tracker | 1 hr |

#### 4.4 Error Handling & Retry ✅

**Goal**: Robust error handling with automatic retry.

**Status**: ✅ Complete

**Implemented**:
- `backend/app/core/retry.py` - Retry decorator with exponential backoff, circuit breaker pattern
- `backend/app/core/resilient_llm.py` - Resilient LLM wrapper with automatic fallback
- `backend/app/agents/nodes/error_handler.py` - Error handler node for graph recovery
- Updated `AgentState` with error handling fields

**Tasks**:

| Task | Description | Status |
|------|-------------|--------|
| 4.4.1 | Create retry decorator with exponential backoff | ✅ Complete |
| 4.4.2 | Add retry logic to LLM calls | ✅ Complete |
| 4.4.3 | Add retry logic to tool calls | ✅ Complete |
| 4.4.4 | Implement circuit breaker for failing endpoints | ✅ Complete |
| 4.4.5 | Add error recovery in graph flow | ✅ Complete |

---

### Phase 5: Frontend Enhancements (Priority: Low)

#### 5.1 Execution Status Dashboard ✅

**Goal**: Real-time visualization of research execution progress.

**Status**: ✅ Complete

**Implemented Components**:

```
frontend/src/
├── api/status.ts                    # Status API functions
├── hooks/useExecutionStatus.ts      # WebSocket + polling hook
├── components/ExecutionStatus/
│   ├── index.ts                     # Exports
│   ├── StatusDashboard.tsx          # Main container with Mission Control theme
│   ├── PlanViewer.tsx               # Collapsible plan with task status
│   ├── AgentIndicator.tsx           # Animated agent status with pulse effects
│   ├── ToolActivity.tsx             # Terminal-style activity log
│   ├── ProgressTimeline.tsx         # Segmented progress with phase markers
│   └── PhaseIndicator.tsx           # Glowing phase badges
```

**Features Implemented**:

| Feature | Description |
|---------|-------------|
| Plan Overview | Collapsible view with task status indicators |
| Active Agent | Heartbeat pulse animation showing current agent |
| Tool Activity | Terminal-style log with typing animation effect |
| Progress Bar | Gradient progress with shimmer animation |
| Phase Timeline | Phase row with completion indicators |
| Error Display | Inline error messages with styling |
| WebSocket + Polling | Real-time updates with automatic fallback |

**Design Theme**: Mission Control / Command Center
- IBM Plex Mono font for technical aesthetic
- Cyan/emerald neon accent colors
- Grid background effects
- Pulse and glow animations
- Terminal-style activity log

**Tasks**:

| Task | Description | Status |
|------|-------------|--------|
| 5.1.1 | Create WebSocket hook for status updates | ✅ Complete |
| 5.1.2 | Create StatusDashboard container component | ✅ Complete |
| 5.1.3 | Create PlanViewer with expandable steps | ✅ Complete |
| 5.1.4 | Create AgentIndicator with status animations | ✅ Complete |
| 5.1.5 | Create ToolActivity feed component | ✅ Complete |
| 5.1.6 | Create ProgressTimeline component | ✅ Complete |
| 5.1.7 | Integrate StatusDashboard into Chat view | ✅ Complete |
| 5.1.8 | Add minimize/expand toggle for dashboard | ✅ Complete |
| 5.1.9 | Add dark mode support for status components | ✅ Complete |

#### 5.2 Plan Visualization & Editing ✅

**Goal**: Allow users to view, edit, and approve research plans before execution.

**Status**: ✅ Complete

**Implemented Components**:

```
backend/app/
├── core/execution_tracker.py    # Added plan management methods
│   ├── update_plan_task()       # Update individual tasks
│   ├── add_plan_task()          # Add new tasks
│   ├── remove_plan_task()       # Remove tasks
│   ├── reorder_plan_tasks()     # Reorder task sequence
│   ├── approve_plan()           # Approve/reject with modifications
│   └── is_plan_approved()       # Check approval status
└── api/endpoints/status.py      # Plan management API endpoints
    ├── PUT /{session_id}/plan/task/{task_id}   # Update task
    ├── POST /{session_id}/plan/task            # Add task
    ├── DELETE /{session_id}/plan/task/{task_id} # Remove task
    ├── PUT /{session_id}/plan/reorder          # Reorder tasks
    └── POST /{session_id}/plan/approve         # Approve plan

frontend/src/
├── api/status.ts                # Plan API functions
│   ├── updatePlanTask()
│   ├── addPlanTask()
│   ├── removePlanTask()
│   ├── reorderPlanTasks()
│   └── approvePlan()
└── components/ExecutionStatus/
    ├── PlanEditor.tsx           # Editable plan with task management
    └── PlanApprovalModal.tsx    # Modal for plan review and approval
```

**Features Implemented**:

| Feature | Description |
|---------|-------------|
| Task Editing | Edit task description and agent assignment |
| Task Status | Visual indicators for pending/in_progress/completed/failed |
| Add/Remove Tasks | Add new tasks or remove existing ones |
| Task Reordering | Move tasks up/down with arrow buttons |
| Plan Approval Modal | Review plan before execution begins |
| Approval Workflow | Approve, reject, or modify plan |
| Real-time Updates | Plan changes sync via WebSocket events |

**Tasks**:

| Task | Description | Status |
|------|-------------|--------|
| 5.2.1 | Create detailed PlanView component | ✅ Complete |
| 5.2.2 | Add task status indicators | ✅ Complete |
| 5.2.3 | Implement plan editing UI | ✅ Complete |
| 5.2.4 | Add plan approval workflow | ✅ Complete |

#### 5.3 Report Viewer ✅

**Goal**: Professional report viewing with navigation, export, and citation features.

**Status**: ✅ Complete

**Implemented Components**:

```
frontend/src/
├── api/reports.ts                    # Report API functions
│   ├── listTemplates()               # List available templates
│   ├── listScopes()                  # List scope options
│   ├── formatReport()                # Format report content
│   ├── parseMarkdownReport()         # Parse markdown to sections
│   └── exportReport()                # Download as MD/HTML/TXT
└── components/ReportViewer/
    ├── index.ts                      # Exports
    ├── ReportViewer.tsx              # Main viewer with markdown rendering
    ├── TableOfContents.tsx           # Navigable section list
    ├── ExportMenu.tsx                # Download dropdown (MD/HTML/TXT)
    └── CitationTooltip.tsx           # Hover previews for citations
```

**Features Implemented**:

| Feature | Description |
|---------|-------------|
| Markdown Rendering | Full markdown support with react-markdown and remark-gfm |
| Table of Contents | Collapsible sidebar with scroll-sync highlighting |
| Export Options | Download as Markdown, HTML, or Plain Text |
| Print Support | Optimized print styles for PDF export |
| Citation Tooltips | Hover previews for [1], [2], etc. markers |
| Reading Progress | Visual progress indicator in TOC |
| Fullscreen Mode | Expand report to fullscreen view |
| Copy to Clipboard | One-click copy of report content |

**Tasks**:

| Task | Description | Status |
|------|-------------|--------|
| 5.3.1 | Create ReportViewer component | ✅ Complete |
| 5.3.2 | Add table of contents navigation | ✅ Complete |
| 5.3.3 | Implement export buttons (MD/HTML/PDF) | ✅ Complete |
| 5.3.4 | Add citation hover previews | ✅ Complete |

#### 5.4 Tool Management UI ✅

**Goal**: Comprehensive tool management interface for viewing, testing, and creating tools.

**Status**: ✅ Complete

**Implemented Components**:

```
frontend/src/
├── api/tools.ts                      # Tool API functions
│   ├── listTools()                   # Get all tools with registry status
│   ├── getTool()                     # Get specific tool details
│   ├── createTool()                  # Create new dynamic tool
│   ├── executeTool()                 # Test tool execution
│   ├── updateToolStatus()            # Enable/disable tools
│   ├── deleteTool()                  # Delete custom tools
│   ├── listToolsByCategory()         # Filter by category
│   └── listToolsForAgent()           # Filter by agent type
└── components/ToolManagement/
    ├── index.ts                      # Exports
    ├── ToolManagementPage.tsx        # Main page with tabs
    ├── ToolList.tsx                  # Filterable tool grid/list
    ├── ToolCard.tsx                  # Individual tool card with actions
    ├── ToolExecutionHistory.tsx      # Execution log with stats
    └── ToolCreateWizard.tsx          # Multi-step tool creation
```

**Features Implemented**:

| Feature | Description |
|---------|-------------|
| Tool Registry View | Grid/list view with category/status filters |
| Tool Cards | Expandable cards with test, enable/disable, delete actions |
| Execution History | Timeline of tool executions with success/error stats |
| Create Wizard | 4-step wizard (basics, code, config, review) |
| Code Examples | Pre-built templates for common tool patterns |
| Category Filtering | Filter by browser, api, math, code, data, file, custom |
| Status Management | Toggle tools active/disabled |
| Navigation | Top nav bar with Chat and Tools tabs |

**Tasks**:

| Task | Description | Status |
|------|-------------|--------|
| 5.4.1 | Create ToolList component | ✅ Complete |
| 5.4.2 | Add tool execution history | ✅ Complete |
| 5.4.3 | Create tool creation wizard | ✅ Complete |

---

## Part 4: Implementation Schedule

### Recommended Order

```
Week 1-2: Phase 1 (LLM Infrastructure)
├── LLM Manager Service
├── Configuration System
└── Task Complexity Analyzer

Week 3-4: Phase 2 (Tool System)
├── Tool Registry
├── Enhanced Coder Agent
└── Built-in Tool Library

Week 5-6: Phase 3 (Report Generation)
├── Report Templates ✅
├── Enhanced Editor Agent ✅
├── Citation Manager ✅
├── Report API Endpoints ✅
└── Report Scope Configuration (NEW)

Week 7-8: Phase 4 (Infrastructure)
├── State Persistence
├── Structured Logging
├── Progress Streaming & Status Tracking (ENHANCED)
└── Error Handling

Week 9+: Phase 5 (Frontend)
├── Execution Status Dashboard (NEW)
├── Plan Visualization & Editing
├── Report Viewer
└── Tool Management UI
```

### Dependencies

```
Phase 1 (LLM) ──┬──► Phase 2 (Tools) ──► Phase 3 (Reports)
                │
                └──► Phase 4 (Infrastructure)
                           │
                           └──► Phase 5 (Frontend)
```

---

## Part 5: Technical Specifications

### 5.1 New Dependencies

**Backend** (add to `requirements.txt`):
```
langchain-anthropic>=0.1.0    # Claude API
pyyaml>=6.0                    # Config files
structlog>=24.0                # Structured logging
weasyprint>=60.0               # PDF generation
docker>=7.0                    # Sandboxed code execution
websockets>=12.0               # Real-time updates
tenacity>=8.0                  # Retry logic
```

**Frontend** (add to `package.json`):
```json
{
  "dependencies": {
    "react-markdown": "^9.0.0",
    "@tanstack/react-query": "^5.0.0",
    "socket.io-client": "^4.7.0"
  }
}
```

### 5.2 Environment Variables

**New Required**:
```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Ollama VMs (comma-separated)
OLLAMA_ENDPOINTS=http://vm1:11434,http://vm2:11434,http://localhost:11434

# Feature flags
ENABLE_CLAUDE_FALLBACK=true
ENABLE_DYNAMIC_TOOLS=true
ENABLE_CODE_EXECUTION=true
```

### 5.3 Database Migrations

**New Tables**:

```sql
-- Tool registry
CREATE TABLE tools (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    is_builtin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Graph state persistence
CREATE TABLE graph_states (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id),
    checkpoint_id VARCHAR(100),
    state_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Citations
CREATE TABLE citations (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id),
    url TEXT NOT NULL,
    title VARCHAR(500),
    author VARCHAR(200),
    date_accessed TIMESTAMP,
    metadata JSON
);
```

---

## Part 6: Testing Strategy

### 6.1 Unit Tests

| Component | Test File | Coverage Target |
|-----------|-----------|-----------------|
| LLMManager | `tests/test_llm_manager.py` | 90% |
| ToolRegistry | `tests/test_tool_registry.py` | 90% |
| ComplexityAnalyzer | `tests/test_complexity.py` | 85% |
| ReportTemplates | `tests/test_reports.py` | 85% |
| CitationManager | `tests/test_citations.py` | 90% |

### 6.2 Integration Tests

| Scenario | Test File |
|----------|-----------|
| Full research flow with Ollama | `tests/integration/test_ollama_flow.py` |
| Claude fallback on complex task | `tests/integration/test_claude_fallback.py` |
| Dynamic tool creation | `tests/integration/test_dynamic_tools.py` |
| Report generation end-to-end | `tests/integration/test_report_generation.py` |

### 6.3 Load Tests

| Scenario | Tool |
|----------|------|
| Multiple concurrent research requests | Locust |
| Ollama VM failover | Custom script |
| Long-running report generation | pytest-timeout |

---

## Part 7: Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ollama VM unavailability | High | Health checks + Claude fallback |
| Claude API rate limits | Medium | Request queuing + caching |
| Generated tool code is unsafe | High | Docker sandbox + code review |
| Report generation exceeds context | Medium | Chunked processing |
| State loss on crash | Medium | Database checkpointing |

---

## Part 8: Success Metrics

| Metric | Target |
|--------|--------|
| Research task completion rate | >95% |
| Average response time (simple) | <30s |
| Average response time (complex) | <5min |
| Tool creation success rate | >80% |
| Report quality score (manual review) | >4/5 |
| System uptime | >99% |
| LLM cost per research task | <$0.50 |

---

## Appendix A: File Change Summary

### New Files to Create

```
backend/
├── app/
│   ├── core/
│   │   ├── llm_manager.py
│   │   └── complexity_analyzer.py
│   ├── agents/
│   │   └── tools/
│   │       ├── registry.py
│   │       ├── math.py
│   │       ├── filesystem.py
│   │       ├── executor.py
│   │       ├── http.py
│   │       └── documents.py
│   └── reports/
│       ├── __init__.py
│       ├── templates/
│       │   ├── base.py
│       │   ├── research_report.py
│       │   ├── technical_analysis.py
│       │   └── executive_summary.py
│       ├── formatters/
│       │   ├── markdown.py
│       │   ├── html.py
│       │   └── pdf.py
│       └── citation_manager.py
├── config/
│   └── llm_config.yaml
└── tests/
    ├── test_llm_manager.py
    ├── test_tool_registry.py
    ├── test_complexity.py
    ├── test_reports.py
    └── integration/
        ├── test_ollama_flow.py
        ├── test_claude_fallback.py
        └── test_report_generation.py
```

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   └── llm.py              # Deprecate, redirect to llm_manager
│   ├── agents/
│   │   ├── graph.py            # Add dynamic tool binding
│   │   └── nodes/
│   │       ├── coder.py        # Major enhancement
│   │       └── editor.py       # Major enhancement
│   └── api/
│       └── endpoints/
│           └── chat.py         # Add WebSocket, tool endpoints
├── requirements.txt            # Add new dependencies
└── .env                        # Add new variables

frontend/
├── src/
│   ├── components/
│   │   ├── Chat.tsx            # Add WebSocket integration
│   │   ├── PlanView.tsx        # New component
│   │   └── ReportViewer.tsx    # New component
│   └── api.ts                  # Add new endpoints
└── package.json                # Add new dependencies
```

---

## Appendix B: Quick Reference

### Starting Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Ollama (ensure running)
ollama serve
ollama pull llama3.2
```

### Environment Setup

```bash
# Copy and edit environment file
cp backend/.env.example backend/.env

# Required variables
LINKUP_API_KEY=your_key
ANTHROPIC_API_KEY=your_key  # For Claude
OLLAMA_ENDPOINTS=http://localhost:11434
```

### Running Tests

```bash
cd backend
pytest tests/ -v
pytest tests/integration/ -v --timeout=120
```

---

*Document Version: 1.6*
*Created: 2025-01-19*
*Last Updated: 2026-01-19*

## Changelog

### v1.6 (2026-01-19)
- Completed Phase 5.4: Tool Management UI
  - Created Tool API functions (list, get, create, execute, update status, delete)
  - Created ToolList component with grid/list views and filtering by category/status
  - Created ToolCard component with test, enable/disable, and delete actions
  - Created ToolExecutionHistory component with execution timeline and stats
  - Created ToolCreateWizard with 4-step flow (basics, code, config, review)
  - Added code examples for quick tool creation templates
  - Integrated Tool Management page into main navigation
  - Updated App.tsx with top navigation bar for Chat/Tools switching
- Updated completion to ~95%
- Frontend builds successfully

### v1.5 (2026-01-19)
- Completed Phase 5.3: Report Viewer
  - Created ReportViewer component with full markdown rendering (react-markdown + remark-gfm)
  - Added TableOfContents with scroll-sync and reading progress indicator
  - Implemented ExportMenu with Markdown, HTML, and Plain Text download options
  - Added CitationTooltip for hover previews on citation markers [1], [2], etc.
  - Integrated ReportViewer into Chat component with automatic report detection
  - Added fullscreen mode, copy to clipboard, and print support
- Frontend builds successfully with new dependencies

### v1.4 (2026-01-19)
- Completed Phase 5.2: Plan Visualization & Editing
  - Added plan management methods to ExecutionTracker (update, add, remove, reorder tasks)
  - Created REST API endpoints for plan editing and approval
  - Created PlanEditor component with task editing, adding, removing, reordering
  - Created PlanApprovalModal for plan review before execution
  - Added plan approval workflow with approve/reject/modify options
  - Integrated plan editing into StatusDashboard with edit toggle
  - Added PlanApprovalStatus and plan_waiting_approval to ExecutionStatus
- All 86 tests passing, frontend builds successfully

### v1.3 (2026-01-19)
- Completed Phase 5.1: Execution Status Dashboard
  - Created "Mission Control" themed status dashboard
  - Implemented StatusDashboard, PlanViewer, AgentIndicator, ToolActivity, ProgressTimeline, PhaseIndicator components
  - Added WebSocket hook with automatic polling fallback
  - Added status API functions for frontend
  - Integrated dashboard into Chat component
  - Added custom CSS animations (pulse, shimmer, blink, scan-line)
  - IBM Plex Mono font for technical aesthetic

### v1.2 (2026-01-19)
- Completed Phase 4.1: State Persistence
  - Created GraphCheckpoint, GraphWrite, SessionRecovery database models
  - Implemented DatabaseCheckpointer for LangGraph state persistence
  - Added session recovery API endpoints
- Completed Phase 4.4: Error Handling & Retry
  - Created retry decorator with exponential backoff
  - Implemented circuit breaker pattern for failing endpoints
  - Created resilient LLM wrapper with automatic fallback
  - Added error handler node for graph flow recovery
  - Updated AgentState with error handling fields
- Added 22 new tests for retry and circuit breaker functionality
- All 86 tests passing

### v1.1 (2026-01-19)
- Added Phase 3.4: Report Scope Configuration
- Enhanced Phase 4.3: Progress Streaming & Status Tracking with ExecutionTracker
- Added Phase 5.1: Execution Status Dashboard
- Marked Phase 3 components (3.1-3.3) as complete
- Renumbered Phase 5 sections
