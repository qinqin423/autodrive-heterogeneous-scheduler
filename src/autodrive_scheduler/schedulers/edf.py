from __future__ import annotations

from autodrive_scheduler.models import Task
from autodrive_scheduler.schedulers.fifo import FIFOScheduler


class EDFScheduler(FIFOScheduler):
    """Non-preemptive EDF: sort wait queue by absolute deadline, select earliest-finish resource."""

    name = "edf"

    def queue_priority(self, task: Task) -> float:
        return task.absolute_deadline_ms