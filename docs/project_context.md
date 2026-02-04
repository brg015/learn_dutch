# Dutch Vocabulary Trainer — Project Overview

## Goal

Build a local-first vocabulary learning tool to test and improve Dutch vocabulary using principled reinforcement strategies.
The initial version will be a **Streamlit app** for self-study, with the ability to scale later (more users, smarter scheduling, mobile UI).

AI is **not part of the learning loop**; it is only used offline to help **build and enrich the lexicon**.


## Learning Algorithm

This application uses a **forgetting-curve–based spaced repetition algorithm**, inspired by the FSRS (Free Spaced Repetition Scheduler) family of models.

The goal is to maximize **long-term retention (months to years)** while:
- the set of items grows continuously,
- study time remains limited,
- and different types of language knowledge are practiced.

The system replaces fixed review intervals or random sampling with **adaptive scheduling based on predicted forgetting**.

### Core principle

Items are reviewed when they are **close to being forgotten**, not according to fixed time schedules.

For each item, the algorithm estimates the probability that the user could still recall it *right now*.  
When this probability drops below a configurable threshold, the item becomes due for review.

This balances efficiency (fewer unnecessary reviews) with robustness (avoiding full forgetting).

### Unit of learning

The basic unit scheduled by the algorithm is a **card**, defined as:

> **(exercise type × prompt × expected answer)**

Examples:
- `(meaning, "verrekijker", "binoculars")`
- `(article, "verrekijker", "de")`
- `(perfectum, "lopen", "gelopen")`
- `(prepositions, "wachten", "op")`

Each card is tracked **independently**, even if multiple cards reference the same word.

This allows different types of knowledge (semantics, grammar, production) to have **separate learning trajectories and forgetting behavior**.

### Memory state per card

Each card maintains a small internal memory state:

- **Stability (S)**  
  Represents how slowly the card is forgotten. Higher stability leads to longer intervals between reviews.

- **Difficulty (D)**  
  Represents how hard this card is for the user. More difficult cards gain stability more slowly.

- **Last review time**  
  Timestamp of the most recent review attempt.

From these values, the algorithm computes:

- **Retrievability (R)**  
  The estimated probability that the user could recall the card at the current time.


### Forgetting model (conceptual)

Retrievability decreases smoothly over time according to a forgetting curve:

- Immediately after a successful recall, retrievability is high
- As time passes, retrievability decays
- Cards with higher stability decay more slowly

The model parameters are **not fixed**:
- Successful recall increases stability
- Forgotten items reduce stability
- Difficulty moderates how quickly stability changes

This allows the algorithm to adapt continuously to the learner.

### Feedback and learning updates

After each review, the card’s memory state is updated based on user feedback.

Minimum supported feedback:
- **Remembered**
- **Forgotten**

Optional (recommended) extensions:
- Graded feedback (e.g. Again / Hard / Good / Easy)
- Response time (RT), stored for potential future use

Effects:
- Successful recall → stability increases
- Forgotten recall → stability decreases
- Difficulty is updated based on consistency and ease of recall

Importantly:
- A failure does **not** reset learning from scratch
- Previously accumulated learning still contributes to future scheduling

### Scheduling rule

A card becomes **due** when its predicted retrievability falls below a target threshold  
(e.g. 70%).

At each study session:

1. Compute retrievability for all cards with review history
2. Select cards with retrievability ≤ target threshold
3. Rank due cards from lowest to highest retrievability  
   (most at risk of forgetting first)
4. Present cards in that order

This replaces random presentation with **risk-based prioritization**.

### New cards (no review history)

Cards that have never been reviewed:
- Do not yet have reliable stability estimates
- Are treated as high priority but are **rate-limited**
  (e.g. a maximum number of new cards per day or session)

New cards start with conservative default parameters and adapt quickly after a few reviews.

### Multiple exercise types

Different exercise types are expected to have different difficulty and forgetting dynamics
(e.g. recognizing a word vs producing a grammatical form).

Therefore:
- Each exercise type maintains its **own memory state**
- Learning progress does not automatically transfer across exercise types
- The algorithm can adapt separately to each form of knowledge

### Design goals

This learning algorithm is designed to:

- Support retention over long time horizons (months to years)
- Scale from small to large vocabularies
- Handle continuous introduction of new material
- Avoid arbitrary fixed schedules
- Adapt to individual learner behavior


## High-Level Architecture

The system is split into two clear concerns:

1. **Lexicon (content)** — mostly static, flexible, hierarchical
2. **Review logs (events)** — append-only, time-series style data

This leads to **two databases**, each used for what it is best at.

---

## Databases

### 1. Lexicon Database — MongoDB

**Purpose:** Store Dutch words and all associated linguistic metadata.

