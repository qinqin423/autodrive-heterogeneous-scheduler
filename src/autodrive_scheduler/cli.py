from __future__ import annotations

import argparse
import json
from pathlib import Path

from autodrive_scheduler.schedulers import DRASScheduler, EDFScheduler, FIFOScheduler, FixedScheduler
from autodrive_scheduler.simulator import run_from_file


_SCHEDULER_MAP = {
    "fixed": FixedScheduler,
    "fifo": FIFOScheduler,
    "edf": EDFScheduler,
    "dras": DRASScheduler,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate heterogeneous autonomous-driving AI service scheduling."
    )
    parser.add_argument("--scheduler", choices=tuple(_SCHEDULER_MAP.keys()), required=True)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scheduler_class = _SCHEDULER_MAP[args.scheduler]
    summary = run_from_file(args.scenario, scheduler_class(), args.output)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

