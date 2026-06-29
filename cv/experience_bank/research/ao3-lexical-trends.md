---
category: research
title: Lexical-Richness Trends Before/After Generative AI (AO3)
org: Ben-Gurion University (Data Mining final project)
dates: "2026"
tags: [data-mining, nlp, time-series, interrupted-time-series, web-scraping, testing, reproducibility, python, statistics, etl, data-engineering]
priority: 3
---

## One-line summary
Interrupted-time-series study of vocabulary richness (MTLD/MATTR) and upload rates on AO3 fanfiction around the public launch of generative-AI writing tools.

## Full description
Measured whether the vocabulary richness and chapter-upload rate of human fanfiction changed after generative-AI writing tools became public, framed as an interrupted-time-series (looking for a jump at a known event date). Built a polite, resumable web scraper (5-second rate limiting, an honest self-identifying User-Agent, automatic backoff, and local caching) with separate cheap-metadata and expensive-full-text streams and a stratified random sample. Computed length-robust lexical-diversity metrics (MTLD, MATTR, HD-D), wrote unit tests for the metric math, and ran the analysis with sensitivity checks for confounding factors. Organized as a modular `src/` package with config-driven parameters and a tests suite.

## Variations

**Short**
Interrupted-time-series data-mining study on AO3 with a polite, resumable, unit-tested scraper and length-robust lexical-diversity metrics.

**Medium**
Built a resumable, rate-limited web-scraping and analysis pipeline to test whether fanfiction vocabulary richness and upload rates shifted after generative AI arrived. Used length-robust metrics (MTLD/MATTR), unit-tested the metric math, and ran an interrupted-time-series with sensitivity checks.

**Long**
Designed a reproducible data-mining study asking whether human fanfiction's vocabulary richness and upload cadence changed when generative-AI writing tools went public, modeled as an interrupted time series. Engineered a polite, resumable scraper (5-second pauses, honest User-Agent, backoff, local caching) with separate metadata and full-text streams and stratified sampling, computed length-robust lexical-diversity measures (MTLD, MATTR, HD-D), unit-tested the math, and analyzed the series with confound sensitivity checks — all in a modular, config-driven `src/` package.

## Technologies
Python, lexicalrichness, requests with caching/backoff, unit tests, pandas, statistics

## Outcomes
- Reproducible, resumable scraping-and-analysis pipeline (never re-downloads a page)
- Unit-tested diversity metrics and interrupted-time-series with sensitivity analysis
- Clean software practices: modular package, config files, tests, ethics/politeness controls
