from __future__ import annotations

from autodrive_scheduler.models import ResourceState, Task
from autodrive_scheduler.schedulers.base import Scheduler


class FixedScheduler(Scheduler):
    """Always use each service's statically configured preferred device."""

    name = "fixed"

    def choose_resource(
        self,
        task: Task,
        resources: dict[str, ResourceState],
        now_ms: float,
    ) -> str:
        del now_ms
        selected = task.service.preferred_resource
        if selected not in resources:
            raise ValueError(f"Preferred resource {selected!r} is not available")
        if selected not in task.service.execution_ms:
            raise ValueError(f"Task {task.task_id!r} is incompatible with {selected!r}")
        return selected

