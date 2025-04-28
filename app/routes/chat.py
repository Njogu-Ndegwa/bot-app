"""
Chat endpoint routes.
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Response
from models.schemas import QueryRequest, ChatResponse
from services.db import get_user_conversation_history, save_conversation
from services.vector_store import VectorStore
from services.llm import create_system_prompt, generate_response, analyze_question
from config import FACEBOOK_VERIFY_TOKEN, PAGE_ACCESS_TOKEN, WHATSAPP_TOKEN
import requests
import json
from hepler import rebuild_vector_db
import asyncio

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
            user_conversation = get_user_conversation_history(user_id)
            # Send conversation history upon first connection
            if user_id and question is None:  # If no question, just the user_id
                # Retrieve the user's conversation history

                await websocket.send_json({
                    "history": user_conversation
                })
                continue

            # Validate input
            if not user_id or not question:
                await websocket.send_json({"error": "Missing user_id or question"})
                continue

            try:

                analyzed_question = await analyze_question(question, user_conversation)
                print(analyzed_question, "Analyzed question")
                # Get relevant documents from vector store
                relevant_docs = vector_store.query(analyzed_question)
                print(relevant_docs, "-----55---")
                # Create system prompt with relevant docs
                system_prompt = create_system_prompt(relevant_docs)

                # Build message list starting with system prompt
                messages = [{"role": "system", "content": system_prompt}]

                # Add user's conversation history

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


# Webhook verification endpoint (GET)
@router.get("/bot-webhook")
async def verify_webhook(request: Request):
    """
    Handles webhook verification requests from Facebook.

    Facebook sends a GET request with query parameters to verify the webhook:
    - hub.mode: Should be "subscribe".
    - hub.verify_token: Must match the predefined VERIFY_TOKEN.
    - hub.challenge: Must be returned as the response body if verification succeeds.
    """
    query_params = request.query_params
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token")
    challenge = query_params.get("hub.challenge")
    
    print(token, "Token")
    print(FACEBOOK_VERIFY_TOKEN, "Facebook Verify token")
    print(mode, "---117")
    if mode == "subscribe" and token == FACEBOOK_VERIFY_TOKEN:
        print("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    else:
        print("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")


# # Webhook message handler (POST)
# @router.post("/bot-webhook")
# async def handle_incoming_messages(request: Request):
#     """
#     Handles incoming messages from Facebook Messenger.

#     This endpoint:
#     1. Parses the incoming webhook payload.
#     2. Processes each messaging event containing a text message.
#     3. Retrieves conversation history using sender_id as user_id.
#     4. Analyzes the message and queries the vector store.
#     5. Generates an LLM response based on the system prompt and history.
#     6. Saves the conversation to the database.
#     7. Sends the response back to the user via the Facebook Messenger API.
#     8. Returns a success status to acknowledge receipt.
#     """
#     try:
#         # Parse the incoming request payload
#         payload = await request.json()
#         print(f"Received Webhook Payload: {json.dumps(payload, indent=2)}")

#         # Process each messaging event
#         for entry in payload.get("entry", []):
#             for messaging_event in entry.get("messaging", []):
#                 if "message" in messaging_event:
#                     sender_id = messaging_event["sender"]["id"]
#                     message_text = messaging_event["message"].get("text", "")
#                     print(f"Message from {sender_id}: {message_text}")

#                     # Skip if no text content (e.g., attachments not handled yet)
#                     if not message_text:
#                         print(f"No text content in message from {sender_id}, skipping")
#                         continue

#                     try:
#                         # Use sender_id as user_id
#                         user_id = sender_id
#                         user_conversation = get_user_conversation_history(user_id)

#                         # Analyze the incoming message
#                         analyzed_question = await analyze_question(message_text, user_conversation)

#                         # Query vector store for relevant documents
#                         relevant_docs = vector_store.query(analyzed_question)

#                         # Create system prompt with relevant documents
#                         system_prompt = create_system_prompt(relevant_docs)

#                         # Build message list: system prompt + history + current message
#                         messages = [{"role": "system", "content": system_prompt}]
#                         for exchange in user_conversation:
#                             messages.append({"role": "user", "content": exchange['question']})
#                             messages.append({"role": "assistant", "content": exchange['answer']})
#                         messages.append({"role": "user", "content": message_text})

#                         # Generate LLM response
#                         llm_response = await generate_response(messages)

#                         # Save the conversation
#                         save_conversation(user_id, message_text, llm_response)

#                         # Send the response back to the user
#                         send_facebook_message(sender_id, llm_response)

#                     except Exception as e:
#                         # Handle errors gracefully
#                         error_msg = f"Sorry, I encountered an error. Please try again later."
#                         print(f"Error processing message from {sender_id}: {e}")
#                         send_facebook_message(sender_id, error_msg)

#         return {"status": "success"}
#     except Exception as e:
#         print(f"Error processing webhook: {e}")
#         raise HTTPException(status_code=500, detail="An error occurred while processing the request")


