"""
Service for generating embeddings.
"""
# Import the actual implementation from your getembeddings module

from openai import OpenAI
from config import LLM_API_KEY

open_client = OpenAI(api_key=LLM_API_KEY)
def get_embedding(text, model="text-embedding-3-small"):
    """
    Given a piece of text, this function calls OpenAI's embeddings.create endpoint
    using the new recommended API, and returns the embedding vector.
    """
    response = open_client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

def generate_embedding(text: str) -> list:
    """
    Generates an embedding vector for the provided text.
    
    Args:
        text: The text to embed
        
    Returns:
        A list representing the embedding vector
    """
    return get_embedding(text)