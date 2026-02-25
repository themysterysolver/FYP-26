#!/usr/bin/env python3
"""
Compare error messages between dynamic_execution_results.csv and hallucination_master_table.csv
"""
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def load_csv(filepath):
    """Load CSV and return as list of dictionaries"""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def compare_error_messages():
    """Compare error messages between the two files"""
    
    # Load both CSVs
    print("Loading CSV files...")
    exec_results = load_csv(PROJECT_ROOT / 'Hallucination detection' / 'dynamic' / 'dynamic_execution_results.csv')
    master_table = load_csv(PROJECT_ROOT / 'APR' / 'ANALYSIS' / 'hallucination_master_table.csv')
    
    # Create lookup dictionary for master table
    master_lookup = {}
    for row in master_table:
        key = (row['dataset'], row['task_id'])
        master_lookup[key] = row
    
    # Compare
    mismatches = []
    for exec_row in exec_results:
        key = (exec_row['dataset'], exec_row['task_id'])
        
        if key not in master_lookup:
            continue
        
        master_row = master_lookup[key]
        
        exec_msg = exec_row.get('error_message', '').strip()
        master_msg = master_row.get('message', '').strip()
        exec_line = exec_row.get('line_number', '').strip()
        master_line = master_row.get('line', '').strip()
        
        # Check if error messages differ (excluding empty values)
        if exec_msg and master_msg and exec_msg != master_msg:
            mismatches.append({
                'task_id': exec_row['task_id'],
                'exec_msg': exec_msg,
                'master_msg': master_msg,
                'exec_line': exec_line,
                'master_line': master_line
            })
    
    # Report results
    print(f"\nTotal mismatches found: {len(mismatches)}")
    print("=" * 120)
    
    for i, m in enumerate(mismatches[:30], 1):  # Show first 30
        print(f"\n[{i}] Task ID: {m['task_id']}")
        print(f"  Exec message:   {m['exec_msg'][:100]}{'...' if len(m['exec_msg']) > 100 else ''}")
        print(f"  Master message: {m['master_msg'][:100]}{'...' if len(m['master_msg']) > 100 else ''}")
        print(f"  Exec line: {m['exec_line']} | Master line: {m['master_line']}")
        print("-" * 120)
    
    if len(mismatches) > 30:
        print(f"\n... and {len(mismatches) - 30} more mismatches")
    
    return mismatches

if __name__ == "__main__":
    compare_error_messages()
