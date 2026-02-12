
We’ll do two parts:

1. **Architecture / Structure of `kg_numpy.json`**
2. **How your code generates each part**



---

# 🏗 PART 1 — Architecture of `kg_numpy.json`

Your KG file is a **hierarchical structural API graph serialized in JSON**.

Top-level structure:

```json
{
  "library": "numpy",
  "version": "runtime",
  "modules": { ... },
  "classes": { ... },
  "functions": { ... }
}
```

Let’s break this down.

---

## 🔹 1️⃣ Root Metadata

```json
"library": "numpy"
```

This defines the **root namespace**.

It represents:

```
Library Node
```

Conceptually:

```
numpy
```

---

```json
"version": "runtime"
```

This indicates the KG was built from the installed runtime.

(You can later replace this with `numpy.__version__`.)

---

# 📦 2️⃣ Modules Section

```json
"modules": {
  "random": {
    "node_type": "module",
    "parent": "numpy"
  }
}
```

This represents:

```
numpy.random
```

Architecture meaning:

* Entity type: Module
* Relationship: Library → HAS_MODULE → Module
* Stored using `"parent"`

Graph meaning:

```
numpy ──HAS_MODULE──> random
```

---

# 🏛 3️⃣ Classes Section

```json
"classes": {
  "ndarray": {
    "node_type": "class",
    "module": "numpy",
    "methods": [...],
    "attributes": [...],
    "description": "..."
  }
}
```

Architecture meaning:

* Entity type: Class
* Relationship: Module → HAS_CLASS → Class
* Ownership stored via `"module"`

Graph meaning:

```
numpy ──HAS_CLASS──> ndarray
```

---

## Inside Each Class

### Methods

```json
"methods": ["reshape", "sum", "mean"]
```

Represents:

```
ndarray ──HAS_METHOD──> reshape
```

---

### Attributes

```json
"attributes": ["shape", "dtype"]
```

Represents:

```
ndarray ──HAS_ATTRIBUTE──> shape
```

---

# ⚙️ 4️⃣ Functions Section

```json
"functions": {
  "mean": {
    "node_type": "function",
    "module": "numpy",
    "parameters": {
      "required": ["a"],
      "optional": ["axis"]
    },
    "returns": "unknown",
    "description": "...",
    "example": ""
  }
}
```

Represents:

```
numpy ──HAS_FUNCTION──> mean
```

---

## Methods Also Stored in Functions

Methods appear like:

```json
"reshape": {
  "node_type": "method",
  "belongs_to": "ndarray",
  ...
}
```

This encodes:

```
ndarray ──HAS_METHOD──> reshape
```

Stored via `"belongs_to"`.

---

# 📊 Complete Conceptual Graph

Your JSON represents:

```
Library
 ├── Module
 ├── Class
 │     ├── Method
 │     └── Attribute
 └── Function
```

It is a **structural namespace graph**.

---

# 🧠 PART 2 — How Your Code Generates This

Now let’s connect architecture to your builder.

Your construction pipeline:

---

## STEP 1 — Load Library

```python
lib = importlib.import_module(lib_name)
```

This loads numpy object into memory.

---

## STEP 2 — Extract Module-Level Symbols

```python
for name in dir(lib):
    obj = getattr(lib, name)
```

You iterate over all attributes of numpy.

This includes:

* functions
* classes
* submodules
* constants

---

## STEP 3 — Identify Functions

```python
if isinstance(obj, (types.FunctionType, types.BuiltinFunctionType)):
```

When true:

You create:

```python
kg["functions"][name] = {
    "node_type": "function",
    "module": lib.__name__,
    ...
}
```

This creates the Function entity.

---

## STEP 4 — Identify Classes

```python
if inspect.isclass(obj):
```

When true:

```python
kg["classes"][name] = {
    "node_type": "class",
    "module": lib.__name__,
    ...
}
```

This creates Class entity.

---

## STEP 5 — Extract Class Members

```python
for attr_name in dir(cls):
```

You inspect inside each class.

If:

```python
callable(attr)
```

→ Method

Else:

→ Attribute

---

## Method Creation

```python
kg["functions"][attr_name] = {
    "node_type": "method",
    "belongs_to": class_name,
}
```

This encodes relationship.

---

## Attribute Creation

```python
class_node["attributes"].append(attr_name)
```

Stored inside class.

---

## STEP 6 — Detect Submodules

```python
if inspect.ismodule(obj):
```

When true:

```python
kg["modules"][name] = {
    "node_type": "module",
    "parent": lib.__name__
}
```

Creates Module entity.

---

# 🔥 Why This Architecture Is Strong

Because it is:

* Extracted from actual runtime
* Deterministic
* Environment-aligned
* Lightweight
* Structured
* Hierarchical

No scraping.
No parsing docs.
No version guessing.

---

# 🎯 Final Architectural Summary (You Can Say This)

> The knowledge graph is a runtime-extracted structural API graph representing library namespace hierarchy. It encodes entity types (Library, Module, Class, Function, Method, Attribute) and ownership relationships through explicit properties such as `module` and `belongs_to`. The graph is serialized in JSON for efficient validation and lookup.

That is a research-grade explanation.

---

## CODE

