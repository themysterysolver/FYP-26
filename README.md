# FYP-26: Hallucination Detection & Automated Program Repair for LLM-Generated Code

## Setup Instructions (Windows)

### Prerequisites

- **Python 3.10+** installed ([download](https://www.python.org/downloads/))
  - During installation, check **"Add Python to PATH"**
- **Git** installed ([download](https://git-scm.com/download/win))

### Step-by-Step Setup

#### 1. Clone the Repository

Open Command Prompt (or PowerShell) and run:

```
git clone <repository-url>
cd FYP-26
```

#### 2. Create a Virtual Environment

```
python -m venv .venv
```

#### 3. Activate the Virtual Environment

**Command Prompt:**
```
.venv\Scripts\activate
```

**PowerShell:**
```
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script, run this first:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

#### 4. Install Dependencies

```
pip install -r requirements.txt
```

#### 5. (Optional) Install Extra Packages for Dynamic Execution

These are only needed if you want to re-run the dynamic execution module, which tests generated code that may use these libraries:

```
pip install scipy scikit-learn seaborn sympy pyyaml xgboost torch
```

### Running the Project

All scripts use relative paths and can be run from any directory. Use `python` (not `python3`) on Windows.

#### Hallucination Detection - Static Analysis

```
cd "Hallucination detection\static\AST"
python ast_analysis.py

cd "..\CFG"
python cfg_analysis.py

cd "..\LIB_API"
python library_api.py
```

#### Hallucination Detection - Dynamic Execution

```
cd "Hallucination detection\dynamic"
python dynamic_execution.py
```

#### Integrate Fault Data

```
cd "Hallucination detection\Fault Information"
python integrate_fault_data.py
```

#### Generate Master Table

```
cd "APR\ANALYSIS"
python gen.py
```

#### Generate Patches

```
cd "APR\PATCH GENERATION"
python patch_generator.py
```

#### Visualizations

```
cd "Hallucination detection\static\AST"
python visualize.py

cd "..\CFG"
python visualize.py

cd "..\LIB_API"
python visualize.py
```

#### View Patches

```
cd "OTHER STUFF"
python view_patches.py stats
```

### Project Structure

```
FYP-26/
├── Code generation/          # Generated code from Qwen model
│   └── Qwen/                 # Per-dataset generation results
├── Hallucination detection/
│   ├── static/               # Static analysis modules
│   │   ├── AST/              # AST-based analysis
│   │   ├── CFG/              # Control flow graph analysis
│   │   ├── LIB_API/          # Library/API usage analysis
│   │   └── SSA/              # SSA analysis
│   ├── dynamic/              # Dynamic test execution
│   └── Fault Information/    # Merged fault data
├── APR/                      # Automated Program Repair
│   ├── ANALYSIS/             # Master table generation
│   ├── PATCH GENERATION/     # Error-marked patch generation
│   └── DS-KG/                # Knowledge graph for repair
├── Dataset used/             # Source datasets
├── OTHER STUFF/              # Utility scripts
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

### Troubleshooting

- **`python` not recognized**: Make sure Python is added to your PATH. Reinstall Python and check "Add Python to PATH".
- **Module not found errors**: Make sure your virtual environment is activated (you should see `(.venv)` in your terminal prompt).
- **Permission errors in PowerShell**: Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.
