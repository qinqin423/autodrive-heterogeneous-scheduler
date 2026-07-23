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

