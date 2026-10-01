# Cascade

**Can frontier intelligence be decomposed into inexpensive specialized inference steps whose composition reproduces frontier-model performance?**

Cascade is a research prototype that pipelines smaller open-weight models — planner, coder, critic, repair — and routes problems by difficulty, aiming to match frontier coding performance at a fraction of the inference cost.

## Thesis

Current frontier models apply the same enormous computation whether the problem is "rename this variable" or "debug a distributed system." Cascade tests whether decomposing that into specialized steps can recover 90–99% of the quality at 10–100× less cost.

## Architecture

```
PROMPT
  ↓
Router (classify difficulty)
  ↓
┌──────────────────────────────────┐
│ easy    → single small model     │
│ normal  → coder                  │
│ hard    → planner + coder        │
│ extreme → planner+coder+critic+repair │
└──────────────────────────────────┘
  ↓
OUTPUT
```

### Pipeline roles

| Role | Job | Target size |
|------|-----|-------------|
| **Router** | Classify problem difficulty, pick pipeline | ~1–3B |
| **Planner** | Break problem into steps, identify files/APIs | ~3–7B |
| **Coder** | Generate the implementation | ~7–32B |
| **Critic** | Review output, find bugs, suggest fixes | ~3–7B |
| **Repair** | Apply critic's feedback, produce final output | ~7–32B |

## Benchmark

Starting with SWE-bench Lite (300 real GitHub issues). Metric: **resolve rate per dollar of inference compute.**

## Getting started

```bash
pip install -e ".[dev]"
```

## Status

Early prototype. Scaffolding phase.
