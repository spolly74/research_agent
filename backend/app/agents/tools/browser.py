from langchain_core.tools import tool
from playwright.sync_api import sync_playwright
import html2text

@tool
def browser_search(query: str):
    """
    Searches the web using a real browser to get results.
    Useful for getting current information when API search is not available.
    """
    with sync_playwright() as p:
        # Use headless=True for production, False to see it work
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Use the HTML-only version of DDG for better scraping compatibility
        # Use the HTML-only version of DDG for better scraping compatibility
        search_url = f"https://html.duckduckgo.com/html/?q={query}&kl=us-en"
        page.goto(search_url)

        # Extract text specifically from the search results
        # DDG HTML version uses .result__body for snippets
        content = page.evaluate("""() => {
            const results = Array.from(document.querySelectorAll('.result__body'));
            return results.map(r => r.innerText).join('\\n\\n');
        }""")

        if not content:
            # Fallback if specific selector fails
            print("--- Browser Tool: specific selector failed, grabbing body ---")
            content = page.evaluate("document.body.innerText")

        browser.close()

        print(f"--- Browser Tool: Content length: {len(content)} ---")
        return content[:8000] # Truncate to avoid massive context

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
