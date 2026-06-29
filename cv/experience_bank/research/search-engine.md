---
category: research
title: Wikipedia Search Engine (Information Retrieval)
org: Ben-Gurion University (Information Retrieval course)
dates: "2024"
tags: [algorithms, data-structures, information-retrieval, search, inverted-index, bm25, pagerank, ranking, python, optimization, big-data, performance]
priority: 1
---

## One-line summary
Built a search engine over a full Wikipedia dump using an inverted index, BM25 ranking, and PageRank, with query-time precomputation for speed.

## Full description
Built an end-to-end search engine over a full Wikipedia dump. Parsed and preprocessed the corpus (stopword removal, Porter stemming) into an inverted index with posting lists, ranked results with BM25 — precomputing per-posting BM25 contributions to cut query-time cost — and combined them with PageRank scores derived from the corpus's anchor-text link structure. Evaluated with a blended Precision@5 / F1@30 metric and analyzed speed/quality trade-offs (a title-only index returned in ~0.6 s while adding the body index reached higher quality at ~6.5 s).

## Variations

**Short**
Wikipedia search engine in Python using an inverted index, BM25, and PageRank, with precomputed scores for fast query-time retrieval.

**Medium**
Built a Python search engine over a full Wikipedia dump: inverted index with posting lists, BM25 ranking (precomputed per-posting to speed up queries), and PageRank from the link structure. Tuned a blended P@5 / F1@30 metric and measured the latency-versus-quality trade-off between title-only and full-body indexes.

**Long**
Built an end-to-end search engine over a full Wikipedia dump. Constructed an inverted index with posting lists after stopword removal and Porter stemming, ranked documents with BM25 (precomputing per-posting contributions so query-time work is minimal), and blended in PageRank scores derived from anchor-text link structure. Evaluated with a combined Precision@5 / F1@30 metric and analyzed concrete speed/quality trade-offs (title-only ≈0.6 s vs adding the body index ≈6.5 s), choosing the configuration that balanced latency and relevance.

## Technologies
Python, inverted index, BM25, PageRank, Porter stemmer, pandas, numpy

## Outcomes
- Ranked retrieval over a Wikipedia-scale corpus
- Query-time optimization via precomputed BM25 contributions
- Measured, documented latency/relevance trade-offs (data-structure and algorithm design)
