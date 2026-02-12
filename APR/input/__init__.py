"""
APR module input construction: build APRInput from generation + detection outputs.
"""
from .builder import (
    build_apr_input,
    build_one_apr_input,
    run_builder,
    write_apr_input_jsonl,
    write_apr_input_parquet,
)
from .schema import APRInput, APR_INPUT_PARQUET_SCHEMA

__all__ = [
    "APRInput",
    "APR_INPUT_PARQUET_SCHEMA",
    "build_apr_input",
    "build_one_apr_input",
    "run_builder",
    "write_apr_input_jsonl",
    "write_apr_input_parquet",
]
