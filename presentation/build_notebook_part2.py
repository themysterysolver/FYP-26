#!/usr/bin/env python3
"""
Script to add remaining sections (4-10) to the APR pipeline notebook.
"""
import json
from pathlib import Path

def add_remaining_sections():
    """Add Sections 4-10 to the notebook."""
    
    notebook_path = Path('/Users/abhinavh.parthiban/Documents/FYP-26/presentation/apr_pipeline_demo.ipynb')
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    additional_cells = [
        # ==================== SECTION 4: DS-KG ====================
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "---\n\n",
                "<a id='section-4'></a>\n",
                "# 4. Data Science Knowledge Graph (DS-KG)\n\n",
                "The DS-KG is a structured knowledge base containing API documentation for 7 major data science libraries:\n",
                "- **numpy**: Array operations and numerical computing\n",
                "- **pandas**: Data manipulation and analysis\n",
                "- **matplotlib.pyplot**: Data visualization\n",
                "- **scipy**: Scientific computing\n",
                "- **sklearn**: Machine learning\n",
                "- **seaborn**: Statistical visualizations\n",
                "- **statsmodels**: Statistical modeling\n\n",
                "## 4.1 KG Coverage Statistics"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Display KG statistics from validation report\n",
                "if kg_validation and 'comparison' in kg_validation:\n",
                "    print(\"DS-KG Library Coverage\")\n",
                "    print(\"=\" * 80)\n",
                "    print(f\"{'Library':<20} {'Modules':<10} {'Classes':<10} {'Functions':<12} {'Param Coverage':<15}\")\n",
                "    print(\"=\" * 80)\n",
                "    \n",
                "    total_funcs = 0\n",
                "    for lib_name, data in kg_validation['comparison'].items():\n",
                "        after = data['after']\n",
                "        lib = after['library']\n",
                "        mods = after['modules']\n",
                "        classes = after['classes']\n",
                "        funcs = after['functions']\n",
                "        coverage = after['param_coverage_pct']\n",
                "        total_funcs += funcs\n",
                "        \n",
                "        print(f\"{lib:<20} {mods:<10} {classes:<10} {funcs:<12} {coverage:.1f}%\")\n",
                "    \n",
                "    print(\"=\" * 80)\n",
                "    print(f\"\\nTotal API entries: ~{total_funcs:,}\")\n",
                "else:\n",
                "    print(\"KG validation data not available\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4.2 Parameter Coverage Improvement\n\n",
                "The KG was significantly enhanced to improve parameter documentation coverage."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualize parameter coverage improvement\n",
                "if kg_validation and 'comparison' in kg_validation:\n",
                "    libraries = []\n",
                "    before_coverage = []\n",
                "    after_coverage = []\n",
                "    \n",
                "    for lib_name, data in kg_validation['comparison'].items():\n",
                "        libraries.append(data['after']['library'])\n",
                "        before_coverage.append(data['before']['param_coverage_pct'])\n",
                "        after_coverage.append(data['after']['param_coverage_pct'])\n",
                "    \n",
                "    fig = go.Figure(data=[\n",
                "        go.Bar(name='Before', x=libraries, y=before_coverage, marker_color='lightcoral'),\n",
                "        go.Bar(name='After', x=libraries, y=after_coverage, marker_color='lightgreen')\n",
                "    ])\n",
                "    \n",
                "    fig.update_layout(\n",
                "        title='DS-KG Parameter Coverage Improvement',\n",
                "        xaxis_title='Library',\n",
                "        yaxis_title='Parameter Coverage (%)',\n",
                "        barmode='group',\n",
                "        height=400,\n",
                "        yaxis=dict(range=[0, 105])\n",
                "    )\n",
                "    \n",
                "    fig.show()\n",
                "    \n",
                "    # Show specific improvements\n",
                "    print(\"\\n📈 Notable Improvements:\")\n",
                "    for lib_name, data in kg_validation['comparison'].items():\n",
                "        before = data['before']['param_coverage_pct']\n",
                "        after = data['after']['param_coverage_pct']\n",
                "        improvement = after - before\n",
                "        if improvement > 10:\n",
                "            print(f\"  - {data['after']['library']}: {before:.1f}% → {after:.1f}% (+{improvement:.1f}%)\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4.3 KG Query Examples"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Load DS-KG engine (if available)\n",
                "try:\n",
                "    from engine import DSKGEngine\n",
                "    \n",
                "    kg_numpy = PROJECT_ROOT / 'APR' / 'DS-KG' / 'kg_numpy.json'\n",
                "    if kg_numpy.exists():\n",
                "        kg_engine = DSKGEngine([str(kg_numpy)])\n",
                "        print(f\"✓ Loaded DS-KG with {len(kg_engine.entries)} numpy entries\")\n",
                "        \n",
                "        # Example 1: Exact API lookup\n",
                "        print(\"\\n\" + \"=\" * 60)\n",
                "        print(\"Example 1: Exact API Lookup\")\n",
                "        print(\"=\" * 60)\n",
                "        result = kg_engine.resolve_api_call('numpy', 'array')\n",
                "        if result:\n",
                "            print(f\"\\nQuery: numpy.array\")\n",
                "            print(f\"Path: {result.get('path', 'N/A')}\")\n",
                "            print(f\"Description: {result.get('description', 'N/A')[:100]}...\")\n",
                "            if 'parameters' in result:\n",
                "                print(f\"Parameters: {len(result['parameters'])} documented\")\n",
                "        \n",
                "        # Example 2: Fuzzy name search\n",
                "        print(\"\\n\" + \"=\" * 60)\n",
                "        print(\"Example 2: Fuzzy Name Search\")\n",
                "        print(\"=\" * 60)\n",
                "        results = kg_engine.get_by_name('mean', limit=3)\n",
                "        print(f\"\\nQuery: 'mean' (fuzzy search)\")\n",
                "        print(f\"Found: {len(results)} matches\")\n",
                "        for i, entry in enumerate(results, 1):\n",
                "            print(f\"  {i}. {entry.get('path', 'N/A')}\")\n",
                "    else:\n",
                "        print(\"⚠ KG files not found, skipping examples\")\n",
                "        kg_engine = None\n",
                "except ImportError:\n",
                "    print(\"⚠ DS-KG engine not available, skipping examples\")\n",
                "    kg_engine = None"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4.4 Formatted KG Entry Example"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Show how KG entries are formatted for LLM prompts\n",
                "kg_entry_example = {\n",
                "    'path': 'numpy.array',\n",
                "    'description': 'Create an array.',\n",
                "    'parameters': [\n",
                "        {'name': 'object', 'type': 'array_like', 'required': True, 'description': 'An array, any object exposing the array interface'},\n",
                "        {'name': 'dtype', 'type': 'data-type', 'required': False, 'description': 'The desired data-type for the array'},\n",
                "        {'name': 'copy', 'type': 'bool', 'required': False, 'description': 'If true (default), then the object is copied'},\n",
                "    ],\n",
                "    'returns': 'ndarray - An array object satisfying the specified requirements',\n",
                "    'deprecated': False\n",
                "}\n",
                "\n",
                "print(\"Formatted KG Entry for LLM Prompt:\")\n",
                "print(\"=\" * 60)\n",
                "print(f\"\\n### {kg_entry_example['path']}\")\n",
                "print(f\"\\n{kg_entry_example['description']}\")\n",
                "print(f\"\\n**Parameters:**\")\n",
                "for param in kg_entry_example['parameters']:\n",
                "    req = \"(required)\" if param['required'] else \"(optional)\"\n",
                "    print(f\"  - `{param['name']}`: {param['type']} {req}\")\n",
                "    print(f\"    {param['description']}\")\n",
                "print(f\"\\n**Returns:** {kg_entry_example['returns']}\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display_key_takeaway(\n",
                "    \"The DS-KG enriches repair prompts with accurate, up-to-date API documentation. \"\n",
                "    \"This prevents the LLM from hallucinating API usage and ensures repairs use correct, \"\n",
                "    \"non-deprecated APIs with proper parameter signatures.\"\n",
                ")"
            ]
        },
        # ==================== SECTION 5: PATCH GENERATION ====================
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "---\n\n",
                "<a id='section-5'></a>\n",
                "# 5. Patch Generation\n\n",
                "Patch generation creates structured representations of errors using Git conflict-style markers. \"\n",
                "These markers precisely localize faults and provide context for repair.\n\n",
                "## 5.1 Hybrid Strategy\n\n",
                "Our patch generator uses a **hybrid strategy**:\n",
                "1. **Static-first**: Check syntax, undefined names, API errors\n",
                "2. **Dynamic-first**: Check test failures, runtime errors\n",
                "3. **Combined**: Merge both sources for comprehensive coverage"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5.2 Marker Format\n\n",
                "All patches use this consistent format:\n\n",
                "```python\n",
                "<<<<<<< [ERROR START: ERROR_TYPE]\n",
                "<original erroneous lines>\n",
                "=======\n",
                "<fix suggestion or test case info>\n",
                ">>>>>>> [ERROR END: ERROR_TYPE]\n",
                "```"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example patches for each error type\n",
                "print(\"Example Patches with Markers\")\n",
                "print(\"=\" * 80)\n",
                "\n",
                "# 1. SYNTAX_ERROR\n",
                "print(\"\\n1. SYNTAX_ERROR Patch:\")\n",
                "print(\"-\" * 80)\n",
                "syntax_patch = \"\"\"def calculate_sum(a, b)\n",
                "<<<<<<< [ERROR START: SYNTAX_ERROR]\n",
                "def calculate_sum(a, b)\n",
                "=======\n",
                "# Syntax Error at line 1: expected ':'\n",
                "# Add colon at end of function definition\n",
                ">>>>>>> [ERROR END: SYNTAX_ERROR]\n",
                "    return a + b\"\"\"\n",
                "print(syntax_patch)\n",
                "\n",
                "# 2. UNDEFINED_NAME\n",
                "print(\"\\n\\n2. UNDEFINED_NAME Patch:\")\n",
                "print(\"-\" * 80)\n",
                "undefined_patch = \"\"\"def calculate_mean(numbers):\n",
                "<<<<<<< [ERROR START: UNDEFINED_NAME]\n",
                "    arr = np.array(numbers)\n",
                "=======\n",
                "# Undefined: 'np', suggested module: 'numpy'\n",
                "# Add: import numpy as np\n",
                ">>>>>>> [ERROR END: UNDEFINED_NAME]\n",
                "    return arr.mean()\"\"\"\n",
                "print(undefined_patch)\n",
                "\n",
                "# 3. API_ERROR\n",
                "print(\"\\n\\n3. API_ERROR Patch:\")\n",
                "print(\"-\" * 80)\n",
                "api_patch = \"\"\"import pandas as pd\n",
                "df = pd.DataFrame({'A': [1, 2, 3]})\n",
                "<<<<<<< [ERROR START: API_ERROR]\n",
                "result = df.ix[0]\n",
                "=======\n",
                "# Deprecated API: pandas.DataFrame.ix\n",
                "# Deprecated since: pandas 0.20.0\n",
                "# Use: .loc[] for label-based indexing or .iloc[] for position-based\n",
                ">>>>>>> [ERROR END: API_ERROR]\"\"\"\n",
                "print(api_patch)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 4. RUNTIME_ERROR\n",
                "print(\"4. RUNTIME_ERROR Patch:\")\n",
                "print(\"-\" * 80)\n",
                "runtime_patch = \"\"\"def divide_numbers(a, b):\n",
                "<<<<<<< [ERROR START: RUNTIME_ERROR]\n",
                "    return a / b\n",
                "=======\n",
                "# Runtime Error: ZeroDivisionError\n",
                "# Message: division by zero\n",
                "# Traceback: line 2, in divide_numbers\n",
                "# Add validation: if b == 0, handle appropriately\n",
                ">>>>>>> [ERROR END: RUNTIME_ERROR]\"\"\"\n",
                "print(runtime_patch)\n",
                "\n",
                "# 5. LOGIC_ERROR\n",
                "print(\"\\n\\n5. LOGIC_ERROR Patch:\")\n",
                "print(\"-\" * 80)\n",
                "logic_patch = \"\"\"def get_first_n(lst, n):\n",
                "<<<<<<< [ERROR START: LOGIC_ERROR]\n",
                "    return lst[:n+1]\n",
                "=======\n",
                "# TEST: get_first_n([1, 2, 3, 4, 5], 3)\n",
                "# EXPECTED: [1, 2, 3]\n",
                "# ACTUAL: [1, 2, 3, 4]\n",
                "# DIFF: Extra element at end\n",
                "# Issue: Off-by-one error in slice\n",
                ">>>>>>> [ERROR END: LOGIC_ERROR]\"\"\"\n",
                "print(logic_patch)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display_key_takeaway(\n",
                "    \"Patch generation with structured markers eliminates ambiguity about error locations. \"\n",
                "    \"The markers clearly show WHAT is wrong, WHERE it occurs, and provide contextual hints \"\n",
                "    \"for fixing it, making the LLM's repair task much simpler and more targeted.\"\n",
                ")"
            ]
        }
    ]
    
    nb['cells'].extend(additional_cells)
    
    with open(notebook_path, 'w') as f:
        json.dump(nb, f, indent=1)
    
    print(f"✓ Added {len(additional_cells)} cells (Sections 4-5)")
    return notebook_path

if __name__ == "__main__":
    notebook_path = add_remaining_sections()
    print(f"✓ Notebook updated: {notebook_path}")
