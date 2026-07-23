import json
from pathlib import Path

from autodrive_scheduler.config import load_scenario
from autodrive_scheduler.schedulers import FIFOScheduler
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

