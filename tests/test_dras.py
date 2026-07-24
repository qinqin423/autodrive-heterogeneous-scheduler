import pytest

from autodrive_scheduler.models import ResourceState, ServiceSpec, Task
from autodrive_scheduler.schedulers import DRASScheduler, EDFScheduler, FIFOScheduler


def make_task(
    name: str = "detector",
    priority: int = 3,
    deadline_ms: float = 100.0,
    arrival_ms: float = 0.0,
    execution_ms: dict[str, float] | None = None,
) -> Task:
    execution = execution_ms if execution_ms is not None else {"cpu": 80.0, "gpu": 20.0}
    service = ServiceSpec(
        name=name,
        priority=priority,
        deadline_ms=deadline_ms,
        preferred_resource="gpu",
        execution_ms=execution,
    )
    return Task(task_id=f"{name}-0000", service=service, arrival_ms=arrival_ms)


def test_dras_inherits_edf_queue_semantics() -> None:
    """DRAS keeps EDF's per-device queue ordering by absolute deadline."""
    task = make_task(deadline_ms=50.0, arrival_ms=100.0)
    dras = DRASScheduler()
    edf = EDFScheduler()
    assert dras.queue_priority(task) == edf.queue_priority(task)
    assert dras.queue_priority(task) == task.absolute_deadline_ms


def test_dras_load_aware_prefers_idle_gpu_for_low_priority_task() -> None:
    """Low-priority lane_detection: FIFO picks loaded NPU (earliest finish),
    DRAS picks idle GPU because the load term penalizes waiting on NPU for a
    low-priority task.

    Interpretable numbers (now_ms=0, deadline=100, priority=2, q_i=0.4):
      - gpu: exec 22, ready_times=[0]  -> finish 22, wait 0
      - npu: exec 16, ready_times=[5]  -> finish 21, wait 5
    FIFO picks npu (21 < 22).
    DRAS scores (min_available_execution_ms = 16):
      npu: response 21/100=0.21, load (1-0.4)*5/100=0.03, slowdown 0 -> 0.24
      gpu: response 22/100=0.22, load 0, slowdown (22/16-1)*0.05=0.01875 -> 0.23875
    DRAS picks gpu (0.23875 < 0.24).
    """
    task = make_task(
        name="lane_detection",
        priority=2,
        deadline_ms=100.0,
        arrival_ms=0.0,
        execution_ms={"cpu": 90.0, "gpu": 22.0, "npu": 16.0},
    )
    resources = {
        "gpu": ResourceState("gpu", 1, ready_times=[0.0]),
        "npu": ResourceState("npu", 1, ready_times=[5.0]),
    }
    assert FIFOScheduler().choose_resource(task, resources, 0.0) == "npu"
    assert DRASScheduler().choose_resource(task, resources, 0.0) == "gpu"


def test_dras_slowdown_uses_only_available_resources() -> None:
    """slowdown_ratio must normalize against only the currently available
    compatible resources, not the full execution_ms map.

    Interpretable numbers (now_ms=0, deadline=100, priority=2, q_i=0.4):
      - service execution_ms: npu=1 (NOT available), gpu=10, cpu=11
      - gpu: ready_times=[1] -> finish 11, wait 1
      - cpu: ready_times=[0] -> finish 11, wait 0
      - available min execution = 10 (gpu)
    Correct normalization (min=10):
      gpu: response 0.11, load (1-0.4)*1/100=0.006, slowdown 0      -> 0.116
      cpu: response 0.11, load 0,          slowdown (11/10-1)*0.05=0.005 -> 0.115
      DRAS picks cpu (0.115 < 0.116).
    Wrong normalization (min=1, including the unavailable npu):
      gpu: slowdown (10/1-1)*0.05=0.45 -> 0.566
      cpu: slowdown (11/1-1)*0.05=0.50 -> 0.610
      would pick gpu. The correct implementation must pick cpu.
    """
    task = make_task(
        name="custom",
        priority=2,
        deadline_ms=100.0,
        arrival_ms=0.0,
        execution_ms={"npu": 1.0, "gpu": 10.0, "cpu": 11.0},
    )
    resources = {
        "gpu": ResourceState("gpu", 1, ready_times=[1.0]),
        "cpu": ResourceState("cpu", 1, ready_times=[0.0]),
    }
    assert DRASScheduler().choose_resource(task, resources, 0.0) == "cpu"


