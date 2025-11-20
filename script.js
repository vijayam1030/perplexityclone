document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');
    const sourcesContainer = document.getElementById('sources-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const loadingText = document.querySelector('.loading-text');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const providerSelect = document.getElementById('provider-select');

    let socket = null;
    let currentAnswer = '';

    // Event Listeners
    searchBtn.addEventListener('click', () => performSearch(searchInput.value));

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch(searchInput.value);
        }
    });

    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            searchInput.value = chip.textContent;
            performSearch(chip.textContent);
        });
    });

    async function performSearch(query) {
        if (!query) return;

        // Clear previous results
        resultsContainer.innerHTML = '';
        sourcesContainer.innerHTML = '';
        currentAnswer = '';
        loadingText.textContent = 'Connecting...';
        loadingIndicator.classList.remove('hidden');

        // Get selected provider
        const provider = providerSelect.value;

        // Close existing connection if any
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }

        // Connect to WebSocket
        socket = new WebSocket('ws://localhost:8000/ws');

        socket.onopen = () => {
            loadingText.textContent = 'Connected. Sending query...';
            socket.send(JSON.stringify({
                query: query,
                use_cache: true,
                provider: provider
            }));
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
            loadingIndicator.classList.add('hidden');
            resultsContainer.innerHTML = `<div class="error-message">Connection error. Please try again.</div>`;
        };

        socket.onclose = () => {
            console.log('WebSocket disconnected');
        };
    }

    function handleWebSocketMessage(data) {
        switch (data.type) {
            case 'status':
                loadingText.textContent = data.message;
                break;

            case 'sources':
                renderSources(data.data);
                // Create answer container if not exists
                if (!document.querySelector('.answer-card')) {
                    const answerCard = document.createElement('div');
                    answerCard.className = 'answer-card';
                    answerCard.innerHTML = `
                        <div class="answer-header">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                            <span>Answer</span>
                        </div>
                        <div class="answer-content" id="answer-content"></div>
                    `;
                    resultsContainer.appendChild(answerCard);
                    loadingIndicator.classList.add('hidden');
                }
                break;

            case 'token':
                currentAnswer += data.data;
                const answerContent = document.getElementById('answer-content');
                if (answerContent) {
                    // Simple markdown parsing for bold and code
                    let formatted = currentAnswer
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/`(.*?)`/g, '<code>$1</code>')
                        .replace(/\n/g, '<br>');
                    answerContent.innerHTML = formatted;
                }
                break;

            case 'cached':
                loadingIndicator.classList.add('hidden');
                renderSources(data.data.sources);

                const answerCard = document.createElement('div');
                answerCard.className = 'answer-card';
                answerCard.innerHTML = `
                    <div class="answer-header">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                        <span>Answer (Cached)</span>
                    </div>
                    <div class="answer-content">${data.data.answer.replace(/\n/g, '<br>')}</div>
                `;
                resultsContainer.appendChild(answerCard);
                break;

            case 'complete':
                loadingText.textContent = 'Done';
                setTimeout(() => {
                    loadingIndicator.classList.add('hidden');
                }, 1000);
                break;

            case 'suggestions':
                updateSuggestions(data.data);
                break;
        }
    }

    function updateSuggestions(suggestions) {
        const suggestionsContainer = document.querySelector('.suggestions');
        if (!suggestionsContainer || !suggestions || suggestions.length === 0) return;

        suggestionsContainer.innerHTML = '';
        suggestions.forEach(suggestion => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.textContent = suggestion;
            chip.addEventListener('click', () => {
                const searchInput = document.getElementById('search-input');
                searchInput.value = suggestion;
                performSearch(suggestion);
            });
            suggestionsContainer.appendChild(chip);
        });
    }

    function renderSources(sources) {
        if (!sources || sources.length === 0) return;

        sourcesContainer.innerHTML = '';
        sources.forEach((source, index) => {
            const sourceCard = document.createElement('a');
            sourceCard.className = 'source-card';
            sourceCard.href = source.url;
            sourceCard.target = '_blank';

            // Get domain for favicon
            let domain = '';
            try {
                domain = new URL(source.url).hostname;
            } catch (e) {
                domain = 'example.com';
            }

            sourceCard.innerHTML = `
                <div class="source-title">${index + 1}. ${source.title}</div>
                <div class="source-domain">
                    <img src="https://www.google.com/s2/favicons?domain=${domain}" class="source-favicon" alt="">
                    ${domain}
                </div>
            `;
            sourcesContainer.appendChild(sourceCard);
        });
    }
});
