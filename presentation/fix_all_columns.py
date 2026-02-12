#!/usr/bin/env python3
"""
Fix all cells in the notebook that use incorrect column names.
"""
import json
import re
from pathlib import Path

def fix_all_column_references():
    """Fix all column name references throughout the notebook."""
    
    notebook_path = Path('/Users/abhinavh.parthiban/Documents/FYP-26/presentation/apr_pipeline_demo.ipynb')
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    fixes_made = 0
    
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        
        source = ''.join(cell['source'])
        original_source = source
        
        # Fix dynamic_df['status'] references
        source = source.replace("dynamic_df['status']", "dynamic_df['hallucination_subtype']")
        source = source.replace('dynamic_df["status"]', 'dynamic_df["hallucination_subtype"]')
        source = source.replace("(dynamic_df['status'] == 'timeout')", "(dynamic_df['hallucination_subtype'] == 'timeout')")
        source = source.replace("(dynamic_df['status'] == 'crash')", "(dynamic_df['hallucination_subtype'] == 'crash')")
        source = source.replace("(dynamic_df['status'] == 'assertion_failure')", "(dynamic_df['hallucination_subtype'] == 'wrong_output')")
        
        # Add column existence checks where needed
        if 'error_counts' in source and 'dynamic_df' in source:
            # This is likely a section that calculates error counts
            if 'if not dynamic_df.empty:' in source and "'hallucination_subtype' in dynamic_df.columns" not in source:
                # Add column check
                source = source.replace(
                    "if not dynamic_df.empty:",
                    "if not dynamic_df.empty and 'hallucination_subtype' in dynamic_df.columns:"
                )
        
        if source != original_source:
            cell['source'] = source.split('\n')
            fixes_made += 1
            print(f"✓ Fixed cell {i}")
    
    # Save notebook
    with open(notebook_path, 'w') as f:
        json.dump(nb, f, indent=1)
    
    print(f"\n✓ Fixed {fixes_made} cells")
    print(f"✓ Notebook saved")

if __name__ == "__main__":
    fix_all_column_references()
