from pydantic import BaseModel, Field
from typing import List, Optional


class Task(BaseModel):
    id: int = Field(description="Unique identifier for the task, starting from 1")
    description: str = Field(description="Clear and concise description of the task")
    assigned_agent: str = Field(description="The role of the agent assigned to this task (e.g., 'researcher', 'writer', 'reviewer')")
    status: str = Field(default="pending", description="Task status: pending, in_progress, completed, failed")
    result: str = Field(default="", description="Summary of the task output")


class ResearchParameters(BaseModel):
    """Parameters controlling research depth based on report scope."""
    min_sources: int = Field(default=5, description="Minimum number of sources to gather")
    max_sources: int = Field(default=10, description="Maximum number of sources to gather")
    depth: str = Field(default="balanced", description="Research depth: minimal, balanced, or detailed")
    focus: str = Field(default="balanced", description="Research focus: key_facts, balanced, or comprehensive")


class ScopeInfo(BaseModel):
    """Report scope configuration."""
    scope: str = Field(default="standard", description="Scope level: brief, standard, comprehensive, or custom")
    target_pages: int = Field(default=4, description="Target number of pages")
    target_word_count: int = Field(default=2000, description="Target word count")
    research_params: ResearchParameters = Field(default_factory=ResearchParameters, description="Research depth parameters")


class Plan(BaseModel):
    main_goal: str = Field(description="The overall objective of the research plan")
    tasks: List[Task] = Field(description="List of tasks to achieve the main goal")
    current_task_id: int = Field(default=0, description="ID of the task currently in progress. 0 if starting.")
    status: str = Field(default="planning", description="Plan status: planning, active, completed, failed")
    scope: Optional[ScopeInfo] = Field(default=None, description="Report scope configuration (auto-detected from query)")
