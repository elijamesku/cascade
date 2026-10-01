"""Benchmark runner: load problems, run pipeline, measure cost vs. correctness."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

from cascade.pipeline import PipelineConfig, run
from cascade.types import CodingProblem, PipelineResult

console = Console()


@dataclass
class BenchResult:
    problem_id: str
    resolved: bool
    difficulty: str
    total_cost_usd: float
    total_tokens: int
    total_latency_ms: float
    n_steps: int


def load_problems(path: Path) -> list[tuple[str, CodingProblem]]:
    """Load problems from a JSONL file. Each line: {id, description, repo, files, test_command}."""
    problems = []
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            problems.append((
                d["id"],
                CodingProblem(
                    description=d["description"],
                    repo=d.get("repo", ""),
                    files=d.get("files", {}),
                    test_command=d.get("test_command", ""),
                ),
            ))
    return problems


def check_patch(problem: CodingProblem, result: PipelineResult) -> bool:
    """Placeholder: in real bench, apply patch and run tests. For now, check non-empty."""
    return bool(result.patch.strip())


def run_bench(
    problems_path: Path,
    config: PipelineConfig,
    output_path: Path | None = None,
    limit: int | None = None,
) -> list[BenchResult]:
    problems = load_problems(problems_path)
    if limit:
        problems = problems[:limit]

    results: list[BenchResult] = []

    for pid, problem in problems:
        console.print(f"\n[bold]--- {pid} ---[/bold]")
        t0 = time.monotonic()
        pipeline_result = run(problem, config)
        elapsed = (time.monotonic() - t0) * 1000

        resolved = check_patch(problem, pipeline_result)

        br = BenchResult(
            problem_id=pid,
            resolved=resolved,
            difficulty=pipeline_result.difficulty.value,
            total_cost_usd=pipeline_result.total_cost,
            total_tokens=pipeline_result.total_tokens,
            total_latency_ms=elapsed,
            n_steps=len(pipeline_result.steps),
        )
        results.append(br)

        status = "[green]PASS[/green]" if resolved else "[red]FAIL[/red]"
        console.print(
            f"  {status}  difficulty={br.difficulty}  "
            f"cost=${br.total_cost_usd:.6f}  tokens={br.total_tokens}  "
            f"steps={br.n_steps}  latency={br.total_latency_ms:.0f}ms"
        )

    _print_summary(results)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        console.print(f"\nResults saved to {output_path}")

    return results


def _print_summary(results: list[BenchResult]) -> None:
    n = len(results)
    if not n:
        return

    resolved = sum(1 for r in results if r.resolved)
    total_cost = sum(r.total_cost_usd for r in results)
    total_tokens = sum(r.total_tokens for r in results)

    table = Table(title="\nBenchmark Summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    table.add_row("Problems", str(n))
    table.add_row("Resolved", f"{resolved}/{n} ({resolved/n*100:.1f}%)")
    table.add_row("Total cost", f"${total_cost:.6f}")
    table.add_row("Avg cost/problem", f"${total_cost/n:.6f}")
    table.add_row("Total tokens", f"{total_tokens:,}")
    table.add_row("Cost per resolved", f"${total_cost/max(resolved,1):.6f}")

    console.print(table)
