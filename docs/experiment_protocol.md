# Experiment protocol

## Reproducibility rules

- Store every scenario in YAML.
- Record a random seed in every scenario.
- Do not manually edit generated result CSV files.
- Run all schedulers on the same generated task stream.
- Report mean and standard deviation when random jitter is enabled.
- Clearly label synthetic device profiles and measured device profiles.

## Planned evaluation matrix

- Scenarios: cruise, parking, emergency burst
- Load levels: low, medium, high, overload
- Schedulers: Fixed, FIFO, EDF, DRAS
- Seeds: at least 10 per stochastic configuration
- Metrics: deadline miss rate, mean/P95 response time, throughput, utilization, scheduling overhead

