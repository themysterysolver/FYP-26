

import sys
import os
import json
import ast
import pandas as pd



SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "UTIL"))

from kg_util import (
    suggest_type,
    suggest_attribute,
    suggest_name,
    detect_type_error,
    detect_attribute_error,
    detect_name_error,
)



PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))




def safe_literal_eval(val):
    """Parse a Python literal string (lib_info column). Returns list or []."""
    if pd.isna(val) or not str(val).strip():
        return []
    try:
        parsed = ast.literal_eval(str(val))
        return parsed if isinstance(parsed, list) else []
    except (ValueError, SyntaxError):
        return []


def safe_json_loads(val):
    """Parse a JSON string (dynamic_info column). Returns dict or {}."""
    if pd.isna(val) or not str(val).strip():
        return {}
    try:
        parsed = json.loads(str(val))
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}





def get_suggestion(row):
    """Return a list of KG suggestion dicts for a single row."""
    error_type = str(row.get("error_type", "")).strip()

    # ----- Library API errors (parsed from lib_info) -----
    if error_type.startswith("lib:"):
        lib_entries = safe_literal_eval(row.get("lib_info"))
        suggestions = []

        for entry in lib_entries:
            etype = entry.get("type", "")

            if etype == "type_error":
                func = entry.get("function", "")
                if func:
                    suggestions.extend(suggest_type(func))

            elif etype == "attribute_error":
                obj = entry.get("object", "")
                attr = entry.get("attribute", "")
                if obj and attr:
                    suggestions.extend(suggest_attribute(obj, attr))

            elif etype == "name_error":
                name = entry.get("name", "")
                if name:
                    suggestions.extend(suggest_name(name))

            # lib: module_not_found -- no KG engine for this yet

        return suggestions

    # ----- Dynamic execution errors (parsed from dynamic_info) -----
    if error_type.startswith("dynamic:"):
        dynamic = safe_json_loads(row.get("dynamic_info"))
        msg = dynamic.get("error_message", "")
        if not msg:
            return []

        if "TypeError" in error_type:
            func = detect_type_error(msg)
            if func:
                return suggest_type(func)

        elif "AttributeError" in error_type:
            parsed = detect_attribute_error(msg)
            if parsed:
                return suggest_attribute(parsed[0], parsed[1])

        elif "NameError" in error_type:
            symbol = detect_name_error(msg)
            if symbol:
                return suggest_name(symbol)

        return []

    # ----- AST / CFG / other errors -- no KG relevance -----
    return []




def main():
    csv_path = os.path.join(PROJECT_ROOT, "patched_code.csv")
    out_path = os.path.join(SCRIPT_DIR, "KG_SUGGESTIONS.csv")

    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path)
    print(f"  Total rows: {len(df)}")

    # Generate suggestions per row
    suggestion_list = []
    hit_count = 0

    for idx, row in df.iterrows():
        suggestions = get_suggestion(row)

        # Deduplicate by api name
        seen = set()
        unique = []
        for s in suggestions:
            key = s.get("api", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(s)

        if unique:
            hit_count += 1

        suggestion_list.append(json.dumps(unique, ensure_ascii=False))

    df["kg_suggestion"] = suggestion_list

    # Write output
    df.to_csv(out_path, index=False)

    print(f"\n  Rows with KG suggestions: {hit_count} / {len(df)}")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
