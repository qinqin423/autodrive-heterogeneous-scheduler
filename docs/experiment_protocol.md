# Experiment protocol

## Reproducibility rules

- Store every scenario in YAML.
- Record a random seed in every scenario.
- Do not manually edit generated result CSV files.
- Run all schedulers on the same generated task stream.
- Report mean and standard deviation when random jitter is enabled.
- Clearly label synthetic device profiles and measured device profiles.

## Controlled variable experiments

### high_load vs emergency_overload

These two scenarios form a controlled variable experiment:

- **high_load**: Deterministic near-saturation background workload without emergency requests.
- **emergency_overload**: Same background workload with periodic emergency obstacle detection requests added starting at 200ms.

The only major change between the two scenarios is the addition of the emergency perception workload. This allows measuring the scheduler's ability to handle urgent tasks under high load conditions.

### Measurement notes

- Wall-clock scheduling overhead should be reported with mean and standard deviation across multiple runs.
- Deterministic scenarios (jitter_ms: 0) produce identical task streams and simulated-time/deadline metrics on repeated runs; wall-clock scheduler-overhead measurements are excluded from this guarantee.

### Benchmark report conventions

- The public benchmark report (docs/benchmark_results.md) excludes wall-clock scheduler overhead to ensure deterministic reproducibility.
- Scheduler overhead measurements require separate repeated runs to report mean and standard deviation.
- The current benchmark uses synthetic execution profiles; measured hardware profiles will be added in future versions.

## Planned evaluation matrix

- Scenarios: cruise, parking, emergency burst
- Load levels: low, medium, high, overload
- Schedulers: Fixed, FIFO, EDF, DRAS
- Seeds: at least 10 per stochastic configuration
- Metrics: deadline miss rate, mean/P95 response time, throughput, utilization, scheduling overhead

