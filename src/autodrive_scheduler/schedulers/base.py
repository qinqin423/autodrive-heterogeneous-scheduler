from __future__ import annotations

from abc import ABC, abstractmethod

from autodrive_scheduler.models import ResourceState, Task


class Scheduler(ABC):
    """Resource-selection policy used by the simulation engine."""

    name: str

    @abstractmethod
    def choose_resource(
        self,
        task: Task,
        resources: dict[str, ResourceState],
        now_ms: float,
    ) -> str:
        """Return the resource name selected for the task."""

    def queue_priority(self, task: Task) -> float:
        """Return the priority value for queue ordering. Lower values are served first.

        Defaults to arrival time for FIFO behavior.
        """
        return task.arrival_ms

