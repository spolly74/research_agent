from pydantic import BaseModel, Field
from typing import List, Optional

class Task(BaseModel):
    id: int = Field(description="Unique identifier for the task, starting from 1")
    description: str = Field(description="Clear and concise description of the task")
    assigned_agent: str = Field(description="The role of the agent assigned to this task (e.g., 'researcher', 'writer', 'reviewer')")
    status: str = Field(default="pending", description="Task status: pending, in_progress, completed, failed")
    result: str = Field(default="", description="Summary of the task output")

class Plan(BaseModel):
    main_goal: str = Field(description="The overall objective of the research plan")
    tasks: List[Task] = Field(description="List of tasks to achieve the main goal")
    current_task_id: int = Field(default=0, description="ID of the task currently in progress. 0 if starting.")
    status: str = Field(default="planning", description="Plan status: planning, active, completed, failed")
