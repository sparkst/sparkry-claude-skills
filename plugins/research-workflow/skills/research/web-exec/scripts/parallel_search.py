#!/usr/bin/env python3
"""
Parallel Web Search Orchestrator

Executes multiple search queries across Tavily and Brave Search in parallel.

Usage:
    python parallel_search.py \
        --plan research/plan.json \
        --output research/sources.json

Requires:
    - TAVILY_API_KEY environment variable
    - BRAVE_API_KEY environment variable (if using Brave)
"""

import argparse
import asyncio
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode


class ParallelSearchOrchestrator:
    """Orchestrates parallel web searches with rate limiting and deduplication."""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results = []

    async def execute_searches(
        self,
        queries: List[str],
        tools: List[str] = ["tavily", "brave_web"]
    ) -> Dict:
        """
        Execute searches in parallel across multiple tools.
        
        Args:
            queries: List of search queries
            tools: List of search tools to use
        
        Returns:
            {
                "execution_date": "2025-10-18T15:00:00Z",
                "queries_executed": [...],
                "sources": [...],
                "execution_metrics": {...}
            }
        """
        start_time = time.time()
        
        # Build task list
        tasks = []
        for query in queries:
            if "tavily" in tools:
                tasks.append(self._tavily_search_async(query))
            if "brave_web" in tools:
                tasks.append(self._brave_web_search_async(query))
            if "brave_news" in tools and self._is_news_query(query):
                tasks.append(self._brave_news_search_async(query))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter errors
        successful = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        if errors:
            print(f"⚠️  {len(errors)} search(es) failed: {errors[:3]}")

        # Merge and deduplicate
        all_sources = []
        for result in successful:
            all_sources.extend(result.get("sources", []))

        unique_sources = self._deduplicate_sources(all_sources)

        wall_time = time.time() - start_time

        return {
            "execution_date": datetime.now().isoformat(),
            "queries_executed": [
                {
                    "query": q,
                    "tools_used": tools,
                    "results_count": len([s for s in unique_sources if q in s.get("query_matched", "")])
                }
                for q in queries
            ],
            "sources": unique_sources,
            "execution_metrics": {
                "total_queries": len(queries),
                "parallel_batches": 1,
                "total_wall_time_seconds": round(wall_time, 2),
                "results_before_dedup": len(all_sources),
                "results_after_dedup": len(unique_sources),
                "deduplication_rate": round((len(all_sources) - len(unique_sources)) / len(all_sources), 2) if all_sources else 0,
                "errors": len(errors)
            }
        }

    async def _tavily_search_async(self, query: str) -> Dict:
        """Async Tavily search with caching."""
        # Check cache
        cached = self._get_cached_result(query, "tavily")
        if cached:
            return cached

        # Simulate API call (replace with actual Tavily client)
        await asyncio.sleep(0.5)  # Simulate network latency
        
        result = {
            "query": query,
            "tool": "tavily",
            "sources": [
                # Placeholder - replace with actual Tavily API call
            ]
        }

        self._save_to_cache(query, "tavily", result)
        return result

    async def _brave_web_search_async(self, query: str) -> Dict:
        """Async Brave web search with caching."""
        cached = self._get_cached_result(query, "brave_web")
        if cached:
            return cached

        await asyncio.sleep(0.3)

        result = {
            "query": query,
            "tool": "brave_web",
            "sources": []
        }

        self._save_to_cache(query, "brave_web", result)
        return result

    async def _brave_news_search_async(self, query: str) -> Dict:
        """Async Brave news search."""
        cached = self._get_cached_result(query, "brave_news")
        if cached:
            return cached

        await asyncio.sleep(0.3)

        result = {
            "query": query,
            "tool": "brave_news",
            "sources": []
        }

        self._save_to_cache(query, "brave_news", result)
        return result

    def _is_news_query(self, query: str) -> bool:
        """Detect if query suggests recent news."""
        news_keywords = ["launch", "announce", "2025", "latest", "recent", "new"]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in news_keywords)

    def _deduplicate_sources(self, sources: List[Dict]) -> List[Dict]:
        """Remove duplicate sources by URL and content hash."""
        seen_urls = set()
        seen_content_hashes = set()
        unique = []

        for source in sources:
            url_normalized = self._normalize_url(source.get("url", ""))
            content_hash = self._hash_content(source.get("excerpt", ""))

            if url_normalized in seen_urls or content_hash in seen_content_hashes:
                continue

            seen_urls.add(url_normalized)
            seen_content_hashes.add(content_hash)
            unique.append(source)

        return unique

    def _normalize_url(self, url: str) -> str:
        """Remove tracking params and normalize URL."""
        if not url:
            return ""

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Remove tracking params
        clean_params = {
            k: v for k, v in query_params.items()
            if k not in ['utm_source', 'utm_medium', 'utm_campaign', 'ref', 'source']
        }

        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_params:
            clean_url += f"?{urlencode(clean_params, doseq=True)}"

        return clean_url.lower()

    def _hash_content(self, content: str) -> str:
        """Hash content for duplicate detection."""
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_result(self, query: str, tool: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Check cache for existing result."""
        cache_key = hashlib.md5(f"{tool}:{query}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        with open(cache_file) as f:
            cached = json.load(f)

        cached_time = datetime.fromisoformat(cached['cached_at'])
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600

        if age_hours > max_age_hours:
            return None

        print(f"✅ Cache hit: {tool}:{query}")
        return cached['result']

    def _save_to_cache(self, query: str, tool: str, result: Dict):
        """Save result to cache."""
        cache_key = hashlib.md5(f"{tool}:{query}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        with open(cache_file, 'w') as f:
            json.dump({
                'query': query,
                'tool': tool,
                'cached_at': datetime.now().isoformat(),
                'result': result
            }, f)


async def main_async(args):
    """Async main function."""
    # Load plan
    with open(args.plan) as f:
        plan = json.load(f)

    queries = plan.get("queries", [])
    if not queries:
        print("❌ No queries found in plan.json")
        return

    # Initialize orchestrator
    orchestrator = ParallelSearchOrchestrator(cache_dir=args.cache_dir)

    # Execute searches
    print(f"🔍 Executing {len(queries)} queries...")
    result = await orchestrator.execute_searches(queries, tools=["tavily", "brave_web"])

    # Save output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"✅ Sources saved to {args.output}")
        print(f"   Total sources: {len(result['sources'])}")
        print(f"   Execution time: {result['execution_metrics']['total_wall_time_seconds']}s")
    else:
        print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Execute parallel web searches"
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to research/plan.json"
    )
    parser.add_argument(
        "--output",
        default="research/sources.json",
        help="Output file path (default: research/sources.json)"
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache",
        help="Cache directory for search results"
    )

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
