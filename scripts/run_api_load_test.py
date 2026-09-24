"""Measure API concurrency against the in-process FastAPI boundary.

This is an engineering smoke/load test, not a production capacity claim.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx


async def run(concurrency: int, requests: int) -> dict[str, object]:
    os.environ.setdefault("API_KEY_REQUIRED", "false")
    os.environ.setdefault("RECONCILIATION_DB", ":memory:")
    from reconciliation_platform.api.app import app

    transport = httpx.ASGITransport(app=app)
    semaphore = asyncio.Semaphore(concurrency)
    statuses: list[int] = []

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        async def one(index: int) -> None:
            async with semaphore:
                response = await client.get("/health")
                statuses.append(response.status_code)

        started = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(requests)))
        elapsed = time.perf_counter() - started

    success = sum(status == 200 for status in statuses)
    return {
        "requests": requests,
        "concurrency": concurrency,
        "elapsed_seconds": round(elapsed, 6),
        "requests_per_second": round(requests / elapsed, 2) if elapsed else 0.0,
        "successful": success,
        "failed": requests - success,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = asyncio.run(run(args.concurrency, args.requests))
    print(json.dumps(result, indent=2))
    if result["failed"]:
        raise SystemExit("load test had failed requests")
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
