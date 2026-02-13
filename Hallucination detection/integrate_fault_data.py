#!/usr/bin/env python3
"""
CSV Integration Script
Merges hallucination detection data from 4 sources into a unified fault information file.
"""

import pandas as pd
import json
import os
from pathlib import Path


def load_csv_files():
    """Load all 4 CSV files."""
    base_path = Path(__file__).parent
    
    # Define file paths
    ast_path = base_path / "static/AST/ast_summary.csv"
    cfg_path = base_path / "static/CFG/cfg_summary.csv"
    libapi_path = base_path / "static/LIB_API/libapi_summary.csv"
    dynamic_path = base_path / "dynamic/dynamic_execution_results.csv"
    
    # Load dataframes
    df_ast = pd.read_csv(ast_path)
    df_cfg = pd.read_csv(cfg_path)
    df_libapi = pd.read_csv(libapi_path)
    df_dynamic = pd.read_csv(dynamic_path)
    
    return df_ast, df_cfg, df_libapi, df_dynamic


def merge_dataframes(df_ast, df_cfg, df_libapi, df_dynamic):
    """Merge all dataframes on task_id."""
    # Start with AST dataframe
    merged = df_ast.copy()
    
    # Merge CFG data
    merged = merged.merge(
        df_cfg[['task_id', 'cfg_analyzed', 'unreachable_code', 'missing_return', 'cfg_details']], 
        on='task_id', 
        how='outer',
        suffixes=('', '_cfg')
    )
    
    # Merge LIB_API data
    merged = merged.merge(
        df_libapi[['task_id', 'libapi_analyzed', 'name_error', 'attribute_error', 
                   'type_error', 'module_not_found', 'total_libapi_errors', 'libapi_details']], 
        on='task_id', 
        how='outer',
        suffixes=('', '_libapi')
    )
    
    # Merge Dynamic data
    merged = merged.merge(
        df_dynamic[['task_id', 'status', 'error_type', 'error_message', 'line_number', 'test_case']], 
        on='task_id', 
        how='outer',
        suffixes=('_static', '_dynamic')
    )
    
    return merged


def determine_status(row):
    """Determine if a task passed or hallucinated based on error conditions."""
    # Check AST errors
    ast_has_error = (
        row.get('ast_parsed') == False or 
        row.get('syntax_error', 0) > 0 or 
        row.get('indentation_error', 0) > 0 or 
        row.get('structural_error', 0) > 0
    )
    
    # Check CFG errors - cfg_details should not be empty list
    cfg_details = str(row.get('cfg_details', '[]'))
    cfg_has_error = cfg_details != '[]' and pd.notna(cfg_details)
    
    # Check LIB_API errors
    libapi_has_error = row.get('total_libapi_errors', 0) > 0
    
    # Check Dynamic errors
    dynamic_status = row.get('status', '')
    dynamic_has_error = dynamic_status == 'failed'
    
    # If any source has errors, status is hallucinated
    if ast_has_error or cfg_has_error or libapi_has_error or dynamic_has_error:
        return 'hallucinated'
    else:
        return 'passed'


def build_ast_info(row):
    """Build AST info JSON string."""
    if determine_status(row) == 'passed':
        return ''
    
    # Check if there's an actual AST error first
    ast_has_error = (
        row.get('ast_parsed') == False or 
        row.get('syntax_error', 0) > 0 or 
        row.get('indentation_error', 0) > 0 or 
        row.get('structural_error', 0) > 0
    )
    
    if not ast_has_error:
        return ''
    
    ast_info = {}
    
    # Check if there's an error type
    if row.get('error_type_static') and pd.notna(row.get('error_type_static')):
        ast_info['type'] = str(row['error_type_static'])
    elif pd.notna(row.get('error_type')) and str(row.get('error_type')) != 'nan':
        ast_info['type'] = str(row['error_type'])
    else:
        ast_info['type'] = ''
    
    # Add line number
    if pd.notna(row.get('line')) and str(row.get('line')) != 'nan':
        try:
            ast_info['value'] = int(float(row['line']))
        except (ValueError, TypeError):
            ast_info['value'] = ''
    else:
        ast_info['value'] = ''
    
    # Add message
    if pd.notna(row.get('message')) and str(row.get('message')) != 'nan':
        ast_info['message'] = str(row['message'])
    else:
        ast_info['message'] = ''
    
    # Only return if there's actual content
    if ast_info.get('type') or ast_info.get('value') or ast_info.get('message'):
        return json.dumps(ast_info)
    return ''


