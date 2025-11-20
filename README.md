# AI Search Engine - Perplexity Clone

A fast, local AI-powered search engine that combines real-time web search with LLM-powered answers, similar to Perplexity. Built with FastAPI, LangGraph, FAISS, and Ollama.

## 🚀 Features

- **Real-Time Web Search**: DuckDuckGo integration with parallel content extraction
- **RAG Pipeline**: FAISS vector search for semantic retrieval
- **Dual-LLM Architecture**: Small model for query analysis, large model for answer generation
- **Smart Caching**: Aggressive caching for 10x-50x speed improvements on repeated queries
- **Modern UI**: Premium dark mode interface with glassmorphism and animations
- **Streaming Support**: WebSocket-based streaming for real-time responses

## 📋 Prerequisites

1. **Python 3.8+**
2. **Ollama** installed and running
3. **Ollama Models** downloaded:
   ```bash
   ollama pull qwen2.5:7b
   ollama pull qwen2.5:14b
   ```

## 🛠️ Installation

### 1. Clone or navigate to the project directory

```bash
cd c:\charry\project\language\random\perplexity
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables (optional)

Copy `.env.example` to `.env` and modify if needed:

```bash
copy .env.example .env
```

## 🎯 Usage

### Option 1: Quick Start (Windows)

Double-click `start.bat` or run:

```bash
start.bat
```

This will:
- Start the FastAPI backend on `http://localhost:8000`
- Open the frontend in your default browser

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
python app.py
```

**Terminal 2 - Frontend:**
```bash
# Open index.html in your browser
# Or use a simple HTTP server:
python -m http.server 8080
```

Then open `http://localhost:8080` in your browser.

## 🧪 Testing

1. Open the web interface
2. Try a sample query: "What are the latest developments in AI?"
3. Watch as the system:
   - Analyzes your query
   - Searches the web
   - Extracts and processes content
   - Generates an AI-powered answer with citations

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │ (HTML/CSS/JS)
└──────┬──────┘
       │ HTTP/WebSocket
┌──────▼──────┐
│   FastAPI   │ (app.py)
└──────┬──────┘
       │
┌──────▼──────────┐
│  Orchestrator   │ (LangGraph)
└──────┬──────────┘
       │
   ┌───┴────┬─────────┬─────────┬────────┐
   │        │         │         │        │
┌──▼──┐ ┌──▼──┐  ┌───▼───┐ ┌───▼───┐ ┌─▼──┐
│Search│ │ RAG │  │  LLM  │ │ Cache │ │...│
└─────┘ └─────┘  └───────┘ └───────┘ └────┘
```

### Components

- **search_layer.py**: DuckDuckGo search + content extraction
- **rag_pipeline.py**: Text chunking + FAISS vector search
- **llm_layer.py**: Ollama integration for LLM inference
- **cache_layer.py**: Disk-based caching with TTL
- **orchestrator.py**: LangGraph workflow coordination
- **app.py**: FastAPI REST & WebSocket endpoints

## 📊 API Endpoints

- `POST /search` - Perform a search
- `GET /health` - Health check
- `GET /cache-stats` - Get cache statistics
- `POST /clear-cache` - Clear all caches
- `WS /ws` - WebSocket for streaming

## ⚙️ Configuration

Edit `.env` to customize:

```env
OLLAMA_BASE_URL=http://localhost:11434
SMALL_MODEL=qwen2.5:7b
LARGE_MODEL=qwen2.5:14b
CACHE_DIR=./cache
CACHE_TTL=3600
MAX_SEARCH_RESULTS=10
```

## 🎨 UI Features

- Dark mode with animated gradient background
- Glassmorphism card design
- Real-time search status updates
- Source citations with links
- Cache hit indicators
- Responsive layout

## 🔧 Troubleshooting

### Ollama connection failed
- Ensure Ollama is running: `ollama serve`
- Check models are installed: `ollama list`
- Verify Ollama URL in `.env`

### Search returns no results
- DuckDuckGo may rate-limit requests
- Try a different query
- Check internet connection

### Slow responses
- First query downloads model (if not cached)
- Subsequent queries should be faster
- Check cache statistics

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Use a virtual environment if needed

## 📝 License

MIT License - Feel free to use and modify!

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://langchain.com/) & [LangGraph](https://langchain-ai.github.io/langgraph/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Ollama](https://ollama.ai/)
- [Sentence Transformers](https://www.sbert.net/)
- [DuckDuckGo Search](https://github.com/deedy5/duckduckgo_search)

Inspired by [Perplexity AI](https://www.perplexity.ai/)
