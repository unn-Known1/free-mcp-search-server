#!/usr/bin/env python3
"""
Test script for FreeMCP Search Server
"""

import requests
import sys

BASE_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint"""
    print("Testing /api/health...")
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy", f"Status not healthy: {data}"
    print("✓ Health check passed")
    return data

def test_search():
    """Test search endpoint"""
    print("\nTesting /api/search...")
    response = requests.get(f"{BASE_URL}/api/search", params={
        "query": "python programming",
        "num_results": 5
    })
    assert response.status_code == 200, f"Search failed: {response.status_code}"
    data = response.json()
    assert "results" in data, "No results in response"
    assert len(data["results"]) > 0, "No results returned"
    print(f"✓ Search passed ({len(data['results'])} results)")
    print(f"  First result: {data['results'][0]['title'][:50]}...")
    return data

def test_extract():
    """Test content extraction"""
    print("\nTesting /api/extract...")
    response = requests.get(f"{BASE_URL}/api/extract", params={
        "url": "https://example.com"
    })
    assert response.status_code == 200, f"Extract failed: {response.status_code}"
    data = response.json()
    assert "content" in data, "No content in response"
    print("✓ Extract passed")
    print(f"  Title: {data.get('title', 'N/A')}")
    return data

def test_batch():
    """Test batch search"""
    print("\nTesting /api/batch...")
    response = requests.post(f"{BASE_URL}/api/batch", json={
        "queries": ["AI news", "Python tips", "Tech reviews"],
        "num_results": 3
    })
    assert response.status_code == 200, f"Batch failed: {response.status_code}"
    data = response.json()
    assert "results" in data, "No results in response"
    assert len(data["results"]) == 3, "Wrong number of result sets"
    print("✓ Batch search passed")
    for query, results in data["results"].items():
        print(f"  '{query}': {len(results)} results")
    return data

def test_news():
    """Test news search"""
    print("\nTesting /api/news...")
    response = requests.get(f"{BASE_URL}/api/news", params={
        "query": "technology",
        "num_results": 5
    })
    assert response.status_code == 200, f"News failed: {response.status_code}"
    data = response.json()
    assert "results" in data, "No results in response"
    print(f"✓ News search passed ({len(data['results'])} results)")
    return data

def main():
    print("=" * 50)
    print("FreeMCP Search Server - Test Suite")
    print("=" * 50)

    try:
        test_health()
        test_search()
        test_extract()
        test_batch()
        test_news()

        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
