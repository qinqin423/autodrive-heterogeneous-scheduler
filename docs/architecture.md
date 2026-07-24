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

ResourceState's reservation estimates are updated at task arrival time in
release order. This arrival-order reservation approximation may differ from
actual completion times after EDF reorders the wait queue, and the error
direction is not fixed: it may be too optimistic for older tasks pushed back
by later short-deadline tasks, or too pessimistic for later urgent tasks
pulled forward by EDF. Therefore, EDF is a baseline heuristic rather than a
globally optimal scheduler.

## DRAS (Deadline- and Resource-Aware Scheduler, v0.3 first version)

DRAS inherits EDF's per-device, non-preemptive queue ordering and overrides only
resource selection. For each compatible resource it computes a score from four
terms: a priority-weighted tardiness ratio, a response ratio, a
priority-discounted load ratio, and a heterogeneous slowdown ratio. The slowdown
denominator uses only the currently available compatible resources, so an
unavailable fastest device does not distort the normalization. Lower score is
preferred; ties are broken by predicted finish time then resource name. The
queue sort itself is unchanged from EDF, so DRAS does not introduce preemption.

The default weights (`tardiness=10.0`, `response=1.0`, `load=1.0`,
`slowdown=0.05`, `max_priority=5.0`) are development defaults chosen before any
DRAS benchmark run, exposed as constructor arguments for ablation. They are
finite, non-negative (`max_priority` positive), and not claimed to be optimal.

`ResourceState`'s reservation estimates are an arrival-order reservation
approximation: updated at arrival time in release order. Because EDF/DRAS then
reorder the wait queue by deadline, `predicted_finish_ms` may differ from the
actual finish time, and the error direction is not fixed (too optimistic for
older tasks pushed back by short-deadline tasks; too pessimistic for later tasks
pulled forward by EDF). DRAS is therefore a lightweight online heuristic, not a
globally optimal scheduler. See [dras_design.md](dras_design.md) for the full
scoring function and rationale.

