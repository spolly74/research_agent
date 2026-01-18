from app.agents.nodes.orchestrator import orchestrator_node
from langchain_core.messages import HumanMessage
from app.agents.state import AgentState

def test_node():
    print("--- Testing Orchestrator Node Directly ---")
    state = {
        "messages": [HumanMessage(content="Research the effective range of a standard bluetooth module.")],
        "plan": None
    }

    try:
        result = orchestrator_node(state)
        print("Node executed successfully.")
        print("Next Step:", result.get("next_step"))
        plan = result.get("plan")
        if plan:
            print("Plan Main Goal:", plan["main_goal"])
            print("Tasks:", len(plan["tasks"]))
    except Exception as e:
        print(f"Node Failed: {e}")

if __name__ == "__main__":
    test_node()