def test_dras_avoids_resource_predicted_to_miss_deadline() -> None:
    """A resource predicted to miss the deadline is penalized by the tardiness
    term. DRAS must pick the on-time resource.

    Interpretable numbers (now_ms=0, deadline=40, priority=5, q_i=1.0):
      - gpu:  exec 16, ready_times=[0]  -> finish 16  (on time)
      - npu:  exec 11, ready_times=[40] -> finish 51  (misses by 11)
    The tardiness term for npu is 10*(1+1)*(51-40)/40 = 5.5, dominating.
    """
    task = make_task(
        name="emergency_obstacle_detection",
        priority=5,
        deadline_ms=40.0,
        arrival_ms=0.0,
        execution_ms={"cpu": 75.0, "gpu": 16.0, "npu": 11.0},
    )
    resources = {
        "gpu": ResourceState("gpu", 1, ready_times=[0.0]),
        "npu": ResourceState("npu", 1, ready_times=[40.0]),
    }
    assert DRASScheduler().choose_resource(task, resources, 0.0) == "gpu"


def test_dras_avoids_slow_idle_cpu() -> None:
    """An idle but very slow CPU that would miss the deadline must not be chosen
    just because it is idle. The fastest on-time resource (npu) is selected.

    Interpretable numbers (now_ms=0, deadline=80, all idle):
      - cpu: exec 110 -> finish 110 (misses 80)
      - gpu: exec 24  -> finish 24
      - npu: exec 18  -> finish 18
    """
    task = make_task(
        name="object_detection",
        priority=3,
        deadline_ms=80.0,
        arrival_ms=0.0,
        execution_ms={"cpu": 110.0, "gpu": 24.0, "npu": 18.0},
    )
    resources = {
        "cpu": ResourceState("cpu", 1, ready_times=[0.0]),
        "gpu": ResourceState("gpu", 1, ready_times=[0.0]),
        "npu": ResourceState("npu", 1, ready_times=[0.0]),
    }
    assert DRASScheduler().choose_resource(task, resources, 0.0) == "npu"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tardiness_weight": -1.0},
        {"response_weight": -0.1},
        {"load_weight": -1.0},
        {"slowdown_weight": -1.0},
        {"tardiness_weight": float("nan")},
        {"response_weight": float("nan")},
        {"load_weight": float("nan")},
        {"slowdown_weight": float("nan")},
        {"tardiness_weight": float("inf")},
        {"response_weight": float("inf")},
        {"load_weight": float("inf")},
        {"slowdown_weight": float("inf")},
        {"tardiness_weight": float("-inf")},
        {"response_weight": float("-inf")},
        {"load_weight": float("-inf")},
        {"slowdown_weight": float("-inf")},
    ],
)
def test_dras_rejects_invalid_weights(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        DRASScheduler(**kwargs)


@pytest.mark.parametrize(
    "max_priority",
    [0.0, -5.0, float("nan"), float("inf"), float("-inf")],
)
def test_dras_rejects_invalid_max_priority(max_priority: float) -> None:
    with pytest.raises(ValueError):
        DRASScheduler(max_priority=max_priority)


def test_dras_deterministic_with_tie_breaking() -> None:
    """When two resources have identical scores and predicted finishes,
    the result must be deterministic and depend only on resource_name.

    Setup:
      - execution_ms: gpu=20, cpu=20 (identical)
      - resources: gpu and cpu both idle (ready_times=[0.0])
      - deadline=100, priority=3, arrival=0
      - Both have score=0.2, predicted_finish=20
      - Sort key is (score, predicted_finish, resource_name)
      - 'cpu' < 'gpu' lexicographically, so cpu is selected
    """
    task = make_task(
        name="tied",
        priority=3,
        deadline_ms=100.0,
        arrival_ms=0.0,
        execution_ms={"gpu": 20.0, "cpu": 20.0},
    )
    resources = {
        "gpu": ResourceState("gpu", 1, ready_times=[0.0]),
        "cpu": ResourceState("cpu", 1, ready_times=[0.0]),
    }
    scheduler = DRASScheduler()
    first = scheduler.choose_resource(task, resources, 0.0)
    second = scheduler.choose_resource(task, resources, 0.0)
    assert first == "cpu"
    assert second == "cpu"


def test_dras_is_deterministic() -> None:
    """Repeated calls with identical inputs return the same resource."""
    task = make_task(
        name="object_detection",
        priority=3,
        deadline_ms=80.0,
        arrival_ms=0.0,
        execution_ms={"cpu": 110.0, "gpu": 24.0, "npu": 18.0},
    )
    resources = {
        "cpu": ResourceState("cpu", 1, ready_times=[10.0]),
        "gpu": ResourceState("gpu", 1, ready_times=[5.0]),
        "npu": ResourceState("npu", 1, ready_times=[0.0]),
    }
    scheduler = DRASScheduler()
    first = scheduler.choose_resource(task, resources, 0.0)
    second = scheduler.choose_resource(task, resources, 0.0)
    assert first == second
