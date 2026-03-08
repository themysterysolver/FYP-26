"""
Fix indentation in hallucinated canonical_solution by calling Gemini API.

Requires:
  pip install google-genai pandas

Set your API key:
  $env:GOOGLE_API_KEY="your_key"   (PowerShell)
  set GOOGLE_API_KEY=your_key      (Windows cmd)
  export GOOGLE_API_KEY=your_key   (Linux/Mac)

Or use GEMINI_API_KEY. Get a key at: https://aistudio.google.com/apikey

Rate limits (429): The script waits on quota errors and retries. If free-tier daily
quota is exceeded (limit: 0), wait until the next day or enable billing.
Use --delay 3 to add a pause between requests and avoid per-minute limits.

Output: human_eval_sft_ready_gemini.csv (saved after each row so you can resume).
"""

import os
import re
import time
import pandas as pd

try:
    from google import genai
    from google.genai import types
    try:
        from google.genai.errors import ClientError
    except ImportError:
        ClientError = None  # type: ignore
except ImportError:
    raise ImportError("Install with: pip install google-genai")

CSV_PATH = os.path.join(os.path.dirname(__file__), "human_eval_sft_ready.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "human_eval_sft_ready_gemini.csv")

# Model must be valid for your API (e.g. gemini-2.0-flash, gemini-2.5-flash). Override with env GEMINI_MODEL or --model.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

SYSTEM_PROMPT = """You are a code formatter. Your only job is to fix Python indentation.

Rules:
- Use exactly 4 spaces per indentation level.
- Preserve all logic, imports, docstrings, and text. Change only leading whitespace.
- Return ONLY the raw Python code. No markdown code fences, no explanation, no preamble."""


def extract_code_from_response(text: str) -> str:
    """Remove markdown code block if present."""
    if not text:
        return ""
    text = text.strip()
    m = re.search(r"```(?:python)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _parse_retry_seconds(error_message: str) -> float:
    """Parse 'Please retry in 21.37s' or similar from 429 error. Returns default 25 if not found."""
    m = re.search(r"retry\s+in\s+([\d.]+)\s*s", error_message, re.I)
    if m:
        return max(1.0, float(m.group(1)) + 1)
    return 25.0


def fix_code_with_gemini(code: str, client, max_retries: int = 5) -> str:
    """Send code to Gemini and return rewritten code with proper indentation. Handles 429 with wait-and-retry."""
    if not code or pd.isna(code):
        return code
    code = str(code).replace("\r\n", "\n").replace("\r", "\n")
    user_message = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Fix the indentation of this Python code (return only the code):\n\n{code}"
    )
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                ),
            )
            text = getattr(response, "text", None)
            if text:
                return extract_code_from_response(text)
        except Exception as e:
            is_429 = (
                (ClientError is not None and isinstance(e, ClientError) and (getattr(e, "status_code", None) == 429 or (e.args and e.args[0] == 429)))
                or "429" in str(e)
                or "RESOURCE_EXHAUSTED" in str(e)
            )
            if is_429:
                wait = _parse_retry_seconds(str(e))
                if attempt < max_retries:
                    print(f"  rate limited, waiting {wait:.0f}s ...", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"  quota exceeded (wait ~{wait:.0f}s or try later). Re-run to resume; progress is saved.")
                    return code
            else:
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    print(f"  Gemini error: {e}")
                    return code
        time.sleep(0.5)
    return code


def main(csv_path: str | None = None, out_path: str | None = None, delay: float = 2.0):
    csv_path = csv_path or CSV_PATH
    out_path = out_path or OUT_PATH
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Set GOOGLE_API_KEY or GEMINI_API_KEY (e.g. from https://aistudio.google.com/apikey)")
        return
    client = genai.Client(api_key=api_key)
    print(f"Using model: {GEMINI_MODEL}")

    df = pd.read_csv(csv_path)
    mask = df["status"] == "hallucinated"
    n = mask.sum()
    delay = float(os.environ.get("GEMINI_DELAY", str(delay)))
    print(f"Fixing indentation for {n} hallucinated rows via Gemini (delay={delay}s between requests)...")
    fixed = df["canonical_solution"].astype(str).copy()
    for idx in df.index[mask]:
        task_id = df.loc[idx, "task_id"]
        code = df.loc[idx, "canonical_solution"]
        print(f"  {task_id} ...", end=" ", flush=True)
        out = fix_code_with_gemini(code, client)
        fixed.loc[idx] = out
        print("ok", flush=True)
        df["canonical_solution"] = fixed
        df.to_csv(out_path, index=False)
        if delay > 0:
            time.sleep(delay)
    df["canonical_solution"] = fixed
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Fix indentation via Gemini API")
    p.add_argument("--input", default=CSV_PATH, help="Input CSV (default: human_eval_sft_ready.csv)")
    p.add_argument("--output", default=OUT_PATH, help="Output CSV (default: human_eval_sft_ready_gemini.csv)")
    p.add_argument("--model", default=GEMINI_MODEL, help=f"Model name (default: {GEMINI_MODEL})")
    p.add_argument("--delay", type=float, default=2.0, help="Seconds to wait between API calls (default: 2, use 0 to disable)")
    args = p.parse_args()
    GEMINI_MODEL = args.model
    main(csv_path=args.input, out_path=args.output, delay=args.delay)
