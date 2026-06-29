---
category: research
title: Earthquake-Prediction Model Evaluation
org: Ben-Gurion University
dates: "2024"
tags: [ml, time-series, sensor-data, classification, feature-engineering, cross-validation, sklearn, python, pipeline]
priority: 3
---

## One-line summary
ML pipeline evaluating which models best fit earthquake sensor data from the 512 hours preceding events.

## Full description
Built a structured ML pipeline to test how well different models fit earthquake sensor data collected in the 512 hours before an event. Iterated over multiple models with cross-validation to find a natural fit (Naïve Bayes), engineered features to improve the data representation, and benchmarked against a dummy-classifier baseline (final F1 0.41, recall 0.89). Also tried an LSTM for the sequential structure but found it underperformed for this dataset and documented that honestly.

## Variations

**Short**
ML pipeline on earthquake sensor data: model search via cross-validation, feature engineering, baseline comparison (F1 0.41, recall 0.89).

**Medium**
Built an end-to-end ML pipeline on pre-event earthquake sensor data: cross-validated model search (Naïve Bayes best), feature engineering, and a dummy-baseline comparison reaching F1 0.41 / recall 0.89. An LSTM was tried but underperformed.

**Long**
Built a structured ML pipeline to evaluate model compatibility with earthquake sensor data from the 512 hours before an event. Started with minimal transformation to see which models naturally fit (Naïve Bayes), used cross-validation throughout, engineered features to improve representation, and benchmarked against a dummy classifier (F1 0.41, recall 0.89). Recorded that an LSTM, tried for the sequential structure, did not perform as hoped — a documented negative result.

## Technologies
Python, scikit-learn, pandas, cross-validation

## Outcomes
- Reproducible model-selection pipeline with baseline comparison
- F1 0.41 / recall 0.89 against a dummy classifier
- Honest documentation of a negative LSTM result
