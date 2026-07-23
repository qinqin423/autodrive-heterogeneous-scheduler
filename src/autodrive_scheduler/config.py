from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import yaml

from autodrive_scheduler.models import ServiceSpec, Task


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def load_scenario(path: str | Path) -> dict[str, Any]:
    scenario_path = Path(path).resolve()
    scenario = _read_yaml(scenario_path)

    for key in ("name", "duration_ms", "devices_file", "services_file", "workloads"):
        if key not in scenario:
            raise ValueError(f"Scenario is missing required key: {key}")

    base_dir = scenario_path.parent
    devices_path = (base_dir / scenario["devices_file"]).resolve()
    services_path = (base_dir / scenario["services_file"]).resolve()

    devices_data = _read_yaml(devices_path).get("devices")
    services_data = _read_yaml(services_path).get("services")
    if not isinstance(devices_data, dict) or not devices_data:
        raise ValueError("Device configuration must contain a non-empty 'devices' mapping")
    if not isinstance(services_data, dict) or not services_data:
        raise ValueError("Service configuration must contain a non-empty 'services' mapping")

    devices: dict[str, int] = {}
    for name, raw in devices_data.items():
        capacity = int(raw["capacity"])
        if capacity < 1:
            raise ValueError(f"Device {name!r} must have capacity >= 1")
        devices[name] = capacity

    services: dict[str, ServiceSpec] = {}
    for name, raw in services_data.items():
        execution_ms = {resource: float(value) for resource, value in raw["execution_ms"].items()}
        unknown_resources = set(execution_ms) - set(devices)
        if unknown_resources:
            raise ValueError(f"Service {name!r} references unknown resources: {sorted(unknown_resources)}")
        preferred = str(raw["preferred_resource"])
        if preferred not in execution_ms:
            raise ValueError(f"Preferred resource for {name!r} must be compatible")
        services[name] = ServiceSpec(
            name=name,
            priority=int(raw["priority"]),
            deadline_ms=float(raw["deadline_ms"]),
            preferred_resource=preferred,
            execution_ms=execution_ms,
        )

    scenario["scenario_path"] = scenario_path
    scenario["devices"] = devices
    scenario["services"] = services
    return scenario


def generate_tasks(scenario: dict[str, Any]) -> list[Task]:
    duration_ms = float(scenario["duration_ms"])
    rng = random.Random(int(scenario.get("random_seed", 0)))
    services: dict[str, ServiceSpec] = scenario["services"]
    tasks: list[Task] = []

    for workload in scenario["workloads"]:
        service_name = str(workload["service"])
        if service_name not in services:
            raise ValueError(f"Workload references unknown service: {service_name}")

        period_ms = float(workload["period_ms"])
        if period_ms <= 0:
            raise ValueError("period_ms must be positive")
        jitter_ms = float(workload.get("jitter_ms", 0.0))
        release_ms = float(workload.get("start_ms", 0.0))
        index = 0

        while release_ms < duration_ms:
            tasks.append(
                Task(
                    task_id=f"{service_name}-{index:04d}",
                    service=services[service_name],
                    arrival_ms=max(0.0, release_ms),
                )
            )
            index += 1
            jitter = rng.uniform(-jitter_ms, jitter_ms) if jitter_ms else 0.0
            release_ms += max(0.001, period_ms + jitter)

    return sorted(tasks, key=lambda task: (task.arrival_ms, task.task_id))

