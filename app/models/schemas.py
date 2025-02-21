"""
Pydantic models for request and response validation.
"""
from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str
    user_id: str

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    reasoning: Optional[str] = None