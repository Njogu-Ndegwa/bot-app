"""
Chat endpoint routes.
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from models.schemas import QueryRequest, ChatResponse
from services.db import get_user_conversation_history, save_conversation
from services.vector_store import VectorStore
from services.llm import create_system_prompt, generate_response

router = APIRouter()
vector_store = VectorStore()

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat interactions.

    This endpoint:
    1. Accepts WebSocket connections.
    2. Receives JSON messages containing user_id and question.
    3. Retrieves relevant documents and conversation history.
    4. Generates a response using the LLM.
    5. Sends the response and updated chat history back to the client.
    6. Saves the conversation to the database.
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            user_id = data.get("user_id")
            question = data.get("question")

            # Send conversation history upon first connection
            if user_id and question is None:  # If no question, just the user_id
                # Retrieve the user's conversation history
                user_conversation = get_user_conversation_history(user_id)
                await websocket.send_json({
                    "history": user_conversation
                })
                continue

            # Validate input
            if not user_id or not question:
                await websocket.send_json({"error": "Missing user_id or question"})
                continue

            try:
                # Get relevant documents from vector store
                relevant_docs = vector_store.query(question)

                # Create system prompt with relevant docs
                system_prompt = create_system_prompt(relevant_docs)

                # Build message list starting with system prompt
                messages = [{"role": "system", "content": system_prompt}]

                # Add user's conversation history
                user_conversation = get_user_conversation_history(user_id)
                for exchange in user_conversation:
                    messages.append({"role": "user", "content": exchange['question']})
                    messages.append({"role": "assistant", "content": exchange['answer']})

                # Add the current question
                messages.append({"role": "user", "content": question})

                # Generate response from LLM
                response_content = await generate_response(messages)

                # Save conversation to database
                save_conversation(user_id, question, response_content)

                # Manually append the new exchange to the history
                updated_history = user_conversation + [{"question": question, "answer": response_content}]

                # Send response and updated history back to client
                await websocket.send_json({
                    "response": response_content,
                    "history": updated_history
                })

            except Exception as e:
                # Send error message if processing fails
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        print("Client disconnected")
