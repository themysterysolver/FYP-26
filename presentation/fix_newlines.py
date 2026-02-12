#!/usr/bin/env python3
"""
Fix missing newlines in the function definition cell.
"""
import json
from pathlib import Path

def fix_cell_newlines():
    """Fix the cell that defines generate_statistics_dashboard."""
    
    notebook_path = Path('/Users/abhinavh.parthiban/Documents/FYP-26/presentation/apr_pipeline_demo.ipynb')
    with open(notebook_path, 'r') as f:
        nb = json.load(f)
    
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            
            if 'def generate_statistics_dashboard' in source:
                print(f"Found problematic cell at index {i}")
                
                # The source should be a list of lines, not a single concatenated string
                # Let's recreate it properly with newlines
                if isinstance(cell['source'], str):
                    # Split by newlines if it's a single string
                    cell['source'] = cell['source'].split('\n')
                elif isinstance(cell['source'], list):
                    # Check if lines are missing \n
                    new_source = []
                    for line in cell['source']:
                        if not line.endswith('\n') and line != cell['source'][-1]:
                            new_source.append(line + '\n')
                        else:
                            new_source.append(line)
                    cell['source'] = new_source
                
                print("✓ Fixed newlines in source")
                break
    
    with open(notebook_path, 'w') as f:
        json.dump(nb, f, indent=1)
    
    print("✓ Notebook saved")

if __name__ == "__main__":
    fix_cell_newlines()
