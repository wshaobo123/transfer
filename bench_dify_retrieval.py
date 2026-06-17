"""
Concurrency benchmark for /api/v1/dify/retrieval

Usage:
  python bench_dify_retrieval.py --apikey <KEY> --knowledge-id <KB_ID> --concurrency 20
  python bench_dify_retrieval.py --apikey <KEY> --knowledge-id <KB_ID> --concurrency 30 --query "你好"
  # with metadata condition
  python bench_dify_retrieval.py --apikey <KEY> --knowledge-id <KB_ID> --concurrency 20 --metadata-condition '{"conditions":[{"name":"status","comparison_operator":"is","value":"active"}]}'
"""

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_HOST = "http://127.0.0.1:9380"
API_PATH = "/api/v1/dify/retrieval"


def retrieval_once(host, apikey, knowledge_id, query, retrieval_setting=None, metadata_condition=None):
    body = {"knowledge_id": knowledge_id, "query": query}
    if retrieval_setting:
        body["retrieval_setting"] = retrieval_setting
    if metadata_condition is not None:
        body["metadata_condition"] = metadata_condition

    t0 = time.perf_counter()
    try:
        resp = requests.post(
            f"{host}{API_PATH}",
            headers={"Authorization": f"Bearer {apikey}", "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
        elapsed = time.perf_counter() - t0
        return elapsed, resp.status_code, resp.json() if resp.text else {}
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return elapsed, None, {"error": str(exc)}


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
    parser.add_argument("--score-threshold", type=float, default=0.0)
    parser.add_argument("--top-k", type=int, default=1024)
    parser.add_argument("--metadata-condition", help="JSON string, e.g. '{\"conditions\":[...]}'")
    args = parser.parse_args()

    retrieval_setting = {"score_threshold": args.score_threshold, "top_k": args.top_k}
    metadata_condition = json.loads(args.metadata_condition) if args.metadata_condition else None

    print(f"POST {args.host}{API_PATH}")
    print(f"concurrency={args.concurrency}  query={args.query!r}")
    print(f"score_threshold={args.score_threshold}  top_k={args.top_k}")
    if metadata_condition is not None:
        print(f"metadata_condition={json.dumps(metadata_condition)}")
    print()

    with ThreadPoolExecutor(max_workers=args.concurrency) as exc:
        futures = [
            exc.submit(retrieval_once, args.host, args.apikey, args.knowledge_id, args.query, retrieval_setting, metadata_condition)
            for _ in range(args.concurrency)
        ]

    times = []
    successes = []
    failures = []
    for f in as_completed(futures):
        elapsed, code, body = f.result()
        times.append(elapsed)
        if code == 200:
            n_records = len(body.get("records", []))
            successes.append((elapsed, n_records, body))
        else:
            failures.append((elapsed, code, body))

    total = len(successes) + len(failures)
    print(f"ok={len(successes)}  fail={len(failures)}  (total {total})")
    print(f"min={min(times):.3f}s  max={max(times):.3f}s  avg={statistics.mean(times):.3f}s")
    print(f"p50={percentile(times, 50):.3f}s  p90={percentile(times, 90):.3f}s  p95={percentile(times, 95):.3f}s  p99={percentile(times, 99):.3f}s")

    # per-request record counts
    if successes:
        record_counts = [r[1] for r in successes]
        print(f"\nrecords per response: min={min(record_counts)}  max={max(record_counts)}  avg={statistics.mean(record_counts):.1f}")

    # show first success as sample
    if successes:
        sample = successes[0][2]
        print(f"\n--- sample response (1st ok) ---")
        print(json.dumps(sample, ensure_ascii=False, indent=2)[:800])

    # show failures
    if failures:
        print(f"\n--- failures ---")
        for elapsed, code, body in failures[:3]:
            print(f"  HTTP {code}  {elapsed:.3f}s  {json.dumps(body, ensure_ascii=False)[:300]}")


if __name__ == "__main__":
    main()
