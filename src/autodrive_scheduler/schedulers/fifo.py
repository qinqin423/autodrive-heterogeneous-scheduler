from __future__ import annotations

from autodrive_scheduler.models import ResourceState, Task
from autodrive_scheduler.schedulers.base import Scheduler


class FIFOScheduler(Scheduler):
    """Keep release order and select the compatible earliest-finish resource."""

    name = "fifo"

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

        return min(
            compatible,
            key=lambda resource_name: (
                resources[resource_name].estimate_finish(
                    now_ms,
                    task.service.execution_ms[resource_name],
                ),
                resource_name,
            ),
        )