@router.post("/bot-webhook")
async def handle_incoming_messages(request: Request):
    """
    Handles incoming messages from both Facebook Messenger and WhatsApp Business API.
    """
    try:
        # Parse the incoming request payload
        payload = await request.json()
        print(f"Received Webhook Payload: {json.dumps(payload, indent=2)}")

        # Determine which platform the message is from based on payload structure
        if "object" in payload:
            # Handle WhatsApp messages
            print("----215---")
            if payload["object"] == "whatsapp_business_account":
                print("----217---")
                for entry in payload.get("entry", []):
                    print("----219---")
                    for change in entry.get("changes", []):
                        print("----221---")
                        if change.get("field") == "messages":
                            print("----223---")
                            for message in change.get("value", {}).get("messages", []):
                                print("----225---")
                                if message.get("type") == "text":
                                    # Extract WhatsApp sender and message info
                                    print("-----228-----")
                                    sender_id = message.get("from")
                                    message_text = message.get("text", {}).get("body", "")
                                    print(f"WhatsApp message from {sender_id}: {message_text}")
                                    
                                    if not message_text:
                                        continue
                                    
                                    await process_message(sender_id, message_text, platform="whatsapp")
            
            # Handle Facebook Messenger messages (your existing code path)
            elif payload["object"] == "page":
                for entry in payload.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if "message" in messaging_event:
                            sender_id = messaging_event["sender"]["id"]
                            message_text = messaging_event["message"].get("text", "")
                            print(f"Message from {sender_id}: {message_text}")

                            if not message_text:
                                print(f"No text content in message from {sender_id}, skipping")
                                continue
                            
                            await process_message(sender_id, message_text, platform="facebook")

        return {"status": "success"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request")

async def process_message(sender_id: str, message_text: str, platform: str):
    """
    Process messages from any platform and send responses.
    """
    try:
        # Use sender_id as user_id
        user_id = sender_id
        user_conversation = get_user_conversation_history(user_id)

        # Analyze the incoming message
        analyzed_question = await analyze_question(message_text, user_conversation)

        # Query vector store for relevant documents
        relevant_docs = vector_store.query(analyzed_question)

        # Create system prompt with relevant documents
        system_prompt = create_system_prompt(relevant_docs)

        # Build message list: system prompt + history + current message
        messages = [{"role": "system", "content": system_prompt}]
        for exchange in user_conversation:
            messages.append({"role": "user", "content": exchange['question']})
            messages.append({"role": "assistant", "content": exchange['answer']})
        messages.append({"role": "user", "content": message_text})

        # Generate LLM response
        llm_response = await generate_response(messages)

        # Save the conversation
        save_conversation(user_id, message_text, llm_response)

        # Send response based on platform
        if platform == "facebook":
            send_facebook_message(sender_id, llm_response)
        elif platform == "whatsapp":
            send_whatsapp_message(sender_id, llm_response)

    except Exception as e:
        # Handle errors gracefully
        error_msg = f"Sorry, I encountered an error. Please try again later."
        print(f"Error processing message from {sender_id}: {e}")
        
        if platform == "facebook":
            send_facebook_message(sender_id, error_msg)
        elif platform == "whatsapp":
            send_whatsapp_message(sender_id, error_msg)


def send_whatsapp_message(recipient_id: str, message_text: str):
    """
    Send a message to the user via WhatsApp Business API.
    """
    # Get your WhatsApp Phone Number ID from the Meta dashboard
    phone_number_id = "551662914706608"  # Replace with your actual Phone Number ID
    
    url = f"https://graph.facebook.com/v15.0/{phone_number_id}/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": WHATSAPP_TOKEN}  # Use the same token or a WhatsApp-specific one
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_id,
        "type": "text",
        "text": {
            "body": message_text
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, params=params)
        response.raise_for_status()
        print(f"WhatsApp message sent to {recipient_id}: {message_text}")
    except requests.RequestException as e:
        print(f"Error sending WhatsApp message to {recipient_id}: {e}")
        if 'response' in locals() and response is not None:
            print(f"API Response: {response.text}")


def send_facebook_message(recipient_id: str, message_text: str):
    """
    Send a message to the user via Facebook Messenger API and log any errors.
    """
    url = "https://graph.facebook.com/v15.0/me/messages"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, params=params)
        response.raise_for_status()
        print(f"Message sent to {recipient_id}: {message_text}")
    except requests.RequestException as e:
        print(f"Error sending message to {recipient_id}: {e}")
        if response is not None:
            print(f"API Response: {response.text}")


@router.get("/rebuild-vector-db")
async def rebuild_vector_db_endpoint():
    """
    Endpoint to trigger an asynchronous rebuild of the vector database.
    
    Returns:
        dict: Confirmation message indicating the rebuild has started.
    """
    asyncio.create_task(rebuild_vector_db())
    return {"message": "Vector DB rebuild started"}