from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType

def coder_node(state: AgentState):
    messages = state["messages"]
    # Coder defaults to Claude for better code generation
    llm = get_llm(task_type=TaskType.CODER)

    system_msg = SystemMessage(content="""
    You are a Coder Agent. Your job is to write python tools or scripts if needed.
    For now, analyze if any custom code is needed to solve the user's request.
    """)

    response = llm.invoke([system_msg] + messages)
    return {"messages": [response], "code_output": response.content}
