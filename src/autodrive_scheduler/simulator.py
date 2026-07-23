from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns

import simpy

from autodrive_scheduler.config import generate_tasks, load_scenario
from autodrive_scheduler.metrics import summarize
from autodrive_scheduler.models import ResourceState, Task, TaskResult
from autodrive_scheduler.schedulers.base import Scheduler


class SimulationRunner:
    """Execute one configured workload with one scheduling policy."""

    def __init__(self, scenario: dict[str, object], scheduler: Scheduler) -> None:
        self.scenario = scenario
        self.scheduler = scheduler
        self.env = simpy.Environment()
        capacities: dict[str, int] = scenario["devices"]  # type: ignore[assignment]
        self.simpy_resources = {
            name: simpy.PriorityResource(self.env, capacity=capacity)
            for name, capacity in capacities.items()
        }
        self.resource_states = {
            name: ResourceState(name=name, capacity=capacity)
            for name, capacity in capacities.items()
        }
        self.results: list[TaskResult] = []

    def _run_task(self, task: Task):
        yield self.env.timeout(task.arrival_ms)

        started_ns = perf_counter_ns()
        resource_name = self.scheduler.choose_resource(
            task,
            self.resource_states,
            float(self.env.now),
        )
        overhead_ms = (perf_counter_ns() - started_ns) / 1_000_000.0
        execution_ms = task.service.execution_ms[resource_name]
        self.resource_states[resource_name].reserve(float(self.env.now), execution_ms)

        resource = self.simpy_resources[resource_name]
        with resource.request(priority=self.scheduler.queue_priority(task)) as request:
            yield request
            start_ms = float(self.env.now)
            yield self.env.timeout(execution_ms)
            finish_ms = float(self.env.now)

        self.results.append(
            TaskResult(
                task_id=task.task_id,
                service=task.service.name,
                resource=resource_name,
                priority=task.service.priority,
                arrival_ms=task.arrival_ms,
                start_ms=start_ms,
                finish_ms=finish_ms,
                deadline_ms=task.absolute_deadline_ms,
                execution_ms=execution_ms,
                scheduler_overhead_ms=overhead_ms,
            )
        )

    def run(self) -> tuple[list[TaskResult], dict[str, object]]:
        tasks = generate_tasks(self.scenario)
        for task in tasks:
            self.env.process(self._run_task(task))
        self.env.run()
        self.results.sort(key=lambda result: (result.arrival_ms, result.task_id))

        duration_ms = max(
            float(self.scenario["duration_ms"]),
            max((result.finish_ms for result in self.results), default=0.0),
        )
        capacities: dict[str, int] = self.scenario["devices"]  # type: ignore[assignment]
        summary = summarize(self.results, duration_ms, capacities)
        summary.update(
            {
                "scenario": self.scenario["name"],
                "scheduler": self.scheduler.name,
                "configured_duration_ms": float(self.scenario["duration_ms"]),
                "observed_duration_ms": duration_ms,
            }
        )
        return self.results, summary


def write_results(
    results: list[TaskResult],
    summary: dict[str, object],
    output_dir: str | Path,
) -> None:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    task_rows = []
    for result in results:
        row = asdict(result)
        row.update(
            {
                "queue_delay_ms": result.queue_delay_ms,
                "response_ms": result.response_ms,
                "deadline_missed": result.deadline_missed,
            }
        )
        task_rows.append(row)

    csv_path = destination / "tasks.csv"
    if task_rows:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=task_rows[0].keys())
            writer.writeheader()
            writer.writerows(task_rows)

    with (destination / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)


def run_from_file(
    scenario_path: str | Path,
    scheduler: Scheduler,
    output_dir: str | Path,
) -> dict[str, object]:
    scenario = load_scenario(scenario_path)
    results, summary = SimulationRunner(scenario, scheduler).run()
    write_results(results, summary, output_dir)
    return summary

