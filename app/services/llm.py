# """
# LLM service for generating responses.
# """
# from litellm import acompletion
# from config import LLM_MODEL, LLM_API_KEY

# async def generate_response(messages: list) -> str:
#     """
#     Generate a response using the LLM model.
    
#     Args:
#         messages: List of messages (system, user, assistant)
        
#     Returns:
#         The LLM's response
#     """
#     response = await acompletion(
#         model=LLM_MODEL,
#         messages=messages,
#         api_key=LLM_API_KEY
#     )
    
#     return response.choices[0].message.content

# def create_system_prompt(context_docs: str) -> str:
#     """
#     Create the system prompt with context documents.
    
#     Args:
#         context_docs: Relevant documents as context
        
#     Returns:
#         Formatted system prompt
#     """
#     return f"""
#     You are a customer support agent representing Omnivoltaic. Your task is to answer customer queries using the product and article information provided. 

#     Respond as if you are an expert from Omnivoltaic, speaking naturally and conversationally. Your responses should reflect the company's voice and avoid formalities like referencing "documents" or "details in the document." Focus on providing straightforward, clear, and helpful answers to the user's questions. 

#     Instead of saying phrases like "mentioned in the document," or "described in the documents," respond as you would in a real customer support conversation. For example, use phrases like "At Omnivoltaic, we offer..." or "Our products include..." to convey the necessary information.

#     Please ensure your answer is concise, direct, and customer-friendly.

#     Here's the relevant information for your query:
        
#     {context_docs}
#     """


# async def analyze_question(question: str, user_conversation: list) -> str:
#     """
#     Analyzes if a question is a follow-up or a unique question.
#     For follow-up questions, it rewrites them with context from previous conversation.
#     For unique questions, it returns the original question.
    
#     Args:
#         question: The current user question
#         user_conversation: List of previous Q&A exchanges [{"question": str, "answer": str}]
        
#     Returns:
#         str: Either the original question or a rewritten question with context
#     """
#     if not user_conversation:
#         return question  # No conversation history, so must be a unique question
    
#     # Prepare context for the LLM to analyze
#     analysis_prompt = f"""
#     Analyze the following conversation and determine if the latest question is a follow-up question
#     or a unique question. If it's a follow-up, rewrite it to include the necessary context.
#     If it's a unique question, return the original question unchanged.
    
#     Previous conversation:
#     """
    
#     # Add conversation history
#     for i, exchange in enumerate(user_conversation[-3:]):  # Only use the last 3 exchanges to save context
#         analysis_prompt += f"\nQ{i+1}: {exchange['question']}\nA{i+1}: {exchange['answer']}\n"
    
#     analysis_prompt += f"\nLatest question: {question}\n\nInstructions:\n"
#     analysis_prompt += """
#     1. If this is a follow-up question that relies on previous context (contains pronouns like "it", "they", 
#        "this", "that", refers to something previously discussed, or is incomplete without context), 
#        rewrite it to be self-contained with relevant context.
#     2. If this is a brand new question unrelated to previous exchanges, return the original question unchanged.
#     3. Start your response with either "REWRITTEN:" followed by the rewritten question, or "ORIGINAL:" 
#        followed by the unchanged question.
#     """
    
#     # Prepare messages for LLM
#     messages = [
#         {"role": "system", "content": "You are an AI assistant that analyzes conversations to determine if questions are follow-ups or unique questions."},
#         {"role": "user", "content": analysis_prompt}
#     ]
    
#     # Use the same LLM to analyze the question
#     response = await generate_response(messages)
    
#     # Parse the response to get the analyzed question
#     if response.startswith("REWRITTEN:"):
#         return response.replace("REWRITTEN:", "").strip()
#     elif response.startswith("ORIGINAL:"):
#         return response.replace("ORIGINAL:", "").strip()
#     else:
#         # If the format is not as expected, return the original question to be safe
#         return question


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
    # Check if the last user message is about pricing with LLM
    if messages and messages[-1]["role"] == "user":
        is_pricing = await check_if_pricing_question(messages[-1]["content"])
        if is_pricing:
            return "Please contact our sales team at team_sales@omnivoltaic.com to get a quote."
    
    response = await acompletion(
        model=LLM_MODEL,
        messages=messages,
        api_key=LLM_API_KEY
    )
    return response.choices[0].message.content

async def check_if_pricing_question(question: str) -> bool:
    """
    Use the LLM to determine if a question is related to pricing.
    
    Args:
        question: The user's question
        
    Returns:
        True if it's a pricing-related question, False otherwise
    """
    pricing_detection_prompt = [
        {"role": "system", "content": """
You are a classifier that determines if a question is asking about pricing, costs, or requesting a quote.
Output only "YES" if the question is related to pricing, costs, or requesting a quote.
Output only "NO" if the question is not about pricing.
        """},
        {"role": "user", "content": f"Question: {question}\nIs this a question about pricing?"}
    ]
    
    print(LLM_MODEL, LLM_API_KEY, "LLM API Key")
    # Use a smaller response size since we only need YES/NO
    response = await acompletion(
        model=LLM_MODEL,
        messages=pricing_detection_prompt,
        api_key=LLM_API_KEY,
        max_tokens=5  # We only need a short YES/NO response
    )
    print(response, "Is Pricing question")
    answer = response.choices[0].message.content.strip().upper()
    return "YES" in answer

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


async def analyze_question(question: str, user_conversation: list) -> str:
    """
    Analyzes if a question is a follow-up or a unique question.
    For follow-up questions, it rewrites them with context from previous conversation.
    For unique questions, it returns the original question.
    
    Args:
        question: The current user question
        user_conversation: List of previous Q&A exchanges [{"question": str, "answer": str}]
        
    Returns:
        str: Either the original question or a rewritten question with context
    """
    # No need to check for pricing questions here as that's handled in generate_response
    if not user_conversation:
        return question  # No conversation history, so must be a unique question
    
    # Prepare context for the LLM to analyze
    analysis_prompt = f"""
    Analyze the following conversation and determine if the latest question is a follow-up question
    or a unique question. If it's a follow-up, rewrite it to include the necessary context.
    If it's a unique question, return the original question unchanged.
    
    Previous conversation:
    """
    
    # Add conversation history
    for i, exchange in enumerate(user_conversation[-3:]):  # Only use the last 3 exchanges to save context
        analysis_prompt += f"\nQ{i+1}: {exchange['question']}\nA{i+1}: {exchange['answer']}\n"
    
    analysis_prompt += f"\nLatest question: {question}\n\nInstructions:\n"
    analysis_prompt += """
    1. If this is a follow-up question that relies on previous context (contains pronouns like "it", "they", 
       "this", "that", refers to something previously discussed, or is incomplete without context), 
       rewrite it to be self-contained with relevant context.
    2. If this is a brand new question unrelated to previous exchanges, return the original question unchanged.
    3. Start your response with either "REWRITTEN:" followed by the rewritten question, or "ORIGINAL:" 
       followed by the unchanged question.
    """
    
    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": "You are an AI assistant that analyzes conversations to determine if questions are follow-ups or unique questions."},
        {"role": "user", "content": analysis_prompt}
    ]
    
    # Use the same LLM to analyze the question
    response = await generate_response(messages)
    
    # Parse the response to get the analyzed question
    if response.startswith("REWRITTEN:"):
        return response.replace("REWRITTEN:", "").strip()
    elif response.startswith("ORIGINAL:"):
        return response.replace("ORIGINAL:", "").strip()
    else:
        # If the format is not as expected, return the original question to be safe
        return question