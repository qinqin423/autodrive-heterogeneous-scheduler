from __future__ import annotations

import argparse
import json
from pathlib import Path

from autodrive_scheduler.schedulers import EDFScheduler, FIFOScheduler, FixedScheduler
from autodrive_scheduler.simulator import run_from_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = PROJECT_ROOT / "configs" / "scenarios" / "smoke.yaml"

_SCHEDULERS = (FixedScheduler(), FIFOScheduler(), EDFScheduler())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline schedulers on a scenario.")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()

    scenario_path = args.scenario.resolve()

    if args.output_root:
        output_root = args.output_root.resolve()
    else:
        scenario_name = scenario_path.stem
        output_root = PROJECT_ROOT / "results" / "generated" / scenario_name

    summaries = []
    for scheduler in _SCHEDULERS:
        summary = run_from_file(
            scenario_path,
            scheduler,
            output_root / scheduler.name,
        )
        summaries.append(summary)
    print(json.dumps(summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
