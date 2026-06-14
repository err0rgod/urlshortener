#!/usr/bin/env python3
"""
Benchmark script for link.zerodaily.in
Tests: POST /shorten latency, GET /<code> redirect latency
Usage: python bench.py [--runs N] [--url TARGET_URL]
"""

import time
import statistics
import argparse
import urllib.request
import urllib.error
import json

BASE = "https://link.zerodaily.in"
DEFAULT_TARGET = "https://www.google.com"
DEFAULT_RUNS = 10


def post_shorten(target_url: str) -> tuple[str, float]:
    """POST /shorten, return (short_code, elapsed_ms)"""
    payload = json.dumps({"url": target_url}).encode()
    req = urllib.request.Request(
        f"{BASE}/shorten",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    elapsed = (time.perf_counter() - t0) * 1000

    # Accept either {"short_url": "..."} or {"short_code": "..."} or raw short url string
    short = (
        body.get("short_url")
        or body.get("short_code")
        or body.get("url")
        or str(body)
    )
    # Extract just the code if a full URL was returned
    code = short.rstrip("/").split("/")[-1]
    return code, elapsed


def get_redirect(code: str) -> tuple[int, float]:
    """GET /<code> without following redirect, return (status_code, elapsed_ms)"""
    req = urllib.request.Request(f"{BASE}/{code}", method="GET")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code  # 301/302 raises HTTPError
    elapsed = (time.perf_counter() - t0) * 1000
    return status, elapsed


def stats(label: str, values: list[float]):
    print(f"\n  {label}")
    print(f"    min   : {min(values):.1f} ms")
    print(f"    max   : {max(values):.1f} ms")
    print(f"    mean  : {statistics.mean(values):.1f} ms")
    print(f"    median: {statistics.median(values):.1f} ms")
    if len(values) > 1:
        print(f"    stdev : {statistics.stdev(values):.1f} ms")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--url", default=DEFAULT_TARGET)
    args = parser.parse_args()

    print(f"Benchmarking {BASE}")
    print(f"Target URL : {args.url}")
    print(f"Runs       : {args.runs}\n")

    create_times = []
    redirect_times = []
    codes = []

    for i in range(1, args.runs + 1):
        # --- POST /shorten ---
        try:
            code, ct = post_shorten(args.url)
            codes.append(code)
            create_times.append(ct)
            print(f"[{i:02d}] POST → {code:<12} {ct:7.1f} ms", end="")
        except Exception as e:
            print(f"[{i:02d}] POST FAILED: {e}")
            continue

        # --- GET /<code> ---
        try:
            status, rt = get_redirect(code)
            redirect_times.append(rt)
            print(f"  |  GET → {status}  {rt:7.1f} ms")
        except Exception as e:
            print(f"  |  GET FAILED: {e}")

        time.sleep(0.2)  # be polite

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    if create_times:
        stats("POST /shorten (create)", create_times)
    else:
        print("  No successful POST requests.")

    if redirect_times:
        stats("GET /<code> (redirect)", redirect_times)
    else:
        print("  No successful GET requests.")

    if create_times and redirect_times:
        combined = [c + r for c, r in zip(create_times, redirect_times)]
        stats("End-to-end (create + redirect)", combined)

    print()


if __name__ == "__main__":
    main()