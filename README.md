---
title: Dutch Vocab Trainer
emoji: 📚
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.32.0"
python_version: "3.11"
app_file: app/streamlit_app.py
pinned: false
---

# Dutch Vocabulary Trainer

A vocabulary learning application for Dutch that combines **AI-powered lexicon enrichment** with **cognitive psychology-based spaced repetition** (FSRS) to maximize long-term retention.

## Overview

This app helps you build and maintain Dutch vocabulary through:

- **AI-enriched lexicon**: Automatically adds grammatical metadata, example sentences, and linguistic context using GPT-4o
- **FSRS-based scheduling**: Adaptive spaced repetition that reviews words when you're about to forget them, not on fixed schedules
- **Google Sheets integration**: Maintain your word list in a spreadsheet and sync bidirectionally
- **Flexible deployment**: Run locally via Streamlit or deploy to Hugging Face Spaces

**Important**: AI is used *offline* to build and enrich the lexicon. The learning algorithm itself is **deterministic** (not AI-based) and grounded in cognitive science principles (forgetting curves, retrievability, adaptive difficulty). While the algorithm has tunable parameters that can be optimized, it uses mathematical formulas rather than machine learning during review sessions.

## How It Works

### 1. Word List Management
Words are maintained in **Google Sheets** with columns for Dutch word, English translation, and custom tags. The app syncs bidirectionally, writing metadata (word IDs, enrichment status) back to the sheet.

```bash
# Import words from Google Sheets
python -m scripts.data.import_from_gsheet --batch-size 20
```

### 2. AI Enrichment (Optional)
After importing, words can be enriched with linguistic metadata:
- Part of speech detection
- Grammatical forms (conjugations for verbs, articles/plurals for nouns)
- CEFR difficulty level
- Bilingual example sentences
- Semantic tags

```bash
# Enrich imported words with AI metadata
python -m scripts.enrichment.enrich_and_update --batch-size 10

# Or test single words
python -m scripts.maintenance.test_single_word lopen "to walk"
```

### 3. Spaced Repetition Learning
The app uses **FSRS** (Free Spaced Repetition Scheduler), a forgetting-curve model that:
- Tracks each word's *stability* (how slowly you forget it) and *difficulty*
- Computes real-time *retrievability* (probability you can recall it now)
- Schedules reviews when retrievability drops below a threshold
- Adapts continuously based on your feedback (remembered vs. forgotten)

Each word has independent learning trajectories for different exercise types (meaning, grammar, production).

### 4. Study & Review
Run the app locally or access it on Hugging Face Spaces:

```bash
# Local Streamlit app
run app/streamlit_app.py
```

The app is also deployed on **Hugging Face Spaces** for cloud access.

## Project Architecture

The system separates **content** (lexicon) from **learning history**:
- **MongoDB**: Stores enriched word entries (flexible schema, AI metadata)
- **SQLite**: Stores review logs (append-only event log for scheduling)

See [project_context.md](project_context.md) for detailed architecture, FSRS algorithm explanation, and design decisions.

## Key Features

- **AI-assisted, not AI-driven**: Language models enrich content; cognitive science drives learning
- **Modular enrichment**: Two-phase AI enrichment (basic info + POS-specific metadata) for cost efficiency
- **Tag-based filtering**: Organize vocabulary by topic, textbook chapter, difficulty, etc.
- **Transparent scheduling**: See exactly why each word is due for review

