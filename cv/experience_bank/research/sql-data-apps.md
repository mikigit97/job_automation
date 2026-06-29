---
category: research
title: SQL Data Applications (Big Data course)
org: Ben-Gurion University (Data Mining in Large Databases)
dates: "2026"
tags: [sql, sqlite, databases, data-engineering, orm, ponyorm, streamlit, web-app, indexing, query-optimization, python, etl, api-integration, deployment]
priority: 1
---

## One-line summary
Four deployed interactive data apps (SQL/SQLite + PonyORM + Streamlit), including schema and index design with a measured 50–80× query speedup.

## Full description
Built four interactive data applications backed by SQLite and deployed live on Streamlit Cloud. Designed relational schemas and indexes for a ~1.8M-row baby-names dataset, loaded it in 50k-row chunks to keep memory flat, and used SQLite's `EXPLAIN QUERY PLAN` plus a timed benchmark to confirm a covering index delivered a 50–80× query speedup (150–200 ms down to 2–5 ms). A second app used the PonyORM object-relational mapper over a normalized multi-entity schema and merged database queries with a live Wikipedia API. Others included a safety-checked free-text SQL query panel (SELECT-only validation) and a database-backed game.

## Variations

**Short**
Built and deployed four SQL/Streamlit data apps with schema and index design, measuring a 50–80× covering-index query speedup.

**Medium**
Built four interactive data applications on SQLite, deployed on Streamlit Cloud. Designed schemas and indexes for a 1.8M-row dataset, verified a 50–80× speedup with `EXPLAIN QUERY PLAN`, used the PonyORM ORM over a normalized schema, and integrated a live Wikipedia API.

**Long**
Built four interactive data applications backed by SQLite and deployed on Streamlit Cloud. Designed relational schemas and indexes for a ~1.8M-row dataset, chunk-loaded the data to keep memory flat, and used `EXPLAIN QUERY PLAN` and a timed benchmark to prove a covering index gave a 50–80× speedup. A second app modeled a normalized multi-entity schema with the PonyORM object-relational mapper and combined SQL queries with a live Wikipedia API; another exposed a safety-checked free-text SQL panel. Demonstrates database design, query optimization, ORMs, and shipping deployed web services.

## Technologies
Python, SQL, SQLite, PonyORM (ORM), Streamlit, pandas, REST / Wikipedia API

## Outcomes
- Four live, deployed data applications
- 50–80× indexed-query speedup proven with `EXPLAIN QUERY PLAN`
- Schema design, covering indexes, chunked bulk loading, and ORM modeling
