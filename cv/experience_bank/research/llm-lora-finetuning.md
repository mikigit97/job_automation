---
category: research
title: LLM Fine-Tuning with LoRA (Sherlock Holmes corpus)
org: Ben-Gurion University (course assignment)
dates: "2026"
tags: [llm, nlp, dl, lora, peft, fine-tuning, transformers, huggingface, pytorch, foundation-models, gpu, slurm, perplexity, genai, ablation]
priority: 2
---

## One-line summary
LoRA continued pre-training plus supervised fine-tuning of a small LLM (Qwen2.5-0.5B) on the Sherlock Holmes canon, evaluated by perplexity and F1.

## Full description
Adapted a small pre-trained causal language model (Qwen2.5-0.5B) to the Sherlock Holmes canon using LoRA — a parameter-efficient fine-tuning method that trains small adapter matrices instead of all the model's weights. Part 1 ran LoRA continued pre-training and showed in-domain perplexity dropped (18.05 → 16.54). Part 2 added supervised fine-tuning on question→answer pairs, lifting exact-match F1/accuracy from 0.011 to 0.291 on a held-out entity-answer test set. Ran 10+ ablation experiments and GPU training jobs on the BGU SLURM cluster (RTX 3090/4090), with each stage documented in plain English.

## Variations

**Short**
LoRA continued pre-training + supervised fine-tuning of Qwen2.5-0.5B; perplexity 18.05→16.54 and F1 0.011→0.291.

**Medium**
Used LoRA (parameter-efficient fine-tuning) to adapt Qwen2.5-0.5B to a literary corpus: continued pre-training cut perplexity 18.05→16.54, and supervised fine-tuning raised QA F1 from 0.011 to 0.291. Ran 10+ ablations as GPU jobs on a SLURM cluster.

**Long**
Adapted a small causal language model (Qwen2.5-0.5B) to the Sherlock Holmes canon with LoRA, a parameter-efficient method that trains small adapter matrices rather than full weights. Continued pre-training lowered in-domain perplexity (18.05→16.54); a second supervised-fine-tuning stage on question→answer pairs raised exact-match F1/accuracy from 0.011 to 0.291 on a held-out test set. Built the data with salient-entity targeting and paraphrase augmentation, ran 10+ ablation experiments as GPU SLURM jobs, and documented every stage.

## Technologies
Python, PyTorch, Hugging Face transformers, LoRA / PEFT, SLURM, GPU (RTX 3090/4090)

## Outcomes
- Perplexity 18.05 → 16.54 from LoRA continued pre-training
- Supervised-fine-tuning F1/accuracy 0.011 → 0.291
- 10+ documented ablation runs; staged, reproducible delivery
