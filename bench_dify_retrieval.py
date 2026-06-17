"""
Concurrency benchmark for /api/v1/dify/retrieval

Usage:
  # 20 concurrent requests
  python bench_dify_retrieval.py --knowledge-id <KB_ID> --query "your question" --concurrency 20

  # 30 concurrent requests
  python bench_dify_retrieval.py --knowledge-id <KB_ID> --query "your question" --concurrency 30

  # change host / use env vars for credentials
  python bench_dify_retrieval.py --host http://127.0.0.1:9380 --email qa@infiniflow.org --password <PWD> --knowledge-id <KB_ID> --concurrency 20
"""

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_HOST = "http://127.0.0.1:9380"
API_URL = "/api/v1/dify/retrieval"
DEFAULT_EMAIL = "qa@infiniflow.org"
DEFAULT_PASSWORD = "123"


def get_auth_token(host, email, password):
    """Obtain Bearer token via login + new_token flow."""
    # Step 1: login
    resp = requests.post(
        f"{host}/v1/user/login",
        json={"email": email, "password": password},
    )
    data = resp.json()
    if data.get("code") != 0:
        sys.exit(f"Login failed: {data.get('message')}")
    auth_header = resp.headers["Authorization"]

    # Step 2: get API token
    resp = requests.post(
        f"{host}/v1/system/new_token",
        headers={"Authorization": auth_header},
    )
    data = resp.json()
    if data.get("code") != 0:
        sys.exit(f"Get token failed: {data.get('message')}")
    return data["data"]["token"]


def retrieval_once(host, token, knowledge_id, query, use_kg=False):
    """Single request to /dify/retrieval. Returns (elapsed_seconds, status_code, response_json)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "knowledge_id": knowledge_id,
        "query": query,
        "use_kg": use_kg,
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(f"{host}{API_URL}", headers=headers, json=body, timeout=60)
        elapsed = time.perf_counter() - t0
        return elapsed, resp.status_code, resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return elapsed, None, str(exc)


def percentile(values, p):
    if not values:
        return 0
    vals = sorted(values)
    k = (len(vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def main():
    parser = argparse.ArgumentParser(description="Concurrency benchmark for /dify/retrieval")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--knowledge-id", required=True, help="Knowledge base ID")
    parser.add_argument("--query", default="test", help="Query text")
    parser.add_argument("--concurrency", type=int, default=20, help="Number of concurrent requests (default 20)")
    parser.add_argument("--use-kg", action="store_true", help="Enable knowledge graph retrieval")
    args = parser.parse_args()

    print(f"Host:        {args.host}")
    print(f"Endpoint:    {API_URL}")
    print(f"Concurrency: {args.concurrency}")

    print("\nObtaining auth token ...")
    token = get_auth_token(args.host, args.email, args.password)
    print("Token obtained.\n")

    # Fire concurrent requests
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(retrieval_once, args.host, token, args.knowledge_id, args.query, args.use_kg)
            for _ in range(args.concurrency)
        ]

        elapsed_times = []
        success = 0
        failure = 0
        errors = []

        for future in as_completed(futures):
            elapsed, status_code, result = future.result()
            elapsed_times.append(elapsed)
            if status_code == 200:
                success += 1
            else:
                failure += 1
                errors.append((status_code, str(result)[:200]))

    total = success + failure
    print(f"\n{'='*50}")
    print(f"Results:  {success} ok, {failure} failed  (total {total})")
    print(f"{'='*50}")
    print(f"Latency (seconds):")
    print(f"  min    {min(elapsed_times):.3f}")
    print(f"  max    {max(elapsed_times):.3f}")
    print(f"  avg    {statistics.mean(elapsed_times):.3f}")
    print(f"  p50    {percentile(elapsed_times, 50):.3f}")
    print(f"  p90    {percentile(elapsed_times, 90):.3f}")
    print(f"  p95    {percentile(elapsed_times, 95):.3f}")
    print(f"  p99    {percentile(elapsed_times, 99):.3f}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for code, msg in errors[:5]:
            print(f"  HTTP {code}: {msg}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")


if __name__ == "__main__":
    main()
