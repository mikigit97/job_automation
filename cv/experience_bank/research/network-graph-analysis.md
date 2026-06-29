---
category: research
title: Large-Scale Network & Graph Analysis
org: Ben-Gurion University (Network Analysis course)
dates: "2026"
tags: [graph, networks, network-analysis, node2vec, embeddings, link-prediction, pagerank, centrality, big-data, polars, streaming, out-of-core, python, llm, ollama]
priority: 2
---

## One-line summary
Graph analysis over real networks — centralities, node2vec embeddings, directed link prediction, and out-of-core processing of a 429M-edge graph.

## Full description
Analyzed several real-world networks (movie co-appearance graphs, Reddit hyperlinks, Enron email, and a 429M-edge chess interaction network). Computed degree distributions, centralities, PageRank, and graph-level embeddings; trained node2vec embeddings for directed link prediction; and detected Enron managers by combining centrality measures with a locally hosted LLM (Ollama running qwen2.5:14b) queried over HTTP. Handled out-of-memory scale by stream-aggregating the 6.85 GB / 429M-edge chess file with polars into a compact weighted edge list instead of loading it whole.

## Variations

**Short**
Graph analysis (centralities, node2vec, link prediction) over real networks, including stream-aggregating a 429M-edge graph that won't fit in memory.

**Medium**
Analyzed real networks with networkx/igraph: centralities, PageRank, node2vec embeddings, and directed link prediction on Reddit hyperlinks. Combined centrality with a local LLM (Ollama) to detect Enron managers, and processed a 429M-edge chess graph out-of-core via polars stream-aggregation.

**Long**
Studied multiple real-world networks (movies, Reddit hyperlinks, Enron email, a 429M-edge chess graph). Computed degree distributions, centralities, PageRank, and graph-level embeddings, trained node2vec embeddings for directed link prediction, and detected Enron managers by fusing centrality metrics with a locally hosted LLM (Ollama, qwen2.5:14b) over HTTP. To handle a 6.85 GB graph too big for memory, stream-aggregated it with polars into a compact weighted edge list and ran analysis on a justified subgraph.

## Technologies
Python, networkx, python-igraph, node2vec, gensim, scikit-learn, polars, umap-learn, Ollama (local LLM over HTTP)

## Outcomes
- Directed and temporal link-prediction models
- Graph embeddings with a 2-D map of 15k+ networks
- Out-of-core handling of a 429M-edge dataset (big-data engineering)
