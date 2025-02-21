# app/config.py
"""Configuration settings for the application."""
import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Database settings
DB_PATH = os.getenv("DB_PATH", "conversation_history.db")

# Vector DB settings
CHROMA_PATH = os.getenv("CHROMA_PATH", "./my_chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "document_chunks")

# LLM settings
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
LLM_API_KEY = os.getenv("LLM_API_KEY")

# Optional: Validate critical configuration
if not LLM_API_KEY:
    print("WARNING: LLM_API_KEY environment variable is not set")