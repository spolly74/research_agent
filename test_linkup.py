import os
from dotenv import load_dotenv
from linkup import LinkupClient

load_dotenv("backend/.env")

def test_linkup():
    api_key = os.getenv("LINKUP_API_KEY")
    print(f"API Key present: {bool(api_key)}")

    if not api_key:
        return

    try:
        client = LinkupClient(api_key=api_key)
        results = client.search(
            query="What are the latest features of Python 3.13 released in 2024?",
            depth="standard",
            output_type="searchResults"
        )
        print("--- Results ---")
        print(f"Count: {len(results.results)}")
        if len(results.results) > 0:
            print(results.results[0].name)
            print(results.results[0].url)
            print(results.results[0].content[:200])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_linkup()
