# Experience Bank

This folder is the full catalog of your university and work experience.
It is the **source of truth** Claude draws from when tailoring your CV.

## How it works

- `base_cv.html` (one level up) defines the **visual template** (fonts, layout, colors, section order).
- This folder defines the **content pool** — every project, role, skill, and achievement, each in its own `.md` file.
- When tailoring for a job, Claude reads the job's requirements, picks the most relevant entries from this bank, and produces a new HTML that reuses the base template's styling with swapped-in content.

The bank can (and should) hold **more** than fits on one page. The tailoring step decides what makes the cut for each specific job.

## File format

Each `.md` file starts with YAML frontmatter and a body:

```
---
category: research | work | education | skills | military | volunteering
title: Short display title (what appears on the CV)
org: Organization or institution
dates: 2024-now   # or "2020" or "2016-2018"
tags: [ml, time-series, pytorch, anomaly-detection, ...]
priority: 1       # 1 = usually include; 3 = include only if highly relevant
---

## One-line summary
Short version for space-constrained tailorings.

## Full description
Longer version with details, metrics, technologies used.

## Variations
- Short (1 sentence, ~20 words)
- Medium (2-3 sentences, ~50 words)
- Long (full paragraph, ~80 words)

## Technologies
Python, PyTorch, pandas, ...

## Outcomes
- What shipped / was delivered
- Metrics if available
```

## Tag conventions

Use lowercase, hyphen-separated tags. Common ones for your field:

- **Domains**: ml, dl, nlp, cv (computer-vision), rl, recsys, time-series, anomaly-detection, forecasting
- **Techniques**: transformers, llm, lstm, autoencoder, rag, fine-tuning, embeddings, foundation-models
- **Languages**: python, sql, java, r
- **Frameworks**: pytorch, tensorflow, huggingface, sklearn
- **Infra**: docker, linux, slurm, cluster, gcp, aws
- **Roles**: research, engineering, data-pipelines, mlops, teaching

When adding a new file, reuse existing tags where possible. Grep for a tag before inventing a new one:
```bash
grep -rh "^tags:" . | sort -u
```

## How to add a new entry

1. Copy the closest existing file in the right subfolder.
2. Edit the frontmatter and body.
3. No manifest file to update — the tailoring step scans frontmatter at runtime.

## What to put where

- `research/` — research projects, papers, theses, course capstones that are substantial
- `work/` — paid or unpaid roles at organizations
- `education/` — degrees (summary) + notable courses/grades/projects that wouldn't fit under research
- `skills/` — skill categories with **evidence** (never a bare list — always "I did X with this")
- `military/` — IDF service details
- `volunteering/` — unpaid community work

## What not to do

- Do not add content you haven't actually done. The tailoring skill will verify against this bank — inventing here defeats the whole safety design.
- Do not store skills as a flat list. Each skill entry should describe how and where you used it.
- Do not duplicate content across files. Each achievement lives in exactly one file.
