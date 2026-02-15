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
    # Match patterns like "X.func() got an unexpected keyword argument"
    # or "func() takes N positional arguments but M were given"
    m = re.search(r"(?:\w+\.)?(\w+)\(\) (?:got an unexpected keyword argument|takes?\b)", msg)
    if m:
        return m.group(1)
    # Match "X.func() missing N required positional argument"
    m = re.search(r"(?:\w+\.)?(\w+)\(\) missing \d+ required", msg)
    if m:
        return m.group(1)
    return None


# ======================================================
# Helpers
# ======================================================

def rank(symbol, candidates):
    return get_close_matches(symbol, candidates, n=2, cutoff=0.85)


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
    """Only return suggestions when the symbol exactly matches a known
    KG function or class name.  Fuzzy matching local variable names
    (e.g. 'result', 'df') against the KG produces irrelevant noise."""
    out = []

    # Exact match in functions
    if symbol in KG["functions"]:
        node = KG["functions"][symbol]
        if node["node_type"] == "function":
            out.append(build_function(symbol, node))
        else:
            out.append(build_method(symbol, node))

    # Exact match in classes
    if symbol in KG["classes"]:
        out.append(build_class(symbol, KG["classes"][symbol]))

    return out[:2]


def suggest_attribute(cls, attr):
    out = []

    if cls in KG["classes"]:
        class_node = KG["classes"][cls]

        for m in rank(attr, class_node["methods"]):
            node = KG["functions"].get(m)
            if node:
                entry = build_method(m, node)
                # Override with the queried class so the suggestion
                # references the actual library/class, not a parent or
                # sibling class that the KG node may point to.
                entry["api"] = f"{cls}.{m}"
                entry["belongs_to"] = cls
                out.append(entry)

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
