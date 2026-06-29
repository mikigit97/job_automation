---
category: research
title: LLM-Agent User-Behavior Simulation
org: Ben-Gurion University
dates: "2026"
tags: [llm, simulation, recsys, agents, ollama, movielens, classification, pipeline, slurm, python, data-generation, genai]
priority: 3
---

## One-line summary
Simulation framework that uses LLM agents plus real MovieLens data to generate labeled user-behavior data for recommendation-system research.

## Full description
Built a multi-phase simulation framework that models three user behavioral types (herder, truthful, strategic) interacting with a movie recommender, using LLM-based agents (via Ollama) and real MovieLens-32M preferences. Generated 300 labeled users across two screen configurations, orchestrated as a five-phase pipeline driven by config files and environment-variable toggles, with SLURM batch jobs for the heavy phases — producing labeled interaction data for a downstream user-type classifier.

## Variations

**Short**
LLM-agent simulation (Ollama + MovieLens-32M) that generates 300 labeled users across behavioral types for recsys classification.

**Medium**
Built a five-phase simulation framework using LLM agents (Ollama) and MovieLens-32M to generate labeled interaction data for three user types. Config-driven with environment-variable toggles and SLURM jobs for the heavy phases, feeding a downstream classifier.

**Long**
Designed a simulation framework that models herder, truthful, and strategic users choosing movies from a recommender, using LLM agents (Ollama) seeded with real MovieLens-32M preferences. Produced 300 labeled users across two screen configurations (preference movies present vs absent), structured as a five-phase orchestrated pipeline with config files, environment-variable toggles, and SLURM batch jobs for compute-heavy stages, generating training data for user-type classification.

## Technologies
Python, Ollama (local LLMs), MovieLens-32M, SLURM, config-driven orchestration

## Outcomes
- 300-user labeled dataset across four method/config combinations
- Reusable, config-driven simulation-plus-classification pipeline
