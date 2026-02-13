#!/usr/bin/env python3
"""
Patch Generator Tool
Generates error-marked code patches from fault information and generated code.
"""

import pandas as pd
import json
import ast
import sys
from typing import List, Tuple, Optional


def load_and_merge_data(fault_info_path: str, master_table_path: str) -> pd.DataFrame:
    """
    Load both CSV files and merge them on dataset + task_id.
    
    Args:
        fault_info_path: Path to fault_information.csv
        master_table_path: Path to hallucination_master_table.csv
    
    Returns:
        Merged DataFrame
    """
    print("Loading fault_information.csv...")
    fault_df = pd.read_csv(fault_info_path)
    
    print("Loading hallucination_master_table.csv...")
    master_df = pd.read_csv(master_table_path)
    
    # Keep only necessary columns from master_table
    master_df = master_df[['dataset', 'task_id', 'generated_code']]
    
    print(f"Fault info rows: {len(fault_df)}")
    print(f"Master table rows: {len(master_df)}")
    
    # Merge on dataset + task_id
    merged_df = fault_df.merge(
        master_df,
        on=['dataset', 'task_id'],
        how='left'
    )
    
    print(f"Merged rows: {len(merged_df)}")
    print(f"Rows with generated_code: {merged_df['generated_code'].notna().sum()}")
    
    return merged_df


def extract_ast_errors(ast_info: str) -> List[Tuple[int, int, str]]:
    """
    Extract error line numbers from ast_info.
    
    Args:
        ast_info: JSON string with 'value' field containing line number
    
    Returns:
        List of (start_line, end_line, error_type) tuples
    """
    if pd.isna(ast_info) or not ast_info or ast_info.strip() == '':
        return []
    
    try:
        info = json.loads(ast_info)
        if 'value' in info and info['value']:
            line_num = int(info['value'])
            error_type = info.get('type', 'AST Error')
            return [(line_num, line_num, f"ast: {error_type}")]
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Warning: Failed to parse ast_info: {ast_info[:100]}... Error: {e}")
    
    return []


def extract_cfg_errors(cfg_info: str) -> List[Tuple[int, int, str]]:
    """
    Extract error line ranges from cfg_info.
    
    Args:
        cfg_info: String representation of list of dicts with 'start_line' and 'end_line'
    
    Returns:
        List of (start_line, end_line, error_type) tuples
    """
    if pd.isna(cfg_info) or not cfg_info or cfg_info.strip() == '':
        return []
    
    try:
        # Use ast.literal_eval to safely parse the list of dicts
        info_list = ast.literal_eval(cfg_info)
        
        if not isinstance(info_list, list):
            return []
        
        errors = []
        for item in info_list:
            if isinstance(item, dict) and 'start_line' in item and 'end_line' in item:
                start_line = int(item['start_line'])
                end_line = int(item['end_line'])
                error_type = item.get('type', 'CFG Error')
                errors.append((start_line, end_line, f"cfg: {error_type}"))
        
        return errors
    except (SyntaxError, ValueError, TypeError) as e:
        print(f"Warning: Failed to parse cfg_info: {cfg_info[:100]}... Error: {e}")
    
    return []


def extract_lib_errors(lib_info: str) -> List[Tuple[int, int, str]]:
    """
    Extract error line numbers from lib_info.
    
    Args:
        lib_info: String representation of list of dicts with 'line' field
    
    Returns:
        List of (start_line, end_line, error_type) tuples
    """
    if pd.isna(lib_info) or not lib_info or lib_info.strip() == '':
        return []
    
    try:
        # Use ast.literal_eval to safely parse the list of dicts
        info_list = ast.literal_eval(lib_info)
        
        if not isinstance(info_list, list):
            return []
        
        errors = []
        for item in info_list:
            if isinstance(item, dict) and 'line' in item:
                line_num = int(item['line'])
                error_type = item.get('type', 'Library Error')
                errors.append((line_num, line_num, f"lib: {error_type}"))
        
        return errors
    except (SyntaxError, ValueError, TypeError) as e:
        print(f"Warning: Failed to parse lib_info: {lib_info[:100]}... Error: {e}")
    
    return []


def extract_dynamic_errors(dynamic_info: str) -> List[Tuple[int, int, str]]:
    """
    Extract error line numbers from dynamic_info.
    
    Args:
        dynamic_info: JSON string with 'line_no' field
    
    Returns:
        List of (start_line, end_line, error_type) tuples
    """
    if pd.isna(dynamic_info) or not dynamic_info or dynamic_info.strip() == '':
        return []
    
    try:
        info = json.loads(dynamic_info)
        
        if 'line_no' in info and info['line_no']:
            line_no_str = str(info['line_no']).strip()
            if line_no_str and line_no_str != '':
                # Convert to int (handle floats like "1.0")
                line_num = int(float(line_no_str))
                if line_num > 0:  # Valid line number
                    error_type = info.get('error_type', 'Dynamic Error')
                    return [(line_num, line_num, f"dynamic: {error_type}")]
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Warning: Failed to parse dynamic_info: {dynamic_info[:100]}... Error: {e}")
    
    return []


