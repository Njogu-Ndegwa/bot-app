"""
LLM service for generating responses.
"""
from litellm import acompletion
from config import LLM_MODEL, LLM_API_KEY

async def generate_response(messages: list) -> str:
    """
    Generate a response using the LLM model.
    
    Args:
        messages: List of messages (system, user, assistant)
        
    Returns:
        The LLM's response
    """
    response = await acompletion(
        model=LLM_MODEL,
        messages=messages,
        api_key=LLM_API_KEY
    )
    
    return response.choices[0].message.content

def create_system_prompt(context_docs: str) -> str:
    """
    Create the system prompt with context documents.
    
    Args:
        context_docs: Relevant documents as context
        
    Returns:
        Formatted system prompt
    """
    return f"""
    You are a customer support agent representing Omnivoltaic. Your task is to answer customer queries using the product and article information provided. 

    Respond as if you are an expert from Omnivoltaic, speaking naturally and conversationally. Your responses should reflect the company's voice and avoid formalities like referencing "documents" or "details in the document." Focus on providing straightforward, clear, and helpful answers to the user's questions. 

    Instead of saying phrases like "mentioned in the document," or "described in the documents," respond as you would in a real customer support conversation. For example, use phrases like "At Omnivoltaic, we offer..." or "Our products include..." to convey the necessary information.

    Please ensure your answer is concise, direct, and customer-friendly.

    Here's the relevant information for your query:
        
    {context_docs}
    """

    