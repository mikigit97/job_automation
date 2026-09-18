---
type: "query"
date: "2026-09-18T21:20:13.488729+00:00"
question: "Why does Relevance Gates connect Pipeline Architecture & Docs to Dashboard Build Pipeline, Test Suite & Fit Tiers, and Ingest & Gmail Import?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["Relevance Gates (title families, seniority, years, dedup, expiry)", "is_relevant()", "ingest.py", "test_gates.py", "config.json (thresholds and title patterns)", "Title Pre-filter before detail fetch"]
---

# Q: Why does Relevance Gates connect Pipeline Architecture & Docs to Dashboard Build Pipeline, Test Suite & Fit Tiers, and Ingest & Gmail Import?

## Answer

Expanded from original query via vocab: [relevance, gates, gate, relevant, title, seniority, years, dedup, expiry]. BFS depth 2 from the Relevance Gates concept node (PLAN.md). The gates are the single keep-or-drop decision rule defined once in PLAN.md and touched by every stage: config.json supplies thresholds and title patterns (shares_data_with), is_relevant() in build_html.py implements them (implements, EXTRACTED), ingest.py applies them at import time (implements, EXTRACTED), test_gates.py's RelevanceGate class pins their behaviour with 11 unit tests (references, EXTRACTED), the scraper prompt's Title Pre-filter applies gates 2a-2d to card titles before detail fetches, and the Gmail Email Classification Rubric is a semantically similar triage filter (INFERRED 0.75). The node bridges four communities because one shared rule has one definition, one config source, two implementation sites, one test suite, and one upstream pre-filter.

## Outcome

- Signal: useful

## Source Nodes

- Relevance Gates (title families, seniority, years, dedup, expiry)
- is_relevant()
- ingest.py
- test_gates.py
- config.json (thresholds and title patterns)
- Title Pre-filter before detail fetch