* One document per **lemma + part of speech**
* Flexible document structure (fields depend on word type)
* Enriched offline via AI batch jobs
* Treated as the *ground truth* for content

**Key fields (always present):**

* `lemma` (dictionary form, e.g. *lopen*)
* `pos` (noun / verb / adj / etc.)
* `translations` (English)
* `difficulty` (e.g. CEFR A2)
* `tags` (e.g. travel, finance)

**Optional POS-specific sections:**

* Nouns: `article`, `plural`
* Verbs: `past`, `perfectum`, `auxiliary`, `separable`
* Examples: bilingual example sentences (future)

**AI metadata:**

* enrichment status, model used, version, timestamp
* no approval flow in MVP (everything unapproved by default)

MongoDB is chosen because lexicon entries are naturally hierarchical and heterogeneous.

---

### 2. Review / Log Database — SQLite

**Purpose:** Track learning history and support scheduling.

* Local SQLite file
* Append-only event log
* Easy analytics and scheduling later

**Each review event stores:**

* timestamp
* lemma
* pos
* result (correct / incorrect)
* translation (e.g. `nl_to_en`)
* prompt_type (e.g. `word`, `sentence`)
* optional latency

No persistent “cards” exist; prompts are generated dynamically from the lexicon.

---

## Learning Flow (MVP)

* Exercise: **Dutch → English**
* Display shows:

  * lemma
  * article / verb forms where applicable
* User reveals answer
* User clicks:

  * ✅ “I knew this”
  * ❌ “I didn’t”
* Result is logged
* Next word is selected **randomly** (scheduler is modular)

No grading, no typing, no AI in the learning loop.

---

## AI Usage (Offline Only)

AI is used in **manual, batch scripts** to:

* validate Dutch–English word pairs
* enrich lexicon entries with metadata
* generate example sentences

AI never runs during review sessions.

---

## Project Structure (MVP)

```
dutch-trainer/
  app/
    streamlit_app.py          # UI only
  core/
    schemas.py                # Pydantic models
    lexicon_repo.py           # MongoDB access
    log_repo.py               # SQLite access
    scheduler.py              # random for MVP
  scripts/
    sync_word_csv.py          # Sync word_list.csv with new words
    enrich_lexicon.py         # AI enrichment function (used by other scripts)
    import_basic_to_mongo.py  # Quick import without AI enrichment
    enrich_and_update.py      # Enrich existing MongoDB entries with AI
  data/
    word_list.csv             # Master word list with user_tags
  logs/
    reviews.sqlite            # local, not committed
  requirements.txt
  .gitignore
  README.md
```

**Design rule:**
Streamlit never talks directly to databases — it calls `core/`.

---

## Workflow: Adding Words to the Lexicon

**Step 1: Maintain word_list.csv**

Add new words to `data/word_list.csv`:
```csv
dutch,english,added_to_lexicon,user_tags
huis,house,FALSE,"Chapter 10"
lopen,to walk,FALSE,"Chapter 5,verbs"
```

Or sync from an external source:
```bash
python -m scripts.sync_word_csv
```

**Step 2: Quick Import to MongoDB**

Import basic word pairs (no AI enrichment yet):
```bash
# Dry run first to test
python -m scripts.import_basic_to_mongo --dry-run --batch-size 5

# Actually import
python -m scripts.import_basic_to_mongo --batch-size 50
```

This will:
- Import Dutch-English pairs to MongoDB
- Parse user_tags from CSV
- Mark words as `added_to_lexicon=TRUE` in CSV
- **No AI calls** = fast and free!

**Step 3: Enrich with AI (Optional)**

Enrich specific words with AI metadata:
```bash
# Enrich words from Chapter 10
python -m scripts.enrich_and_update --user-tag "Chapter 10" --dry-run

# Enrich all unenriched words (first 10)
python -m scripts.enrich_and_update --batch-size 10
```

This will:
- Add POS, conjugations, articles, examples
- Normalize lemma if needed (e.g., "liep" → "lopen")
- Preserve original import_data for reference

**Step 4: Review in Streamlit**

Use the app to review and study the words.

---

## Deployment & Scope (MVP)

* Single user
* Local execution
* Streamlit UI
* MongoDB (Atlas free tier or local)
* SQLite local file
* No authentication
* No mobile support yet

---

## Future-Proofing (Explicitly Out of Scope for MVP)

* Advanced scheduling (SM-2 / adaptive)
* Typing or graded answers
* Multiple exercise modes
* Multi-user support
* Mobile app
* Approval workflow for AI-generated content

---

## Design Principles

* Local-first
* Simple now, extensible later
* Clear separation of content vs learning history
* AI assists content creation, not learning
* Manual inspection and control always possible

---

If you want next:

* a `README.md` for GitHub
* the initial Mongo document schema
* the SQLite schema
* or the first Streamlit page scaffold

Just say which one.
