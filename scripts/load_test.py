"""Prueba de carga simple y reproducible, sin dependencias adicionales."""

import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def request(url: str, timeout: float) -> tuple[bool, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read()
            return 200 <= response.status < 400, time.perf_counter() - started
    except Exception:
        return False, time.perf_counter() - started


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[min(int(len(values) * fraction), len(values) - 1)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/universo/personajes?limit=20")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    args = parser.parse_args()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(request, args.url, args.timeout) for _ in range(args.requests)]
        results = [future.result() for future in as_completed(futures)]
    elapsed = time.perf_counter() - started

    latencies = [latency for _, latency in results]
    successes = sum(ok for ok, _ in results)
    report = {
        "url": args.url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successes": successes,
        "errors": args.requests - successes,
        "error_rate": round((args.requests - successes) / args.requests, 4),
        "requests_per_second": round(args.requests / elapsed, 2),
        "latency_ms": {
            "average": round(statistics.mean(latencies) * 1000, 2),
            "p95": round(percentile(latencies, 0.95) * 1000, 2),
            "maximum": round(max(latencies) * 1000, 2),
        },
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["error_rate"] <= args.max_error_rate else 1)


if __name__ == "__main__":
    main()
