---
category: research
title: Time-Series Forecasting Benchmark (Master's Research)
org: Ben-Gurion University, M.Sc. Data Science
dates: ongoing
tags: [ml, dl, time-series, forecasting, probabilistic-forecasting, conformal-prediction, foundation-models, pytorch, research, experiment-design, software-engineering, framework, slurm, simulation, networking, profinet, distributed-computing, cli]
priority: 1
---

## One-line summary
Master's research: a modular benchmark framework comparing 30+ time-series forecasting models, plus a packet-scheduling simulator built on probabilistic forecasts.

## Full description
Built a modular forecasting-benchmark framework for industrial-network interarrival times (the gaps between Profinet packets). Part 1 compares 30+ models — naive baselines, statistical models (ARIMA/ETS/TBATS), deep-learning models, and time-series foundation models (Chronos, Moirai) — on point forecasts across a stress grid, with a model registry, a CLI experiment runner, and parallel SLURM array jobs on the cluster. Part 2 turns distributional (quantile) forecasts into a packet-scheduling decision: a three-stage pipeline (evaluate → rank by CRPS → simulate) that slots low-priority packets between high-priority ones on a shared link, using conformal prediction (including adaptive conformal inference) to get calibrated quantiles from any model. Built the data generator, evaluator, discrete-event link simulator, and experiment-tracking utilities.

## Variations

**Short**
Modular framework benchmarking 30+ time-series forecasting models (incl. foundation models) with SLURM parallel sweeps, plus a quantile-forecast packet-scheduling simulator.

**Medium**
Built a modular time-series forecasting benchmark comparing 30+ models — statistical, deep-learning, and foundation models (Chronos/Moirai) — with a model registry, CLI runner, and parallel SLURM jobs. Extended it with conformal-prediction quantile forecasts that drive a discrete-event packet-scheduling simulator on a shared industrial link.

**Long**
Master's research building a modular benchmark framework for forecasting industrial-network interarrival times. Part 1 compares 30+ models (naive, ARIMA/ETS/TBATS, deep learning, and foundation models like Chronos and Moirai) on point forecasts across a stress grid, orchestrated by a model registry, a configurable CLI experiment runner, and parallel SLURM array jobs. Part 2 uses probabilistic (quantile) forecasts — obtained via native, sample-based, or conformal-prediction methods including adaptive conformal inference — in a three-stage pipeline (evaluate by CRPS → rank → simulate) whose discrete-event simulator schedules low-priority packets between high-priority ones to approach time-sensitive-networking safety on commodity hardware. Engineered the data generator, evaluator, simulator, scheduler, and experiment-tracking utilities as reusable components.

## Technologies
Python, PyTorch, statistical forecasting (ARIMA/ETS/TBATS), foundation models (Chronos, Moirai), conformal prediction, SLURM, pandas, numpy, matplotlib

## Outcomes
- Reusable, modular benchmark framework (model registry + CLI + parallel SLURM sweeps) comparing 30+ models
- Probabilistic-forecasting pipeline driving a discrete-event packet-scheduling simulator
- Engineering at scale: parallel cluster jobs, experiment tracking, clean component separation
