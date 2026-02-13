#!/usr/bin/env python3
"""
Patch Viewer Tool
Simple CLI tool to browse and view patches from patched_code.csv
"""

import pandas as pd
import sys


def view_patch_by_index(df, index):
    """Display a patch by its row index."""
    if index < 0 or index >= len(df):
        print(f"Error: Index {index} out of range (0-{len(df)-1})")
        return
    
    row = df.iloc[index]
    print("=" * 80)
    print(f"PATCH {index + 1} of {len(df)}")
    print("=" * 80)
    print(f"Dataset:        {row['dataset']}")
    print(f"Task ID:        {row['task_id']}")
    print(f"Status:         {row['status']}")
    print(f"Error Source:   {row['error_source']}")
    print(f"Error Type:     {row['error_type']}")
    print(f"Error Lines:    {row['error_line_start']}-{row['error_line_end']}")
    print()
    print("PATCHED CODE:")
    print("-" * 80)
    print(row['patched_code'])
    print("-" * 80)
    print()
    print("FULL GENERATED CODE:")
    print("-" * 80)
    print(row['generated_code'])
    print("-" * 80)


def view_patch_by_task(df, dataset, task_id):
    """Display all patches for a specific task."""
    matches = df[(df['dataset'] == dataset) & (df['task_id'] == task_id)]
    
    if len(matches) == 0:
        print(f"No patches found for {dataset} {task_id}")
        return
    
    print("=" * 80)
    print(f"PATCHES FOR {dataset} {task_id}")
    print("=" * 80)
    print(f"Found {len(matches)} error(s)\n")
    
    for idx, (_, row) in enumerate(matches.iterrows(), 1):
        print(f"Error {idx}:")
        print(f"  Source:   {row['error_source']}")
        print(f"  Type:     {row['error_type']}")
        print(f"  Lines:    {row['error_line_start']}-{row['error_line_end']}")
        print()
        print("  Patched Code:")
        print("  " + "-" * 76)
        for line in row['patched_code'].split('\n'):
            print(f"  {line}")
        print("  " + "-" * 76)
        print()


def show_statistics(df):
    """Display statistics about the patches."""
    print("=" * 80)
    print("PATCH STATISTICS")
    print("=" * 80)
    print(f"Total patches: {len(df)}")
    print()
    
    print("By Dataset:")
    print(df['dataset'].value_counts().to_string())
    print()
    
    print("By Error Source:")
    print(df['error_source'].value_counts().to_string())
    print()
    
    print("By Status:")
    print(df['status'].value_counts().to_string())
    print()
    
    # Tasks with multiple errors
    task_counts = df.groupby(['dataset', 'task_id']).size()
    multiple_errors = task_counts[task_counts > 1]
    print(f"Tasks with multiple errors: {len(multiple_errors)}")
    print()


def search_by_error_type(df, error_type_substring):
    """Search patches by error type."""
    matches = df[df['error_type'].str.contains(error_type_substring, case=False, na=False)]
    
    print("=" * 80)
    print(f"SEARCH RESULTS: '{error_type_substring}'")
    print("=" * 80)
    print(f"Found {len(matches)} match(es)\n")
    
    if len(matches) > 0:
        print("First 10 matches:")
        for idx, (_, row) in enumerate(matches.head(10).iterrows(), 1):
            print(f"{idx}. {row['dataset']} {row['task_id']}: {row['error_type']} (lines {row['error_line_start']}-{row['error_line_end']})")


def main():
    """Main function with interactive menu."""
    # Load the data
    print("Loading patched_code.csv...")
    try:
        df = pd.read_csv('patched_code.csv')
    except FileNotFoundError:
        print("Error: patched_code.csv not found. Run patch_generator.py first.")
        sys.exit(1)
    
    print(f"Loaded {len(df)} patches.\n")
    
    if len(sys.argv) > 1:
        # Command-line mode
        command = sys.argv[1]
        
        if command == 'stats':
            show_statistics(df)
        
        elif command == 'view' and len(sys.argv) > 2:
            index = int(sys.argv[2])
            view_patch_by_index(df, index)
        
        elif command == 'task' and len(sys.argv) > 3:
            dataset = sys.argv[2]
            task_id = sys.argv[3]
            view_patch_by_task(df, dataset, task_id)
        
        elif command == 'search' and len(sys.argv) > 2:
            error_type = sys.argv[2]
            search_by_error_type(df, error_type)
        
        else:
            print("Usage:")
            print("  python3 view_patches.py stats")
            print("  python3 view_patches.py view <index>")
            print("  python3 view_patches.py task <dataset> <task_id>")
            print("  python3 view_patches.py search <error_type>")
    
    else:
        # Interactive mode
        while True:
            print("\n" + "=" * 80)
            print("PATCH VIEWER MENU")
            print("=" * 80)
            print("1. View statistics")
            print("2. View patch by index")
            print("3. View patches for a task")
            print("4. Search by error type")
            print("5. List first 10 patches")
            print("6. Exit")
            print()
            
            choice = input("Enter choice (1-6): ").strip()
            
            if choice == '1':
                show_statistics(df)
            
            elif choice == '2':
                index = int(input("Enter patch index (0-{}): ".format(len(df)-1)))
                view_patch_by_index(df, index)
            
            elif choice == '3':
                dataset = input("Enter dataset (e.g., MBPP, DS1000): ").strip()
                task_id = input("Enter task ID: ").strip()
                view_patch_by_task(df, dataset, task_id)
            
            elif choice == '4':
                error_type = input("Enter error type to search for: ").strip()
                search_by_error_type(df, error_type)
            
            elif choice == '5':
                print("\nFirst 10 patches:")
                for idx in range(min(10, len(df))):
                    row = df.iloc[idx]
                    print(f"{idx}. {row['dataset']} {row['task_id']}: {row['error_source']}: {row['error_type']} (lines {row['error_line_start']}-{row['error_line_end']})")
            
            elif choice == '6':
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")


if __name__ == '__main__':
    main()
