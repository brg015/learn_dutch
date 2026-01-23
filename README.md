---
title: Dutch Vocabulary Trainer
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8501
---

# Dutch Vocabulary Trainer

A local-first vocabulary learning tool for Dutch using AI-enriched content and principled reinforcement strategies.

## Quick Start

### 1. Activate Virtual Environment
```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file with:
```
MONGO_URI=your_mongodb_connection_string
OPENAI_API_KEY=your_openai_api_key
```

### 4. Import Words
```bash
# Quick import without AI enrichment
python -m scripts.import_basic_to_mongo --batch-size 50

# Optional: Enrich with AI metadata
python -m scripts.enrich_and_update --batch-size 10
```

### 5. Run the Streamlit App
```powershell
# Option 1: Use the helper script
.\run_app.ps1

# Option 2: Manual command
$env:PYTHONPATH = "."; streamlit run app/streamlit_app.py
```

## Useful Commands

```bash
# Freeze dependencies
pip freeze > requirements.txt

# Sync word list from external source
python -m scripts.sync_word_csv

# Import basic words (no AI)
python -m scripts.import_basic_to_mongo --dry-run --batch-size 5

# Enrich specific words with AI
python -m scripts.enrich_and_update --user-tag "Chapter 10"
```

## Project Structure

See [project_context.md](project_context.md) for detailed architecture and design decisions

