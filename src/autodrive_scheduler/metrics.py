from __future__ import annotations

import math
from collections import defaultdict
from statistics import fmean

from autodrive_scheduler.models import TaskResult


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def summarize(
    results: list[TaskResult],
    duration_ms: float,
    device_capacities: dict[str, int],
) -> dict[str, object]:
    responses = [result.response_ms for result in results]
    missed = sum(result.deadline_missed for result in results)
    busy_ms: dict[str, float] = defaultdict(float)
    overhead = [result.scheduler_overhead_ms for result in results]

    for result in results:
        busy_ms[result.resource] += result.execution_ms

    utilization = {
        resource: busy_ms[resource] / (duration_ms * capacity)
        for resource, capacity in device_capacities.items()
    }

    return {
        "completed_tasks": len(results),
        "deadline_misses": missed,
        "deadline_miss_rate": missed / len(results) if results else 0.0,
        "mean_response_ms": fmean(responses) if responses else 0.0,
        "p95_response_ms": _percentile(responses, 0.95),
        "throughput_tasks_per_s": len(results) / (duration_ms / 1000.0),
        "mean_scheduler_overhead_ms": fmean(overhead) if overhead else 0.0,
        "resource_utilization": utilization,
    }

