# Research Agent - Implementation Analysis & Plan

## Executive Summary

This document provides a comprehensive analysis of the current research agent implementation and a detailed plan to reach the final vision: a multi-agent research system with orchestrated LLM access across Ollama VMs, Claude API fallback, dynamic tool creation, and professional-grade report generation.

**Current Completion: ~50-60%**

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

### Phase 4: Infrastructure Improvements (Priority: Medium-Low)

#### 4.1 State Persistence

**Goal**: Persist LangGraph state to database for recovery.

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 4.1.1 | Create `GraphState` database model | 30 min |
| 4.1.2 | Implement `DatabaseCheckpointer` for LangGraph | 3 hr |
| 4.1.3 | Add state recovery on session resume | 1 hr |
| 4.1.4 | Add state cleanup for old sessions | 1 hr |

#### 4.2 Structured Logging

**Goal**: Replace print statements with proper logging.

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 4.2.1 | Configure Python logging with structlog | 1 hr |
| 4.2.2 | Add request ID tracking | 30 min |
| 4.2.3 | Replace all print statements | 2 hr |
| 4.2.4 | Add log aggregation endpoint | 1 hr |

#### 4.3 Progress Streaming

**Goal**: Real-time progress updates to frontend.

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 4.3.1 | Add WebSocket endpoint | 2 hr |
| 4.3.2 | Emit progress events from each agent | 2 hr |
| 4.3.3 | Update frontend to consume WebSocket | 2 hr |
| 4.3.4 | Add progress indicators to UI | 2 hr |

#### 4.4 Error Handling & Retry

**Goal**: Robust error handling with automatic retry.

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 4.4.1 | Create retry decorator with exponential backoff | 1 hr |
| 4.4.2 | Add retry logic to LLM calls | 1 hr |
| 4.4.3 | Add retry logic to tool calls | 1 hr |
| 4.4.4 | Implement circuit breaker for failing endpoints | 2 hr |
| 4.4.5 | Add error recovery in graph flow | 2 hr |

---

### Phase 5: Frontend Enhancements (Priority: Low)

#### 5.1 Plan Visualization

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 5.1.1 | Create PlanView component | 2 hr |
| 5.1.2 | Add task status indicators | 1 hr |
| 5.1.3 | Implement plan editing UI | 3 hr |
| 5.1.4 | Add plan approval workflow | 2 hr |

#### 5.2 Report Viewer

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 5.2.1 | Create ReportViewer component | 2 hr |
| 5.2.2 | Add table of contents navigation | 1 hr |
| 5.2.3 | Implement export buttons (MD/HTML/PDF) | 2 hr |
| 5.2.4 | Add citation hover previews | 2 hr |

#### 5.3 Tool Management UI

**Tasks**:

| Task | Description | Estimate |
|------|-------------|----------|
| 5.3.1 | Create ToolList component | 1 hr |
| 5.3.2 | Add tool execution history | 2 hr |
| 5.3.3 | Create tool creation wizard | 3 hr |

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
├── Report Templates
├── Enhanced Editor Agent
└── Citation Manager

Week 7-8: Phase 4 (Infrastructure)
├── State Persistence
├── Structured Logging
├── Progress Streaming
└── Error Handling

Week 9+: Phase 5 (Frontend)
├── Plan Visualization
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

*Document Version: 1.0*
*Created: 2025-01-19*
*Last Updated: 2025-01-19*
