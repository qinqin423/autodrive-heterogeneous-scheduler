from autodrive_scheduler.models import ResourceState, ServiceSpec, Task
from autodrive_scheduler.schedulers import FIFOScheduler, FixedScheduler


def make_task() -> Task:
    service = ServiceSpec(
        name="detector",
        priority=3,
        deadline_ms=100,
        preferred_resource="gpu",
        execution_ms={"cpu": 80.0, "gpu": 20.0},
    )
    return Task(task_id="detector-0000", service=service, arrival_ms=0.0)


def test_fixed_scheduler_uses_preferred_resource() -> None:
    resources = {
        "cpu": ResourceState("cpu", 1),
        "gpu": ResourceState("gpu", 1),
    }
    assert FixedScheduler().choose_resource(make_task(), resources, 0.0) == "gpu"


def test_fifo_scheduler_uses_earliest_predicted_finish() -> None:
    resources = {
        "cpu": ResourceState("cpu", 1, ready_times=[0.0]),
        "gpu": ResourceState("gpu", 1, ready_times=[100.0]),
    }
    assert FIFOScheduler().choose_resource(make_task(), resources, 0.0) == "cpu"

