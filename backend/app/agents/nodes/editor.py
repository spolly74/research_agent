from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

def editor_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()

    system_msg = SystemMessage(content="""
    You are an Editor Agent. Your job is to provide the final answer to the user.
    Synthesize the research, code, and reviews into a clear, concise response.
    Do NOT include meta-commentary like "Here is the final report". Just answer the question directly.
    """)

    response = llm.invoke([system_msg] + messages)
    return {"messages": [response], "final_report": response.content}
