"""
Orchestrator using LangGraph to coordinate the full search pipeline.
Manages the flow: Query Analysis → Search → RAG → Answer Generation
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import asyncio
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

from search_layer import SearchLayer
from rag_pipeline import RAGPipeline
from llm_layer import LLMLayer
from cache_layer import CacheLayer

class SearchState(TypedDict):
    """State for the search pipeline."""
    query: str
    query_analysis: Dict[str, Any]
    search_results: List[Dict[str, str]]
    extracted_contents: List[Dict[str, str]]
    rag_results: Dict[str, Any]
    context: str
    answer: str
    sources: List[Dict[str, str]]
    error: str | None
    use_cache: bool
    cached_result: Dict[str, Any] | None

class SearchOrchestrator:
    """Orchestrates the full AI search pipeline using LangGraph."""
    
    def __init__(self, cache_dir: str = "./cache", ollama_url: str = "http://localhost:11434"):
        """
        Initialize the orchestrator with all pipeline components.
        
        Args:
            cache_dir: Directory for cache storage
            ollama_url: Ollama API URL
        """
        self.cache = CacheLayer(cache_dir=cache_dir)
        self.search_layer = SearchLayer()
        self.rag = RAGPipeline()
        self.llm = LLMLayer(base_url=ollama_url, small_model="mistral:7b", large_model="mistral:7b")
        
        # Build the state graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine for the search pipeline."""
        workflow = StateGraph(SearchState)
        
        # Add nodes
        workflow.add_node("check_cache", self._check_cache)
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("search_web", self._search_web)
        workflow.add_node("extract_rag", self._extract_and_rag)
        workflow.add_node("generate_answer", self._generate_answer)
        
        # Define edges
        workflow.set_entry_point("check_cache")
        
        # Conditional edge from cache check
        workflow.add_conditional_edges(
            "check_cache",
            lambda state: "return_cached" if state.get("cached_result") else "continue",
            {
                "return_cached": END,
                "continue": "analyze_query"
            }
        )
        
        workflow.add_edge("analyze_query", "search_web")
        workflow.add_edge("search_web", "extract_rag")
        workflow.add_edge("extract_rag", "generate_answer")
        workflow.add_edge("generate_answer", END)
        
        return workflow.compile()
    
    def _check_cache(self, state: SearchState) -> SearchState:
        """Check if we have a cached result for this query."""
        query = state["query"]
        
        if state.get("use_cache", True):
            cached = self.cache.get_query_result(query)
            if cached:
                print(f"✓ Cache hit for query: {query}")
                state["cached_result"] = cached
                state["answer"] = cached.get("answer", "")
                state["sources"] = cached.get("sources", [])
                return state
        
        print(f"✗ Cache miss for query: {query}")
        state["cached_result"] = None
        return state
    
    def _analyze_query(self, state: SearchState) -> SearchState:
        """Analyze the query using small LLM."""
        print("→ Analyzing query...")
        query = state["query"]
        
        try:
            analysis = self.llm.analyze_query(query)
            # Preserve provider if it was set in initial state
            if "provider" in state.get("query_analysis", {}):
                analysis["provider"] = state["query_analysis"]["provider"]
            
            state["query_analysis"] = analysis
            print(f"  Intent: {analysis.get('intent', 'N/A')}")
        except Exception as e:
            print(f"  Error in query analysis: {e}")
            # Preserve provider
            provider = state.get("query_analysis", {}).get("provider", "duckduckgo")
            state["query_analysis"] = {
                "intent": query,
                "search_queries": [query],
                "provider": provider
            }
        
        return state
    
    def _search_web(self, state: SearchState) -> SearchState:
        """Perform web search and content extraction."""
        print("→ Searching web...")
        query = state["query"]
        analysis = state.get("query_analysis", {})
        provider = analysis.get("provider", "duckduckgo")
        
        # Use refined search queries if available
        search_queries = analysis.get("search_queries", [query])
        primary_query = search_queries[0] if search_queries else query
        
        if provider == "all":
            all_results = []
            all_contents = []
            # Search all providers
            for p in ["google", "duckduckgo", "wikipedia"]:
                print(f"  → Searching {p}...")
                try:
                    # Check cache for individual provider search
                    # Note: We are not caching 'all' searches as a single block currently
                    result = self.search_layer.search_and_extract(primary_query, provider=p)
                    all_results.extend(result.get("search_results", []))
                    all_contents.extend(result.get("extracted_contents", []))
                except Exception as e:
                    print(f"  Error searching {p}: {e}")
            
            state["search_results"] = all_results
            state["extracted_contents"] = all_contents
            print(f"  Found {len(state['search_results'])} total results from all sources")
            
        else:
            # Check search cache (only for default provider for now)
            cached_search = self.cache.get_search_results(primary_query)
            if cached_search and provider == "duckduckgo":
                print("  ✓ Using cached search results")
                state["search_results"] = cached_search
            else:
                result = self.search_layer.search_and_extract(primary_query, provider=provider)
                state["search_results"] = result.get("search_results", [])
                state["extracted_contents"] = result.get("extracted_contents", [])
                
                # Cache search results (only for default provider)
                if provider == "duckduckgo":
                    self.cache.set_search_results(primary_query, state["search_results"])
                print(f"  Found {len(state['search_results'])} results")
        
        return state
    
    def _extract_and_rag(self, state: SearchState) -> SearchState:
        """Extract content and perform RAG retrieval."""
        print("→ Processing RAG pipeline...")
        query = state["query"]
        
        # If we have cached search results, we need to extract content
        if "extracted_contents" not in state or not state["extracted_contents"]:
            search_results = state.get("search_results", [])
            urls = [r["url"] for r in search_results]
            
            try:
                # Try to get existing loop
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create new loop if none exists
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                # With nest_asyncio, run_until_complete should work even if loop is running
                extracted = loop.run_until_complete(self.search_layer.fetch_all_contents(urls))
                state["extracted_contents"] = extracted
            except Exception as e:
                print(f"Error extracting content: {e}")
                state["extracted_contents"] = []
        
        # Perform RAG
        extracted_contents = state.get("extracted_contents", [])
        if extracted_contents:
            rag_results = self.rag.process_documents(extracted_contents, query, top_k=10)
            state["rag_results"] = rag_results
            state["context"] = self.rag.format_context(rag_results)
            state["sources"] = rag_results.get("sources", [])
            print(f"  Retrieved {len(rag_results.get('chunks', []))} relevant chunks")
        else:
            state["rag_results"] = {}
            state["context"] = ""
            state["sources"] = []
            print("  No content extracted")
        
        return state
    
    def _generate_answer(self, state: SearchState) -> SearchState:
        """Generate final answer using large LLM."""
        print("→ Generating answer...")
        query = state["query"]
        context = state.get("context", "")
        sources = state.get("sources", [])
        
        if not context:
            state["answer"] = "I couldn't find enough relevant information to answer your question."
            return state
        
        try:
            answer = self.llm.generate_answer(query, context, sources, stream=False)
            state["answer"] = answer
            
            # Cache the result
            cache_data = {
                "answer": answer,
                "sources": sources,
                "query": query
            }
            self.cache.set_query_result(query, cache_data)
            
            print("  ✓ Answer generated")
        except Exception as e:
            print(f"  Error generating answer: {e}")
            state["answer"] = f"Error generating answer: {e}"
        
        return state
    
    def search(self, query: str, use_cache: bool = True, provider: str = "all") -> Dict[str, Any]:
        """
        Execute the full search pipeline.
        
        Args:
            query: User's search query
            use_cache: Whether to use cached results
            provider: Search provider to use
            
        Returns:
            Dict with answer, sources, and metadata
        """
        print(f"\n{'='*60}")
        print(f"Query: {query} (Provider: {provider})")
        print(f"{'='*60}")
        
        # Initialize state
        initial_state = SearchState(
            query=query,
            query_analysis={"provider": provider},
            search_results=[],
            extracted_contents=[],
            rag_results={},
            context="",
            answer="",
            sources=[],
            error=None,
            use_cache=use_cache,
            cached_result=None
        )
        
        # Run the graph
        try:
            final_state = self.graph.invoke(initial_state)
            
            # Return results
            return {
                "query": query,
                "answer": final_state.get("answer", ""),
                "sources": final_state.get("sources", []),
                "cached": final_state.get("cached_result") is not None,
                "cache_stats": self.cache.get_stats()
            }
        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "query": query,
                "answer": f"An error occurred: {str(e)}",
                "sources": [],
                "cached": False,
                "error": str(e)
            }
    
    def search_stream(self, query: str, use_cache: bool = True, provider: str = "all"):
        """
        Execute search pipeline with streaming answer generation.
        
        Args:
            query: User's search query
            use_cache: Whether to use cached results
            provider: Search provider to use
            
        Yields:
            Dict chunks with progress updates and answer tokens
        """
        # Check cache first
        if use_cache:
            cached = self.cache.get_query_result(query)
            if cached:
                # Send cached result first
                yield {"type": "cached", "data": cached}
                
                # Check if we have cached suggestions, if not generate them
                if "suggestions" in cached and cached["suggestions"]:
                    yield {"type": "suggestions", "data": cached["suggestions"]}
                else:
                    # Generate new suggestions for cached result
                    yield {"type": "status", "message": "Generating follow-up questions..."}
                    suggestions = self.llm.generate_suggestions(query)
                    yield {"type": "suggestions", "data": suggestions}
                    
                    # Update cache with suggestions
                    cached["suggestions"] = suggestions
                    self.cache.set_query_result(query, cached)
                
                return
        
        # Run pipeline up to answer generation
        yield {"type": "status", "message": "Analyzing query..."}
        analysis = self.llm.analyze_query(query)
        
        if provider == "all":
            all_results = []
            all_contents = []
            
            # Define providers to search
            providers = ["google", "duckduckgo", "wikipedia"]
            
            yield {"type": "status", "message": "Searching all sources in parallel..."}
            
            # Helper function for parallel execution
            def search_provider(p):
                try:
                    return p, self.search_layer.search_and_extract(query, provider=p)
                except Exception as e:
                    print(f"Error searching {p}: {e}")
                    return p, {"search_results": [], "extracted_contents": []}
            
            # Execute searches in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all tasks
                future_to_provider = {executor.submit(search_provider, p): p for p in providers}
                
                # Collect results as they complete
                for future in as_completed(future_to_provider):
                    provider_name, search_results_data = future.result()
                    yield {"type": "status", "message": f"Received results from {provider_name}"}
                    all_results.extend(search_results_data.get("search_results", []))
                    all_contents.extend(search_results_data.get("extracted_contents", []))
            
            search_results_data = {
                "search_results": all_results,
                "extracted_contents": all_contents
            }
            
        else:
            yield {"type": "status", "message": f"Searching with {provider}..."}
            search_results_data = self.search_layer.search_and_extract(query, provider=provider)
        
        yield {"type": "status", "message": "Processing content..."}
        extracted = search_results_data.get("extracted_contents", [])
        rag_results = self.rag.process_documents(extracted, query, top_k=10)
        context = self.rag.format_context(rag_results)
        sources = rag_results.get("sources", [])
        
        # Send sources
        yield {"type": "sources", "data": sources}
        
        yield {"type": "status", "message": "Generating answer & suggestions..."}
        
        # Start suggestion generation in background
        executor = ThreadPoolExecutor(max_workers=1)
        suggestion_future = executor.submit(self.llm.generate_suggestions, query)
        suggestions_sent = False
        
        # Stream answer generation
        answer_parts = []
        try:
            for token in self.llm.generate_answer(query, context, sources, stream=True):
                answer_parts.append(token)
                yield {"type": "token", "data": token}
                
                # Check if suggestions are ready
                if not suggestions_sent and suggestion_future.done():
                    suggestions = suggestion_future.result()
                    yield {"type": "suggestions", "data": suggestions}
                    suggestions_sent = True
        finally:
            # Ensure we get suggestions if they finish after answer
            if not suggestions_sent:
                try:
                    suggestions = suggestion_future.result()
                    yield {"type": "suggestions", "data": suggestions}
                except Exception as e:
                    print(f"Error getting suggestions: {e}")
            
            executor.shutdown(wait=False)
        
        # Cache result
        full_answer = "".join(answer_parts)
        cache_data = {
            "answer": full_answer,
            "sources": sources,
            "query": query
        }
        self.cache.set_query_result(query, cache_data)
        
        yield {"type": "complete", "data": {"answer": full_answer, "sources": sources, "suggestions": suggestions}}
