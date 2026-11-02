"""Summarize the last 100000 API request events from JSONL on stdin; no network I/O."""

import json
import math
import sys
from collections import defaultdict, deque


def percentile(values: list[float], percent: float) -> float:
    return round(values[max(0, math.ceil(len(values) * percent) - 1)], 2)


records = deque(maxlen=100000)
for line in sys.stdin:
    try:
        row = json.loads(line)
        duration = float(row.get("duration_ms", -1))
        if row.get("message") != "request_completed" or not 0 <= duration < math.inf:
            continue
        records.append(
            (
                str(row.get("method", "unknown")),
                str(row.get("route", "_unmatched")),
                int(row["status"]),
                duration,
            )
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        continue

groups = defaultdict(list)
for method, route, status, duration in records:
    groups[(method, route)].append((status, duration))
result = []
bounds = [50, 100, 250, 500, 1000, 2500, 5000, 10000]
for (method, route), values in sorted(groups.items()):
    durations = sorted(value for _, value in values)

    result.append(
        {
            "method": method,
            "route": route,
            "requests": len(values),
            "server_errors": sum(status >= 500 for status, _ in values),
            "p50_ms": percentile(durations, 0.5),
            "p95_ms": percentile(durations, 0.95),
            "p99_ms": percentile(durations, 0.99),
            "duration_histogram_cumulative": {
                str(bound): sum(value <= bound for value in durations) for bound in bounds
            },
        }
    )
print(json.dumps({"window": "last 100000 request events", "routes": result}, indent=2))
