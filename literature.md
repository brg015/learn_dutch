# Literature and Theoretical Background

This document summarizes the **academic literature and applied systems** that inform the design of the learning algorithm used in this project.

The goal is **not** to claim that specific parameter values are theoretically fixed, but to ground the **structure, assumptions, and constraints** of the model in established research on human memory, spacing, and retrieval.

Where numeric constants are used in the implementation, they are **theory-consistent initial guesses**, intended to be refined through empirical optimization once sufficient learner data is available.

---

## 1. Forgetting Curves and Memory Strength

These works motivate modeling memory as a latent strength or stability variable that decays smoothly over time and determines recall probability.

**Ebbinghaus, H. (1885).**  
*Über das Gedächtnis: Untersuchungen zur experimentellen Psychologie.*  
Leipzig: Duncker & Humblot.  
→ Original experimental work establishing the forgetting curve.

**Wixted, J. T. (2004).**  
*The psychology and neuroscience of forgetting.*  
Annual Review of Psychology, 55, 235–269.  
→ Comprehensive review of forgetting curves, including exponential and power-law decay.

**Anderson, J. R., & Schooler, L. J. (1991).**  
*Reflections of the environment in memory.*  
Psychological Science, 2(6), 396–408.  
→ Rational analysis framework; memory decay reflects environmental statistics.

**Relevance to this project:**
- Justifies modeling recall probability as a function of elapsed time and memory strength.
- Supports the use of a latent stability variable controlling forgetting rate.

---

## 2. Spacing Effects and Desirable Difficulty

These papers explain why **effortful, well-timed retrieval** leads to stronger long-term memory than easy or massed practice.

**Bjork, R. A., & Bjork, E. L. (1992).**  
*A new theory of disuse and an old theory of stimulus fluctuation.*  
In A. Healy et al. (Eds.), *From Learning Processes to Cognitive Processes* (pp. 35–67).  
→ Foundational theory distinguishing retrieval strength from storage strength.

**Bjork, R. A. (1994).**  
*Memory and metamemory considerations in the training of human beings.*  
In J. Metcalfe & A. Shimamura (Eds.), *Metacognition: Knowing about knowing*.  
→ Introduces “desirable difficulty” as a principle of learning.

**Kornell, N., Bjork, R. A., & Garcia, M. A. (2011).**  
*Why tests appear to prevent forgetting: A distribution-based bifurcation model.*  
Journal of Memory and Language, 65(2), 85–97.  
→ Explains why retrieval success near failure produces large learning gains.

**Relevance to this project:**
- Motivates weighting learning updates by how close an item was to being forgotten.
- Supports rewarding “risky” success more than easy success.
- Explains why same-day repetition should not count the same as spaced retrieval.

---

## 3. Computational Models of Spaced Practice

These works provide concrete models linking recall probability, memory strength, and optimal scheduling.

**Pavlik, P. I., & Anderson, J. R. (2005).**  
*Practice and forgetting effects on vocabulary memory: An activation-based model of the spacing effect.*  
Cognitive Science, 29(4), 559–586.  
→ Highly relevant to vocabulary learning; models memory strength and spacing explicitly.

**Pavlik, P. I., & Anderson, J. R. (2008).**  
*Using a model to compute the optimal schedule of practice.*  
Journal of Experimental Psychology: Applied, 14(2), 101–117.  
→ Demonstrates how memory models can drive scheduling decisions.

**Mozer, M. C., Pashler, H., Cepeda, N. J., Lindsey, R. V., & Vul, E. (2009).**  
*Predicting the optimal spacing of study: A multiscale context model of memory.*  
Advances in Neural Information Processing Systems (NeurIPS).  
→ Another computational approach to optimal spacing.

**Relevance to this project:**
- Supports scheduling based on predicted recall probability.
- Motivates separating forgetting dynamics from learning dynamics.
- Validates model-based scheduling over fixed heuristics.

---

## 4. Difficulty, Learning Efficiency, and Fluency

These works motivate separating **forgetting rate** from **learning efficiency**, and treating difficulty as a modifier of how much learning occurs.

**Anderson, J. R. (2007).**  
*How can the human mind occur in the physical universe?*  
Oxford University Press.  
→ ACT-R framework; distinguishes activation decay from learning rate.

**Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006).**  
*Distributed practice in verbal recall tasks: A review and quantitative synthesis.*  
Psychological Bulletin, 132(3), 354–380.  
→ Meta-analysis of spacing effects and diminishing returns of massed practice.

**Relevance to this project:**
- Justifies modeling difficulty as a learning-efficiency parameter rather than a decay parameter.
- Supports the idea that short-term practice improves fluency but not long-term consolidation.

---

## 5. Modern Applied Spaced Repetition Systems (FSRS Lineage)

These references connect the design to real-world systems used at scale.

**Chen, W., et al. (2023).**  
*FSRS: A modern spaced repetition scheduling algorithm.*  
Open-source technical documentation and community validation.  
→ Introduces stability, difficulty, and retrievability as core state variables.

**Open Spaced Repetition Project.**  
*Free Spaced Repetition Scheduler (FSRS).*  
https://github.com/open-spaced-repetition  
→ Canonical reference implementation and design discussions.

**Relevance to this project:**
- Confirms the practicality of stability/difficulty-based scheduling.
- Demonstrates parameter optimization from review logs.
- Provides a real-world benchmark for model behavior.

---

## 6. How This Project Uses the Literature

This project adopts the **structure and principles** supported by the literature:

- Latent memory state with smooth forgetting
- Spaced retrieval as the primary driver of long-term retention
- Difficulty modulating learning efficiency
- Diminishing returns of massed practice

Numeric parameter values (e.g. learning rates, scaling constants) are treated as:

> **Theory-consistent initial defaults**, not theoretical constants.

They are intended to be refined empirically once sufficient user data is available.

---

## 7. Recommended Reading Priority

If time is limited, the most relevant papers are:

1. Bjork & Bjork (1992) – desirable difficulty  
2. Pavlik & Anderson (2005) – vocabulary learning + spacing model  
3. Wixted (2004) – forgetting curves  
4. Cepeda et al. (2006) – spacing meta-analysis  
5. FSRS documentation – applied system reference

---

This document is meant to evolve as the model and empirical evidence grow.