def generate_patch(code: str, start_line: int, end_line: int) -> Optional[str]:
    """
    Generate patched code with error markers.
    
    Args:
        code: The generated code
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
    
    Returns:
        Patched code with error markers, or None if invalid
    """
    if pd.isna(code) or not code:
        return None
    
    # Split code into lines
    lines = code.split('\n')
    total_lines = len(lines)
    
    # Validate line numbers
    if start_line < 1 or end_line < 1 or start_line > total_lines or end_line > total_lines:
        print(f"Warning: Invalid line numbers {start_line}-{end_line} for code with {total_lines} lines")
        return None
    
    if start_line > end_line:
        print(f"Warning: start_line {start_line} > end_line {end_line}")
        return None
    
    # Convert to 0-indexed
    start_idx = start_line - 1
    end_idx = end_line - 1
    
    # Build patched code
    patched_lines = []
    
    # Add context line above (if exists)
    if start_idx > 0:
        patched_lines.append(lines[start_idx - 1])
    
    # Add error start marker
    patched_lines.append("<<<< [ERROR START]")
    
    # Add error lines
    for i in range(start_idx, end_idx + 1):
        patched_lines.append(lines[i])
    
    # Add error finish marker
    patched_lines.append("[ERROR FINISH] >>>>")
    
    # Add context line below (if exists)
    if end_idx < total_lines - 1:
        patched_lines.append(lines[end_idx + 1])
    
    return '\n'.join(patched_lines)


def process_row(row: pd.Series) -> List[dict]:
    """
    Process a single row and generate separate rows for each error.
    
    Args:
        row: A row from the merged DataFrame
    
    Returns:
        List of dictionaries, one for each error found
    """
    # Extract all errors
    all_errors = []
    
    ast_errors = extract_ast_errors(row['ast_info'])
    for start, end, error_type in ast_errors:
        all_errors.append(('ast', start, end, error_type))
    
    cfg_errors = extract_cfg_errors(row['cfg_info'])
    for start, end, error_type in cfg_errors:
        all_errors.append(('cfg', start, end, error_type))
    
    lib_errors = extract_lib_errors(row['lib_info'])
    for start, end, error_type in lib_errors:
        all_errors.append(('lib', start, end, error_type))
    
    dynamic_errors = extract_dynamic_errors(row['dynamic_info'])
    for start, end, error_type in dynamic_errors:
        all_errors.append(('dynamic', start, end, error_type))
    
    # If no errors found, skip this row
    if not all_errors:
        return []
    
    # Generate a row for each error
    result_rows = []
    for error_source, start_line, end_line, error_type in all_errors:
        patched_code = generate_patch(row['generated_code'], start_line, end_line)
        
        # Skip if patch generation failed
        if patched_code is None:
            continue
        
        # Create new row with all original fields plus new fields
        new_row = {
            'dataset': row['dataset'],
            'status': row['status'],
            'task_id': row['task_id'],
            'ast_info': row['ast_info'],
            'cfg_info': row['cfg_info'],
            'lib_info': row['lib_info'],
            'dynamic_info': row['dynamic_info'],
            'generated_code': row['generated_code'],
            'patched_code': patched_code,
            'error_source': error_source,
            'error_type': error_type,
            'error_line_start': start_line,
            'error_line_end': end_line
        }
        
        result_rows.append(new_row)
    
    return result_rows


def main():
    """Main execution function."""
    # File paths
    fault_info_path = 'Hallucination detection/Fault Information/fault_information.csv'
    master_table_path = 'APR/ANALYSIS/hallucination_master_table.csv'
    output_path = 'patched_code.csv'
    
    print("=" * 80)
    print("PATCH GENERATOR TOOL")
    print("=" * 80)
    print()
    
    # Step 1: Load and merge data
    print("Step 1: Loading and merging data...")
    merged_df = load_and_merge_data(fault_info_path, master_table_path)
    print()
    
    # Step 2-4: Process each row and expand
    print("Step 2-4: Processing rows and generating patches...")
    all_result_rows = []
    
    for idx, row in merged_df.iterrows():
        if idx % 100 == 0:
            print(f"Processing row {idx}/{len(merged_df)}...")
        
        result_rows = process_row(row)
        all_result_rows.extend(result_rows)
    
    print(f"Total patches generated: {len(all_result_rows)}")
    print()
    
    # Step 5: Write output
    print("Step 5: Writing output to patched_code.csv...")
    result_df = pd.DataFrame(all_result_rows)
    
    # Reorder columns
    column_order = [
        'dataset', 'status', 'task_id',
        'ast_info', 'cfg_info', 'lib_info', 'dynamic_info',
        'generated_code', 'patched_code',
        'error_source', 'error_type', 'error_line_start', 'error_line_end'
    ]
    
    result_df = result_df[column_order]
    result_df.to_csv(output_path, index=False)
    
    print(f"Successfully wrote {len(result_df)} rows to {output_path}")
    print()
    
    # Print summary statistics
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total input rows: {len(merged_df)}")
    print(f"Total output rows: {len(result_df)}")
    print(f"\nError source breakdown:")
    print(result_df['error_source'].value_counts())
    print()
    print("Done!")


if __name__ == '__main__':
    main()
