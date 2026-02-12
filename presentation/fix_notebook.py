#!/usr/bin/env python3
"""
Fix the notebook to use correct column names from CSV files.
"""
import json
from pathlib import Path

def fix_statistics_function():
    """Fix the generate_statistics_dashboard function."""
    
    notebook_path = Path('/Users/abhinavh.parthiban/Documents/FYP-26/presentation/apr_pipeline_demo.ipynb')
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    # Find and replace the statistics function cell
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code' and 'def generate_statistics_dashboard' in ''.join(cell['source']):
            print(f"Found statistics function at cell {i}")
            
            # New corrected code
            new_source = [
                "# Helper functions for data analysis\n",
                "\n",
                "def load_examples_by_error_type(error_type: str, limit: int = 5) -> List[Dict]:\n",
                "    \"\"\"Load sample APR inputs filtered by error type.\"\"\"\n",
                "    matching = []\n",
                "    for inp in apr_inputs:\n",
                "        # Check static analysis\n",
                "        if error_type == 'SYNTAX_ERROR' and inp.get('static_ast', {}).get('status') == 'syntax_error':\n",
                "            matching.append(inp)\n",
                "        elif error_type == 'UNDEFINED_NAME' and inp.get('static_ast', {}).get('undefined_names'):\n",
                "            matching.append(inp)\n",
                "        elif error_type == 'API_ERROR' and inp.get('static_library_api', {}).get('total_libapi_errors', 0) > 0:\n",
                "            matching.append(inp)\n",
                "        elif error_type == 'RUNTIME_ERROR' and inp.get('dynamic_analysis', {}).get('status') == 'runtime_error':\n",
                "            matching.append(inp)\n",
                "        elif error_type == 'LOGIC_ERROR' and inp.get('dynamic_analysis', {}).get('status') == 'assertion_failure':\n",
                "            matching.append(inp)\n",
                "        \n",
                "        if len(matching) >= limit:\n",
                "            break\n",
                "    \n",
                "    return matching\n",
                "\n",
                "def generate_statistics_dashboard() -> Dict[str, Any]:\n",
                "    \"\"\"Generate aggregate statistics from the dataset.\"\"\"\n",
                "    stats = {\n",
                "        'total_examples': len(apr_inputs),\n",
                "        'datasets': {},\n",
                "        'error_types': Counter(),\n",
                "        'static_analysis': {},\n",
                "        'dynamic_analysis': {},\n",
                "    }\n",
                "    \n",
                "    # Count by dataset\n",
                "    for inp in apr_inputs:\n",
                "        dataset = inp.get('source_dataset', 'unknown')\n",
                "        stats['datasets'][dataset] = stats['datasets'].get(dataset, 0) + 1\n",
                "    \n",
                "    # Static analysis stats - use correct column names\n",
                "    if not ast_df.empty:\n",
                "        if 'syntax_error' in ast_df.columns:\n",
                "            stats['static_analysis']['syntax_errors'] = int(ast_df['syntax_error'].sum())\n",
                "        if 'error_type' in ast_df.columns:\n",
                "            stats['static_analysis']['undefined_names'] = int((ast_df['error_type'] == 'NameError').sum())\n",
                "    \n",
                "    if not cfg_df.empty:\n",
                "        if 'unreachable_code' in cfg_df.columns:\n",
                "            stats['static_analysis']['unreachable_code'] = int(cfg_df['unreachable_code'].sum())\n",
                "        if 'missing_return' in cfg_df.columns:\n",
                "            stats['static_analysis']['missing_return'] = int(cfg_df['missing_return'].sum())\n",
                "    \n",
                "    if not libapi_df.empty:\n",
                "        if 'total_libapi_errors' in libapi_df.columns:\n",
                "            stats['static_analysis']['api_errors'] = int(libapi_df['total_libapi_errors'].sum())\n",
                "    \n",
                "    # Dynamic analysis stats - use correct column names\n",
                "    if not dynamic_df.empty:\n",
                "        stats['dynamic_analysis']['total_executed'] = len(dynamic_df)\n",
                "        \n",
                "        # Use hallucination_subtype instead of status\n",
                "        if 'hallucination_subtype' in dynamic_df.columns:\n",
                "            stats['dynamic_analysis']['timeouts'] = int((dynamic_df['hallucination_subtype'] == 'timeout').sum())\n",
                "            stats['dynamic_analysis']['crashes'] = int((dynamic_df['hallucination_subtype'] == 'crash').sum())\n",
                "            stats['dynamic_analysis']['wrong_output'] = int((dynamic_df['hallucination_subtype'] == 'wrong_output').sum())\n",
                "        \n",
                "        # Alternative: check valid column\n",
                "        if 'valid' in dynamic_df.columns:\n",
                "            stats['dynamic_analysis']['invalid_count'] = int((~dynamic_df['valid']).sum())\n",
                "    \n",
                "    return stats\n",
                "\n",
                "# Generate initial statistics\n",
                "stats = generate_statistics_dashboard()\n",
                "print(\"✓ Statistics dashboard generated\")\n",
                "print(f\"  - Total examples: {stats['total_examples']}\")\n",
                "print(f\"  - Datasets: {list(stats['datasets'].keys())}\")"
            ]
            
            cell['source'] = new_source
            print("✓ Updated statistics function")
            break
    
    # Save notebook
    with open(notebook_path, 'w') as f:
        json.dump(nb, f, indent=1)
    
    print(f"✓ Notebook fixed and saved")

if __name__ == "__main__":
    fix_statistics_function()
