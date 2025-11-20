"""
LLM inference layer using Ollama for query analysis and answer generation.
Supports dual-LLM architecture with small and large models.
"""

import requests
import json
from typing import Dict, List, Generator, Optional

class LLMLayer:
    def __init__(self, base_url: str = "http://localhost:11434", small_model: str = "mistral:7b", large_model: str = "mistral:7b"):
        """
        Initialize LLM layer with Ollama.
        
        Args:
            base_url: Ollama API base URL
            small_model: Model name for query analysis & planning
            large_model: Model name for final answer generation
        """
        self.base_url = base_url
        self.small_model = small_model
        self.large_model = large_model
    
    def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Ollama connection error: {e}")
            return False
    
    def analyze_query(self, query: str) -> Dict[str, any]:
        """
        Analyze the query using small model to understand intent and plan.
        
        Args:
            query: User's search query
            
        Returns:
            Dict with query analysis (intent, subqueries, etc.)
        """
        prompt = f"""Analyze this search query and provide:
1. The main intent/topic
2. Key entities or concepts
3. Whether it needs real-time information
4. 2-3 refined search queries to find relevant information

Query: {query}

Respond in JSON format:
{{
  "intent": "brief description",
  "entities": ["entity1", "entity2"],
  "needs_realtime": true/false,
  "search_queries": ["query1", "query2"]
}}"""
        
        try:
            response = self._generate(self.small_model, prompt, temperature=0.3)
            
            # Try to extract JSON from response
            response_text = response.strip()
            
            # Find JSON block
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "{" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                response_text = response_text[start:end]
            
            analysis = json.loads(response_text)
            return analysis
        except Exception as e:
            print(f"Query analysis error: {e}")
            # Return default analysis
            return {
                "intent": query,
                "entities": [],
                "needs_realtime": True,
                "search_queries": [query]
            }
    
    def generate_answer(self, query: str, context: str, sources: List[Dict[str, str]], stream: bool = False) -> Generator[str, None, None] or str:
        """
        Generate final answer using large model with retrieved context.
        
        Args:
            query: User's original query
            context: Retrieved context from RAG
            sources: List of source URLs and metadata
            stream: Whether to stream the response
            
        Returns:
            Generated answer (streaming or complete)
        """
        # Format sources
        sources_text = "\n".join([f"- {s.get('title', s.get('domain', s['url']))}: {s['url']}" for s in sources])
        
        prompt = f"""You are an AI search assistant. Answer the user's question using the provided context from web sources.

User Question: {query}

Context from web sources:
{context}

Sources:
{sources_text}

Instructions:
1. Provide a comprehensive, accurate answer based on the context
2. Cite sources using [1], [2], etc. when making specific claims
3. If the context doesn't fully answer the question, say so
4. Be concise but thorough
5. Use clear, professional language

Answer:"""
        
        if stream:
            return self._generate_stream(self.large_model, prompt)
        else:
            return self._generate(self.large_model, prompt)
    
    def _generate(self, model: str, prompt: str, temperature: float = 0.7) -> str:
        """
        Generate completion from Ollama (non-streaming).
        
        Args:
            model: Model name
            prompt: Prompt text
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error: LLM returned status {response.status_code}"
        except Exception as e:
            return f"Error generating response: {e}"
    
    def _generate_stream(self, model: str, prompt: str, temperature: float = 0.7) -> Generator[str, None, None]:
        """
        Generate completion from Ollama (streaming).
        
        Args:
            model: Model name
            prompt: Prompt text
            temperature: Sampling temperature
            
        Yields:
            Generated text chunks
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": True
                },
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                yield f"Error: LLM returned status {response.status_code}"
        except Exception as e:
            yield f"Error generating response: {e}"
    def generate_suggestions(self, query: str) -> List[str]:
        """
        Generate follow-up search suggestions based on the query.
        
        Args:
            query: User's search query
            
        Returns:
            List of suggestion strings
        """
        prompt = f"""Based on the search query "{query}", generate 3 short, relevant follow-up search questions.
        Return ONLY the questions, one per line. Do not number them. Do not add quotes."""
        
        try:
            response = self._generate(self.small_model, prompt, temperature=0.5)
            suggestions = []
            import re
            for line in response.split('\n'):
                line = line.strip()
                if line:
                    # Remove leading numbers (1., 1), bullets (-, *), and quotes
                    cleaned = re.sub(r'^[\d\.\-\*\s"\']+', '', line).strip('"\'')
                    if cleaned:
                        suggestions.append(cleaned)
            return suggestions[:3]
        except Exception as e:
            print(f"Suggestion generation error: {e}")
            return []
