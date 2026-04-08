"""
Extract DS1000 SFT training loss table from the saved Jupyter notebook output.

Reads HTML logged by Hugging Face Trainer (Step / Training Loss) and writes CSV.

Usage:
  python extract_ds1000_sft_loss.py
  python extract_ds1000_sft_loss.py --notebook path/to/notebook.ipynb
"""

import argparse
import json
import os
import re

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIS_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(VIS_DIR)
DEFAULT_NOTEBOOK = os.path.join(
    PROJECT_ROOT,
    "FED-CONS-FINAL - TT",
    "DS1000",
    "SFT_LoRA_Adapters_Windows_try_fix.ipynb",
)
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "ds1000_sft_training_loss.csv")
DEFAULT_SUMMARY = os.path.join(SCRIPT_DIR, "ds1000_sft_run_summary.json")

ROW_RE = re.compile(
    r"<tr>\s*<td>(\d+)</td>\s*<td>([\d.]+)</td>\s*</tr>",
    re.IGNORECASE,
)
EPOCH_PROGRESS_RE = re.compile(r"Epoch\s+(\d+)/(\d+)", re.IGNORECASE)
MAX_STEP_RE = re.compile(r"\[(\d+)/(\d+)")
TRAIN_OUTPUT_RE = re.compile(
    r"TrainOutput\(global_step=(\d+),\s*training_loss=([\d.eE+-]+)",
)


def _cell_source(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return str(src)


def find_train_cell_outputs(nb: dict) -> tuple[list[dict] | None, str | None]:
    """Return outputs of the code cell that runs trainer.train()."""
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = _cell_source(cell)
        lines = [ln.strip() for ln in src.splitlines()]
        if any(ln == "trainer.train()" or ln.startswith("trainer.train(") for ln in lines):
            return cell.get("outputs", []), src
    return None, None


def collect_training_html(outputs: list) -> str:
    chunks: list[str] = []
    for out in outputs:
        if out.get("output_type") != "display_data":
            continue
        data = out.get("data") or {}
        html = data.get("text/html")
        if not html:
            continue
        if isinstance(html, list):
            chunks.append("".join(html))
        else:
            chunks.append(html)
    return "".join(chunks)


def collect_stream_text(outputs: list) -> str:
    parts: list[str] = []
    for out in outputs:
        if out.get("output_type") == "stream":
            text = out.get("text", "")
            if isinstance(text, list):
                parts.append("".join(text))
            else:
                parts.append(text)
        elif out.get("output_type") == "execute_result":
            data = out.get("data") or {}
            plain = data.get("text/plain")
            if isinstance(plain, list):
                parts.append("".join(plain))
            elif plain:
                parts.append(str(plain))
    return "".join(parts)


def parse_epoch_info(html: str) -> tuple[int, int] | None:
    """Return (current_epoch, total_epochs) from progress HTML, or None."""
    m = EPOCH_PROGRESS_RE.search(html)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_max_step(html: str) -> int | None:
    m = MAX_STEP_RE.search(html)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return b if a == b else b


def parse_train_output(stream: str) -> dict | None:
    m = TRAIN_OUTPUT_RE.search(stream)
    if not m:
        return None
    return {
        "global_step": int(m.group(1)),
        "training_loss": float(m.group(2)),
    }


def extract_loss_rows(html: str) -> list[tuple[int, float]]:
    rows: list[tuple[int, float]] = []
    for step_s, loss_s in ROW_RE.findall(html):
        rows.append((int(step_s), float(loss_s)))
    # de-dup preserve order
    seen = set()
    out: list[tuple[int, float]] = []
    for s, l in rows:
        if s in seen:
            continue
        seen.add(s)
        out.append((s, l))
    out.sort(key=lambda x: x[0])
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Extract DS1000 SFT loss from notebook.")
    p.add_argument("--notebook", default=DEFAULT_NOTEBOOK, help="Path to .ipynb")
    p.add_argument("--csv", default=DEFAULT_CSV, help="Output CSV path")
    p.add_argument("--summary", default=DEFAULT_SUMMARY, help="Output JSON summary path")
    args = p.parse_args()

    with open(args.notebook, encoding="utf-8") as f:
        nb = json.load(f)

    outputs, _src = find_train_cell_outputs(nb)
    if not outputs:
        raise SystemExit("Could not find a code cell that runs trainer.train().")

    html = collect_training_html(outputs)
    if not html or "Training Loss" not in html:
        raise SystemExit("No training loss HTML table in trainer.train() outputs.")

    stream = collect_stream_text(outputs)
    pairs = extract_loss_rows(html)
    if not pairs:
        raise SystemExit("Parsed zero loss rows from HTML.")

    epoch_info = parse_epoch_info(html)
    max_step_html = parse_max_step(html)
    max_step_data = max(s for s, _ in pairs)
    num_epochs = epoch_info[1] if epoch_info else None
    if num_epochs is None:
        # infer: common case 375 steps / 3 epochs
        if max_step_html and max_step_html % 125 == 0:
            num_epochs = max_step_html // 125
        else:
            num_epochs = 3

    global_max = max(max_step_data, max_step_html or 0)
    steps_per_epoch = global_max // num_epochs if num_epochs else 1
    if steps_per_epoch < 1:
        steps_per_epoch = 1

    rows = []
    for step, loss in pairs:
        ep = min((step - 1) // steps_per_epoch + 1, num_epochs)
        rows.append({"step": step, "epoch": ep, "training_loss": loss})

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(os.path.abspath(args.csv)) or ".", exist_ok=True)
    df.to_csv(args.csv, index=False)
    print(f"Wrote {len(df)} rows to {args.csv}")

    summary = {
        "notebook": os.path.abspath(args.notebook),
        "num_epochs": num_epochs,
        "steps_per_epoch": steps_per_epoch,
        "max_logged_step": max_step_data,
    }
    to = parse_train_output(stream)
    if to:
        summary.update(to)
    with open(args.summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {args.summary}")


if __name__ == "__main__":
    main()
