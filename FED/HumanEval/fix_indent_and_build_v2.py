"""
Fix indentation errors in hallucinated canonical_solution and write human_eval_sft_ready_v2.csv.

Pattern: inside a block (after a line ending with ':'), first line has indent A, lines 2..end have B.
- If A > B: first line is over-indented (e.g. 12 vs 8) -> reduce first line to B.
- If A < B: lines 2..end are over-indented (e.g. 4 vs 8) -> subtract (B - A) from all lines with indent >= B.
Applied per block (after each line ending with ':') then to the whole body after docstring.
"""

import pandas as pd
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "human_eval_sft_ready.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "human_eval_sft_ready_v2.csv")


def indent_len(ln: str) -> int:
    return len(ln) - len(ln.lstrip())


def fix_indent_offset_in_lines(lines: list, start: int, end: int) -> None:
    """In-place fix for lines[start:end]: first non-empty vs rest offset."""
    region = [(i, lines[i]) for i in range(start, end) if i < len(lines) and lines[i].strip()]
    if len(region) < 2:
        return
    i1, line1 = region[0]
    i2, line2 = region[1]
    ind1 = indent_len(line1)
    ind2 = indent_len(line2)
    if ind1 == ind2:
        return
    if ind1 > ind2:
        # First line over-indented -> reduce to ind2
        lines[i1] = " " * ind2 + line1.lstrip()
    else:
        # Lines 2..end over-indented -> subtract (ind2 - ind1) from lines with indent >= ind2
        delta = ind2 - ind1
        for j in range(start, end):
            if j >= len(lines) or not lines[j].strip():
                continue
            curr = indent_len(lines[j])
            if curr >= ind2:
                new_indent = max(0, curr - delta)
                lines[j] = " " * new_indent + lines[j].lstrip()


def get_body_start_index(lines: list) -> int:
    """Index after which the function body starts (after docstring)."""
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('"""') or s.startswith("'''"):
            j = i + 1
            while j < len(lines):
                if '"""' in lines[j] or "'''" in lines[j]:
                    return j + 1
                j += 1
            return j
    return 0


def fix_body_indentation(text: str) -> str:
    """Fix offset indentation: per block after ':', then whole body first vs rest."""
    if not text or pd.isna(text):
        return text
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    body_start = get_body_start_index(lines)
    n = len(lines)

    # 1) Fix per block: after each line ending with ':'
    i = body_start
    while i < n:
        line = lines[i]
        if line.rstrip().endswith(":"):
            block_indent = indent_len(line)
            j = i + 1
            while j < n:
                if lines[j].strip() and indent_len(lines[j]) <= block_indent:
                    break
                j += 1
            fix_indent_offset_in_lines(lines, i + 1, j)
            i = j
        else:
            i += 1

    # 2) Fix whole body: first vs second non-empty line
    body_lines = lines[body_start:]
    non_empty = [(ii, ln) for ii, ln in enumerate(body_lines) if ln.strip()]
    if len(non_empty) >= 2:
        i1, line1 = non_empty[0]
        i2, line2 = non_empty[1]
        ind1 = indent_len(line1)
        ind2 = indent_len(line2)
        if ind1 != ind2:
            if ind1 > ind2:
                body_lines[i1] = " " * ind2 + line1.lstrip()
            else:
                delta = ind2 - ind1
                for j, ln in enumerate(body_lines):
                    if ln.strip() and indent_len(ln) >= ind2:
                        curr = indent_len(ln)
                        body_lines[j] = " " * max(0, curr - delta) + ln.lstrip()
        lines = lines[:body_start] + body_lines

    return "\n".join(lines)


def main():
    df = pd.read_csv(CSV_PATH)
    mask = df["status"] == "hallucinated"
    fixed = df["canonical_solution"].astype(str).copy()
    fixed[mask] = fixed[mask].apply(fix_body_indentation)
    df["canonical_solution"] = fixed
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df)} rows to {OUT_PATH}")
    print("Hallucinated rows updated with indentation fix.")


if __name__ == "__main__":
    main()
