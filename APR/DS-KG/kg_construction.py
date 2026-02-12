"""
DS-1000 Library Knowledge Graph Construction
--------------------------------------------
• Builds KG using dir(), inspect(), help()
• Extracts modules, classes, functions, methods, attributes
• Stores executable truth in JSON
"""

import importlib
import inspect
import json
import types

#loading library
def load_library(lib_name):
    return importlib.import_module(lib_name)

#nit KG structure
def init_kg(lib_name):
    return {
        "library": lib_name,
        "version": "runtime", #we can replace this with version if needed
        "modules": {},
        "classes": {},
        "functions": {}
    }

#extract functiona signature and optional parameters and actual
def get_signature(obj):
    try:
        sig = inspect.signature(obj)
        required, optional = [], []

        for name, param in sig.parameters.items():
            if param.default is inspect.Parameter.empty:
                required.append(name)
            else:
                optional.append(name)

        return required, optional
    except Exception:
        return [], []


def get_short_doc(obj):
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    return doc.split("\n")[0]

#extract functions in the module
def extract_functions(lib, kg):
    for name in dir(lib):
        try:
            obj = getattr(lib, name)
        except Exception:
            continue

        if isinstance(obj, (types.FunctionType, types.BuiltinFunctionType)):
            required, optional = get_signature(obj)

            kg["functions"][name] = {
                "node_type": "function",
                "module": lib.__name__,
                "parameters": {
                    "required": required,
                    "optional": optional
                },
                "returns": "unknown",
                "description": get_short_doc(obj),
                "example": ""
            }

#extract class types in the module
def extract_classes(lib, kg):
    for name in dir(lib):
        try:
            obj = getattr(lib, name)
        except Exception:
            continue

        if inspect.isclass(obj):
            kg["classes"][name] = {
                "node_type": "class",
                "module": lib.__name__,
                "methods": [],
                "attributes": [],
                "description": get_short_doc(obj)
            }

#extract methods and attributes of the classes
def extract_class_members(lib, kg):
    for class_name, class_node in kg["classes"].items():
        try:
            cls = getattr(lib, class_name)
        except Exception:
            continue

        for attr_name in dir(cls):
            if attr_name.startswith("__"):
                continue

            try:
                attr = getattr(cls, attr_name)
            except Exception:
                continue

            # METHOD
            if callable(attr):
                required, optional = get_signature(attr)

                kg["functions"][attr_name] = {
                    "node_type": "method",
                    "belongs_to": class_name,
                    "parameters": {
                        "required": required,
                        "optional": optional
                    },
                    "returns": "unknown",
                    "description": get_short_doc(attr),
                    "example": ""
                }

                class_node["methods"].append(attr_name)

            # ATTRIBUTE
            else:
                class_node["attributes"].append(attr_name)

#extracting sub-modules
def extract_submodules(lib, kg):
    for name in dir(lib):
        try:
            obj = getattr(lib, name)
        except Exception:
            continue

        if inspect.ismodule(obj):
            kg["modules"][name] = {
                "node_type": "module",
                "parent": lib.__name__
            }
#driver code
def build_kg(lib_name):
    lib = load_library(lib_name)
    kg = init_kg(lib_name)

    extract_functions(lib, kg)
    extract_classes(lib, kg)
    extract_class_members(lib, kg)
    extract_submodules(lib, kg)

    return kg

#saving
def save_kg(kg, path):
    with open(path, "w") as f:
        json.dump(kg, f, indent=2)

#main
if __name__ == "__main__":
    DS1000_LIBRARIES = [
        "numpy",
        "pandas",
        "matplotlib.pyplot",
        "seaborn",
        "scipy",
        "sklearn",
        "statsmodels.api"
    ]

    for lib_name in DS1000_LIBRARIES:
        try:
            print(f"\nBuilding KG for {lib_name} ...")

            kg = build_kg(lib_name)

            file_name = f"kg_{lib_name.replace('.', '_')}.json"
            save_kg(kg, file_name)

            print(f"Saved{file_name}")

        except Exception as e:
            print(f"Failed for {lib_name}: {e}")

    print("\n completed!!")