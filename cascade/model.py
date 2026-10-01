"""Thin wrapper around OpenAI-compatible inference APIs."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from openai import OpenAI

from cascade.types import StepResult

# Rough per-token costs (USD) for popular open models via common providers.
# These are placeholders — swap in real provider pricing.
MODEL_COSTS: dict[str, tuple[float, float]] = {
    # (prompt $/token, completion $/token)
    "qwen2.5-coder-32b": (0.0000002, 0.0000006),
    "qwen2.5-coder-7b": (0.00000005, 0.00000015),
    "qwen2.5-coder-3b": (0.00000002, 0.00000006),
    "deepseek-v3": (0.00000014, 0.00000028),
    "deepseek-coder-v2": (0.00000014, 0.00000028),
    # Frontier baselines for comparison
    "claude-sonnet-5": (0.000003, 0.000015),
    "gpt-4o": (0.0000025, 0.00001),
}


@dataclass
class ModelConfig:
    name: str
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    temperature: float = 0.0
    max_tokens: int = 4096


def call_model(config: ModelConfig, messages: list[dict], role_name: str = "") -> StepResult:
    client = OpenAI(base_url=config.base_url, api_key=config.api_key)

    t0 = time.monotonic()
    response = client.chat.completions.create(
        model=config.name,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    latency = (time.monotonic() - t0) * 1000

    usage = response.usage
    prompt_tok = usage.prompt_tokens if usage else 0
    completion_tok = usage.completion_tokens if usage else 0

    costs = MODEL_COSTS.get(config.name, (0.0, 0.0))
    cost = prompt_tok * costs[0] + completion_tok * costs[1]

    return StepResult(
        role=role_name or config.name,
        content=response.choices[0].message.content or "",
        model=config.name,
        prompt_tokens=prompt_tok,
        completion_tokens=completion_tok,
        latency_ms=latency,
        cost_usd=cost,
    )
