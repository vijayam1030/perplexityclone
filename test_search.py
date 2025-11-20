import sys
sys.path.insert(0, 'backend')

from orchestrator import SearchOrchestrator

print("Initializing orchestrator...")
orch = SearchOrchestrator()

print("\nTesting search with simple query...")
result = orch.search("What is Python?", use_cache=False)

print("\n" + "="*60)
print("RESULT:")
print("="*60)
print(f"Query: {result['query']}")
print(f"Cached: {result['cached']}")
print(f"\nAnswer:\n{result['answer']}")
print(f"\nSources: {len(result['sources'])}")
for i, src in enumerate(result['sources'], 1):
    print(f"  [{i}] {src.get('title', src.get('url', 'Unknown'))}")
