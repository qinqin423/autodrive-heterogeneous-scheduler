from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ServiceSpec:
    """Static execution and deadline profile for one AI service."""

    name: str
    priority: int
    deadline_ms: float
    preferred_resource: str
    execution_ms: dict[str, float]

    def compatible_resources(self) -> tuple[str, ...]:
        return tuple(self.execution_ms)


@dataclass(frozen=True)
class Task:
    """One released instance of an AI service."""

    task_id: str
    service: ServiceSpec
    arrival_ms: float

    @property
    def absolute_deadline_ms(self) -> float:
        return self.arrival_ms + self.service.deadline_ms


@dataclass
class ResourceState:
    """Scheduler-visible state for a finite-capacity compute device."""

    name: str
    capacity: int
    ready_times: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"Resource {self.name!r} must have capacity >= 1")
        if not self.ready_times:
            self.ready_times = [0.0] * self.capacity
        if len(self.ready_times) != self.capacity:
            raise ValueError("ready_times length must match capacity")

    def estimate_finish(self, now_ms: float, execution_ms: float) -> float:
        earliest_lane = min(self.ready_times)
        return max(now_ms, earliest_lane) + execution_ms

    def reserve(self, now_ms: float, execution_ms: float) -> float:
        lane_index = min(range(self.capacity), key=self.ready_times.__getitem__)
        start_ms = max(now_ms, self.ready_times[lane_index])
        finish_ms = start_ms + execution_ms
        self.ready_times[lane_index] = finish_ms
        return finish_ms


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    service: str
    resource: str
    priority: int
    arrival_ms: float
    start_ms: float
    finish_ms: float
    deadline_ms: float
    execution_ms: float
    scheduler_overhead_ms: float

    @property
    def queue_delay_ms(self) -> float:
        return self.start_ms - self.arrival_ms

    @property
    def response_ms(self) -> float:
        return self.finish_ms - self.arrival_ms

    @property
    def deadline_missed(self) -> bool:
        return self.finish_ms > self.deadline_ms

