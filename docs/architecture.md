# Architecture

## Simulation flow

1. Load and validate device, service, and scenario YAML files.
2. Generate deterministic task instances from periodic workload definitions.
3. Release tasks into a SimPy environment at their configured arrival times.
4. Ask the selected scheduler to assign each task to a compatible resource.
5. Execute the task using a finite-capacity SimPy resource.
6. Record queue delay, execution time, response time, deadline status, and utilization.
7. Export task-level CSV data and an aggregate JSON summary.

## v0.1 scheduling semantics

### Fixed

Each service is statically mapped to its configured preferred resource. This represents a simple deployment in which model-to-device binding does not adapt to runtime load.

### FIFO

Tasks are considered in release order. For the current task, the scheduler estimates the finish time on every compatible resource and selects the resource with the earliest predicted finish. It does not reorder already released tasks by deadline or priority.

### EDF (Earliest Deadline First)

EDF is a per-device, non-preemptive scheduler that sorts each device's wait queue by task absolute deadline. Tasks with earlier deadlines are served first. The resource selection logic inherits FIFO's earliest-finish heuristic: for each task, it estimates the finish time on every compatible resource and selects the resource with the earliest predicted finish. Once a task starts executing, it runs to completion without interruption.

Note that ResourceState's reservation estimates are updated at task arrival time in release order. This optimistic prediction may differ from the actual completion times after EDF reorders the wait queue. Therefore, this is a baseline algorithm and not a globally optimal EDF scheduler.

## Planned DRAS extension

The Deadline- and Resource-Aware Scheduler will use predicted finish time, remaining slack, task priority, resource compatibility, and current load. The v0.1 interfaces intentionally separate scheduling policy from simulation so that DRAS can be added without rewriting the engine.

