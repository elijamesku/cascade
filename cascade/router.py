"""Classify problem difficulty to decide which pipeline stages to run."""

from __future__ import annotations

from cascade.model import ModelConfig, call_model
from cascade.types import CodingProblem, Difficulty

ROUTER_PROMPT = """You are a coding problem difficulty classifier. Given a coding problem description, classify it into exactly one category:

- EASY: simple rename, typo fix, one-line change, config tweak
- NORMAL: straightforward bug fix or small feature, single file, clear solution
- HARD: multi-file change, requires understanding system architecture, non-obvious fix
- EXTREME: complex debugging, distributed systems, requires deep reasoning and iteration

Respond with ONLY the difficulty level as a single word: EASY, NORMAL, HARD, or EXTREME."""


def classify(problem: CodingProblem, model: ModelConfig) -> tuple[Difficulty, float]:
    """Return (difficulty, cost_usd) for routing the problem."""
    result = call_model(
        model,
        [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": problem.description},
        ],
        role_name="router",
    )

    text = result.content.strip().upper()
    for d in Difficulty:
        if d.value.upper() in text:
            return d, result.cost_usd

    return Difficulty.NORMAL, result.cost_usd


# Heuristic fallback that avoids any model call.
def classify_heuristic(problem: CodingProblem) -> Difficulty:
    desc = problem.description.lower()
    n_files = len(problem.files)

    if any(w in desc for w in ["rename", "typo", "config", "version bump"]):
        return Difficulty.EASY
    if n_files > 5 or any(w in desc for w in ["distributed", "concurren", "race condition"]):
        return Difficulty.EXTREME
    if n_files > 2 or any(w in desc for w in ["refactor", "architect", "migration"]):
        return Difficulty.HARD
    return Difficulty.NORMAL
