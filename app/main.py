"""
Main application module.
"""
from fastapi import FastAPI
import uvicorn
from routes.chat import router as chat_router
from services.db import init_db

# Initialize the application
app = FastAPI(title="Omnivoltaic Support Bot API")

# Initialize database
init_db()

# Register routes
app.include_router(chat_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)