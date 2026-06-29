---
category: research
title: Tweet Device Classification (NLP)
org: Ben-Gurion University
dates: "2025"
tags: [nlp, classification, ml, dl, transformers, distilbert, huggingface, feature-engineering, tfidf, cross-validation, hyperparameter-tuning, python, sklearn]
priority: 2
---

## One-line summary
Classified tweets by source device (Android vs iPhone), comparing five model families from logistic regression to a fine-tuned DistilBERT transformer.

## Full description
Built an NLP pipeline to predict whether a tweet was posted from Android or iPhone. Engineered temporal features, 25+ handcrafted stylometric features, and TF-IDF (1–2 gram) representations, then compared Logistic Regression, SVM, Random Forest, a feed-forward neural network, and a fine-tuned DistilBERT transformer using 5-fold stratified cross-validation with grid-searched hyperparameters. DistilBERT performed best (F1 0.862), with stylometric and temporal features driving the classical models.

## Variations

**Short**
NLP device classifier comparing classical ML and a fine-tuned DistilBERT (best F1 0.862) with stratified CV and grid search.

**Medium**
Built a tweet-source NLP classifier: engineered temporal, stylometric, and TF-IDF features and benchmarked five model families (LogReg, SVM, Random Forest, FFNN, DistilBERT) under 5-fold stratified cross-validation with grid search. DistilBERT won at F1 0.862.

**Long**
Designed an NLP pipeline to predict a tweet's source device. Built a thorough preprocessing chain (normalization, URL/mention stripping, contraction expansion, lemmatization), engineered temporal and 25+ stylometric features alongside TF-IDF (1–2 gram) vectors, and compared Logistic Regression, SVM, Random Forest, a feed-forward neural net, and a fine-tuned DistilBERT under 5-fold stratified cross-validation with grid-searched hyperparameters. DistilBERT achieved the best F1 (0.862); feature-importance analysis showed stylometric and temporal signals dominated the classical models.

## Technologies
Python, scikit-learn, NLTK, Hugging Face DistilBERT, TF-IDF, pandas

## Outcomes
- Best F1 0.862 (fine-tuned DistilBERT) across five model families
- Systematic 5-fold cross-validation and grid search
- Feature-engineering and feature-importance analysis
