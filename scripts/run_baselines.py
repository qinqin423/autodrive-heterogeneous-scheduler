from __future__ import annotations

import json
from pathlib import Path

from autodrive_scheduler.schedulers import FIFOScheduler, FixedScheduler
from autodrive_scheduler.simulator import run_from_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = PROJECT_ROOT / "configs" / "scenarios" / "smoke.yaml"
RESULTS_ROOT = PROJECT_ROOT / "results" / "sample"


def main() -> None:
    summaries = []
    for scheduler in (FixedScheduler(), FIFOScheduler()):
        summary = run_from_file(
            SCENARIO,
            scheduler,
            RESULTS_ROOT / scheduler.name,
        )
        summaries.append(summary)
    print(json.dumps(summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

