"""CLI entry point for cascade."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cascade.bench import run_bench
from cascade.model import ModelConfig
from cascade.pipeline import PipelineConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Cascade: frontier coding at commodity cost")
    sub = parser.add_subparsers(dest="command")

    # --- bench ---
    bench_p = sub.add_parser("bench", help="Run benchmark")
    bench_p.add_argument("problems", type=Path, help="Path to problems JSONL")
    bench_p.add_argument("--output", "-o", type=Path, help="Output results JSON")
    bench_p.add_argument("--limit", "-n", type=int, help="Max problems to run")
    bench_p.add_argument("--model", default="qwen2.5-coder-32b", help="Base model name")
    bench_p.add_argument("--base-url", default="http://localhost:11434/v1", help="API base URL")
    bench_p.add_argument("--api-key", default="ollama", help="API key")
    bench_p.add_argument("--heuristic-router", action="store_true", help="Use heuristic router")

    # --- solve ---
    solve_p = sub.add_parser("solve", help="Solve a single problem from stdin or file")
    solve_p.add_argument("--file", "-f", type=Path, help="Problem description file")
    solve_p.add_argument("--model", default="qwen2.5-coder-32b")
    solve_p.add_argument("--base-url", default="http://localhost:11434/v1")
    solve_p.add_argument("--api-key", default="ollama")

    args = parser.parse_args()

    if args.command == "bench":
        _run_bench(args)
    elif args.command == "solve":
        _run_solve(args)
    else:
        parser.print_help()
        sys.exit(1)


def _make_config(args: argparse.Namespace) -> PipelineConfig:
    base = ModelConfig(name=args.model, base_url=args.base_url, api_key=args.api_key)
    small = ModelConfig(
        name=args.model.replace("32b", "7b").replace("v3", "coder-v2"),
        base_url=args.base_url,
        api_key=args.api_key,
        max_tokens=2048,
    )
    return PipelineConfig(
        router_model=small if not getattr(args, "heuristic_router", False) else None,
        planner_model=small,
        coder_model=base,
        critic_model=small,
        repair_model=base,
        use_heuristic_router=getattr(args, "heuristic_router", False),
    )


def _run_bench(args: argparse.Namespace) -> None:
    config = _make_config(args)
    run_bench(args.problems, config, output_path=args.output, limit=args.limit)


def _run_solve(args: argparse.Namespace) -> None:
    from cascade.pipeline import run as run_pipeline
    from cascade.types import CodingProblem

    if args.file:
        description = args.file.read_text()
    else:
        description = sys.stdin.read()

    problem = CodingProblem(description=description)
    config = _make_config(args)
    result = run_pipeline(problem, config)

    print(result.patch)
    print(f"\n# Cost: ${result.total_cost:.6f} | Tokens: {result.total_tokens} | "
          f"Steps: {len(result.steps)} | Difficulty: {result.difficulty.value}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
