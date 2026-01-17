from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_plan_generation():
    print("--- 1. Creating Session ---")
    response = client.post("/api/chat/sessions", json={"title": "Test Plan"})
    assert response.status_code == 200
    session_id = response.json()["id"]
    print(f"Session ID: {session_id}")

    print("--- 2. Sending Request (Should trigger Orchestrator) ---")
    # We use a complex request to ensure it generates a plan (not just 'ANSWER')
    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"content": "Research the history of the diode and write a python script to plot its IV curve.", "role": "user"}
    )
    assert response.status_code == 200
    print("Request processed.")

    print("--- 3. Checking for Plan ---")
    response = client.get(f"/api/chat/sessions/{session_id}/plan")
    assert response.status_code == 200
    data = response.json()

    print("Plan Status:", data["status"])
    if data["plan"]:
        print("Plan Goal:", data["plan"]["main_goal"])
        print("Tasks:")
        for t in data["plan"]["tasks"]:
            print(f"- {t['description']} ({t['assigned_agent']})")
    else:
        print("No plan found in state.")

if __name__ == "__main__":
    test_plan_generation()
