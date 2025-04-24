
"""
ChromaDB integration for vector storage and retrieval.
"""
import chromadb
from config import CHROMA_PATH, COLLECTION_NAME
from services.embedding import generate_embedding
from typing import List

class VectorStore:
    """Interface for ChromaDB vector database operations."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        # Don’t store collection here; fetch it dynamically
        self.collection_name = COLLECTION_NAME
    
    def get_collection(self):
        """Fetch or create the collection dynamically."""
        try:
            return self.client.get_collection(name=self.collection_name)
        except Exception as e:
            # If collection doesn’t exist, create it (initial empty state)
            if "does not exist" in str(e):
                return self.client.create_collection(name=self.collection_name)
            raise e
    
    def query(self, question: str, n_results: int = 5) -> str:
        """
        Query the vector store with the user question.
        
        Args:
            question: User's question
            n_results: Number of similar documents to retrieve
            
        Returns:
            Combined text from the most relevant documents
        """
        # Generate embedding for the query
        query_embedding = generate_embedding(question)
        
        # Fetch the current collection
        collection = self.get_collection()
        
        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Extract and combine documents
        documents = results.get("documents", [])
        flattened_documents = [item for sublist in documents for item in sublist]
        combined_documents = "\n\n".join(flattened_documents)
        
        return combined_documents
    
    def switch_collection(self, new_collection_name: str):
        """
        Switch to a different collection by name.
        
        Args:
            new_collection_name: Name of the collection to switch to
        """
        self.collection_name = new_collection_name