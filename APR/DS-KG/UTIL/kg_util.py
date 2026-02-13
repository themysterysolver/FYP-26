import pandas as pd
import json
import re
import glob
import os
from difflib import get_close_matches

# ======================================================
# Locate project root (KG files live there)
# ======================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

# ======================================================
# Load ALL KG files
# ======================================================

def load_kgs():
    kg = {"functions": {}, "classes": {}}

    for file in glob.glob(os.path.join(BASE_DIR, "kg_*.json")):
        with open(file, "r", encoding="utf8") as f:
            data = json.load(f)
            kg["functions"].update(data.get("functions", {}))
            kg["classes"].update(data.get("classes", {}))

    return kg


KG = load_kgs()

print("Loaded functions:", len(KG["functions"]))
print("Loaded classes:", len(KG["classes"]))

# ======================================================
# Error detectors
# ======================================================

def detect_name_error(msg):
    m = re.search(r"name '(.+?)' is not defined", msg)
    return m.group(1) if m else None


def detect_attribute_error(msg):
    m = re.search(r"'(.+?)' object has no attribute '(.+?)'", msg)
    return m.groups() if m else None


def detect_type_error(msg):
    m = re.search(r"(\w+)\(", msg)
    return m.group(1) if m else None


# ======================================================
# Helpers
# ======================================================

def rank(symbol, candidates):
    return get_close_matches(symbol, candidates, n=2, cutoff=0.6)


def build_function(name, node):
    return {
        "api": f"{node.get('module','')}.{name}",
        "type": node["node_type"],
        "required_params": node["parameters"]["required"],
        "optional_params": node["parameters"]["optional"],
        "description": node.get("description", "")
    }


def build_method(name, node):
    return {
        "api": f"{node['belongs_to']}.{name}",
        "type": "method",
        "belongs_to": node["belongs_to"],
        "required_params": node["parameters"]["required"],
        "optional_params": node["parameters"]["optional"],
        "description": node.get("description", "")
    }


def build_class(name, node):
    return {
        "api": name,
        "type": "class",
        "methods": node.get("methods", [])[:10],
        "attributes": node.get("attributes", [])[:10],
        "description": node.get("description", "")
    }


# ======================================================
# Suggestion engines
# ======================================================

def suggest_name(symbol):
    out = []

    for m in rank(symbol, KG["functions"].keys()):
        node = KG["functions"][m]
        if node["node_type"] == "function":
            out.append(build_function(m, node))
        else:
            out.append(build_method(m, node))

    for c in rank(symbol, KG["classes"].keys()):
        out.append(build_class(c, KG["classes"][c]))

    return out[:2]


def suggest_attribute(cls, attr):
    out = []

    if cls in KG["classes"]:
        class_node = KG["classes"][cls]

        for m in rank(attr, class_node["methods"]):
            node = KG["functions"].get(m)
            if node:
                out.append(build_method(m, node))

        for a in rank(attr, class_node["attributes"]):
            out.append({
                "api": f"{cls}.{a}",
                "type": "attribute",
                "belongs_to": cls
            })

    return out[:2]


def suggest_type(func):
    out = []

    if func in KG["functions"]:
        node = KG["functions"][func]
        if node["node_type"] == "function":
            out.append(build_function(func, node))
        else:
            out.append(build_method(func, node))

    return out[:2]


# ======================================================
# Main
# ======================================================

def generate_suggestions(csv_path):
    df = pd.read_csv(csv_path)

    results = []

    for _, row in df.iterrows():
        msg = str(row.get("status", ""))

        suggestion = []

        name = detect_name_error(msg)
        if name:
            suggestion = suggest_name(name)

        if not suggestion:
            attr = detect_attribute_error(msg)
            if attr:
                suggestion = suggest_attribute(attr[0], attr[1])

        if not suggestion:
            func = detect_type_error(msg)
            if func:
                suggestion = suggest_type(func)

        results.append(json.dumps(suggestion, ensure_ascii=False))

    df["suggestion"] = results
    df[["task_id", "status", "suggestion"]].to_csv(
        "task_status_suggestions.csv",
        index=False
    )

    print("\n✅ task_status_suggestions.csv generated")


if __name__ == "__main__":
    generate_suggestions("task_status.csv")
