from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

def editor_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()

    You are an Editor Agent. Your job is to provide the final answer to the user.
    Synthesize the research, code, and reviews into a clear, concise response.

    CRITICAL: You MUST produce a response. If the research is valid, summarize it.
    If the previous messages contain the answer (e.g. from the Researcher), repeat it clearly.
    Do not be silent.
    """)

    print("--- Editor Node: Invoking LLM ---")
    response = llm.invoke([system_msg] + messages)
    print(f"--- Editor Node: response length: {len(response.content)} ---")
    return {"messages": [response], "final_report": response.content}
