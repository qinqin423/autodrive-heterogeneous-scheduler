from pathlib import Path

from autodrive_scheduler.config import generate_tasks, load_scenario


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = PROJECT_ROOT / "configs" / "scenarios" / "smoke.yaml"


def test_smoke_scenario_generates_expected_tasks() -> None:
    scenario = load_scenario(SCENARIO)
    tasks = generate_tasks(scenario)

    assert len(tasks) == 25
    assert tasks[0].task_id == "object_detection-0000"
    assert tasks[0].arrival_ms == 0
    assert tasks[-1].arrival_ms < scenario["duration_ms"]


def test_generated_tasks_are_deterministically_ordered() -> None:
    scenario = load_scenario(SCENARIO)
    first = generate_tasks(scenario)
    second = generate_tasks(scenario)

    assert first == second

