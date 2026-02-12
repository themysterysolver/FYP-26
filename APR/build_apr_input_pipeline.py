#!/usr/bin/env python3
"""
Build APR input from generation + detection outputs.
Usage (from project root, with venv that has pandas):
  python APR/build_apr_input_pipeline.py [--output PATH] [--format jsonl|parquet]
  python -m APR.build_apr_input_pipeline --output APR/input/apr_input.jsonl
"""
from __future__ import annotations

import argparse
import os

# Run from project root so APR.input is importable
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in __import__("sys").path:
    __import__("sys").path.insert(0, _PROJECT_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build APRInput JSONL/Parquet from detection outputs")
    parser.add_argument("--output", "-o", default="", help="Output path (default: apr_input.jsonl in APR/input)")
    parser.add_argument("--format", "-f", choices=["jsonl", "parquet"], default="jsonl", help="Output format")
    parser.add_argument("--generation-dir", default="", help="Dir with mbpp_gen.csv, humaneval_gen.csv, ds1k_gen.csv")
    parser.add_argument("--static-dir", default="", help="Dir with ast_summary.csv, cfg_summary.csv, libapi_summary.csv")
    parser.add_argument("--dynamic-dir", default="", help="Dir with dynamic_*.jsonl")
    args = parser.parse_args()

    from APR.input import run_builder, write_apr_input_jsonl, write_apr_input_parquet

    generation_dir = args.generation_dir or os.path.join(_PROJECT_ROOT, "APR", "ANALYSIS")
    static_dir = args.static_dir or os.path.join(_PROJECT_ROOT, "APR", "ANALYSIS")
    dynamic_dir = args.dynamic_dir or os.path.join(_PROJECT_ROOT, "Hallucination detection", "dynamic")

    apr_inputs = run_builder(
        generation_dir=generation_dir,
        static_dir=static_dir,
        dynamic_dir=dynamic_dir,
        output_path=None,
    )

    output_path = args.output
    if not output_path:
        output_path = os.path.join(_PROJECT_ROOT, "APR", "input", "apr_input.jsonl")
        if args.format == "parquet":
            output_path = os.path.join(_PROJECT_ROOT, "APR", "input", "apr_input.parquet")

    if args.format == "parquet":
        write_apr_input_parquet(apr_inputs, output_path)
    else:
        write_apr_input_jsonl(apr_inputs, output_path)

    print(f"Wrote {len(apr_inputs)} APRInput records to {output_path}")


if __name__ == "__main__":
    main()
