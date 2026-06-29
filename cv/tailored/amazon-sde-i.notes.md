# CV tailored — Amazon SDE-I (Software Development Engineer I)

Tailored 2026-06-29. Output: `cv/tailored/amazon-sde-i.html`

(Logged here next to the output because this project stores postings in `jobs.json`,
not in the deprecated `positions/<id>/` folder referenced by the skill template.)

## Matched must-have qualifications
- **General-purpose programming language** (Java / Python / C++ / C# / Go / Rust / TypeScript)
  → Python, Java, C# surfaced in Programming skills + projects.
- **Data structure usage / basic algorithm development / OOD**
  → Wikipedia search engine (inverted index, BM25, PageRank); multithreaded client–server
    game (object-oriented design); Education (Data Structures 97, Computational Models 99).
- **Degree** (enrolled in or graduated within 24 months, CS/CE/Data Science/Info Systems)
  → M.Sc. Data Science (current) + B.Sc. Data Engineering (completed).

## Preferred qualifications hit
- Databases (SQL) → SQL/Streamlit data apps with index design + measured 50–80× speedup.
- Version control → Git across all projects.
- Debugging / troubleshooting complex systems → Samsung support; (bank also has S7comm parser).
- Distributed / scalable systems → concurrent client–server game; forecasting framework on a cluster.
- GenAI / AI productivity → LLMs & LoRA fine-tuning listed in ML skills (bank: LoRA, LLM projects).
- Communication / customer focus → Samsung technical support; Professional Summary framing.

## Bank entries included
- research/multithreaded-trivia-game.md
- research/search-engine.md
- research/sql-data-apps.md
- research/time-series-masters.md   (forecasting benchmark framework)
- work/cyberbgu.md
- work/samsung.md
- skills/programming.md, skills/software-and-data.md, skills/machine-learning.md, skills/tools.md
- education/{msc-data-science,bsc-data-engineering}.md, military/iaf-f16-technician.md, volunteering/volunteering.md

## Deliberately left out (kept on one page / lower relevance for a backend SDE role)
- work/math-tutor.md (dropped to make room for a 4th project)
- research: deezer-recsys, anomaly-detection, network-graph-analysis, llm-lora-finetuning,
  trump-tweet-classification, user-type-llm-simulation, ao3-lexical-trends, earthquake-ml,
  s7comm-parser, appparties-web-app  (all available in the bank for other postings)

## Keyword rewrites applied (bank wording → posting wording)
- "time-series forecasting research" → "modular framework … across a distributed compute cluster"
  (surfaces the posting's "scalable solutions / large distributed computing").
- "recommendation/sequence models" not used; led instead with concurrency, algorithms, and databases.
- Header subtitle: "Data Engineer | …" → "Software Engineer | Data Science M.Sc. Student".

## Self-audit
- Every concrete claim maps to a bank entry (verified by grep + manual review).
- HTML valid; `print-container`, `<html>`, `<body>`, and the `window.print()` button preserved.
- No placeholder text. Section headings unchanged from the base template.
- One-page fit: content volume is close to the base (traded one work entry for one project).
  If it spills past one A4 page in Chrome's print preview, drop the **Volunteering** line first,
  then shorten the longest project description.
