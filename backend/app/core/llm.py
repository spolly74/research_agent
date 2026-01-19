from langchain_ollama import ChatOllama
import os

def get_llm(model: str = "llama3.2"):
    """
    Returns a ChatOllama instance.

    By default, connects to Ollama at http://localhost:11434.
    You can override this by setting the OLLAMA_BASE_URL environment variable.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    llm = ChatOllama(
        model=model,
        temperature=0,
        base_url=base_url,
    )
    return llm
