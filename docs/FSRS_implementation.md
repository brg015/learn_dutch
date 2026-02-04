# FSRS Implementation – Design Specification

## Purpose

This document describes the **intended learning algorithm design** for the vocabulary trainer.

It is a **design-first specification**, not a description of the current code.
The goal is to define principles, memory state, and update rules clearly before (or independent of) implementation.

The system is based on **FSRS-style spaced repetition**, extended with a principled separation between:

- **Long-Term Memory (LTM)** updates  
- **Short-Term Memory (STM)** practice and fluency repair

---

## Core Design Principles

1. **Spaced retrieval drives long-term memory**
   - The most important learning signal comes from retrieval after meaningful time gaps.
   - The first spaced retrieval attempt of a day carries the most weight for long-term updates.

2. **Short-term practice supports fluency, not consolidation**
   - Repeated same-day exposure improves access and fluency.
   - It should not be credited as strongly as spaced retrieval.

3. **The algorithm must not force study sessions**
   - Users may continue studying beyond “due” items.
   - Extra study should focus on weak or recently failed material without corrupting long-term scheduling.

4. **Memory state should be interpretable**
   - Model variables correspond to meaningful cognitive quantities (forgetting rate, learning efficiency).

---

## Unit of Scheduling

The basic unit of learning is a **card**, defined as:

(lemma × exercise type × prompt → answer)

Examples:
- (verrekijker, translation)
- (verrekijker, article)
- (lopen, perfectum)
- (wachten, prepositions)

Each card is tracked independently and has its own memory state.

---

## Memory State Variables

Each card maintains the following **persistent state**.

### Stability (S)
- Units: days
- Meaning: how slowly the memory decays
- Larger S means slower forgetting

### Difficulty (D)
- Unitless, range 1–10
- Meaning: how hard this card is for the learner
- Higher D means slower learning

These are **long-term parameters**, updated only by LTM events.

---

## Derived Quantity: Retrievability

At any moment, the probability that the learner can recall a card is:

R = exp( -Δt / S )

Where:
- Δt = time since last LTM review (in days)
- S = stability

Interpretation:
- Immediately after review: R is close to 1
- As time passes: R decays smoothly
- A card is considered **due** when R drops below a target threshold (e.g. 0.70)

---

## Feedback Scale (User Input)

User feedback is graded on four levels:

| Label  | Meaning                          |
|------|----------------------------------|
| Again | Retrieval failed                 |
| Hard  | Retrieved with high effort       |
| Medium| Retrieved normally               |
| Easy  | Retrieved fluently               |

These labels are **signals**, not ground truth.

---

## Long-Term Memory (LTM) Updates

### When LTM Updates Occur

- Once per card per day
- At the first meaningful retrieval attempt after a non-trivial delay
- This update drives long-term scheduling

---

### LTM Stability Update

For a successful retrieval (Hard / Medium / Easy):

ΔS = k * S * base_gain(rating) * (1 - R) * f(D_used)  
S_new = S + ΔS

Where:
- (1 - R) rewards risky (well-spaced) success
- f(D) reduces learning gains for difficult items
- f(D) = 1 / (1+ alpha*(D-1)) 
- alpha controls how much difficulty reduces learning efficiency, with a large alpha leading to slower learning (ΔS)

Key principle:
Spaced, effortful success produces the largest stability gains.

---

### Stability Reduction on Failure (LTM only)

For a failed retrieval (Again):

S_new = max(S_min, S * (1 - k_fail * R))

Failures are penalized more strongly when recall was expected (high R).

---

### LTM Difficulty Update

Difficulty reflects **learning efficiency**, not forgetting speed.

D_new = clip(
    D + eta * surprise * u(rating),
    min=1,
    max=10
)

- Suprise = {
    on failure: R
    on succuss (hard, medium, or easy): (1-R)
}
- eta controls how quickly difficulty adapts, higher eta leads to faster changes

Conceptually:
- Failure increases difficulty
- Easy success decreases difficulty
- Changes are larger when the outcome was surprising given R

Difficulty updates happen **only during LTM events**.

---

## Short-Term Memory (STM) Practice

STM exists to:
- Repair same-day failures
- Improve access and fluency
- Support later spaced learning

STM **never updates stability (S)**.

---

## Effective Difficulty (D_eff)

To allow STM to matter without corrupting long-term memory, we introduce:

### D_eff – Effective Difficulty
- Used only for learning efficiency
- Initialized as:

D_eff = D

- Modified by STM success
- Used at the next LTM update to scale stability gains

D remains the true long-term difficulty.

---

## STM → Difficulty Update Rule

### Counterfactual Difficulty Clamp

After an LTM event, compute:

D_floor = the difficulty the card would have had
          if the learner had answered Hard (correct with effort)

STM may move D_eff toward D_floor, but never below it.

This encodes the rule:
STM can repair fluency up to “Hard-correct,” but cannot certify mastery.

---

### STM Success Update

On the m-th STM success of the day:

D_eff = D_floor + (D_eff - D_floor) * (1 - lambda_m)

With diminishing returns:

lambda_m = 0.5 / (m + 1)

Interpretation:
- First STM success moves about 50% toward the floor
- Subsequent successes produce smaller gains
- STM repairs fluency without overstating long-term mastery

STM failures:
- Do not update D or D_eff
- Are logged only

---

## Interaction Between STM and LTM

- STM never updates S directly
- STM improves learning efficiency
- On the next LTM review:
  - Stability updates use D_eff instead of D
- After the LTM update:
  - D_eff is reset to D

This ensures STM helps without misleading the scheduler.

---

## Scheduling Pools (Conceptual)

The system operates over three conceptual pools:

1. LTM pool
   - Cards with low retrievability (R < threshold)
   - Ranked by urgency (lowest R first)

2. STM pool
   - Cards failed or marked Hard today
   - Used for optional extra practice

3. New cards
   - No memory state yet
   - Intake-limited per day

Users may study indefinitely; the system adapts without forcing sessions.

---

## Default Parameters (Initial Guesses)

These are **initial defaults**, not claims of optimality.

### Global Constants

| Parameter | Value |
|---------|-------|
| R_target | 0.70 |
| S_min   | 0.5 days |
| D range | 1–10 |
| k       | 1.2 |
| k_fail  | 0.6 |
| alpha   | 0.15 |
| eta     | 0.8 |

---

### Base Learning Gain by Rating

| Rating | base_gain |
|------|-----------|
| Hard | 0.5 |
| Medium | 1.0 |
| Easy | 1.8 |

---

### Difficulty Update Direction by Rating

| Rating | u(rating) |
|------|------------|
| Again | +1.0 |
| Hard  | +0.35 |
| Medium| -0.20 |
| Easy  | -0.60 |

Difficulty is clipped to the range [1, 10].

---

## Logging and Future Optimization

All events should be logged:
- LTM attempts
- STM attempts (success/failure, response time)
- State before and after LTM updates

This enables:
- Parameter optimization
- Evaluation of STM effectiveness
- Future RT-based or confidence-based modeling

---

## Status

- This document defines the **target design**
- Implementation may lag behind specification
- STM/LTM separation is planned but not fully implemented

---

Code should be written to match the model — not the other way around.
