import requests
import time
import json

BASE_URL = "http://localhost:8000/api/chat"

def test_agent():
    print("Creating session...")
    resp = requests.post(f"{BASE_URL}/sessions", json={"title": "Verification"})
    if resp.status_code != 200:
        print("Failed to create session:", resp.text)
        return

    session_id = resp.json()["id"]
    print(f"Session ID: {session_id}")

    print("Sending message...")
    msg_resp = requests.post(f"{BASE_URL}/sessions/{session_id}/messages",
                             json={"role": "user", "content": "What is the capital of France?"})

    if msg_resp.status_code != 200:
        print("Failed to send message:", msg_resp.text)
        return

    print("Message sent. Waiting for agent processing (polling)...")

    # Poll for assistant message
    for i in range(30):
        time.sleep(2)
        s_resp = requests.get(f"{BASE_URL}/sessions/{session_id}")
        data = s_resp.json()
        messages = data.get("messages", [])
        if len(messages) > 1:
            last_msg = messages[-1]
            if last_msg["role"] == "assistant":
                print("\n--- Assistant Response ---")
                print(last_msg["content"])
                print("--------------------------")
                return

    print("Timeout waiting for response.")

if __name__ == "__main__":
    test_agent()
