"""
RAG (Retrieval-Augmented Generation) pipeline with FAISS vector search.
Handles text chunking, embedding generation, and semantic retrieval.
"""

import numpy as np
from typing import List, Dict, Tuple
from sentence_transformers import SentenceTransformer
import faiss

class RAGPipeline:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize RAG pipeline.
        
        Args:
            model_name: Name of the sentence transformer model
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.model = SentenceTransformer(model_name)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or len(text) == 0:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size * 0.5:  # Only break if we're past halfway
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        
        return [c for c in chunks if len(c) > 50]  # Filter out very small chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            NumPy array of embeddings
        """
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings
    
    def create_vector_store(self, chunks: List[str]) -> Tuple[faiss.IndexFlatL2, List[str]]:
        """
        Create FAISS vector store from text chunks.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            Tuple of (FAISS index, chunks list)
        """
        if not chunks:
            return None, []
        
        # Generate embeddings
        embeddings = self.generate_embeddings(chunks)
        
        # Create FAISS index
        index = faiss.IndexFlatL2(self.dimension)
        index.add(embeddings.astype('float32'))
        
        return index, chunks
    
    def search_similar(self, index: faiss.IndexFlatL2, chunks: List[str], query: str, top_k: int = 5) -> List[Dict[str, any]]:
        """
        Search for similar chunks to the query.
        
        Args:
            index: FAISS index
            chunks: List of text chunks
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of dicts with chunk, score, and index
        """
        if not index or not chunks:
            return []
        
        # Embed the query
        query_embedding = self.model.encode([query])[0]
        
        # Search in FAISS
        distances, indices = index.search(
            query_embedding.reshape(1, -1).astype('float32'), 
            min(top_k, len(chunks))
        )
        
        # Format results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(chunks):  # Ensure valid index
                results.append({
                    "chunk": chunks[idx],
                    "score": float(distance),
                    "rank": i + 1,
                    "index": int(idx)
                })
        
        return results
    
    def process_documents(self, documents: List[Dict[str, str]], query: str, top_k: int = 5) -> Dict[str, any]:
        """
        Process documents through the full RAG pipeline.
        
        Args:
            documents: List of dicts with 'content' and 'url'
            query: Search query
            top_k: Number of top chunks to retrieve
            
        Returns:
            Dict with retrieved chunks and metadata
        """
        if not documents:
            return {
                "chunks": [],
                "total_chunks": 0,
                "sources": []
            }
        
        # Chunk all documents
        all_chunks = []
        chunk_sources = []  # Track which document each chunk came from
        
        for doc in documents:
            content = doc.get("content", "")
            url = doc.get("url", "")
            domain = doc.get("domain", "")
            
            doc_chunks = self.chunk_text(content)
            all_chunks.extend(doc_chunks)
            
            # Track source for each chunk
            for _ in doc_chunks:
                chunk_sources.append({
                    "url": url,
                    "domain": domain
                })
        
        if not all_chunks:
            return {
                "chunks": [],
                "total_chunks": 0,
                "sources": []
            }
        
        # Create vector store
        index, chunks = self.create_vector_store(all_chunks)
        
        # Search for relevant chunks
        results = self.search_similar(index, chunks, query, top_k)
        
        # Add source information to results
        for result in results:
            chunk_idx = result["index"]
            if chunk_idx < len(chunk_sources):
                result["source"] = chunk_sources[chunk_idx]
        
        # Get unique sources
        unique_sources = list({doc["url"]: doc for doc in documents}.values())
        
        return {
            "chunks": results,
            "total_chunks": len(all_chunks),
            "sources": unique_sources,
            "query": query
        }
    
    def format_context(self, rag_results: Dict[str, any], max_chunks: int = 5) -> str:
        """
        Format RAG results into context string for LLM.
        
        Args:
            rag_results: Results from process_documents
            max_chunks: Maximum number of chunks to include
            
        Returns:
            Formatted context string
        """
        chunks = rag_results.get("chunks", [])[:max_chunks]
        
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk_data in enumerate(chunks, 1):
            chunk = chunk_data["chunk"]
            source = chunk_data.get("source", {})
            url = source.get("url", "Unknown")
            domain = source.get("domain", "Unknown")
            
            context_parts.append(f"[Source {i} - {domain}]\n{chunk}\n")
        
        return "\n".join(context_parts)
