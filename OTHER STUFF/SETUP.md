# Project setup (Python)

After installing Python, use a virtual environment and install dependencies.

## 1. Create and activate the virtual environment

Already created at `.venv/`. To activate:

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

## 2. Install packages

With the venv activated:
```bash
pip install -r requirements.txt
```

(If you see an SSL error, try running the terminal outside the sandbox or check your network/certificates.)

## 3. Installed packages

- **pandas** – data handling (Hallucination detection, Code generation, LIB_API)
- **numpy** – numerical operations (check scripts, LIB_API analysis)
- **matplotlib** – plotting (visualize scripts, analysis)

## 4. Run the LIB_API proof of concept

From project root with venv activated:
```bash
python "Hallucination detection/static/LIB_API/proof_of_concept/proof_multi_error.py"
```

Or from the `LIB_API` folder:
```bash
cd "Hallucination detection/static/LIB_API"
python proof_of_concept/proof_multi_error.py
```
