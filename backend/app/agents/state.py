from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next_step: str
    research_data: List[str]
    review_feedback: str
    code_output: str
    final_report: str
