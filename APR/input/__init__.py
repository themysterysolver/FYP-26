"""
APR module input construction: build APRInput from generation + detection outputs.
"""
from .schema import APRInput, APR_INPUT_PARQUET_SCHEMA

_BUILDER_ATTRS = (
    "build_apr_input",
    "build_one_apr_input",
    "run_builder",
    "write_apr_input_jsonl",
    "write_apr_input_parquet",
)


def __getattr__(name: str):
    if name in _BUILDER_ATTRS:
        from .builder import (
            build_apr_input,
            build_one_apr_input,
            run_builder,
            write_apr_input_jsonl,
            write_apr_input_parquet,
        )
        return {
            "build_apr_input": build_apr_input,
            "build_one_apr_input": build_one_apr_input,
            "run_builder": run_builder,
            "write_apr_input_jsonl": write_apr_input_jsonl,
            "write_apr_input_parquet": write_apr_input_parquet,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "APRInput",
    "APR_INPUT_PARQUET_SCHEMA",
    "build_apr_input",
    "build_one_apr_input",
    "run_builder",
    "write_apr_input_jsonl",
    "write_apr_input_parquet",
]
