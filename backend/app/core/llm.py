from langchain_ollama import ChatOllama
import os

def get_llm(model: str = "llama3.2"):
    """
    Returns a ChatOllama instance.
    Assumes Ollama is running locally on default port 11434.
    """
    llm = ChatOllama(
        model=model,
        temperature=0,
    )
    return llm
