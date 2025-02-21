"""
Database connection and operations.
"""
import sqlite3
from sqlite3 import Connection
from config import DB_PATH

def get_db_connection() -> Connection:
    """Creates a database connection and returns the connection object."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This allows access to columns by name
    return conn

def init_db() -> None:
    """Creates the conversations table if it doesn't exist."""
    conn = get_db_connection()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            );
        ''')

def get_user_conversation_history(user_id: str) -> list:
    """Retrieves conversation history for a specific user as a list of exchanges."""
    conn = get_db_connection()
    with conn:
        user_conversation = conn.execute(
            'SELECT question, answer FROM conversations WHERE user_id = ? ORDER BY id', 
            (user_id,)
        ).fetchall()
        return [{"question": row['question'], "answer": row['answer']} for row in user_conversation]

def save_conversation(user_id: str, question: str, answer: str) -> None:
    """Saves a conversation entry to the database."""
    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO conversations (user_id, question, answer) VALUES (?, ?, ?)',
            (user_id, question, answer)
        )