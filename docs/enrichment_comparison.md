# Enrichment Approach Comparison

This document compares the **monolithic** and **modular** approaches to AI-powered lexicon enrichment.

## Overview

### Monolithic Approach (Current)

**File**: `scripts/enrichment/enrich_lexicon.py`

Single API call that returns complete enrichment (basic info + POS-specific metadata).

**Pros**:
- Simple: one call per word
- Fast: single API round-trip (~3-5s per word)
- AI sees full context when making decisions

**Cons**:
- Expensive: pays for large prompt (~2500 input tokens) even for simple words
- All-or-nothing: can't selectively re-enrich POS metadata
- Monolithic prompts harder to maintain

### Modular Approach (New)

**File**: `scripts/enrichment/enrich_modular.py`

Two-phase API calls:
1. **Phase 1**: Basic info (lemma, POS, translation, definition, difficulty, tags, examples)
2. **Phase 2**: POS-specific metadata (only for nouns, verbs, adjectives)

**Pros**:
- Cost-efficient: adverbs/prepositions/etc. skip Phase 2 (~40% savings)
- Selective re-enrichment: re-run only Phase 2 for specific POS
- Cleaner prompts: each phase has focused instructions
- Version control: track `word_version` and `pos_version` separately

**Cons**:
- More complex: two API calls + state tracking
- Slower: ~6-10s per word (two sequential calls)
- Potential inconsistency: Phase 1 and Phase 2 might disagree on edge cases

## Cost Analysis

Assuming `gpt-4o-2024-08-06` pricing:
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

### Monolithic Cost (per word)
```
Input:  ~2,500 tokens × $2.50 = $0.00625
Output: ~600 tokens × $10.00 = $0.00600
Total:  $0.01225 per word
```

### Modular Cost

**Phase 1 (all words)**:
```
Input:  ~800 tokens × $2.50 = $0.00200
Output: ~200 tokens × $10.00 = $0.00200
Total:  $0.00400 per word
```

**Phase 2 (nouns)**:
```
Input:  ~500 tokens × $2.50 = $0.00125
Output: ~400 tokens × $10.00 = $0.00400
Total:  $0.00525 per noun
```

**Phase 2 (verbs)**:
```
Input:  ~1,000 tokens × $2.50 = $0.00250
Output: ~600 tokens × $10.00 = $0.00600
Total:  $0.00850 per verb
```

**Phase 2 (adjectives)**:
```
Input:  ~600 tokens × $2.50 = $0.00150
Output: ~400 tokens × $10.00 = $0.00400
Total:  $0.00550 per adjective
```

### Total Cost Comparison

**Vocabulary breakdown** (typical):
- Nouns: 40%
- Verbs: 30%
- Adjectives: 15%
- Other (adverbs, prepositions, etc.): 15%

**Monolithic** (1000 words):
```
1000 words × $0.01225 = $12.25
```

**Modular** (1000 words):
```
Phase 1: 1000 words × $0.00400 = $4.00

Phase 2:
  400 nouns × $0.00525      = $2.10
  300 verbs × $0.00850      = $2.55
  150 adjectives × $0.00550 = $0.83
  150 other (skip Phase 2)  = $0.00

Total: $4.00 + $5.48 = $9.48
```

**Savings**: $12.25 - $9.48 = **$2.77 (22.6% cheaper)**

## Usage Examples

### Monolithic Enrichment

```bash
# Enrich all unenriched words
python -m scripts.enrichment.enrich_and_update --batch-size 10

# Test single word
python -m scripts.enrichment.enrich_lexicon lopen "to walk"
```

### Modular Enrichment

```bash
# Enrich all unenriched words (both phases)
python -m scripts.enrichment.enrich_and_update_modular --batch-size 10

# Run only Phase 1 (basic enrichment)
python -m scripts.enrichment.enrich_and_update_modular --phase 1 --batch-size 10

# Run only Phase 2 (for words that have Phase 1)
python -m scripts.enrichment.enrich_and_update_modular --phase 2

# Test single word
python -m scripts.enrichment.enrich_modular lopen "to walk"
```

### Comparison Tool

```bash
# Compare both approaches side-by-side
python -m scripts.maintenance.compare_enrichment lopen "to walk"
python -m scripts.maintenance.compare_enrichment praten "to talk"
```

## Database Schema

### Monolithic Tracking

```python
enrichment: {
    enriched: true,
    enriched_at: datetime,
    model_used: "gpt-4o-2024-08-06",
    version: 1,
    lemma_normalized: false
}
```

### Modular Tracking

```python
enrichment: {
    # Phase 1
    word_enriched: true,
    word_enriched_at: datetime,
    word_model: "gpt-4o-2024-08-06",
    word_version: 1,

    # Phase 2
    pos_enriched: true,
    pos_enriched_at: datetime,
    pos_model: "gpt-4o-2024-08-06",
    pos_version: 1,

    # Common
    lemma_normalized: false
}
```

## Selective Re-enrichment

### Scenario: Verb preposition examples need improvement

**Monolithic**: Re-enrich ALL verbs (expensive, might change other fields)
```bash
python -m scripts.enrichment.enrich_and_update --pos verb
```

**Modular**: Re-enrich only Phase 2 for verbs (cheaper, preserves Phase 1)
```bash
# First, mark verb Phase 2 as unenriched
python scripts/maintenance/reset_phase2_verbs.py

# Then re-run Phase 2 with improved prompt
python -m scripts.enrichment.enrich_and_update_modular --phase 2
```

## Shared Constants

Both approaches use the same prompts from `scripts/enrichment/constants.py`:

- `UNIVERSAL_INSTRUCTIONS`: POS, translation, definition, difficulty, tags
- `NOUN_INSTRUCTIONS`: Article, plural, diminutive, examples
- `VERB_INSTRUCTIONS`: Conjugation, prepositions, examples
- `ADJECTIVE_INSTRUCTIONS`: Comparison, examples
- `N_EXAMPLES`: Number of examples per form (currently 2)

This ensures fair comparison and easier maintenance.

## Configuration

To change the number of examples, edit `scripts/enrichment/constants.py`:

```python
N_EXAMPLES = 5  # Change from 2 to 5
```

This will affect both monolithic and modular approaches equally.

## Recommendation

**Test both approaches** on a sample of 50-100 words:

1. Run comparison tool on diverse words (nouns, verbs, adjectives)
2. Check consistency of basic info (lemma, POS, translation)
3. Compare POS metadata quality
4. Review actual costs in OpenAI usage logs
5. Consider your priorities:
   - **Cost-conscious**: Use modular
   - **Latency-conscious**: Use monolithic
   - **Quality-focused**: Test both, pick the better one

**Suggested workflow**:

1. Use modular for initial batch enrichment (cheaper)
2. Manually review quality
3. If Phase 2 needs improvement for specific POS, re-run only Phase 2
4. For small batches or testing, either approach is fine
