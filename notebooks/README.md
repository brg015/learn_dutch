# Notebooks

Interactive Jupyter notebooks for exploratory analysis and testing.

## Available Notebooks

### analytics.ipynb
**Purpose**: Visualize and analyze FSRS review data

**What it does**:
- Connects to `learning.db` (FSRS SQLite database)
- Generates visualizations for:
  - Stability and difficulty distributions
  - Retrievability heatmaps
  - Review history over time
  - Feedback grade patterns
  - Problem word identification
  - Learning curves
  - Response time analysis
  - Forgetting curves
- Exports a text summary report

**When to use**: After studying cards to review your learning progress and identify problem areas.

**Dependencies**: pandas, matplotlib, seaborn

---

### build_lexicon.ipynb
**Purpose**: Interactive lexicon management and enrichment testing

**What it does**:
- Connects to MongoDB lexicon database
- Shows current lexicon stats (total, enriched, unenriched)
- Displays sample words needing enrichment
- Allows inspection of enriched word metadata
- Provides a sandbox for testing enrichment workflows

**When to use**:
- To inspect the current state of your lexicon
- To verify enrichment results
- To explore MongoDB data interactively

**Note**: For production imports/enrichment, use the command-line scripts:
- `python -m scripts.data.import_from_gsheet`
- `python -m scripts.enrichment.enrich_and_update`

---

### review_logs.ipynb
**Purpose**: Reserved for future review log analysis

**Status**: Empty placeholder

---

## Setup

Install notebook dependencies:

```bash
pip install jupyter notebook pandas matplotlib seaborn
```

Run Jupyter:

```bash
jupyter notebook
```

Then navigate to the `notebooks/` directory and open any `.ipynb` file.

## File Organization

```
notebooks/
├── README.md              # This file
├── analytics.ipynb        # FSRS review analytics
├── build_lexicon.ipynb    # Lexicon exploration
└── review_logs.ipynb      # Placeholder
```

Notebooks are for **exploration and analysis only**. For production workflows, use the scripts in `scripts/`.
