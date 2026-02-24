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


def _find_import_line(code: str, module_name: str) -> Optional[int]:
    """
    Find the line number (1-indexed) of the import for *module_name* in *code*.
    Handles 'import X', 'from X import ...', and submodule patterns like 'X.Y'.
    """
    if pd.isna(code) or not code:
        return None
    base_module = module_name.split('.')[0]
    for i, line in enumerate(code.split('\n'), 1):
        stripped = line.strip()
        if (stripped.startswith('import ') or stripped.startswith('from ')) and base_module in stripped:
            return i
    return None


def _find_first_matplotlib_call(code: str) -> Optional[int]:
    """
    Find the line number (1-indexed) of the first matplotlib/seaborn plotting
    call in *code*.  Returns None if no such call is found.
    """
    import re
    patterns = [
        r'plt\.\w+\(',
        r'fig\s*[,=]',
        r'ax\w*\.plot\(',
        r'ax\w*\.scatter\(',
        r'ax\w*\.bar\(',
        r'ax\w*\.hist\(',
        r'ax\w*\.imshow\(',
        r'sns\.\w+\(',
    ]
    combined = '|'.join(patterns)
    for i, line in enumerate(code.split('\n'), 1):
        if re.search(combined, line):
            return i
    return None


def extract_dynamic_errors(dynamic_info: str, generated_code: str = '') -> List[Tuple[int, int, str]]:
    """
    Extract error line numbers from dynamic_info.
    
    For ModuleNotFoundError the line_no recorded by the dynamic module may
    refer to the *test-harness* code rather than the generated code.  When
    *generated_code* is supplied we validate (and, if necessary, correct)
    the line number so it points to the actual import in the generated code.
    
    Args:
        dynamic_info: JSON string with 'line_no' field
        generated_code: The generated code string (used for validation)
    
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
                line_num = int(float(line_no_str))
                if line_num > 0:
                    error_type = info.get('error_type', 'Dynamic Error')

                    if generated_code and isinstance(generated_code, str):
                        import re
                        error_msg = info.get('error_message', '')

                        # ModuleNotFoundError: verify the module is actually
                        # imported in the generated code.  If not, the error
                        # originates from the test harness -- skip entirely.
                        if error_type == 'ModuleNotFoundError':
                            m = re.search(r"No module named '([^']+)'", error_msg)
                            if m:
                                module_name = m.group(1)
                                correct_line = _find_import_line(generated_code, module_name)
                                if correct_line:
                                    line_num = correct_line
                                else:
                                    return []

                        # AttributeError: if the missing attribute appears in
                        # the generated code, point to that line.  If it
                        # doesn't appear at all the error is from the test
                        # harness -- skip the marker.
                        if error_type == 'AttributeError':
                            m = re.search(r"has no attribute '([^']+)'", error_msg)
                            if m:
                                attr = m.group(1)
                                if attr not in generated_code:
                                    return []
                                for i, line in enumerate(generated_code.split('\n'), 1):
                                    if attr in line:
                                        line_num = i
                                        break

                        if error_type == 'TypeError':
                            m_takes = re.search(
                                r'(\w+)\.(\w+)\(\) takes .+ positional arguments? but (\d+) were given',
                                error_msg
                            )
                            if m_takes:
                                method = m_takes.group(2)
                                if '.' + method + '(' not in generated_code:
                                    return []
                                # Method IS in the code but the code uses
                                # keyword args so the positional count comes
                                # from the test harness's reference call.
                                call_m = re.search(
                                    r'\.' + re.escape(method) + r'\(([^)]*)\)',
                                    generated_code
                                )
                                if call_m and '=' in call_m.group(1):
                                    return []

                            # "Invalid value ... for dtype" on a trivial
                            # assignment like "result = df" -- the error
                            # surfaces during test comparison, not in the
                            # generated code itself.
                            if 'Invalid value' in error_msg and 'dtype' in error_msg:
                                code_lines_list = generated_code.split('\n')
                                if 0 < line_num <= len(code_lines_list):
                                    target_line = code_lines_list[line_num - 1].strip()
                                    if re.match(r'^result\s*=\s*\w+$', target_line):
                                        return []

                        # ValueError about deprecated frequency strings:
                        # point to the .resample() call, not the last line.
                        if error_type == 'ValueError' and 'Invalid frequency' in error_msg:
                            for i, line in enumerate(generated_code.split('\n'), 1):
                                if '.resample(' in line:
                                    line_num = i
                                    break

                        # FigureManager RuntimeError: the traceback line is
                        # unreliable -- point to the first plotting call.
                        if error_type == 'RuntimeError' and 'FigureManager' in error_msg:
                            plt_line = _find_first_matplotlib_call(generated_code)
                            if plt_line:
                                line_num = plt_line

                    return [(line_num, line_num, f"dynamic: {error_type}")]
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Warning: Failed to parse dynamic_info: {dynamic_info[:100]}... Error: {e}")
    
    return []


def generate_patch(code: str, errors: List[Tuple[int, int, str]]) -> Optional[str]:
    """
    Generate the full code with error markers inserted at each error location.
    
    Args:
        code: The generated code
        errors: List of (start_line, end_line, error_type) tuples (1-indexed)
    
    Returns:
        Full code with error markers at each error location, or None if invalid
    """
    if pd.isna(code) or not code:
        return None
    
    lines = code.split('\n')
    total_lines = len(lines)
    
    # Build lookup: line_idx -> markers before/after
    start_markers = {}  # idx -> list of error_type strings
    end_markers = {}    # idx -> list of error_type strings
    
    for start_line, end_line, error_type in errors:
        # Validate line numbers
        if start_line < 1 or end_line < 1 or start_line > total_lines or end_line > total_lines:
            print(f"Warning: Invalid line numbers {start_line}-{end_line} for code with {total_lines} lines")
            continue
        if start_line > end_line:
            print(f"Warning: start_line {start_line} > end_line {end_line}")
            continue

        # If the target line is blank, shift to the nearest non-blank line.
        # Prefer searching upward (the error is usually on the code above
        # a trailing blank), fall back to searching downward.
        if lines[start_line - 1].strip() == '':
            adjusted = None
            for offset in range(1, total_lines):
                up = start_line - offset
                if up >= 1 and lines[up - 1].strip() != '':
                    adjusted = up
                    break
                down = start_line + offset
                if down <= total_lines and lines[down - 1].strip() != '':
                    adjusted = down
                    break
            if adjusted is not None:
                start_line = adjusted
                end_line = adjusted
            else:
                continue
        
        start_markers.setdefault(start_line - 1, []).append(error_type)
        end_markers.setdefault(end_line - 1, []).append(error_type)
    
    # If no valid errors, return None
    if not start_markers:
        return None
    
    # Build the full patched code with markers
    patched_lines = []
    for i, line in enumerate(lines):
        if i in start_markers:
            for et in start_markers[i]:
                patched_lines.append(f"<<<< [ERROR START] ({et})")
        patched_lines.append(line)
        if i in end_markers:
            for et in end_markers[i]:
                patched_lines.append(f"[ERROR FINISH] ({et}) >>>>")
    
    return '\n'.join(patched_lines)


def process_row(row: pd.Series) -> Optional[dict]:
    """
    Process a single row and generate one combined patched code with all errors marked.
    
    Args:
        row: A row from the merged DataFrame
    
    Returns:
        A single dictionary with aggregated error info, or None if no errors found
    """
    # Extract all errors from each source
    all_errors = []  # List of (source, start, end, error_type)
    
    ast_errors = extract_ast_errors(row['ast_info'])
    for start, end, error_type in ast_errors:
        all_errors.append(('ast', start, end, error_type))
    
    # NOTE: CFG errors commented out for now — will be re-enabled later
    # cfg_errors = extract_cfg_errors(row['cfg_info'])
    # for start, end, error_type in cfg_errors:
    #     all_errors.append(('cfg', start, end, error_type))
    
    lib_errors = extract_lib_errors(row['lib_info'])
    for start, end, error_type in lib_errors:
        all_errors.append(('lib', start, end, error_type))
    
    dynamic_errors = extract_dynamic_errors(row['dynamic_info'], row.get('generated_code', ''))
    for start, end, error_type in dynamic_errors:
        all_errors.append(('dynamic', start, end, error_type))
    
    # If no errors found, skip this row
    if not all_errors:
        return None
    
    # Build the list of (start, end, error_type) for generate_full_patch
    error_tuples = [(start, end, etype) for _, start, end, etype in all_errors]
    
    # Generate a single patched code with ALL error markers in the full code
    patched_code = generate_patch(row['generated_code'], error_tuples)
    
    # Skip if patch generation failed
    if patched_code is None:
        return None
    
    # Aggregate error metadata
    error_sources = ','.join(source for source, _, _, _ in all_errors)
    error_types = ','.join(etype for _, _, _, etype in all_errors)
    error_lines = ','.join(f"{start}-{end}" for _, start, end, _ in all_errors)
    
    return {
        'dataset': row['dataset'],
        'status': row['status'],
        'task_id': row['task_id'],
        'ast_info': row['ast_info'],
        'cfg_info': row['cfg_info'],
        'lib_info': row['lib_info'],
        'dynamic_info': row['dynamic_info'],
        'generated_code': row['generated_code'],
        'patched_code': patched_code,
        'error_sources': error_sources,
        'error_types': error_types,
        'error_lines': error_lines
    }


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
    
    # Step 2-4: Process each row and generate combined patches
    print("Step 2-4: Processing rows and generating patches...")
    all_result_rows = []
    
    for idx, row in merged_df.iterrows():
        if idx % 100 == 0:
            print(f"Processing row {idx}/{len(merged_df)}...")
        
        result = process_row(row)
        if result is not None:
            all_result_rows.append(result)
    
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
        'error_sources', 'error_types', 'error_lines'
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
    print()
    print("Done!")


if __name__ == '__main__':
    main()
