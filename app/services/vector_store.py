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
        """Initialize ChromaDB client and collection."""
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_collection(name=COLLECTION_NAME)
    
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
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Extract and combine documents
        documents = results.get("documents", [])
        flattened_documents = [item for sublist in documents for item in sublist]
        combined_documents = "\n\n".join(flattened_documents)
        
        return combined_documents
