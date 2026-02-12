#!/usr/bin/env python3
"""
Script to build the complete APR pipeline demonstration notebook.
This generates all remaining sections programmatically.
"""
import json
from pathlib import Path

def build_complete_notebook():
    """Build the complete notebook with all sections."""
    
    # Read the existing notebook
    notebook_path = Path('/Users/abhinavh.parthiban/Documents/FYP-26/presentation/apr_pipeline_demo.ipynb')
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    # Additional cells to add
    additional_cells = [
        # CFG Example
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example: Unreachable Code\n",
                "unreachable_example = \"\"\"def process_data(x):\n",
                "    if x > 0:\n",
                "        return x * 2\n",
                "    return x\n",
                "    print('This will never execute')  # Unreachable!\n",
                "\"\"\"\n",
                "\n",
                "print(\"Example: Unreachable Code\")\n",
                "print(\"=\" * 60)\n",
                "display_code(unreachable_example, title=\"Buggy Code\")\n",
                "\n",
                "print(\"\\n✗ CFG Analysis Result:\")\n",
                "print(\"  Unreachable Code: 1 instance\")\n",
                "print(\"  Location: line 5\")\n",
                "print(\"  Reason: All paths return before this statement\")"
            ]
        },
        # SSA Section
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2.3 SSA Analysis\n\n",
                "Static Single Assignment analysis catches variables used before definition."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example: Use Before Definition\n",
                "ssa_example = \"\"\"def calculate_total():\n",
                "    result = count * 2  # 'count' not defined yet\n",
                "    count = 10\n",
                "    return result\n",
                "\"\"\"\n",
                "\n",
                "print(\"Example: Use Before Definition\")\n",
                "print(\"=\" * 60)\n",
                "display_code(ssa_example, title=\"Buggy Code\")\n",
                "\n",
                "print(\"\\n✗ SSA Analysis Result:\")\n",
                "print(\"  Undefined Variables: ['count']\")\n",
                "print(\"  Used at line 2 before definition at line 3\")"
            ]
        },
        # LIB_API Section
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2.4 LIB_API Analysis\n\n",
                "Library API analysis validates correct usage of data science libraries."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example: Deprecated API Usage\n",
                "api_error_example = \"\"\"import pandas as pd\n",
                "\n",
                "df = pd.DataFrame({'A': [1, 2, 3]})\n",
                "result = df.ix[0]  # df.ix is deprecated!\n",
                "\"\"\"\n",
                "\n",
                "print(\"Example: Deprecated API\")\n",
                "print(\"=\" * 60)\n",
                "display_code(api_error_example, title=\"Buggy Code\")\n",
                "\n",
                "print(\"\\n✗ LIB_API Analysis Result:\")\n",
                "print(\"  Deprecated APIs: 1\")\n",
                "print(\"  API: pandas.DataFrame.ix\")\n",
                "print(\"  Deprecated since: pandas 0.20.0\")\n",
                "print(\"  Recommended: Use .loc[] or .iloc[] instead\")"
            ]
        },
        # Static Analysis Visualization
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2.5 Static Analysis Statistics"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualize static analysis results\n",
                "static_stats = stats['static_analysis']\n",
                "\n",
                "if static_stats:\n",
                "    categories = list(static_stats.keys())\n",
                "    values = list(static_stats.values())\n",
                "    \n",
                "    fig = go.Figure(data=[\n",
                "        go.Bar(\n",
                "            x=categories,\n",
                "            y=values,\n",
                "            marker=dict(\n",
                "                color=values,\n",
                "                colorscale='Reds',\n",
                "                showscale=True\n",
                "            ),\n",
                "            text=values,\n",
                "            textposition='outside'\n",
                "        )\n",
                "    ])\n",
                "    \n",
                "    fig.update_layout(\n",
                "        title=\"Static Analysis: Error Detection Counts\",\n",
                "        xaxis_title=\"Error Type\",\n",
                "        yaxis_title=\"Count\",\n",
                "        height=400\n",
                "    )\n",
                "    \n",
                "    fig.show()\n",
                "else:\n",
                "    print(\"No static analysis data available\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display_key_takeaway(\n",
                "    \"Static analysis provides fast, zero-cost error detection without code execution. \"\n",
                "    \"It catches syntax errors, undefined names, API misuse, and control flow issues \"\n",
                "    \"instantly, enabling early fault localization.\"\n",
                ")"
            ]
        },
        # Section 3: Dynamic Analysis
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "---\n\n",
                "<a id='section-3'></a>\n",
                "# 3. Hallucination Detection: Dynamic Analysis\n\n",
                "Dynamic analysis executes the generated code with test cases to detect:\n",
                "- **Timeouts**: Infinite loops\n",
                "- **Crashes**: Runtime exceptions\n",
                "- **Wrong Output**: Logic errors where code runs but produces incorrect results\n\n",
                "## 3.1 Test Generation Strategies\n\n",
                "We use two complementary test generation techniques:\n\n",
                "1. **Boundary Value Analysis (BVA)**: Tests edge cases (min, max, zero, empty)\n",
                "2. **Equivalence Class Partitioning (ECP)**: Tests invalid inputs\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example: Test Generation\n",
                "print(\"Test Generation Example\")\n",
                "print(\"=\" * 60)\n",
                "print(\"\\nOriginal Test Case:\")\n",
                "print(\"  calculate_sum([1, 2, 3]) → expected: 6\")\n",
                "\n",
                "print(\"\\nBVA Generated Tests:\")\n",
                "print(\"  - BVA Low:  calculate_sum([]) → edge case: empty list\")\n",
                "print(\"  - BVA High: calculate_sum([1000, 2000, 3000]) → large values\")\n",
                "print(\"  - BVA Zero: calculate_sum([0, 0, 0]) → zero boundary\")\n",
                "\n",
                "print(\"\\nECP Generated Tests:\")\n",
                "print(\"  - ECP Invalid: calculate_sum(None) → invalid input type\")\n",
                "\n",
                "print(\"\\n📊 Total tests: 1 original + 3 BVA + 1 ECP = 5 tests\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3.2 Dynamic Execution Examples"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example 1: Timeout (Infinite Loop)\n",
                "timeout_example = \"\"\"def find_value(arr, target):\n",
                "    i = 0\n",
                "    while i < len(arr):  # Bug: forgot to increment i\n",
                "        if arr[i] == target:\n",
                "            return i\n",
                "    return -1\n",
                "\"\"\"\n",
                "\n",
                "print(\"Example 1: Timeout Detection\")\n",
                "print(\"=\" * 60)\n",
                "display_code(timeout_example, title=\"Buggy Code\")\n",
                "\n",
                "print(\"\\n✗ Dynamic Analysis Result:\")\n",
                "print(\"  Status: timeout\")\n",
                "print(\"  Execution Time: >5000ms (limit exceeded)\")\n",
                "print(\"  Hallucination Subtype: timeout\")\n",
                "print(\"  Can Repair: false (infinite loops are hard to fix automatically)\")\n",
                "print(\"  Issue: Variable 'i' never incremented in loop\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example 2: Runtime Error\n",
                "runtime_error_example = \"\"\"def divide_numbers(a, b):\n",
                "    return a / b  # What if b is 0?\n",
                "\"\"\"\n",
                "\n",
                "print(\"Example 2: Runtime Error (Division by Zero)\")\n",
                "print(\"=\" * 60)\n",
                "display_code(runtime_error_example, title=\"Buggy Code\")\n",
                "\n",
                "print(\"\\nTest Case: divide_numbers(10, 0)\")\n",
                "print(\"\\n✗ Dynamic Analysis Result:\")\n",
                "print(\"  Status: crash\")\n",
                "print(\"  Exception Type: ZeroDivisionError\")\n",
                "print(\"  Exception Message: division by zero\")\n",
                "print(\"  Traceback:\")\n",
                "print(\"    File \\\"<string>\\\", line 2, in divide_numbers\")\n",
                "print(\"  Hallucination Subtype: arithmetic_error\")\n",
                "print(\"  Detected by: BVA test (boundary: zero)\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example 3: Logic Error (Wrong Output)\n",
                "logic_error_example = \"\"\"def get_first_n(lst, n):\n",
                "    return lst[:n+1]  # Bug: should be lst[:n]\n",
                "\"\"\"\n",
                "\n",
                "print(\"Example 3: Logic Error (Wrong Output)\")\n",
                "print(\"=\" * 60)\n",
                "display_code(logic_error_example, title=\"Buggy Code\")\n",
                "\n",
                "print(\"\\nTest Case: get_first_n([1, 2, 3, 4, 5], 3)\")\n",
                "print(\"\\n✗ Dynamic Analysis Result:\")\n",
                "print(\"  Status: assertion_failure\")\n",
                "print(\"  Expected: [1, 2, 3]\")\n",
                "print(\"  Actual:   [1, 2, 3, 4]\")\n",
                "print(\"  Hallucination Subtype: wrong_output (off-by-one)\")\n",
                "print(\"  Issue: Slice index is off by one\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3.3 Dynamic Analysis Statistics"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualize dynamic analysis results\n",
                "dynamic_stats = stats['dynamic_analysis']\n",
                "\n",
                "if dynamic_stats and dynamic_stats.get('total_executed', 0) > 0:\n",
                "    # Create funnel visualization\n",
                "    categories = ['Executed', 'Failed', 'Timeout', 'Crash', 'Wrong Output']\n",
                "    values = [\n",
                "        dynamic_stats.get('total_executed', 0),\n",
                "        dynamic_stats.get('timeouts', 0) + dynamic_stats.get('crashes', 0) + dynamic_stats.get('wrong_output', 0),\n",
                "        dynamic_stats.get('timeouts', 0),\n",
                "        dynamic_stats.get('crashes', 0),\n",
                "        dynamic_stats.get('wrong_output', 0)\n",
                "    ]\n",
                "    \n",
                "    fig = go.Figure(go.Funnel(\n",
                "        y=categories,\n",
                "        x=values,\n",
                "        textposition=\"inside\",\n",
                "        textinfo=\"value+percent initial\",\n",
                "        marker=dict(\n",
                "            color=[\"lightblue\", \"orange\", \"red\", \"darkred\", \"purple\"]\n",
                "        )\n",
                "    ))\n",
                "    \n",
                "    fig.update_layout(\n",
                "        title=\"Dynamic Analysis: Execution Funnel\",\n",
                "        height=400\n",
                "    )\n",
                "    \n",
                "    fig.show()\n",
                "else:\n",
                "    print(\"No dynamic analysis data available\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "display_key_takeaway(\n",
                "    \"Dynamic analysis catches errors that static analysis misses - especially logic errors \"\n",
                "    \"where code is syntactically correct but produces wrong results. BVA and ECP test generation \"\n",
                "    \"significantly increase error detection coverage by testing edge cases.\"\n",
                ")"
            ]
        }
    ]
    
    # Add all cells to the notebook
    nb['cells'].extend(additional_cells)
    
    # Write back
    with open(notebook_path, 'w') as f:
        json.dump(nb, f, indent=1)
    
    print(f"✓ Added {len(additional_cells)} cells to notebook")
    return notebook_path

if __name__ == "__main__":
    notebook_path = build_complete_notebook()
    print(f"✓ Notebook updated: {notebook_path}")
