import requests
import time
import json

BASE_URL = "http://localhost:8000/api/chat"

def check_response(session_id):
    print("Waiting for response...")
    for i in range(45):
        time.sleep(2)
        s_resp = requests.get(f"{BASE_URL}/sessions/{session_id}")
        data = s_resp.json()
        messages = data.get("messages", [])
        if len(messages) > 1:
            last_msg = messages[-1]
            if last_msg["role"] == "assistant":
                print("\n--- Assistant Response ---")
                print(last_msg["content"][:200] + "...")
                print("--------------------------")
                return
    print("Timeout.")

def test_flow(query, title):
    print(f"\nTesting Flow: {title} ('{query}')")
    resp = requests.post(f"{BASE_URL}/sessions", json={"title": title})
    session_id = resp.json()["id"]
    requests.post(f"{BASE_URL}/sessions/{session_id}/messages",
                  json={"role": "user", "content": query})
    check_response(session_id)

if __name__ == "__main__":
    # Test 1: Direct Answer (Should be fast, no tools)
    test_flow("What is the capital of France?", "Orchestrator Direct")

    # Test 2: Research (Should take longer, use tools)
    test_flow("What is the latest iPhone model released in 2024?", "Orchestrator Research")
