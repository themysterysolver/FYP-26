"""One-off: build Verify_DS1000_Adapter_Windows.ipynb (JSON-only config) from FED_AVG_CHECK_TT copy."""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
SRC = os.path.join(REPO, "FED_AVG_CHECK_TT", "Verify_DS1000_Adapter_Windows.ipynb")
DST = os.path.join(ROOT, "Verify_DS1000_Adapter_Windows.ipynb")

PATH_CELL = r'''import os
import json
import zipfile

try:
    NOTEBOOK_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    NOTEBOOK_DIR = os.getcwd()

# All inputs live in the same folder as this notebook: JSON, baseline CSV, lora_adapters/
VERIFICATION_JSON = os.path.join(NOTEBOOK_DIR, "verification_task_ids.json")
if not os.path.isfile(VERIFICATION_JSON):
    raise FileNotFoundError(
        "Place verification_task_ids.json next to this notebook:\\n" + VERIFICATION_JSON
    )
with open(VERIFICATION_JSON, "r", encoding="utf-8") as f:
    _manifest = json.load(f)

MANIFEST_TASK_IDS = _manifest.get("task_ids") or []
if not MANIFEST_TASK_IDS:
    raise ValueError("verification_task_ids.json must contain a non-empty task_ids list.")

# Compare run to expected[this_key] — default for FedErrorAvg folder; use "fedavg_adapter" for FedAvg LoRA
VERIFICATION_EXPECT_KEY = _manifest.get("verification_expect_key", "federroravg_adapter")
VERIFICATION_JSON_PATH = VERIFICATION_JSON  # alias for manifest check cell at end

BASELINE_CSV_PATH = os.path.join(NOTEBOOK_DIR, "ds1000_pipeline_output.csv")
ADAPTER_ZIP_OR_DIR = os.path.join(NOTEBOOK_DIR, "lora_adapters")

if os.path.isfile(ADAPTER_ZIP_OR_DIR) and ADAPTER_ZIP_OR_DIR.lower().endswith(".zip"):
    ADAPTER_PATH = os.path.join(NOTEBOOK_DIR, "lora_adapters_extracted")
    os.makedirs(ADAPTER_PATH, exist_ok=True)
    with zipfile.ZipFile(ADAPTER_ZIP_OR_DIR, "r") as z:
        z.extractall(ADAPTER_PATH)
    subdirs = [d for d in os.listdir(ADAPTER_PATH) if os.path.isdir(os.path.join(ADAPTER_PATH, d))]
    if len(subdirs) == 1 and os.path.isfile(os.path.join(ADAPTER_PATH, subdirs[0], "adapter_config.json")):
        ADAPTER_PATH = os.path.join(ADAPTER_PATH, subdirs[0])
else:
    ADAPTER_PATH = ADAPTER_ZIP_OR_DIR
    if os.path.isdir(ADAPTER_PATH):
        subdirs = [d for d in os.listdir(ADAPTER_PATH) if os.path.isdir(os.path.join(ADAPTER_PATH, d))]
        if len(subdirs) == 1 and os.path.isfile(os.path.join(ADAPTER_PATH, subdirs[0], "adapter_config.json")):
            ADAPTER_PATH = os.path.join(ADAPTER_PATH, subdirs[0])

print("verification_task_ids.json:", VERIFICATION_JSON)
print("task_ids:", len(MANIFEST_TASK_IDS), "— expect key:", VERIFICATION_EXPECT_KEY)
print("Baseline CSV:", BASELINE_CSV_PATH)
print("Adapters at:", ADAPTER_PATH)
'''

BASELINE_CELL = r'''# Baseline rows for tasks listed in verification_task_ids.json only (same folder as notebook)
import pandas as pd

df_baseline = pd.read_csv(BASELINE_CSV_PATH)
df_baseline["task_id"] = df_baseline["task_id"].astype(str)
sid = [str(x) for x in MANIFEST_TASK_IDS]
missing = [t for t in sid if t not in set(df_baseline["task_id"])]
if missing:
    raise ValueError(f"Baseline CSV missing task_ids: {missing}")

df_baseline = df_baseline[df_baseline["task_id"].isin(sid)].copy()
df_baseline = df_baseline.set_index("task_id").loc[sid].reset_index()

passed_baseline = (df_baseline["status"] == "passed").sum()
total_baseline = len(df_baseline)
pass_rate_baseline = passed_baseline / total_baseline if total_baseline else 0
print(f"Baseline (JSON subset): {passed_baseline}/{total_baseline} passed, pass@1 = {pass_rate_baseline:.2%}")
'''

MD4 = """## 4. Baseline CSV + JSON task list\n\n`verification_task_ids.json` (same folder as this notebook) lists `task_ids`. `ds1000_pipeline_output.csv` must contain those rows. No `final_dataset_v2_test.csv` required for this notebook.\n"""

MD0 = """# DS1000 adapter verification (JSON-only config)\n\n**Upload together in one folder:** this `.ipynb`, `verification_task_ids.json`, `ds1000_pipeline_output.csv`, and your LoRA in `lora_adapters/` (or `lora_adapters.zip`).\n\nOptional in JSON: `\"verification_expect_key\": \"fedavg_adapter\"` or `\"federroravg_adapter\"` (default here: FedErrorAvg). The notebook compares the run to `expected[verification_expect_key]`.\n"""


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        nb = json.load(f)
    cells = nb["cells"]

    # Drop shell junk cells
    cells = [c for c in cells if "".join(c.get("source", [])).strip() not in ("!cd loara_adapters", "!ls")]

    # Patch cells by section headers
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        if "## 2. Paths" in src and c["cell_type"] == "markdown":
            # next code cell is paths
            if i + 1 < len(cells) and cells[i + 1]["cell_type"] == "code":
                cells[i + 1]["source"] = [PATH_CELL]
                cells[i + 1]["outputs"] = []
                cells[i + 1]["execution_count"] = None
        if "## 4. Load baseline from CSV" in src or "## 4. Load baseline" in src:
            c["source"] = [MD4]
        if src.startswith("# Load DS1000 ids from the generated"):
            cells[i] = {
                "cell_type": "code",
                "metadata": {},
                "source": [BASELINE_CELL],
                "outputs": [],
                "execution_count": None,
            }
        if src.startswith("# Optional subset: load"):
            cells[i] = {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "_Removed: subset is always loaded from `verification_task_ids.json` in the paths cell._\n"
                ],
            }
        if "# DS1000 Adapter Verification v2" in src and c["cell_type"] == "markdown":
            c["source"] = [MD0]

    # Remove the markdown-only stub if we want a cleaner nb - replace with empty delete
    nb["cells"] = [c for c in cells if not (
        c["cell_type"] == "markdown"
        and "_Removed: subset" in "".join(c.get("source", []))
    )]

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("Wrote", DST)


if __name__ == "__main__":
    main()
