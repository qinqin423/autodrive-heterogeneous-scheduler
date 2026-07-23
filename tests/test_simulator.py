import json
from pathlib import Path

from autodrive_scheduler.config import load_scenario
from autodrive_scheduler.schedulers import EDFScheduler, FIFOScheduler
from autodrive_scheduler.simulator import SimulationRunner, write_results


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = PROJECT_ROOT / "configs" / "scenarios" / "smoke.yaml"


def test_simulation_completes_and_writes_reproducible_outputs(tmp_path: Path) -> None:
    scenario = load_scenario(SCENARIO)
    results, summary = SimulationRunner(scenario, FIFOScheduler()).run()

    assert len(results) == 25
    assert summary["completed_tasks"] == 25
    assert 0.0 <= summary["deadline_miss_rate"] <= 1.0
    assert set(summary["resource_utilization"]) == {"cpu", "gpu", "npu"}

    write_results(results, summary, tmp_path)
    assert (tmp_path / "tasks.csv").exists()
    saved_summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert saved_summary["scheduler"] == "fifo"


def test_non_preemptive_edf_priority_ordering() -> None:
    from autodrive_scheduler.models import ServiceSpec

    blocker_service = ServiceSpec(
        name="blocker",
        priority=1,
        deadline_ms=1000.0,
        preferred_resource="cpu",
        execution_ms={"cpu": 100.0},
    )

    long_deadline_service = ServiceSpec(
        name="long-deadline",
        priority=1,
        deadline_ms=200.0,
        preferred_resource="cpu",
        execution_ms={"cpu": 10.0},
    )

    short_deadline_service = ServiceSpec(
        name="short-deadline",
        priority=1,
        deadline_ms=50.0,
        preferred_resource="cpu",
        execution_ms={"cpu": 10.0},
    )

    scenario = {
        "name": "edf-test",
        "duration_ms": 200.0,
        "devices": {"cpu": 1},
        "services": {
            "blocker": blocker_service,
            "long-deadline": long_deadline_service,
            "short-deadline": short_deadline_service,
        },
        "workloads": [
            {"service": "blocker", "period_ms": 1000.0, "start_ms": 0.0},
            {"service": "long-deadline", "period_ms": 1000.0, "start_ms": 10.0},
            {"service": "short-deadline", "period_ms": 1000.0, "start_ms": 20.0},
        ],
    }

    fifo_results, _ = SimulationRunner(scenario, FIFOScheduler()).run()
    edf_results, _ = SimulationRunner(scenario, EDFScheduler()).run()

    fifo_start_order = [
        (r.service, r.start_ms)
        for r in sorted(fifo_results, key=lambda x: x.start_ms)
    ]
    edf_start_order = [
        (r.service, r.start_ms)
        for r in sorted(edf_results, key=lambda x: x.start_ms)
    ]

    assert fifo_start_order[0] == ("blocker", 0.0)
    assert fifo_start_order[1] == ("long-deadline", 100.0)
    assert fifo_start_order[2] == ("short-deadline", 110.0)

    assert edf_start_order[0] == ("blocker", 0.0)
    assert edf_start_order[1] == ("short-deadline", 100.0)
    assert edf_start_order[2] == ("long-deadline", 110.0)

