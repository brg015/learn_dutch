# Reflexive Verb Handling

This document explains how reflexive verbs (e.g., "zich schamen", "zich vergissen") are handled in the Dutch vocabulary trainer.

## What are Reflexive Verbs?

Reflexive verbs require a reflexive pronoun that refers back to the subject:
- **zich schamen** (to be ashamed)
- **zich vergissen** (to be mistaken)
- **zich herinneren** (to remember)

The reflexive pronoun changes based on the subject:
- ik schaam **me**
- jij schaamt **je**
- hij/zij schaamt **zich**
- wij schamen **ons**
- jullie schamen **je**
- zij schamen **zich**

## Import Handling

### Google Sheets Import

When importing from Google Sheets, reflexive verbs can be entered with "zich":

| dutch | english | user_tags | word_id | enriched |
|-------|---------|-----------|---------|----------|
| zich schamen | to be ashamed | emotions | | |
| zich vergissen | to be mistaken | | | |

**Detection Logic**:
- Input: `"zich schamen"`
- Detected as: `EntryType.WORD` (not PHRASE)
- Reason: Starts with "zich " → special case like "de " or "het "

See [scripts/data/import_from_gsheet.py:detect_entry_type()](../scripts/data/import_from_gsheet.py) for implementation.

## Schema Design

### VerbMetadata

The `is_reflexive` flag identifies reflexive verbs:

```python
class VerbMetadata(BaseModel):
    # ... other fields ...
    is_reflexive: Optional[bool] = None  # True if verb requires "zich"
```

### Lemma Normalization

**Important**: The lemma should be stored **without** "zich":

- ✅ Correct: `lemma="schamen"`, `verb_meta.is_reflexive=True`
- ❌ Wrong: `lemma="zich schamen"`

This allows for:
1. Consistent lemma lookup (search for "schamen" not "zich schamen")
2. Clear separation of the reflexive marker from the verb root
3. Proper conjugation display (the reflexive pronoun changes, the verb doesn't)

## AI Enrichment

The AI enrichment prompt instructs the model to:

1. **Detect reflexive verbs**: If the input contains "zich", recognize it as reflexive
2. **Normalize the lemma**: Remove "zich" from the lemma field
3. **Set the flag**: Mark `verb_meta.is_reflexive = True`
4. **Provide examples**: Include examples with various reflexive pronouns (me/je/zich/ons)

Example enrichment for "zich schamen":
```json
{
  "lemma": "schamen",
  "pos": "verb",
  "translations": ["to be ashamed", "to feel ashamed"],
  "verb_meta": {
    "is_reflexive": true,
    "past_singular": "schaamde",
    "past_participle": "geschaamd",
    "auxiliary": "hebben",
    "examples_present": [
      {
        "dutch": "Ik schaam me voor mijn fout.",
        "english": "I'm ashamed of my mistake."
      }
    ]
  }
}
```

See [scripts/enrichment/enrich_lexicon.py](../scripts/enrichment/enrich_lexicon.py) for the full prompt.

## Display in App

When displaying reflexive verbs in the Streamlit app:

### Option 1: Show with "zich"
Display `zich + lemma` for flashcards:
```python
if word.get("verb_meta", {}).get("is_reflexive"):
    display_text = f"zich {word['lemma']}"
else:
    display_text = word['lemma']
```

### Option 2: Show without "zich"
Display just the lemma, let the user infer from context:
```python
display_text = word['lemma']
# User sees "schamen" and knows from examples it's reflexive
```

**Recommendation**: Option 1 (show with "zich") for clarity, especially for beginners.

## Examples in Database

For reflexive verbs, examples should include the reflexive pronoun:

```json
{
  "lemma": "vergissen",
  "verb_meta": {
    "is_reflexive": true,
    "examples_present": [
      {
        "dutch": "Je vergist je, dat is niet waar.",
        "english": "You're mistaken, that's not true."
      }
    ]
  }
}
```

## Comparison with Articles (de/het)

Reflexive verbs work similarly to nouns with articles:

| Type | Import Format | Lemma | Metadata Flag | Display |
|------|---------------|-------|---------------|---------|
| Noun | `de hond` | `hond` | `noun_meta.article="de"` | `de hond` |
| Noun | `het huis` | `huis` | `noun_meta.article="het"` | `het huis` |
| Verb | `zich schamen` | `schamen` | `verb_meta.is_reflexive=True` | `zich schamen` |

In all cases:
- ✅ Import accepts the full form ("de hond", "zich schamen")
- ✅ Stored lemma is normalized ("hond", "schamen")
- ✅ Metadata flag preserves the requirement
- ✅ Display shows the full form

## Migration

Existing entries with `lemma="zich schamen"` can be fixed with a migration script:

```python
# Find reflexive verbs with "zich" in lemma
entries = collection.find({
    "pos": "verb",
    "lemma": {"$regex": "^zich "}
})

for entry in entries:
    # Remove "zich " from lemma
    new_lemma = entry["lemma"].replace("zich ", "")

    # Update entry
    collection.update_one(
        {"_id": entry["_id"]},
        {
            "$set": {
                "lemma": new_lemma,
                "verb_meta.is_reflexive": True
            }
        }
    )
```

## Testing

To test reflexive verb import:

1. Add to Google Sheet:
   ```
   dutch: zich vergissen
   english: to be mistaken
   ```

2. Import:
   ```bash
   python -m scripts.data.import_from_gsheet --sheet-id YOUR_ID --batch-size 1
   ```

3. Verify entry_type:
   ```python
   from core import lexicon_repo
   word = lexicon_repo.get_word_by_lemma_pos("zich vergissen", "verb")
   # OR (after enrichment with normalization)
   word = lexicon_repo.get_word_by_lemma_pos("vergissen", "verb")
   assert word["entry_type"] == "word"  # Not "phrase"
   ```

4. Enrich:
   ```bash
   python -m scripts.enrichment.enrich_and_update --batch-size 1
   ```

5. Verify reflexive flag:
   ```python
   assert word["verb_meta"]["is_reflexive"] == True
   assert word["lemma"] == "vergissen"  # Not "zich vergissen"
   ```

## Summary

✅ Import "zich schamen" → detected as WORD (not PHRASE)
✅ Store as `lemma="schamen"` with `is_reflexive=True`
✅ Display as "zich schamen" in app
✅ Examples include reflexive pronouns (me/je/zich/ons)
✅ Consistent with article handling (de/het)
