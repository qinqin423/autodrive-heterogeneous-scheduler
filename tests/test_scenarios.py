from pathlib import Path

from autodrive_scheduler.config import generate_tasks, load_scenario
from autodrive_scheduler.schedulers import EDFScheduler, FIFOScheduler
from autodrive_scheduler.simulator import SimulationRunner


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_high_load_task_count() -> None:
    scenario = load_scenario(PROJECT_ROOT / "configs" / "scenarios" / "high_load.yaml")
    tasks = generate_tasks(scenario)
    assert len(tasks) == 134


def test_emergency_overload_task_count() -> None:
    scenario = load_scenario(PROJECT_ROOT / "configs" / "scenarios" / "emergency_overload.yaml")
    tasks = generate_tasks(scenario)
    assert len(tasks) == 148

    emergency_tasks = [t for t in tasks if t.service.name == "emergency_obstacle_detection"]
    assert len(emergency_tasks) == 14


def test_background_tasks_consistency() -> None:
    high_load_scenario = load_scenario(PROJECT_ROOT / "configs" / "scenarios" / "high_load.yaml")
    overload_scenario = load_scenario(PROJECT_ROOT / "configs" / "scenarios" / "emergency_overload.yaml")

    high_load_tasks = generate_tasks(high_load_scenario)
    overload_tasks = generate_tasks(overload_scenario)

    overload_background_tasks = [
        t for t in overload_tasks
        if t.service.name != "emergency_obstacle_detection"
    ]

    assert high_load_tasks == overload_background_tasks


def test_emergency_overload_deadline_miss_comparison() -> None:
    scenario = load_scenario(PROJECT_ROOT / "configs" / "scenarios" / "emergency_overload.yaml")

    _, fifo_summary = SimulationRunner(scenario, FIFOScheduler()).run()
    _, edf_summary = SimulationRunner(scenario, EDFScheduler()).run()

    fifo_misses = fifo_summary["deadline_misses"]
    edf_misses = edf_summary["deadline_misses"]

    assert fifo_misses > 0
    assert edf_misses < fifo_misses
