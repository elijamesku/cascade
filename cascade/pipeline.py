"""The core pipeline: route → plan → code → critique → repair."""

from __future__ import annotations

from cascade.model import ModelConfig, call_model
from cascade.roles import CODER, CRITIC, PLANNER, REPAIR
from cascade.router import classify, classify_heuristic
from cascade.types import CodingProblem, Difficulty, PipelineResult, StepResult


class PipelineConfig:
    def __init__(
        self,
        router_model: ModelConfig | None = None,
        planner_model: ModelConfig | None = None,
        coder_model: ModelConfig | None = None,
        critic_model: ModelConfig | None = None,
        repair_model: ModelConfig | None = None,
        max_repair_rounds: int = 2,
        use_heuristic_router: bool = False,
    ):
        self.router_model = router_model
        self.planner_model = planner_model
        self.coder_model = coder_model
        self.critic_model = critic_model
        self.repair_model = repair_model
        self.max_repair_rounds = max_repair_rounds
        self.use_heuristic_router = use_heuristic_router


def _format_context(problem: CodingProblem) -> str:
    parts = [f"## Problem\n{problem.description}"]
    if problem.files:
        parts.append("## Relevant files")
        for path, content in problem.files.items():
            parts.append(f"### {path}\n```\n{content}\n```")
    return "\n\n".join(parts)


def run(problem: CodingProblem, config: PipelineConfig) -> PipelineResult:
    steps: list[StepResult] = []
    context = _format_context(problem)

    # --- Route ---
    if config.use_heuristic_router:
        difficulty = classify_heuristic(problem)
    elif config.router_model:
        difficulty, route_cost = classify(problem, config.router_model)
        steps.append(StepResult(
            role="router", content=difficulty.value, model=config.router_model.name,
            cost_usd=route_cost,
        ))
    else:
        difficulty = Difficulty.NORMAL

    # --- Easy: single coder call ---
    if difficulty == Difficulty.EASY:
        assert config.coder_model
        result = call_model(
            config.coder_model,
            [
                {"role": "system", "content": CODER},
                {"role": "user", "content": context + "\n\nPlan: make the obvious minimal fix."},
            ],
            role_name="coder",
        )
        steps.append(result)
        return PipelineResult(patch=result.content, steps=steps, difficulty=difficulty)

    # --- Normal+: plan then code ---
    plan_text = ""
    if difficulty in (Difficulty.HARD, Difficulty.EXTREME) and config.planner_model:
        plan_result = call_model(
            config.planner_model,
            [
                {"role": "system", "content": PLANNER},
                {"role": "user", "content": context},
            ],
            role_name="planner",
        )
        steps.append(plan_result)
        plan_text = plan_result.content

    # --- Code ---
    assert config.coder_model
    coder_prompt = context
    if plan_text:
        coder_prompt += f"\n\n## Implementation plan\n{plan_text}"

    code_result = call_model(
        config.coder_model,
        [
            {"role": "system", "content": CODER},
            {"role": "user", "content": coder_prompt},
        ],
        role_name="coder",
    )
    steps.append(code_result)
    current_patch = code_result.content

    # --- Critic + Repair loop (hard/extreme only) ---
    if difficulty in (Difficulty.HARD, Difficulty.EXTREME) and config.critic_model:
        for _ in range(config.max_repair_rounds):
            critic_result = call_model(
                config.critic_model,
                [
                    {"role": "system", "content": CRITIC},
                    {"role": "user", "content": f"{context}\n\n## Proposed patch\n{current_patch}"},
                ],
                role_name="critic",
            )
            steps.append(critic_result)

            if "LGTM" in critic_result.content.upper():
                break

            if config.repair_model:
                repair_result = call_model(
                    config.repair_model,
                    [
                        {"role": "system", "content": REPAIR},
                        {"role": "user", "content": (
                            f"{context}\n\n"
                            f"## Current patch\n{current_patch}\n\n"
                            f"## Review feedback\n{critic_result.content}"
                        )},
                    ],
                    role_name="repair",
                )
                steps.append(repair_result)
                current_patch = repair_result.content

    return PipelineResult(patch=current_patch, steps=steps, difficulty=difficulty)
