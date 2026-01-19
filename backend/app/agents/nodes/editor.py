from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType

def editor_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm(task_type=TaskType.EDITOR)

    system_msg = SystemMessage(content="""
    You are an Editor Agent. Your job is to provide the final answer to the user.
    Synthesize the research, code, and reviews into a clear, concise response.

    CRITICAL: You MUST produce a response. If the research is valid, summarize it.
    If the previous messages contain the answer (e.g. from the Researcher), repeat it clearly.
    Do not be silent.
    """)

    print("--- Editor Node: Invoking LLM ---")
    print(f"--- Editor Node: Input Messages: {len(messages)} messages ---")
    if len(messages) > 0:
        print(f"--- Editor Node: Last Message Role: {messages[-1].type} ---")
        print(f"--- Editor Node: Last Message Content: {messages[-1].content[:200]}... ---")
    response = llm.invoke([system_msg] + messages)
    final_content = response.content

    # Smart Fallback: If LLM fails, use the last message if it has content
    if not final_content or len(final_content.strip()) == 0:
        if len(messages) > 0 and messages[-1].content:
            print("--- Editor Node: LLM empty, using last message as fallback ---")
            final_content = messages[-1].content
        else:
            final_content = "I'm sorry, I couldn't generate a final report based on the research. Please try refining your request."

    return {"messages": [response], "final_report": final_content}
