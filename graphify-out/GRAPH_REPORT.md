# Graph Report - job_automation  (2026-09-19)

## Corpus Check
- 55 files · ~75,186 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 1, .plugin 1)

## Summary
- 247 nodes · 447 edges · 14 communities (9 shown, 5 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 48 edges (avg confidence: 0.9)
- Token cost: 260,292 input · 0 output

## Community Hubs (Navigation)
- Dashboard Build Pipeline
- CV Documents & Variants
- Test Suite & Fit Tiers
- Research Projects & Techniques
- Pipeline Architecture & Docs
- CV PDF Rendering
- Ingest & Gmail Import
- Relevance Gate Tests
- Schema Migration Tests
- Ingest Tests
- CV Tailoring Core
- Scraping Methods
- AppParties Project
- SQL Course Project

## God Nodes (most connected - your core abstractions)
1. `Amazon SDE-I Tailoring Notes` - 17 edges
2. `Config` - 15 edges
3. `run()` - 15 edges
4. `Base CV (Data Engineer)` - 14 edges
5. `RelevanceGate` - 12 edges
6. `ensure_fields()` - 11 edges
7. `process()` - 11 edges
8. `Migration` - 10 edges
9. `AI/LLM Engineer CV Variant` - 10 edges
10. `Software Engineer ML CV Variant` - 10 edges

## Surprising Connections (you probably didn't know these)
- `compute_fit()` --implements--> `Fit Tier (strong/ok/weak sort order)`  [INFERRED]
  build_html.py → PLAN.md
- `Email Classification Rubric (Offer > Interview > Rejected > Auto_ack, English+Hebrew keywords)` --semantically_similar_to--> `Relevance Gates (title families, seniority, years, dedup, expiry)`  [INFERRED] [semantically similar]
  prompts/gmail_sync.md → PLAN.md
- `is_relevant()` --implements--> `Relevance Gates (title families, seniority, years, dedup, expiry)`  [EXTRACTED]
  build_html.py → PLAN.md
- `Mickael Zeitoun CV PDF Export` --implements--> `Amazon SDE-I Tailored CV`  [INFERRED]
  cv/tailored/Mickael Zeitoun - CV.pdf → cv/tailored/amazon-sde-i.html
- `enrich()` --references--> `Config`  [EXTRACTED]
  ingest.py → build_html.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Experience Bank Content Pool Entries** — cv_experience_bank_education_bsc_data_engineering_bsc_data_engineering, cv_experience_bank_education_msc_data_science_msc_data_science, cv_experience_bank_military_iaf_f16_technician_iaf_f16_technician, cv_experience_bank_research_anomaly_detection_anomaly_detection, cv_experience_bank_research_ao3_lexical_trends_ao3_lexical_trends, cv_experience_bank_research_appparties_web_app_appparties, cv_experience_bank_research_deezer_recsys_deezer_recsys, cv_experience_bank_research_earthquake_ml_earthquake_ml, cv_experience_bank_research_llm_lora_finetuning_llm_lora_finetuning, cv_experience_bank_research_multithreaded_trivia_game_trivia_game, cv_experience_bank_research_network_graph_analysis_network_graph_analysis, cv_experience_bank_research_s7comm_parser_s7comm_parser, cv_experience_bank_research_search_engine_wikipedia_search_engine, cv_experience_bank_research_sql_data_apps_sql_data_apps, cv_experience_bank_research_time_series_masters_time_series_benchmark, cv_experience_bank_research_trump_tweet_classification_tweet_device_classification, cv_experience_bank_research_user_type_llm_simulation_user_type_llm_simulation, cv_experience_bank_skills_machine_learning_machine_learning_skills [EXTRACTED 1.00]
- **Projects Run as SLURM Cluster Jobs** — cv_experience_bank_research_llm_lora_finetuning_llm_lora_finetuning, cv_experience_bank_research_time_series_masters_time_series_benchmark, cv_experience_bank_research_user_type_llm_simulation_user_type_llm_simulation [EXTRACTED 1.00]
- **PyTorch Deep-Learning Projects** — cv_experience_bank_research_anomaly_detection_anomaly_detection, cv_experience_bank_research_deezer_recsys_deezer_recsys, cv_experience_bank_research_llm_lora_finetuning_llm_lora_finetuning, cv_experience_bank_research_time_series_masters_time_series_benchmark [EXTRACTED 1.00]
- **CV Template Family (base, role variants, tailored)** — cv_base_cv, cv_variants_ai_llm_engineer, cv_variants_data_scientist_ml, cv_variants_software_engineer_ml, cv_tailored_amazon_sde_i [INFERRED 0.95]
- **Experience Bank Skills Pool** — cv_experience_bank_skills_programming, cv_experience_bank_skills_software_and_data, cv_experience_bank_skills_tools, cv_experience_bank_skills_machine_learning [INFERRED 0.85]
- **Field-scoped writers of jobs.json (Who writes what)** — templates_dashboard, prompts_gmail_sync, prompts_scrape, skills_cv_tailor_skill, ingest, build_html, jobs [EXTRACTED 1.00]
- **Pipeline data flow: scrapers/Gmail/dashboard/Fit CVs feed jobs.json, build_html.py renders Job_applications.html** — prompts_scrape, prompts_scrape_bigtech, prompts_gmail_sync, prompts_tailor_cvs, jobs, build_html, job_applications [EXTRACTED 1.00]
- **Relevance gating system: config-driven gates shared by ingest and build, tested by test_gates** — config, ingest, build_html, tests_test_gates, plan_relevance_gates [EXTRACTED 1.00]

## Communities (14 total, 5 thin omitted)

### Community 0 - "Dashboard Build Pipeline"
Cohesion: 0.08
Nodes (47): age_days(), _archive(), auto_maintain(), backup(), classify_title(), _clean_list(), compute_fit(), Config (+39 more)

### Community 1 - "CV Documents & Variants"
Cohesion: 0.10
Nodes (40): Base CV (Data Engineer), Ben-Gurion University, Mickael Zeitoun, Base CV PDF Render, B.Sc. Data Engineering Education Entry, M.Sc. Data Science Education Entry, IAF F-16 Technician Military Entry, Anomaly Detection Research Entry (+32 more)

### Community 2 - "Test Suite & Fit Tiers"
Cohesion: 0.08
Nodes (12): json, pathlib, AgencyDetection, DedupKey, FitTier, job(), Maintenance, Purge (+4 more)

### Community 3 - "Research Projects & Techniques"
Cohesion: 0.09
Nodes (27): Ben-Gurion University, B.Sc. Data Engineering (Ben-Gurion University), M.Sc. Data Science (Meitar Excellence Program), IAF F-16 Aeronautics Technician (Sergeant Major), Anomaly Detection in Multi-Sensor Time Series, Autoencoder Reconstruction-Error Anomaly Detection, AO3 Lexical-Richness Trends Before/After Generative AI, Interrupted Time Series Design (+19 more)

### Community 4 - "Pipeline Architecture & Docs"
Cohesion: 0.14
Nodes (24): CLAUDE.md Session Protocol and Task Index, config.json (thresholds and title patterns), Experience Bank (cv/experience_bank/ content pool), Generated Dashboard (Job_applications.html), jobs.json (the single store, schema v2), PLAN.md Architecture Plan (v2), Field Ownership - one writer per field, field-scoped read-modify-write. Rationale: multiple independent writers (scraper, Gmail task, dashboard, CV skill) share one jobs.json without a server or database; giving each field exactly one owner and patching only owned fields prevents writers from clobbering each other., Relevance Gates (title families, seniority, years, dedup, expiry) (+16 more)

### Community 5 - "CV PDF Rendering"
Cohesion: 0.15
Nodes (16): argparse, autofit(), build_html(), main(), Render a tailored CV HTML to a single-page A4 PDF and verify the rendering. WHY…, Largest scale that still fits on one A4 page., render(), save_preview() (+8 more)

### Community 6 - "Ingest & Gmail Import"
Cohesion: 0.20
Nodes (15): dedup_key(), gmail_raw.json (Gmail import scratch output), hashlib, _as_list(), enrich(), main(), make_id(), new_record() (+7 more)

### Community 10 - "CV Tailoring Core"
Cohesion: 0.67
Nodes (3): Base CV Visual Template (base_cv.html), CV Tailoring Process, Experience Bank (CV content pool)

### Community 11 - "Scraping Methods"
Cohesion: 0.67
Nodes (3): Big-Tech Boards (NVIDIA, Google, Apple, Amazon Israel careers pages), LinkedIn Guest API read via navigate+get_page_text. Rationale: the old inject-JS method suffered ~1KB output truncation and content blocks that were properties of javascript_tool's return channel; navigating to the guest endpoints and reading rendered text avoids all of it, though the same rate limits (HTTP 429 ~60 requests) still apply., LinkedIn Scraper (six queries, guest API window from state.json)

## Knowledge Gaps
- **31 isolated node(s):** `Experience Bank (CV content pool)`, `Base CV Visual Template (base_cv.html)`, `B.Sc. Data Engineering (Ben-Gurion University)`, `IAF F-16 Aeronautics Technician (Sergeant Major)`, `Autoencoder Reconstruction-Error Anomaly Detection` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 73 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RelevanceGate` connect `Relevance Gate Tests` to `Test Suite & Fit Tiers`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `Relevance Gates (title families, seniority, years, dedup, expiry)` connect `Pipeline Architecture & Docs` to `Dashboard Build Pipeline`, `Test Suite & Fit Tiers`, `Ingest & Gmail Import`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Migration` connect `Schema Migration Tests` to `Test Suite & Fit Tiers`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `Base CV (Data Engineer)` (e.g. with `Anomaly Detection Research Entry` and `Deezer RecSys Research Entry`) actually correct?**
  _`Base CV (Data Engineer)` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Experience Bank (CV content pool)`, `Base CV Visual Template (base_cv.html)`, `B.Sc. Data Engineering (Ben-Gurion University)` to the rest of the system?**
  _31 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Dashboard Build Pipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.08078431372549019 - nodes in this community are weakly interconnected._
- **Should `CV Documents & Variants` be split into smaller, more focused modules?**
  _Cohesion score 0.09615384615384616 - nodes in this community are weakly interconnected._