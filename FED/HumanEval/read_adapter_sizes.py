#!/usr/bin/env python3
"""
LoRA Adapter Size and Load-Time Diagnostics

Reports disk sizes and (optionally) tensor sizes for a lora_adapters directory.
Use to diagnose slow .pt loading (e.g. ~20 min load times).

Usage:
  python read_adapter_sizes.py [ADAPTER_DIR] [--load] [--verbose] [--csv OUTPUT.csv]
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path


def report_disk_sizes(adapter_dir: Path) -> list[dict]:
    """Walk directory, collect file sizes. Returns list of {file, size_bytes, size_mb}."""
    rows = []
    adapter_dir = Path(adapter_dir).resolve()
    if not adapter_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {adapter_dir}")

    for root, _dirs, files in os.walk(adapter_dir):
        for name in files:
            fpath = Path(root) / name
            try:
                size_bytes = fpath.stat().st_size
            except OSError:
                size_bytes = 0
            rel = fpath.relative_to(adapter_dir)
            rows.append({
                "file": str(rel),
                "size_bytes": size_bytes,
                "size_mb": size_bytes / (1024 * 1024),
            })
    return rows


def find_adapter_file(adapter_dir: Path) -> tuple[Path | None, str]:
    """Find lora_state_dict.pt or adapter_model.safetensors. Returns (path, 'pt'|'safetensors')."""
    adapter_dir = Path(adapter_dir).resolve()
    pt_path = adapter_dir / "lora_state_dict.pt"
    sf_path = adapter_dir / "adapter_model.safetensors"
    if pt_path.is_file():
        return pt_path, "pt"
    if sf_path.is_file():
        return sf_path, "safetensors"
    return None, ""


def load_lora_state(path: Path, fmt: str):
    """Load LoRA state from .pt or safetensors."""
    if fmt == "pt":
        import torch
        return torch.load(path, map_location="cpu", weights_only=True)
    if fmt == "safetensors":
        from safetensors.torch import load_file
        return load_file(path)
    raise ValueError(f"Unknown format: {fmt}")


def tensor_memory_bytes(tensor) -> int:
    """Estimate memory for a tensor (numel * dtype bytes)."""
    import torch
    dt = tensor.dtype
    if dt == torch.float32:
        return tensor.numel() * 4
    if dt == torch.float16 or dt == torch.bfloat16:
        return tensor.numel() * 2
    if dt == torch.float64:
        return tensor.numel() * 8
    return tensor.numel() * 4  # assume float32 for unknown


def report_tensor_sizes(lora_state) -> list[dict]:
    """Extract tensor name, shape, numel, memory_bytes."""
    rows = []
    for name, tensor in lora_state.items():
        shape = tuple(tensor.shape)
        numel = tensor.numel()
        mem = tensor_memory_bytes(tensor)
        rows.append({
            "tensor_name": name,
            "shape": str(shape),
            "numel": numel,
            "memory_bytes": mem,
        })
    return rows


def main() -> None:
    default_dir = Path(__file__).resolve().parent / "sft_humaneval_output_v0" / "lora_adapters"
    parser = argparse.ArgumentParser(
        description="Report disk sizes and optionally tensor sizes for LoRA adapter directory."
    )
    parser.add_argument(
        "adapter_dir",
        nargs="?",
        default=str(default_dir),
        help=f"Path to lora_adapters directory (default: {default_dir})",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Also load .pt/safetensors and report tensor stats and load time",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each tensor name and shape",
    )
    parser.add_argument(
        "--csv",
        metavar="OUTPUT.csv",
        default=None,
        help="Write results to CSV file",
    )
    args = parser.parse_args()

    adapter_dir = Path(args.adapter_dir).resolve()
    if not adapter_dir.is_dir():
        print(f"Error: not a directory: {adapter_dir}", file=sys.stderr)
        sys.exit(1)

    csv_rows_disk = []
    csv_rows_tensors = []

    # 1. Disk sizes
    print("=== Disk sizes (lora_adapters directory) ===")
    print(f"  Path: {adapter_dir}\n")
    rows = report_disk_sizes(adapter_dir)
    total_bytes = 0
    for r in rows:
        total_bytes += r["size_bytes"]
        print(f"  {r['file']}: {r['size_bytes']:,} bytes ({r['size_mb']:.2f} MB)")
        csv_rows_disk.append(r)
    print(f"\n  Total: {total_bytes:,} bytes ({total_bytes / (1024 * 1024):.2f} MB)\n")

    # 2. Load tensors (optional)
    if args.load:
        adapter_path, fmt = find_adapter_file(adapter_dir)
        if not adapter_path or not fmt:
            print("  No lora_state_dict.pt or adapter_model.safetensors found. Skipping load.")
        else:
            print(f"=== Loading: {adapter_path.name} (format: {fmt}) ===")
            t0 = time.perf_counter()
            try:
                lora_state = load_lora_state(adapter_path, fmt)
            except Exception as e:
                print(f"  Error loading: {e}", file=sys.stderr)
                sys.exit(1)
            elapsed = time.perf_counter() - t0
            print(f"  Load time: {elapsed:.2f} seconds\n")

            tensor_rows = report_tensor_sizes(lora_state)
            total_numel = sum(r["numel"] for r in tensor_rows)
            total_mem = sum(r["memory_bytes"] for r in tensor_rows)

            print("=== Tensor summary ===")
            print(f"  Number of tensors: {len(tensor_rows)}")
            print(f"  Total elements: {total_numel:,}")
            print(f"  Total memory (est.): {total_mem:,} bytes ({total_mem / (1024 * 1024):.2f} MB)\n")

            if args.verbose:
                print("=== Per-tensor (name, shape, numel, memory_bytes) ===")
                for r in tensor_rows:
                    print(f"  {r['tensor_name']}: {r['shape']}  numel={r['numel']:,}  mem={r['memory_bytes']:,} B")
                print()

            csv_rows_tensors = tensor_rows

    # 3. CSV output
    if args.csv:
        out_path = Path(args.csv)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "size_bytes", "size_mb"])
            for r in csv_rows_disk:
                w.writerow([r["file"], r["size_bytes"], f"{r['size_mb']:.6f}"])
            if csv_rows_tensors:
                w.writerow([])  # blank line
                w.writerow(["tensor_name", "shape", "numel", "memory_bytes"])
                for r in csv_rows_tensors:
                    w.writerow([r["tensor_name"], r["shape"], r["numel"], r["memory_bytes"]])
        print(f"Wrote CSV to {out_path}")


if __name__ == "__main__":
    main()
