"""Frontier baseline: send the same problem to a single frontier model for comparison."""

from __future__ import annotations

from cascade.model import ModelConfig, call_model
from cascade.types import CodingProblem, Difficulty, PipelineResult


BASELINE_PROMPT = """You are an expert software engineer. Given a coding problem and relevant source files, produce a unified diff patch that solves the problem.

Output ONLY a valid unified diff (```diff ... ```)."""


def run_baseline(problem: CodingProblem, model: ModelConfig) -> PipelineResult:
    parts = [f"## Problem\n{problem.description}"]
    if problem.files:
        parts.append("## Relevant files")
        for path, content in problem.files.items():
            parts.append(f"### {path}\n```\n{content}\n```")
    context = "\n\n".join(parts)

    result = call_model(
        model,
        [
            {"role": "system", "content": BASELINE_PROMPT},
            {"role": "user", "content": context},
        ],
        role_name="baseline",
    )

    return PipelineResult(
        patch=result.content,
        steps=[result],
        difficulty=Difficulty.NORMAL,
    )