```
import importlib
import inspect
import json
import types

# =========================
# STEP 1 — Load library
# =========================
def load_library(lib_name):
    return importlib.import_module(lib_name)

# =========================
# STEP 2 — Init KG
# =========================
def init_kg(lib_name):
    return {
        "library": lib_name,
        "version": "runtime",
        "modules": {},
        "classes": {},
        "functions": {}
    }

# =========================
# STEP 3.1 — Safe signature
# =========================
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

# =========================
# STEP 3.2 — Short doc
# =========================
def get_short_doc(obj):
    doc = inspect.getdoc(obj)
    if not doc:
        return ""
    return doc.split("\n")[0]

# =========================
# STEP 4 — Module functions
# =========================
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

# =========================
# STEP 5 — Classes
# =========================
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

# =========================
# STEP 6 — Class members
# =========================
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

# =========================
# STEP 7 — Submodules
# =========================
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

# =========================
# STEP 8 — Build KG
# =========================
def build_kg(lib_name):
    lib = load_library(lib_name)
    kg = init_kg(lib_name)

    extract_functions(lib, kg)
    extract_classes(lib, kg)
    extract_class_members(lib, kg)
    extract_submodules(lib, kg)

    return kg

# =========================
# STEP 9 — Save KG
# =========================
def save_kg(kg, path):
    with open(path, "w") as f:
        json.dump(kg, f, indent=2)

# =========================
# STEP 10 — RUN (example)
# =========================
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
            print(f"\n🚀 Building KG for {lib_name} ...")

            kg = build_kg(lib_name)

            # make filename safe (replace dots)
            file_name = f"kg_{lib_name.replace('.', '_')}.json"
            save_kg(kg, file_name)

            print(f"✅ Saved {file_name}")

        except Exception as e:
            print(f"❌ Failed for {lib_name}: {e}")

    print("\n🎉 All DS-1000 Knowledge Graphs generated")
```
---

# 🧱 1️⃣ What is a Library?

A **library** is a collection of related code packaged together.

Example:

```python
import numpy
import pandas
import scipy
```

Here:

* `numpy` → library
* `pandas` → library
* `scipy` → library

A library is basically a **folder of Python code** that contains:

* modules
* classes
* functions
* submodules

Think of a library as:

```
A large toolbox
```

---

# 📦 2️⃣ What is a Module?

A **module** is a single Python file inside a library.

Example:

```python
import scipy.stats
```

Here:

* `scipy` → library
* `stats` → module inside scipy

If you look at SciPy’s structure:

```
scipy/
   stats/
   optimize/
   linalg/
```

Each of those is a module (or submodule).

You can think of modules as:

```
Folders or files inside a library
```

---

# 🏛 3️⃣ What is a Class?

A **class** is a blueprint for creating objects.

Example:

```python
import pandas as pd

df = pd.DataFrame(...)
```

Here:

* `DataFrame` → class
* `df` → object (instance of that class)

A class defines:

* behavior (methods)
* data (attributes)

Think of a class as:

```
A blueprint
```

---

# ⚙️ 4️⃣ What is a Function?

A **function** is a standalone callable block of code.

Example:

```python
import numpy as np

np.mean([1,2,3])
```

Here:

* `mean` → function
* It does something and returns a result

Functions:

* live inside modules
* are not attached to a specific object

---

# 🔧 5️⃣ What is a Method?

A **method** is a function that belongs to a class.

Example:

```python
arr = np.array([1,2,3])
arr.reshape((3,1))
```

Here:

* `reshape` → method
* It belongs to the class `ndarray`
* It acts on `arr`

Difference:

| Function    | Method             |
| ----------- | ------------------ |
| Independent | Belongs to a class |
| `np.mean()` | `arr.reshape()`    |

---

# 📎 6️⃣ What is an Attribute?

An **attribute** is data stored inside an object.

Example:

```python
arr = np.array([1,2,3])
arr.shape
```

Here:

* `shape` → attribute
* It stores information
* It is not called with parentheses

Difference:

| Method          | Attribute    |
| --------------- | ------------ |
| `arr.reshape()` | `arr.shape`  |
| Callable        | Not callable |
| Performs action | Stores data  |

---

# 🧠 Simple Mental Model

Think of it like a company:

```
Library  → Company
Module   → Department
Class    → Job role
Function → Tool in department
Method   → Action that role can perform
Attribute→ Data stored by role
```

---

# 🏗 Example with NumPy

```python
import numpy as np
```

### Library:

```
numpy
```

### Module:

```
numpy.random
numpy.linalg
```

### Class:

```
numpy.ndarray
```

### Function:

```
numpy.mean()
numpy.sum()
```

### Method:

```
array.reshape()
array.astype()
```

### Attribute:

```
array.shape
array.dtype
```

---

# 🎯 Why This Matters for Your KG

Your KG is capturing exactly this structure:

```
Library
 ├── Module
 │     ├── Class
 │     │      ├── Method
 │     │      └── Attribute
 │     └── Function
```

It is modeling the **structure of Python itself**.

---

# 🔥 Most Important Distinction

Many students confuse these:

### ❌ `np.mean` is NOT a method

It is a function inside the numpy module.

### ✅ `arr.mean()` is a method

It belongs to ndarray class.

That difference is crucial for hallucination detection.

---

# 🏁 Final Clear Definitions

| Term      | Simple Meaning                |
| --------- | ----------------------------- |
| Library   | Big package of code           |
| Module    | File/subfolder inside library |
| Class     | Blueprint for objects         |
| Function  | Standalone operation          |
| Method    | Operation inside class        |
| Attribute | Data inside object            |

---

