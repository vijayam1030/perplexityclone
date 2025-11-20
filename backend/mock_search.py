"""
Mock search results for testing when DuckDuckGo is rate-limited.
"""

MOCK_RESULTS = {
    "machine learning": {
        "search_results": [
            {
                "title": "Machine Learning - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Machine_learning",
                "snippet": "Machine learning is a field of study in artificial intelligence..."
            },
            {
                "title": "What is Machine Learning?",
                "url": "https://example.com/ml",
                "snippet": "Machine learning is a method of data analysis that automates analytical model building."
            }
        ],
        "extracted_contents": [
            {
                "url": "https://en.wikipedia.org/wiki/Machine_learning",
                "domain": "wikipedia.org",
                "content": "Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without explicit instructions. Recently, generative artificial neural networks have been able to surpass many previous approaches in performance.\n\nMachine learning approaches are traditionally divided into three broad categories: supervised learning, unsupervised learning, and reinforcement learning. Supervised learning algorithms build a mathematical model of a set of data that contains both the inputs and the desired outputs. Unsupervised learning algorithms take a set of data that contains only inputs, and find structure in the data, like grouping or clustering of data points."
            },
            {
                "url": "https://example.com/ml",
                "domain": "example.com",
                "content": "Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. Machine learning focuses on the development of computer programs that can access data and use it to learn for themselves.\n\nThe process of learning begins with observations or data, such as examples, direct experience, or instruction, in order to look for patterns in data and make better decisions in the future based on the examples that we provide. The primary aim is to allow the computers to learn automatically without human intervention or assistance and adjust actions accordingly."
            }
        ]
    },
    "python": {
        "search_results": [
            {
                "title": "Python (programming language) - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
                "snippet": "Python is a high-level, general-purpose programming language..."
            }
        ],
        "extracted_contents": [
            {
                "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
                "domain": "wikipedia.org",
                "content": "Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation. Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured, object-oriented and functional programming.\n\nPython was created by Guido van Rossum and first released in 1991. Python 3, released in 2008, is the current version. Python is widely used in web development, data science, artificial intelligence, scientific computing, and automation."
            }
        ]
    }
}

def get_mock_results(query):
    """Get mock results for common queries."""
    query_lower = query.lower()
    
    # Try to find a matching mock result
    for key, results in MOCK_RESULTS.items():
        if key in query_lower:
            return results
    
    # Default result
    return {
        "search_results": [
            {
                "title": "Example Article",
                "url": "https://example.com/article",
                "snippet": f"This is a mock result for: {query}"
            }
        ],
        "extracted_contents": [
            {
                "url": "https://example.com/article",
                "domain": "example.com",
                "content": f"This is mock content about {query}. Machine learning and artificial intelligence are rapidly evolving fields. Python is a popular programming language for data science. Recent developments include large language models, computer vision advances, and improved natural language processing capabilities."
            }
        ]
    }
