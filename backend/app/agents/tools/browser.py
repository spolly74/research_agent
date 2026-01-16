import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from playwright.sync_api import sync_playwright
import html2text
from linkup import LinkupClient

load_dotenv()

@tool
def browser_search(query: str):
    """
    Searches the web using the Linkup API to get accurate results.
    """
    api_key = os.getenv("LINKUP_API_KEY")
    if not api_key:
        return "Error: LINKUP_API_KEY not found in environment variables."

    try:
        client = LinkupClient(api_key=api_key)
        results = client.search(
            query=query,
            depth="standard",
            output_type="searchResults"
        )

        # Format results for the LLM
        formatted_output = ""
        for result in results.results:
            formatted_output += f"Title: {result.name}\n"
            formatted_output += f"URL: {result.url}\n"
            formatted_output += f"Content: {result.content}\n\n"

        return formatted_output[:10000] # Cap output size

    except Exception as e:
        return f"Error performing search: {str(e)}"

@tool
def visit_page(url: str):
    """
    Visits a specific URL and returns the page content as markdown.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            content = page.content()
            browser.close()

            h = html2text.HTML2Text()
            h.ignore_links = False
            return h.handle(content)[:15000]
        except Exception as e:
            browser.close()
            return f"Error visiting page: {str(e)}"
