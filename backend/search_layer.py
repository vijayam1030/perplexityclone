"""
Real-time search layer using multiple providers with content extraction.
Performs parallel fetching and HTML parsing for speed.
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import html2text
import re
from urllib.parse import urlparse
import wikipedia
from googlesearch import search as google_search
import nest_asyncio
import requests

# Apply nest_asyncio
nest_asyncio.apply()

class SearchLayer:
    def __init__(self, max_results: int = 10, max_content_length: int = 5000):
        """
        Initialize search layer.
        
        Args:
            max_results: Maximum number of search results to fetch
            max_content_length: Maximum length of content to extract per page
        """
        self.max_results = max_results
        self.max_content_length = max_content_length
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
    
    def search(self, query: str, provider: str = "duckduckgo") -> List[Dict[str, str]]:
        """
        Perform web search using specified provider.
        
        Args:
            query: The search query
            provider: Search provider ('duckduckgo', 'wikipedia', 'google')
            
        Returns:
            List of search results with title, url, and snippet
        """
        print(f"  → Searching with {provider}...")
        
        if provider == "wikipedia":
            return self._search_wikipedia(query)
        elif provider == "google":
            return self._search_google(query)
        elif provider == "bing":
            return self._search_bing(query)
        elif provider == "brave":
            return self._search_brave(query)
        else:
            return self._search_duckduckgo(query)

    def _search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        """Search using DuckDuckGo."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
                
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", "")
                    })
                return formatted_results
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []

    def _search_wikipedia(self, query: str) -> List[Dict[str, str]]:
        """Search using Wikipedia API."""
        try:
            results = wikipedia.search(query, results=self.max_results)
            formatted_results = []
            
            for title in results:
                try:
                    page = wikipedia.page(title, auto_suggest=False)
                    formatted_results.append({
                        "title": page.title,
                        "url": page.url,
                        "snippet": page.summary[:200] + "..."
                    })
                except (wikipedia.DisambiguationError, wikipedia.PageError):
                    continue
                    
            return formatted_results
        except Exception as e:
            print(f"Wikipedia search error: {e}")
            return []

    def _search_google(self, query: str) -> List[Dict[str, str]]:
        """Search using Google (via googlesearch-python)."""
        try:
            # Note: googlesearch-python only returns URLs, so we'll have to fetch titles/snippets later
            # or just use the URL as title for now
            results = list(google_search(query, num_results=self.max_results, advanced=True))
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.description
                })
            return formatted_results
        except Exception as e:
            print(f"Google search error: {e}")
            return []
    
    def _search_bing(self, query: str) -> List[Dict[str, str]]:
        """Search using Bing."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            formatted_results = []
            results = soup.select('.b_algo')[:self.max_results]
            
            for result in results:
                title_elem = result.select_one('h2 a')
                snippet_elem = result.select_one('.b_caption p')
                
                if title_elem:
                    formatted_results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": title_elem.get('href', ''),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Bing search error: {e}")
            return []
    
    def _search_brave(self, query: str) -> List[Dict[str, str]]:
        """Search using Brave Search."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            url = f"https://search.brave.com/search?q={query.replace(' ', '+')}"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            formatted_results = []
            # Brave uses different selectors - adjust as needed
            results = soup.select('.snippet')[:self.max_results]
            
            for result in results:
                title_elem = result.select_one('.snippet-title')
                url_elem = result.select_one('.snippet-url')
                snippet_elem = result.select_one('.snippet-description')
                
                if title_elem:
                    formatted_results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url_elem.get('href', '') if url_elem else '',
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Brave search error: {e}")
            return []
    
    async def fetch_url_content(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch and extract content from a URL asynchronously."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                return self._extract_content(html, url)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _extract_content(self, html: str, url: str) -> str:
        """Extract main content from HTML."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            main_content = None
            for tag in ['article', 'main', 'div[role="main"]']:
                main_content = soup.find(tag)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            if not main_content:
                return ""
            
            text = self.html_converter.handle(str(main_content))
            text = self._clean_text(text)
            
            if len(text) > self.max_content_length:
                text = text[:self.max_content_length] + "..."
            
            return text
        except Exception as e:
            print(f"Error extracting content: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\'\"\(\)]', '', text)
        return text.strip()
    
    async def fetch_all_contents(self, urls: List[str]) -> List[Dict[str, str]]:
        """Fetch content from multiple URLs in parallel."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_url_content(session, url) for url in urls]
            contents = await asyncio.gather(*tasks)
            
            results = []
            for url, content in zip(urls, contents):
                if content:
                    results.append({
                        "url": url,
                        "content": content,
                        "domain": urlparse(url).netloc
                    })
            return results
    
    def search_and_extract(self, query: str, provider: str = "duckduckgo") -> Dict[str, any]:
        """
        Perform search and extract content from results.
        
        Args:
            query: The search query
            provider: Search provider to use
            
        Returns:
            Dict with search results and extracted contents
        """
        # Perform search
        search_results = self.search(query, provider)
        
        if not search_results:
            return {
                "query": query,
                "search_results": [],
                "extracted_contents": []
            }
        
        # Extract URLs
        urls = [result["url"] for result in search_results]
        
        # Fetch contents asynchronously
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        try:
            extracted_contents = loop.run_until_complete(self.fetch_all_contents(urls))
        except Exception as e:
            print(f"Error fetching contents: {e}")
            extracted_contents = []
        
        return {
            "query": query,
            "search_results": search_results,
            "extracted_contents": extracted_contents
        }