def build_cfg_info(row):
    """Build CFG info JSON string."""
    if determine_status(row) == 'passed':
        return ''
    
    cfg_details = row.get('cfg_details', '[]')
    if pd.notna(cfg_details) and str(cfg_details) != '[]':
        return str(cfg_details)
    return ''


def build_lib_info(row):
    """Build LIB_API info JSON string."""
    if determine_status(row) == 'passed':
        return ''
    
    libapi_details = row.get('libapi_details', '[]')
    if pd.notna(libapi_details) and str(libapi_details) != '[]':
        return str(libapi_details)
    return ''


def build_dynamic_info(row):
    """Build Dynamic info JSON string."""
    if determine_status(row) == 'passed':
        return ''
    
    dynamic_status = row.get('status', '')
    if dynamic_status == 'failed':
        dynamic_info = {}
        
        # Add error type - prefer _dynamic suffix if it exists
        if pd.notna(row.get('error_type_dynamic')) and str(row.get('error_type_dynamic')) != 'nan':
            dynamic_info['error_type'] = str(row['error_type_dynamic'])
        elif pd.notna(row.get('error_type')) and str(row.get('error_type')) != 'nan':
            dynamic_info['error_type'] = str(row['error_type'])
        else:
            dynamic_info['error_type'] = ''
        
        # Add error message
        if pd.notna(row.get('error_message')) and str(row.get('error_message')) != 'nan':
            dynamic_info['error_message'] = str(row['error_message'])
        else:
            dynamic_info['error_message'] = ''
        
        # Add line number
        if pd.notna(row.get('line_number')) and str(row.get('line_number')) != 'nan':
            dynamic_info['line_no'] = str(row['line_number'])
        else:
            dynamic_info['line_no'] = ''
        
        # Add test case - preserve empty strings for failed tests without test case data
        test_case_value = row.get('test_case', '')
        if pd.notna(test_case_value) and str(test_case_value).strip() != '' and str(test_case_value) != 'nan':
            dynamic_info['test_case'] = str(test_case_value)
        else:
            dynamic_info['test_case'] = ''
        
        return json.dumps(dynamic_info)
    
    return ''


def create_output_dataframe(merged_df):
    """Create the final output dataframe with specified columns."""
    output_data = []
    
    for _, row in merged_df.iterrows():
        status = determine_status(row)
        task_id = row['task_id']
        dataset = row.get('dataset', '')  # Get dataset from merged_df
        
        if status == 'passed':
            # Only populate status and task_id
            output_data.append({
                'dataset': dataset,
                'status': status,
                'task_id': task_id,
                'ast_info': '',
                'cfg_info': '',
                'lib_info': '',
                'dynamic_info': ''
            })
        else:
            # Populate all fields
            output_data.append({
                'dataset': dataset,
                'status': status,
                'task_id': task_id,
                'ast_info': build_ast_info(row),
                'cfg_info': build_cfg_info(row),
                'lib_info': build_lib_info(row),
                'dynamic_info': build_dynamic_info(row)
            })
    
    return pd.DataFrame(output_data)


def main():
    """Main execution function."""
    print("Loading CSV files...")
    df_ast, df_cfg, df_libapi, df_dynamic = load_csv_files()
    
    print(f"Loaded {len(df_ast)} AST records")
    print(f"Loaded {len(df_cfg)} CFG records")
    print(f"Loaded {len(df_libapi)} LIB_API records")
    print(f"Loaded {len(df_dynamic)} Dynamic records")
    
    print("\nMerging dataframes...")
    merged_df = merge_dataframes(df_ast, df_cfg, df_libapi, df_dynamic)
    print(f"Merged dataframe has {len(merged_df)} records")
    
    print("\nCreating output dataframe...")
    output_df = create_output_dataframe(merged_df)
    
    # Count statuses
    passed_count = len(output_df[output_df['status'] == 'passed'])
    hallucinated_count = len(output_df[output_df['status'] == 'hallucinated'])
    print(f"Status breakdown: {passed_count} passed, {hallucinated_count} hallucinated")
    
    # Create output directory
    output_dir = Path(__file__).parent / "Fault Information"
    output_dir.mkdir(exist_ok=True)
    
    # Write output
    output_path = output_dir / "fault_information.csv"
    # Replace any NaN with empty strings before writing
    output_df = output_df.fillna('')
    output_df.to_csv(output_path, index=False, quoting=1)  # quoting=1 means QUOTE_ALL
    
    print(f"\nOutput written to: {output_path}")
    print("Integration complete!")


if __name__ == "__main__":
    main()
