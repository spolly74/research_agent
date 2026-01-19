from typing import TypedDict, Annotated, List, Union, Optional
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    Shared state for the agent graph.

    All agents can read and update this state during execution.
    """
    # Core state
    messages: Annotated[List[BaseMessage], operator.add]
    next_step: str

    # Session tracking
    session_id: Optional[str]  # Unique session identifier for tracking

    # Research data
    research_data: List[str]
    review_feedback: str
    code_output: str
    final_report: str

    # Planning
    plan: dict  # serialized Plan model
    scope_config: Optional[dict]  # scope configuration from orchestrator

    # Error handling
    last_error: Optional[str]  # Last error message for recovery
    failed_node: Optional[str]  # Name of the node that failed
    error_count: int  # Number of errors encountered
    skip_tools: List[str]  # Tools to skip due to failures
    error_handled: bool  # Whether error has been handled
