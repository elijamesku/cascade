from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Difficulty(Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXTREME = "extreme"


@dataclass
class CodingProblem:
    description: str
    repo: str = ""
    files: dict[str, str] = field(default_factory=dict)
    test_command: str = ""


@dataclass
class StepResult:
    role: str
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0
    cost_usd: float = 0


@dataclass
class PipelineResult:
    patch: str
    steps: list[StepResult] = field(default_factory=list)
    difficulty: Difficulty = Difficulty.NORMAL

    @property
    def total_cost(self) -> float:
        return sum(s.cost_usd for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return sum(s.prompt_tokens + s.completion_tokens for s in self.steps)

    @property
    def total_latency_ms(self) -> float:
        return sum(s.latency_ms for s in self.steps)
