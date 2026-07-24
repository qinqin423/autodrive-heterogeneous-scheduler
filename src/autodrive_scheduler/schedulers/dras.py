from __future__ import annotations

import math

from autodrive_scheduler.models import ResourceState, Task
from autodrive_scheduler.schedulers.edf import EDFScheduler


class DRASScheduler(EDFScheduler):
    """Deadline- and Resource-Aware Scheduler (v0.3, first version).

    A lightweight online heuristic that inherits EDF's per-device, non-preemptive
    queue ordering and only overrides resource selection. The scoring function
    combines tardiness risk, response ratio, current load, and heterogeneous
    slowdown. Lower score is preferred.

    This is not a globally optimal scheduler. ResourceState's reservation
    estimates are an arrival-order reservation approximation: they are updated at
    task arrival time in release order. Because EDF/DRAS then reorder each
    device's wait queue by deadline, these estimates may differ from the actual
    completion times, and the error direction is not fixed: estimates may be too
    optimistic for older tasks that get pushed back by later short-deadline
    tasks, and too pessimistic for later tasks that get pulled forward by EDF.
    """

    name = "dras"

    def __init__(
        self,
        tardiness_weight: float = 10.0,
        response_weight: float = 1.0,
        load_weight: float = 1.0,
        slowdown_weight: float = 0.05,
        max_priority: float = 5.0,
    ) -> None:
        for name, value in (
            ("tardiness_weight", tardiness_weight),
            ("response_weight", response_weight),
            ("load_weight", load_weight),
            ("slowdown_weight", slowdown_weight),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if not math.isfinite(max_priority) or max_priority <= 0:
            raise ValueError("max_priority must be finite and > 0")

        self.tardiness_weight = tardiness_weight
        self.response_weight = response_weight
        self.load_weight = load_weight
        self.slowdown_weight = slowdown_weight
        self.max_priority = max_priority

    def choose_resource(
        self,
        task: Task,
        resources: dict[str, ResourceState],
        now_ms: float,
    ) -> str:
        compatible = [
            resource_name
            for resource_name in task.service.compatible_resources()
            if resource_name in resources
        ]
        if not compatible:
            raise ValueError(f"No compatible resource is available for {task.task_id!r}")

        minimum_available_execution_ms = min(
            task.service.execution_ms[name] for name in compatible
        )

        scored = [
            (
                self._score(
                    task,
                    resources[resource_name],
                    now_ms,
                    minimum_available_execution_ms,
                ),
                resources[resource_name].estimate_finish(
                    now_ms,
                    task.service.execution_ms[resource_name],
                ),
                resource_name,
            )
            for resource_name in compatible
        ]
        return min(scored)[2]

    def _score(
        self,
        task: Task,
        resource: ResourceState,
        now_ms: float,
        minimum_available_execution_ms: float,
    ) -> float:
        execution_ms = task.service.execution_ms[resource.name]

        q_i = max(0.0, min(1.0, task.service.priority / self.max_priority))
        wait_ms = max(0.0, min(resource.ready_times) - now_ms)
        predicted_finish_ms = resource.estimate_finish(now_ms, execution_ms)

        response_ratio = (predicted_finish_ms - task.arrival_ms) / task.service.deadline_ms
        tardiness_ratio = max(
            0.0,
            (predicted_finish_ms - task.absolute_deadline_ms) / task.service.deadline_ms,
        )
        load_ratio = wait_ms / task.service.deadline_ms
        slowdown_ratio = execution_ms / minimum_available_execution_ms - 1.0

        return (
            self.tardiness_weight * (1.0 + q_i) * tardiness_ratio
            + self.response_weight * response_ratio
            + self.load_weight * (1.0 - q_i) * load_ratio
            + self.slowdown_weight * slowdown_ratio
        )
