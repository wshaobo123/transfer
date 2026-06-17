"""
Concurrency benchmark for /api/v1/dify/retrieval

Usage:
  python bench_dify_retrieval.py --apikey <KEY> --knowledge-id <KB_ID> --concurrency 20
  python bench_dify_retrieval.py --apikey <KEY> --knowledge-id <KB_ID> --concurrency 30 --query "你好"
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_HOST = "http://127.0.0.1:9380"
API_PATH = "/api/v1/dify/retrieval"


def retrieval_once(host, apikey, knowledge_id, query):
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            f"{host}{API_PATH}",
            headers={"Authorization": f"Bearer {apikey}", "Content-Type": "application/json"},
            json={"knowledge_id": knowledge_id, "query": query},
            timeout=60,
        )
        elapsed = time.perf_counter() - t0
        return elapsed, resp.status_code, resp.json() if resp.text else {}
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return elapsed, None, str(exc)


def percentile(vals, p):
    if not vals:
        return 0
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apikey", required=True, help="RAGFlow API key")
    parser.add_argument("--knowledge-id", required=True, help="Knowledge base ID")
    parser.add_argument("--query", default="test")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--host", default=DEFAULT_HOST)
    args = parser.parse_args()

    print(f"POST {args.host}{API_PATH}")
    print(f"concurrency={args.concurrency}  query={args.query!r}\n")

    with ThreadPoolExecutor(max_workers=args.concurrency) as exc:
        futures = [exc.submit(retrieval_once, args.host, args.apikey, args.knowledge_id, args.query) for _ in range(args.concurrency)]

    times = []
    ok = fail = 0
    for f in as_completed(futures):
        elapsed, code, _body = f.result()
        times.append(elapsed)
        if code == 200:
            ok += 1
        else:
            fail += 1

    print(f"ok={ok}  fail={fail}")
    print(f"min={min(times):.3f}s  max={max(times):.3f}s  avg={statistics.mean(times):.3f}s")
    print(f"p50={percentile(times, 50):.3f}s  p90={percentile(times, 90):.3f}s  p95={percentile(times, 95):.3f}s  p99={percentile(times, 99):.3f}s")


if __name__ == "__main__":
    main()
