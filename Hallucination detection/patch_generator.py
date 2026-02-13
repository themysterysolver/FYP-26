import pandas as pd
import json
import ast
from typing import List, Tuple, Set, Optional

def parse_ast_info(ast_info_str) -> List[int]:
    """
    Parse ast_info field and extract line numbers from 'value' field.
    Returns list of line numbers.
    """
    if pd.isna(ast_info_str) or not ast_info_str or str(ast_info_str).strip() == '':
        return []
    
    try:
        ast_data = json.loads(str(ast_info_str))
        value = ast_data.get('value')
        if value is not None:
            # Convert float to int if needed
            return [int(float(value))]
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        pass
    
    return []

def parse_cfg_info(cfg_info_str) -> List[Tuple[int, int]]:
    """
    Parse cfg_info field and extract (start_line, end_line) tuples.
    Returns list of tuples.
    
    NOTE: COMMENTED OUT FOR NOW - Will be used later
    """
    # COMMENTED OUT - CFG_INFO DISABLED FOR NOW
    return []
    
    # if pd.isna(cfg_info_str) or not cfg_info_str or str(cfg_info_str).strip() == '':
    #     return []
    # 
    # try:
    #     # Use ast.literal_eval for Python-style list/dict strings
    #     cfg_data = ast.literal_eval(str(cfg_info_str))
    #     if isinstance(cfg_data, list):
    #         ranges = []
    #         for item in cfg_data:
    #             if isinstance(item, dict) and 'start_line' in item and 'end_line' in item:
    #                 start = int(item['start_line'])
    #                 end = int(item['end_line'])
    #                 ranges.append((start, end))
    #         return ranges
    # except (ValueError, SyntaxError, KeyError, TypeError):
    #     pass
    # 
    # return []

def parse_lib_info(lib_info_str) -> List[int]:
    """
    Parse lib_info field and extract line numbers from 'line' field.
    Returns list of line numbers.
    """
    if pd.isna(lib_info_str) or not lib_info_str or str(lib_info_str).strip() == '':
        return []
    
    try:
        lib_data = json.loads(str(lib_info_str))
        line = lib_data.get('line')
        if line is not None and line != '':
            # Convert float to int if needed
            return [int(float(line))]
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        pass
    
    return []

def parse_dynamic_info(dynamic_info_str) -> List[int]:
    """
    Parse dynamic_info field and extract line numbers from 'line_no' field.
    Returns list of line numbers.
    """
    if pd.isna(dynamic_info_str) or not dynamic_info_str or str(dynamic_info_str).strip() == '':
        return []
    
    try:
        dynamic_data = json.loads(str(dynamic_info_str))
        line_no = dynamic_data.get('line_no')
        if line_no is not None and line_no != '':
            # Convert float to int if needed
            return [int(float(line_no))]
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        pass
    
    return []

def extract_all_error_lines(row) -> Set[Tuple[int, int]]:
    """
    Extract all error line numbers/ranges from all info fields.
    Returns a set of tuples (start_line, end_line) where single lines have start == end.
    
    NOTE: CFG info parsing is COMMENTED OUT for now
    """
    error_ranges = set()
    
    # Parse AST info - single lines
    ast_lines = parse_ast_info(row['ast_info'])
    for line in ast_lines:
        error_ranges.add((line, line))
    
    # COMMENTED OUT - CFG info parsing disabled for now
    # # Parse CFG info - ranges
    # cfg_ranges = parse_cfg_info(row['cfg_info'])
    # for start, end in cfg_ranges:
    #     error_ranges.add((start, end))
    
    # Parse lib info - single lines
    lib_lines = parse_lib_info(row['lib_info'])
    for line in lib_lines:
        error_ranges.add((line, line))
    
    # Parse dynamic info - single lines
    dynamic_lines = parse_dynamic_info(row['dynamic_info'])
    for line in dynamic_lines:
        error_ranges.add((line, line))
    
    return error_ranges

