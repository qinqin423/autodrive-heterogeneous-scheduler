# DRAS Design (v0.3, first version)

## Problem definition

Fixed binding ignores runtime load; FIFO ignores deadlines; EDF sorts each
device's wait queue by deadline but still selects the resource with the earliest
predicted finish, which may concentrate work on a fast accelerator and does not
explicitly account for task priority during resource selection. DRAS (Deadline-
and Resource-Aware Scheduler) is a proposed lightweight online heuristic that
keeps EDF's per-device, non-preemptive queue ordering and replaces only the
resource-selection step with a score that jointly considers deadline risk,
response, current load, and heterogeneous slowdown.

DRAS is **not** a globally optimal scheduler. It is a single-step greedy
heuristic evaluated at task arrival time using the arrival-order reservation
approximation maintained by `ResourceState`.

## Scoring variables

For task `i` and compatible resource `r`, with `now_ms` the current simulation
time. The slowdown denominator uses only the currently available compatible
resources (`minimum_available_execution_ms`), not the full `execution_ms` map,
so an unavailable fastest device does not distort the normalization.

| Variable | Formula | Meaning |
|----------|---------|---------|
| `q_i` | `clip(priority / max_priority, 0, 1)` | Normalized priority in `[0, 1]`. Higher means more urgent. |
| `wait_ms` | `max(0, min(resource.ready_times) - now_ms)` | Estimated queue wait before the task can start on `r`. |
| `predicted_finish_ms` | `resource.estimate_finish(now_ms, execution_ms)` | Estimated finish time = `max(now_ms, earliest_lane) + execution_ms`. |
| `response_ratio` | `(predicted_finish_ms - arrival_ms) / deadline_ms` | End-to-end response normalized by the relative deadline. |
| `tardiness_ratio` | `max(0, (predicted_finish_ms - absolute_deadline_ms) / deadline_ms)` | Zero when on time; positive when predicted to miss. |
| `load_ratio` | `wait_ms / deadline_ms` | Current queue pressure normalized by the relative deadline. |
| `slowdown_ratio` | `execution_ms / minimum_available_execution_ms - 1` | Heterogeneous speed penalty for picking a slower resource. Zero for the fastest available compatible resource. |

## Scoring function

```
score = tardiness_weight * (1 + q_i) * tardiness_ratio
      + response_weight   * response_ratio
      + load_weight       * (1 - q_i) * load_ratio
      + slowdown_weight   * slowdown_ratio
```

Lower score is preferred. Resource selection picks the minimum of
`(score, predicted_finish_ms, resource_name)` deterministically.

Design intent of each term:

- The **tardiness** term is multiplied by `(1 + q_i)` so high-priority tasks are
  pushed harder away from resources that predict a miss.
- The **load** term is multiplied by `(1 - q_i)` so low-priority tasks are
  discouraged from occupying a loaded fast accelerator that a later
  high-priority task may need.
- The **response** term keeps overall latency low.
- The **slowdown** term discourages picking a much slower resource merely
  because it is idle.

## Default parameters

| Parameter | Default | Constraint |
|-----------|---------|------------|
| `tardiness_weight` | `10.0` | finite and `>= 0` |
| `response_weight` | `1.0` | finite and `>= 0` |
| `load_weight` | `1.0` | finite and `>= 0` |
| `slowdown_weight` | `0.05` | finite and `>= 0` |
| `max_priority` | `5.0` | finite and `> 0` |

`NaN` and non-finite values are rejected. These weights are development defaults
chosen before any DRAS benchmark run. They are exposed as constructor arguments
so that later ablation experiments can sweep them. The defaults are not claimed
to be optimal and will be validated against the development scenarios
(`high_load`, `emergency_overload`) and ablation studies in later work.

## Why DRAS inherits EDF queue ordering

EDF's per-device, non-preemptive queue sort by absolute deadline is a sensible
default for urgency within a single device. DRAS focuses on the orthogonal
resource-selection decision: given that a task will wait in some device's queue,
which device's queue should it enter? Inheriting `EDFScheduler` and overriding
only `choose_resource` keeps the queue semantics unchanged and avoids
reimplementing the deadline sort.

## Differences from Fixed, FIFO, and EDF

| Scheduler | Queue order | Resource selection |
|-----------|-------------|--------------------|
| Fixed | arrival (FIFO) | static `preferred_resource` |
| FIFO | arrival (FIFO) | earliest predicted finish |
| EDF | absolute deadline | earliest predicted finish (inherited from FIFO) |
| DRAS | absolute deadline (inherited from EDF) | minimum DRAS score |

DRAS is the only policy that considers priority, load, and slowdown together
when choosing a resource.

## Limitations of the ResourceState reservation estimate

`ResourceState.ready_times` is an arrival-order reservation approximation: it is
updated at task arrival time via `reserve()`, in release order. Because EDF/DRAS
then reorder each device's wait queue by deadline, the actual start and finish
times may differ from these estimates, and the error direction is not fixed:

- For an older task that gets pushed back by later short-deadline tasks, the
  reserved lane time is too optimistic (the task actually starts later than
  reserved).
- For a later task that gets pulled forward by EDF ahead of older long-deadline
  tasks, the reserved estimate may be too pessimistic.

`predicted_finish_ms` is therefore an approximation, not a guarantee. DRAS does
not re-evaluate scores after queue reordering; it is a single-step heuristic.
This is why DRAS is described as a lightweight online heuristic rather than a
globally optimal scheduler.
