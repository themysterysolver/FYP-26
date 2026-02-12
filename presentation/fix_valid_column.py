#!/usr/bin/env python3
"""
Fix the TypeError with the valid column in generate_statistics_dashboard.
"""
import json
from pathlib import Path

def fix_valid_column_error():
    """Fix the invalid_count calculation that's causing TypeError."""
    
    notebook_path = Path('/Users/abhinavh.parthiban/Documents/FYP-26/presentation/apr_pipeline_demo.ipynb')
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        
        source = ''.join(cell['source'])
        
        if 'def generate_statistics_dashboard' in source and "~dynamic_df['valid']" in source:
            print(f"Found problematic code at cell {i}")
            
            # Fix the TypeError by properly handling the valid column
            source = source.replace(
                "stats['dynamic_analysis']['invalid_count'] = int((~dynamic_df['valid']).sum())",
                "stats['dynamic_analysis']['invalid_count'] = int((dynamic_df['valid'] == False).sum())"
            )
            
            cell['source'] = source.split('\n')
            print("✓ Fixed valid column error")
            break
    
    with open(notebook_path, 'w') as f:
        json.dump(nb, f, indent=1)
    
    print("✓ Notebook saved")

if __name__ == "__main__":
    fix_valid_column_error()