def generate_patched_code(generated_code: str, error_ranges: Set[Tuple[int, int]]) -> str:
    """
    Generate patched code with error markers inserted around erroneous lines.
    
    Args:
        generated_code: The original generated code
        error_ranges: Set of (start_line, end_line) tuples indicating error locations
    
    Returns:
        Patched code with error markers
    """
    if not generated_code or not error_ranges:
        return generated_code
    
    # Strip leading/trailing whitespace and split into lines
    # This ensures consistent line numbering regardless of CSV storage format
    generated_code = generated_code.strip()
    lines = generated_code.split('\n')
    total_lines = len(lines)
    
    # Sort error ranges by start line
    sorted_ranges = sorted(error_ranges)
    
    # Merge overlapping ranges
    merged_ranges = []
    for start, end in sorted_ranges:
        # Validate line numbers
        if start < 1 or end < 1:
            continue
        if start > total_lines or end > total_lines:
            continue
            
        if merged_ranges and start <= merged_ranges[-1][1] + 1:
            # Overlapping or adjacent - merge
            merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], end))
        else:
            merged_ranges.append((start, end))
    
    # Insert markers in reverse order to maintain line numbers
    patched_lines = lines.copy()
    offset = 0
    
    for start, end in merged_ranges:
        # Adjust for 1-based indexing
        start_idx = start - 1 + offset
        end_idx = end - 1 + offset
        
        # Insert end marker after the error range
        patched_lines.insert(end_idx + 1, '[ERROR FINISH] >>>>')
        
        # Insert start marker before the error range
        patched_lines.insert(start_idx, '<<<< [ERROR START]')
        
        # Update offset for next insertion
        offset += 2
    
    return '\n'.join(patched_lines)

def main():
    print("Loading fault information CSV...")
    fault_df = pd.read_csv(
        'Hallucination detection/Fault Information/fault_information.csv',
        encoding='utf-8'
    )
    
    print(f"Loaded {len(fault_df)} rows from fault_information.csv")
    
    print("\nLoading hallucination master table CSV...")
    master_df = pd.read_csv(
        'APR/ANALYSIS/hallucination_master_table.csv',
        encoding='utf-8'
    )
    
    print(f"Loaded {len(master_df)} rows from hallucination_master_table.csv")
    
    # Merge the dataframes on dataset and task_id
    print("\nMerging dataframes...")
    merged_df = fault_df.merge(
        master_df[['dataset', 'task_id', 'generated_code']],
        on=['dataset', 'task_id'],
        how='left'
    )
    
    print(f"Merged result: {len(merged_df)} rows")
    
    # Initialize patched_code column
    merged_df['patched_code'] = ''
    
    print("\nGenerating patches for hallucinated code...")
    hallucinated_count = 0
    passed_count = 0
    
    for idx, row in merged_df.iterrows():
        if idx % 100 == 0:
            print(f"Processing row {idx}/{len(merged_df)}...")
        
        if row['status'] == 'hallucinated':
            hallucinated_count += 1
            
            # Extract error lines/ranges from all sources
            error_ranges = extract_all_error_lines(row)
            
            # Generate patched code
            generated_code = row.get('generated_code', '')
            if pd.notna(generated_code) and generated_code:
                # Strip generated_code to remove leading/trailing whitespace for consistent line numbering
                generated_code_stripped = str(generated_code).strip()
                patched = generate_patched_code(generated_code_stripped, error_ranges)
                # Store the stripped version in both columns for consistency
                merged_df.loc[idx, 'generated_code'] = generated_code_stripped
                merged_df.loc[idx, 'patched_code'] = patched
            else:
                merged_df.loc[idx, 'patched_code'] = ''
        
        elif row['status'] == 'passed':
            passed_count += 1
            # For passed code, leave patched_code empty
            merged_df.loc[idx, 'patched_code'] = ''
    
    print(f"\nProcessed {hallucinated_count} hallucinated rows")
    print(f"Processed {passed_count} passed rows")
    
    # Write output CSV
    print("\nWriting patched_code.csv...")
    output_path = 'Hallucination detection/patched_code.csv'
    merged_df.to_csv(
        output_path,
        index=False,
        encoding='utf-8',
        quoting=1  # QUOTE_ALL for proper handling of multi-line fields
    )
    
    print(f"Successfully wrote {len(merged_df)} rows to {output_path}")
    
    # Print some statistics
    print("\n=== Statistics ===")
    print(f"Total rows: {len(merged_df)}")
    print(f"Hallucinated rows: {hallucinated_count}")
    print(f"Passed rows: {passed_count}")
    print(f"Rows with generated_code: {merged_df['generated_code'].notna().sum()}")
    print(f"Rows with patched_code: {(merged_df['patched_code'] != '').sum()}")

if __name__ == '__main__':
    main()
