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
import re
import types

# Configuration for important submodules per library
LIBRARY_SUBMODULES = {
    "scipy": ["stats", "linalg", "optimize", "integrate", "signal", "sparse"],
    "sklearn": [
        "linear_model", "tree", "ensemble", "svm", "neighbors",
        "preprocessing", "metrics", "model_selection", "datasets"
    ],
}

#loading library
def load_library(lib_name):
    return importlib.import_module(lib_name)

#init KG structure
def init_kg(lib_name):
    return {
        "library": lib_name,
        "version": "runtime", #we can replace this with version if needed
        "modules": {},
        "classes": {},
        "functions": {}
    }

def parse_signature_from_description(description):
    """
    Parse function signature from docstring when inspect.signature fails.
    Handles patterns like:
    - zeros(shape, dtype=float, order='C', *, like=None)
    - array(object, dtype=None, *, copy=True, ...)
    - funcname(param1[, param2[, param3]])  # numpy optional style
    """
    if not description:
        return [], []
    
    # Extract first line which usually contains signature
    first_line = description.split('\n')[0].strip()
    
    # Pattern to match: funcname(params...)
    match = re.search(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\((.*?)\)(?:\s|$)', first_line)
    if not match:
        return [], []
    
    params_str = match.group(1)
    if not params_str or params_str.strip() in ['', '...']:
        return [], []
    
    required = []
    optional = []
    
    # Split by comma, but be careful with nested structures
    params = []
    depth = 0
    current = []
    for char in params_str + ',':
        if char in '([{':
            depth += 1
            current.append(char)
        elif char in ')]}':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            param = ''.join(current).strip()
            if param:
                params.append(param)
            current = []
        else:
            current.append(char)
    
    # Process each parameter
    for param in params:
        # Skip * (keyword-only separator) and / (positional-only separator)
        if param in ['*', '/', '**kwargs', '*args']:
            continue
        
        # Remove numpy optional brackets: [param] or [, param]
        param = re.sub(r'^\[,?\s*', '', param)
        param = re.sub(r'\]$', '', param)
        param = param.strip()
        
        if not param or param == '...':
            continue
        
        # Extract parameter name (before = or space)
        param_name = re.split(r'[=\s]', param)[0].strip()
        
        # Skip invalid names
        if not param_name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', param_name):
            continue
        
        # Check if it has a default value (optional parameter)
        if '=' in param:
            optional.append(param_name)
        else:
            required.append(param_name)
    
    return required, optional

#extract function signature and optional parameters
def get_signature(obj):
    # Try inspect.signature first (works for Python functions)
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
        pass
    
    # Fallback: parse from docstring (for C builtins like numpy functions)
    try:
        doc = inspect.getdoc(obj)
        if doc:
            required, optional = parse_signature_from_description(doc)
            if required or optional:
                return required, optional
    except Exception:
        pass
    
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

def get_important_submodules(lib_name):
    """Return list of important submodules to explore for a library."""
    return LIBRARY_SUBMODULES.get(lib_name, [])

def extract_from_submodule(parent_lib_name, submodule_name, kg):
    """
    Extract functions and classes from a submodule.
    E.g., extract from scipy.stats when parent is scipy
    """
    full_module_name = f"{parent_lib_name}.{submodule_name}"
    
    try:
        submodule = importlib.import_module(full_module_name)
    except Exception as e:
        print(f"    Warning: Could not import {full_module_name}: {e}")
        return
    
    # Track what we're adding to avoid duplicates
    added_functions = set()
    added_classes = set()
    
    # Extract functions from submodule
    for name in dir(submodule):
        # Skip private members
        if name.startswith('_'):
            continue
        
        try:
            obj = getattr(submodule, name)
        except Exception:
            continue
        
        # Extract functions
        if isinstance(obj, (types.FunctionType, types.BuiltinFunctionType)):
            # Create unique key with module path to avoid conflicts
            func_key = f"{submodule_name}.{name}"
            
            if func_key not in kg["functions"] and func_key not in added_functions:
                required, optional = get_signature(obj)
                
                kg["functions"][func_key] = {
                    "node_type": "function",
                    "module": full_module_name,
                    "parameters": {
                        "required": required,
                        "optional": optional
                    },
                    "returns": "unknown",
                    "description": get_short_doc(obj),
                    "example": ""
                }
                added_functions.add(func_key)
        
        # Extract classes
        elif inspect.isclass(obj):
            class_key = f"{submodule_name}.{name}"
            
            if class_key not in kg["classes"] and class_key not in added_classes:
                kg["classes"][class_key] = {
                    "node_type": "class",
                    "module": full_module_name,
                    "methods": [],
                    "attributes": [],
                    "description": get_short_doc(obj)
                }
                added_classes.add(class_key)
                
                # Extract class members
                for attr_name in dir(obj):
                    if attr_name.startswith("__"):
                        continue
                    
                    try:
                        attr = getattr(obj, attr_name)
                    except Exception:
                        continue
                    
                    if callable(attr):
                        method_key = f"{class_key}.{attr_name}"
                        if method_key not in kg["functions"]:
                            required, optional = get_signature(attr)
                            
                            kg["functions"][method_key] = {
                                "node_type": "method",
                                "belongs_to": class_key,
                                "parameters": {
                                    "required": required,
                                    "optional": optional
                                },
                                "returns": "unknown",
                                "description": get_short_doc(attr),
                                "example": ""
                            }
                            kg["classes"][class_key]["methods"].append(attr_name)
                    else:
                        kg["classes"][class_key]["attributes"].append(attr_name)
#driver code
def build_kg(lib_name):
    lib = load_library(lib_name)
    kg = init_kg(lib_name)

    # Extract from main module
    extract_functions(lib, kg)
    extract_classes(lib, kg)
    extract_class_members(lib, kg)
    extract_submodules(lib, kg)
    
    # Extract from important submodules (scipy, sklearn)
    submodules = get_important_submodules(lib_name)
    if submodules:
        print(f"  Exploring {len(submodules)} submodules...")
        for submod_name in submodules:
            try:
                extract_from_submodule(lib_name, submod_name, kg)
            except Exception as e:
                print(f"    Warning: Failed to extract {lib_name}.{submod_name}: {e}")

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