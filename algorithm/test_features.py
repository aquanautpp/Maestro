#!/usr/bin/env python3
"""Quick test script for all 10 features."""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(name, method, url, data=None):
    """Test an API endpoint."""
    try:
        if method == "GET":
            r = requests.get(f"{BASE_URL}{url}", timeout=5)
        else:
            r = requests.post(f"{BASE_URL}{url}", json=data, timeout=5)

        status = "OK" if r.status_code == 200 else f"FAIL ({r.status_code})"
        print(f"  [{status}] {name}")
        if r.status_code == 200:
            return r.json()
        return None
    except requests.exceptions.ConnectionError:
        print(f"  [SKIP] {name} - Server not running")
        return None
    except Exception as e:
        print(f"  [ERROR] {name} - {e}")
        return None

def main():
    print("\n=== MAESTRO Feature Tests ===\n")

    # Feature 2: Age-Adaptive Guidance
    print("Feature 2: Age-Adaptive Guidance")
    test_endpoint("Set family profile", "POST", "/api/family/profile",
                  {"child_birth_date": "2023-06-15", "child_name": "Test"})
    test_endpoint("Get family profile", "GET", "/api/family/profile")
    test_endpoint("Age-filtered content", "GET", "/api/content/age-filtered")

    # Feature 10: Multi-Child Support
    print("\nFeature 10: Multi-Child Support")
    test_endpoint("List children", "GET", "/api/family/children")
    test_endpoint("Get household", "GET", "/api/family/household")

    # Feature 4: Pattern Analysis
    print("\nFeature 4: Pattern Analysis")
    test_endpoint("Get patterns", "GET", "/api/analytics/patterns")
    test_endpoint("Get strengths", "GET", "/api/analytics/strengths")

    # Feature 6: Quality Scoring
    print("\nFeature 6: Quality Scoring")
    test_endpoint("Session quality", "GET", "/api/session/quality")

    # Feature 1: RAG Knowledge Base
    print("\nFeature 1: RAG Knowledge Base")
    test_endpoint("Knowledge search", "GET", "/api/knowledge/search?q=serve%20return")
    test_endpoint("Knowledge stats", "GET", "/api/knowledge/stats")

    # Feature 9: Research Library
    print("\nFeature 9: Research Library")
    test_endpoint("Research papers", "GET", "/api/research/papers")
    test_endpoint("Featured papers", "GET", "/api/research/featured")

    # Feature 3: Context-Aware Tips
    print("\nFeature 3: Context-Aware Tips")
    test_endpoint("Contextual tip", "GET", "/api/tips/contextual")
    test_endpoint("Tip schedule", "GET", "/api/tips/schedule")

    # Feature 5: LLM Coaching
    print("\nFeature 5: LLM Coaching")
    test_endpoint("Weekly coaching", "GET", "/api/coaching/weekly")

    # Feature 8: Milestones
    print("\nFeature 8: Milestone Integration")
    test_endpoint("Get milestones", "GET", "/api/milestones")
    test_endpoint("Milestone activities", "GET", "/api/milestones/activities")
    test_endpoint("Milestone progress", "GET", "/api/milestones/progress")

    # Feature 7: Curriculum
    print("\nFeature 7: Curriculum System")
    test_endpoint("Curriculum overview", "GET", "/api/curriculum/overview")
    test_endpoint("Current curriculum", "GET", "/api/curriculum/current")
    test_endpoint("Week 1", "GET", "/api/curriculum/week/1")
    test_endpoint("Daily challenge", "GET", "/api/curriculum/daily-challenge")
    test_endpoint("Achievements", "GET", "/api/curriculum/achievements")
    test_endpoint("Progress", "GET", "/api/curriculum/progress")

    # Core functionality
    print("\nCore: Detection")
    test_endpoint("Server status", "GET", "/api/status")
    test_endpoint("Current session", "GET", "/api/session")

    print("\n=== Tests Complete ===\n")
    print("To test voice detection, run the server and speak into your microphone.")
    print("Use: python realtime_detector.py --autostart")

if __name__ == "__main__":
    main()
